from typing import Optional

from django.core.exceptions import ValidationError


class PendingValidationException(ValidationError):
    def __init__(self, message: Optional[str] = None):
        if message is None:
            message = "Pending validation(s)."
        super().__init__(message)


class FailedValidationException(ValidationError):
    def __init__(self, message: Optional[str] = None):
        if message is None:
            message = "Failed validation(s)."
        super().__init__(message)
