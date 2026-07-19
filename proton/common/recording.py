"""
recording.py is for data collection via a device, that doesn't depend on what device it is getting data from. 
It polls a read function on a clock and streams each sample to a csv, flushing as it goes long, so that any device can
return one sample at a time and can be recorded the same way.

This is so that
     1.) There is a way to use many different polled hardware devices (if using detectors to collect data for PROTON)
     2.) If a device disconnects at any point, the data collected so far isn't lost
"""

import csv
import sys
import time
from pathlib import Path
from proton.common.exceptions import ProtonError

def _report_outcome(status, written, error, duration, out_path, noun):
    """Prints the one line that says how a recording run actually ended.

    A caught exception always reads as a failure on stderr, exception message included, since
    a run that stopped after a few minutes must never look like it ran the full hour. Zero rows
    with no exception gets its own wording too, since a run that quietly gathered nothing used
    to print the same "wrote 0" line a real, empty run would. A KeyboardInterrupt already prints
    its own line where it is caught, so status "interrupted" has nothing more to add here.
    """
    if status == "stopped":
        print(f"recording stopped early after {written} {noun}: {error}", file = sys.stderr)
    elif status == "completed" and written == 0:
        # the loop ran its course but never got one successful read
        print(f"recording produced no {noun}: the device returned nothing before recording ended", file = sys.stderr)
    elif status == "completed":
        print(f"recording finished the full run: {written} {noun} written over {duration} seconds")
    print("wrote", written, noun, "to", out_path)

def record_samples(read_one, out_path, duration, poll_interval, fields = None):
    """
    This polls read_one once per interval for up to the duration seconds and writes
    each sample to out_path.

    read_one is any zero argument callable, that returns one sample with
    named fields (so RadProDevice.read_raw_samples fits, and so does your
    own function for some other device in the use of alternative hardware).

    fields names the csv columns, and if you were to leave it out, the function
    takes them off the sample itself when that sample is a namedtuple.

    the caller essentially owns the device, this only borrows its read function,
    so you keep your device in its own block around this call.

    Every row is flushed the moment it is read, so this also ensures that
    your data doesn't dissapear if there were a crash

    An early stop from a caught OSError or ProtonError always prints to stderr as a failure,
    exception included, so it can never read like a completed run. A full run and a run that
    wrote nothing each get their own distinct line too (see _report_outcome).
    """
    out_path = Path(out_path) # checks that folder is there before trying to open a file inside it
    out_path.parent.mkdir(parents = True, exist_ok = True)
    cols = fields
    writer = None
    written = 0
    status = "completed" # stays this way unless one of the excepts below says otherwise
    error = None
    with out_path.open("w", newline = "") as f:
        start = time.monotonic()
        next_poll = start
        try:
            while time.monotonic() - start < duration:
                sample = read_one()
                if cols is None:
                    # the first sample settles the columns and writes the header
                    cols = sample._fields
                if writer is None:
                    # if the caller did not name the fields, we take them off the sample, which work  for any namedtuple
                    writer = csv.writer(f)
                    writer.writerow(cols)
                writer.writerow([getattr(sample, c) for c in cols]) # the row will follow the same order as the header
                f.flush() # writes the row to disk now instead of leaving it in the buffer
                written += 1
                next_poll += poll_interval
                now = time.monotonic()
                if now < next_poll:
                    time.sleep(next_poll - now) # still time left, so sleep the remaindeer to hold the cadence
                else:
                    next_poll = now # a read ran long and we fell behind, so resync instead of trying to catch up later
        except KeyboardInterrupt:
            # When stopped on purpose, every row up to here will be already saved
            status = "interrupted"
            print("Stopped early 0-0")

        except (OSError, ProtonError) as problem:
            # The device disconnected or a read failed partway through.
            # Rows written are safe, _report_outcome below prints this with the exception
            status = "stopped"
            error = problem

        _report_outcome(status, written, error, duration, out_path, "rows")
        return written

def record_snapshot(read_one, out_path, duration, poll_interval, write):
    """
    Polls read_one once per interval for up to duration seconds, and writes each snapshot out
    to out_path with write(sample, out_path). Every write replaces the last one, so out_path
    always holds the latest full read rather than a growing history of them.

    I wrote this for a sample that does not fit one csv row, a spectrum's whole histogram for
    instance, where record_samples would have to flatten or serialize it into a single cell.
    write posesses the file format entirely (your own format, headers and all), so this function
    only deals with the polling and the partial run handling, the same job record_samples
    does for row based samples. TLDR, this is works for spectrum/continuous data.

    An early stop from a caught OSError or ProtonError always prints to stderr as a failure,
    exception included, so it can never read like a completed run. A full run and a run that
    quietly wrote nothing each get their own distinct line too (see _report_outcome).
    """
    written = 0
    status = "completed" # stays this way unless one of the excepts below says otherwise
    error = None
    start = time.monotonic()
    next_poll = start
    try:
        while time.monotonic() - start < duration:
            sample = read_one()
            write(sample, out_path)
            written += 1
            next_poll += poll_interval
            now = time.monotonic()
            if now < next_poll:
                time.sleep(next_poll - now) # still time left, so sleep the remainder to hold the cadence
            else:
                next_poll = now # a read ran long and we fell behind, so resync instead of trying to catch up later
    except KeyboardInterrupt:
        # when stopped on purpose, the last snapshot written is already on disk
        status = "interrupted"
        print("Stopped early 0-0")

    except (OSError, ProtonError) as problem:
        # the device disconnected or a read failed partway through, the last snapshot is still safe
        # _report_outcome below prints this with the exception
        status = "stopped"
        error = problem

    _report_outcome(status, written, error, duration, out_path, "snapshots")
    return written

def record_device(device_cls, out_path, fields = None, duration = 3600, poll_interval = None, **device_kwargs):
    """opens device_cls, records a run to out_path, and falls back to the device's own defaults.

    device_kwargs forwards straight to device_cls's constructor. I made it a catch all kwarg
    instead of a fixed port argument, so this works for a device that opens a port, one that
    opens no hardware at all, and anything in between. Pass port = ... for a serial device the
    same as before, or nothing for a general device that needs no arguments.
    """
    if poll_interval is None:
        poll_interval = device_cls.DEFAULT_POLL_INTERVAL
    with device_cls(**device_kwargs) as device:
        print("recording from", device.get_device_id())
        return record_samples(
            read_one = device.read_raw_sample,
            out_path = out_path,
            duration = duration,
            poll_interval = poll_interval,
            fields = fields
        )
    