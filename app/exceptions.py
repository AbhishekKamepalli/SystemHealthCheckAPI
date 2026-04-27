"""Custom exceptions used by the health evaluation API."""


class ValidationError400(Exception):
    """Raised when request data fails domain-specific validation."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)
