# This file tests for everything relating to the exceptions file
# Proton Error is what the recorder catches to keep data, so its important this works.

import pytest
from proton.common.exceptions import ProtonError


class TestProtonError:
    """Tests ProtonError. :)"""
    def test_keeps_the_message(self):
        """We stash the message on the error so that callers can
        just read it back off the object"""
        assert ProtonError("something broke").message == "something broke"

    def test_str_is_the_message(self):
        """printing the error should just show the message, the same as a normal exception"""
        assert str(ProtonError("KABOOM")) == "KABOOM"

    def test_is_a_real_exception(self):
        """ProtonError has to subclass Exception, so it can actually be raised and caught."""
        assert issubclass(ProtonError, Exception)
        with pytest.raises(ProtonError):
            raise ProtonError("x")