# This is taking a while, I will reconsider if I need to test it this much. As you can see outlined below, it was going to take a while.


import pytest
from proton.Hardware.Detectors.geiger_counts.readout import (
    RawSample,
    GeneralCountsDevice,
)


class TestRawSampleContract:
    """Tests relating to the RawSamples in readout.py"""
    def test_field_order(self):
        """The column order is a contract the recorder and csv both rely on, so this is just a normal test"""
        assert RawSample._fields == ("pulse_count", "tube_rate", "wall_time", "monotonic")
    
    def test_fields_match_the_device(self):
        """GeneralCountsDevice will write and read by these names, so they have to match the sample"""
        assert GeneralCountsDevice.FIELDS == RawSample._fields

"""
class TestShowRawReplies:

class TestParity:

class TestRadProDevice:

class TestRadProError:

class TestGeneralCountsReplay:
"""