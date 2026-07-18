"""Tests for exceptions.py. ProtonError is what the recorder catches to keep data already collected."""

import pytest
from proton.common.exceptions import ProtonError


class TestProtonError:
    """Tests for ProtonError."""
    def test_keeps_the_message(self):
        """Test that ProtonError stores the message on .message."""
        assert ProtonError("something broke").message == "something broke"

    def test_str_is_the_message(self):
        """Test that str on the error returns the message, the same as a normal exception."""
        assert str(ProtonError("KABOOM")) == "KABOOM"

    def test_is_a_real_exception(self):
        """Test that ProtonError subclasses Exception and can be raised and caught."""
        assert issubclass(ProtonError, Exception)
        with pytest.raises(ProtonError):
            raise ProtonError("x")
