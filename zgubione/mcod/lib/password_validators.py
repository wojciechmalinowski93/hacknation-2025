from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from mcod import settings


class McodPasswordValidator:
    def validate(self, password, user=None):
        special_characters = settings.SPECIAL_CHARS
        if not any(char.isdigit() for char in password):
            raise ValidationError(
                _("Password must contain at least one digit."),
                code="password_no_digit",
            )
        if password.lower() == password or password.upper() == password:
            raise ValidationError(
                _("Password must contain at least one upper and one lower letter."),
                code="password_wrong_case",
            )
        if not any(char in special_characters for char in password):
            raise ValidationError(
                _("Password must contain at least one special character."),
                code="password_no_special",
            )

    def get_help_text(self):
        return _("Your password must contain at least: one digit, one special char, one upper and one lower letter")
