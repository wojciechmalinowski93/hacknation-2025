import base64
import binascii

from django.core.validators import RegexValidator
from django.utils.html import strip_tags
from marshmallow import ValidationError
from marshmallow.validate import Validator


class Base64(Validator):
    default_base64_error = "Invalid data format for base64 encoding."
    default_length_error = "Too long data."

    def __init__(self, max_size=None, base64_error=None, length_error=None):
        self.base64_error = base64_error or self.default_base64_error
        self.length_error = length_error or self.default_length_error
        self.max_size = max_size

    def __call__(self, value):
        data = value.split(";base64,")[-1].encode("utf-8")
        try:
            data = base64.b64decode(data)
        except binascii.Error:
            raise ValidationError(self.base64_error)
        if self.max_size:
            if len(data) > self.max_size:
                raise ValidationError(self.length_error)
        return value


class ContainsLetterValidator(RegexValidator):
    regex = r"[^\W\d_]+"
    message = "Upewnij się, że ta wartość zawiera przynajmniej jedną literę."

    def __call__(self, value):
        return super().__call__(strip_tags(value))
