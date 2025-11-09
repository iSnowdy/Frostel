class FrostelException(Exception):
    """Base exception class for Frostel application."""

    pass


class CircuitBreakerException(FrostelException):
    """Base exception class for Circuit exceptions."""

    pass
