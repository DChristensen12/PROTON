"""recording.py is for the part of data collection that doesn't care about
what device it is getting data from. It polls a read function on a clock and streams
each sample to a csv, flushing as it goes long, so that any device can
hand back one sample at a time and can be recorded the same way

This is so that
1.) There is a way to use many different polled hardware devices (if using detectors for proton)
2.) If the device disconnects at any point, the data collected so far isn't lost
"""

import csv
import time
from pathlib import Path
from proton.common.exceptions import ProtonError

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
    """
    out_path = Path(out_path) # checks that folder is there before trying to open a file inside it
    out_path.parent.mkdir(parents = True, exist_ok = True)
    cols = fields
    writer = None
    written = 0
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
                f.flush() # write the row to disk now instead of leaving it in the buffer
                written += 1
                next_poll += poll_interval 
                now = time.monotonic()
                if now < next_poll: 
                    time.sleep(next_poll - now) # still time left, so sleep the remaindeer to hold the cadence
                else:
                    next_poll = now # a read ran long and we fell behind, so resync instead of trying to catch up later
        except KeyboardInterrupt:
            # When stopped on purpose, every row up to here will be already saved
            print("Stopped early 0-0")

        except (OSError, ProtonError) as problem:
            # The device dropped out or stopped answering partway through. 
            # Rows written are safe, just reports it now and keep data collected thus far
            print("The device stopped partway through, keeping what was saved:",  problem)
        
        print("wrote", written, "samples to", out_path)
        return written

def record_device(device_cls, out_path, fields = None, duration = 3600, port = None, poll_interval = None):
    """opens device_cls, records a run to out_path, and falls back to the device's own defaults."""
    if poll_interval is None:
        poll_interval = device_cls.DEFAULT_POLL_INTERVAL # The port stays None when unset, so the device fills in its own DEFAULT_PORT
    with device_cls(port = port) as device:
        print("recording from", device.get_device_id())
        return record_samples(
            read_one = device.read_raw_sample,
            out_path = out_path,
            duration = duration,
            poll_interval = poll_interval,
            fields = fields
        )
    