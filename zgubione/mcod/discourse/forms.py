from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from mcod.users.forms import AdminLoginForm


class ForumLoginForm(AdminLoginForm):
    error_messages = {
        **AdminLoginForm.error_messages,
        "forum_login": _("Only administrators and agents have access to forum"),
    }

    def confirm_login_allowed(self, user):
        if user.state == "pending":
            raise ValidationError(
                self.error_messages["confirm_email"],
                code="confirm_email",
            )
        elif user.state == "blocked":
            raise ValidationError(
                self.error_messages["blocked"],
                code="blocked",
            )
        if not user.is_active:
            raise forms.ValidationError(
                self.error_messages["inactive"],
                code="inactive",
            )
        if not user.has_access_to_forum:
            raise ValidationError(self.error_messages["forum_login"], code="forum_login")
