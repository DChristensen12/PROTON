
class ProtonError(Exception):
    """The base for every error PROTON raises. Catch this to handle anything from the library in one place."""

    def __init__(self, message):
        """Keeps the failed command and the raw reply on the error so we can see what went wrong"""
        super().__init__(message)
        self.message = message # what went wrong