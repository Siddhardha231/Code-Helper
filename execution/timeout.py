class TimeoutException(Exception):
    """Raised when an execution exceeds the allotted time limit."""
    pass


DEFAULT_TIMEOUT_SECONDS: int = 30
