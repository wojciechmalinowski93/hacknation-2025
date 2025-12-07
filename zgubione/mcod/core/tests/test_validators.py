import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import (
    get_default_password_validators,
    validate_password,
)
from django.core.exceptions import ValidationError
from marshmallow.validate import ValidationError as mmValidationError

from mcod.lib import field_validators


@pytest.mark.run(order=0)
def test_invalid_passwords(invalid_passwords_with_user):
    u = get_user_model()(email="aaa@bbb.cc", fullname="Test User")
    for password in invalid_passwords_with_user:
        with pytest.raises(ValidationError):
            validate_password(password, user=u)


@pytest.mark.run(order=0)
def test_valid_passwords(valid_passwords):
    u = get_user_model()(email="aaa@bbb.cc", fullname="Test User")
    for password in valid_passwords:
        assert validate_password(password, user=u) is None


@pytest.mark.run(order=0)
def test_password_validators_help_text():
    validators = get_default_password_validators()
    for validator in validators:
        assert len(validator.get_help_text()) > 0


@pytest.mark.run
class TestFieldsValidators:
    def test_base64_validator(self, base64_image):
        validator = field_validators.Base64()
        with pytest.raises(mmValidationError) as e:
            validator("123")
        assert e.value.messages[0] == field_validators.Base64.default_base64_error

        image, img_size = base64_image

        validator = field_validators.Base64(max_size=img_size - 1)

        with pytest.raises(mmValidationError) as e:
            validator(image)
        assert e.value.messages[0] == field_validators.Base64.default_length_error

        validator = field_validators.Base64(max_size=img_size - 1, base64_error="Ala ma kota", length_error="Kot ma alę")
        with pytest.raises(mmValidationError) as e:
            validator("123")
        assert e.value.messages[0] == "Ala ma kota"

        with pytest.raises(mmValidationError) as e:
            validator(image)
        assert e.value.messages[0] == "Kot ma alę"

        validator = field_validators.Base64(max_size=img_size)
        assert validator(image) == image
