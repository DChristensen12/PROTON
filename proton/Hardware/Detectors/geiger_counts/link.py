# This scirpt contains everything relating to a geiger counter that produces serial outputs (linking to a device and bringing in data).

import csv
import time
from typing import NamedTuple
import serial
from pathlib import Path

class RawSample(NamedTuple):
    """Pulls one raw reading off a dvice, stampled with when it is read"""
    pulse_count: int # the running total of pulses the tube has counted, the real raw signal
    tube_rate: float # the rate the device reports itself in cpm
    wall_time: float # unix time
    monotonic: float # a clock that never jumps back, used for intervals

#class GeneralGCDevice:
"""For those who use a different hardware device, you can match it to
this class. It is the General Geiger Counts Device Class."""


class RadProDevice:
    """ Wrapper around the Rad Pro serial protocal"""

    DEFAULT_PORT = "/dev/ttyACM1" # This is where GC-01 lands on my machine, could also be /dev/ttyACM0
    BAUD_RATE = 115200 # pyserial asks for one of these, so we use the value from the firmware documents
    SERIAL_TIMEOUT = 2.0 # how long one read waits before I'd call the device silent, in seconds
    DEFAULT_POLL_INTERVAL = 1.0 #how often the logger polls the cumulative pulse count, in seconds
    FALLBACK_SENSITIVITY_CPM_PER_USVH = 153.8 # M4011 tube sensitivity in cpm per uSv/h. Used as a display fallback when the device cannot report its own calibrated valye.

    __slots__ = ("_port_name", "_serial")

    def __init__(self, port = None, baud = None, timeout = None, serial_port = None):
        """
        Opens the serial port to the device, or use a port object passed in.
        We fall back to the class defaults when the caller leaves an argument out.
        """

        port = port if port is not None else self.DEFAULT_PORT
        baud = baud if baud is not None else self.BAUD_RATE
        timeout = timeout if timeout is not None else self.SERIAL_TIMEOUT
        self._port_name = port
        if serial_port is not None:
            self._serial = serial_port # Use object handed to it
        else:
            self._serial = serial.Serial(port, baudrate = baud, timeout = timeout)

    def __enter__(self):
        """Lets you use the device in a with block"""
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        """Always close the port on the way out, even when something has failed."""
        self.close()

    def close(self):
        """Closes the serial port if it still open when called"""
        if self._serial is not None and self._serial.is_open:
            self._serial.close()
        
    def _command(self, command):
        """Sends one command and returns the raw text the device replies with.

        The device could possibly send a stray blank line, not sure if it prefixes
        replies with OK, so I handle both and let the peek function below show me the real format."""

        # We clear anything sitting in the buffer first so an old reply cannot bleed into this one.
        self._serial.reset_input_buffer()
        self._serial.write((command + "\n").encode("ascii"))

        for _ in range(4):
            line = self._serial.readline().decode("ascii", errors = "replace").strip()
            if line == "":
                continue # that means there is a stray blank line, so read the next one
            if line.startswith("ERROR"):
                raise RadProError("device returned:" + line)
            if line == "OK":
                continue # the valye is on the next line, so keep reading
            if line.startswith("OK "):
                return line[3:].strip() # drop the OK prefix and keep the value
            return line
        raise RadProError("no usable response to command: " + command)
    
    def _peek(port = DEFAULT_PORT):
        """Temp function to see what the device sends back"""

    def get_device_id(self):
        """Asks the device who it is to confirm we are talking to the right one"""
        return self._command("GET deviceId")
    
    def get_pulse_count(self):
        """Reads the running total of pulses the tube has counted thus far"""
        return int(self._command("GET tubePulseCount"))
    
    def get_tube_rate(self):
        """Reads the rate the device reports for itself, in counts per minute"""
        return float(self._command("GET tubeRate"))
    
    def read_raw_sample(self):
        """
        Pulls one timestamped raw sample off the device.
        
        We grab both clocks first, so the timestamps sit as close as it could be to 
        the actual read, then pull the count and device rate.
        """
        Wall_time = time.time()
        Monotonic = time.monotonic()
        Pulse_count = self.get_pulse_count()
        Tube_rate = self.get_tube_rate()
        return RawSample(pulse_count = Pulse_count, tube_rate = Tube_rate, wall_time = Wall_time, monotonic = Monotonic)
    


class RadProError(Exception):
    """If the device says ERROR, went quiet, or 
    sends something I cannot parse."""
    
    def __init__(self, *args):
        super().__init__(*args)


