from dal import autocomplete
from django import forms
from django.contrib.admin import forms as admin_forms
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.contrib.auth import forms as auth_forms
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from suit.widgets import SuitDateWidget, SuitTimeWidget

from mcod import settings
from mcod.lib.forms.fields import InternalPhoneNumberField, PhoneNumberField
from mcod.lib.widgets import CKEditorWidget
from mcod.users.models import Meeting, User


class FilteredSelectMultipleCustom(FilteredSelectMultiple):
    template_name = "widgets/select_custom.html"

    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"
        js = [
            "vendor/jquery/jquery%s.js" % extra,
            "jquery.init.js",
            "core.js",
            "SelectBox.js",
            "SelectFilter2_custom.js",
        ]
        return forms.Media(js=["admin/js/%s" % path for path in js])


class MeetingForm(forms.ModelForm):

    class Meta:
        model = Meeting
        fields = [
            "title",
            "venue",
            "description",
            "start_date",
            "start_time",
            "end_time",
            "status",
            "members",
        ]
        labels = (
            {
                "title": _("Meeting name"),
            },
        )
        widgets = {
            "start_date": SuitDateWidget,
            "start_time": SuitTimeWidget,
            "end_time": SuitTimeWidget,
            "description": CKEditorWidget,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("title", "venue", "description"):
            if name in self.fields:
                self.fields[name].widget.attrs.update({"class": "span12"})


class RadioSelect(forms.widgets.RadioSelect):
    template_name = "admin/users/user/radio.html"


class GovLinkedWidget(forms.Widget):
    """Widget for changing form field to string."""

    def render(self, name, value, attrs=None, renderer=None):
        val = mark_safe(value)
        return _("Yes" if val == "True" else "No")


class UserForm(forms.ModelForm):
    phone = PhoneNumberField(label=_("Phone number"), required=False)
    phone_internal = InternalPhoneNumberField(label=_("int."), required=False)
    is_academy_admin = forms.BooleanField(label=_("Admin AOD"), required=False)
    is_labs_admin = forms.BooleanField(label=_("Admin LOD"), required=False)
    is_agent_opts = forms.ChoiceField(
        choices=(("new", _("New permissions")), ("from_agent", _("Copy from agent"))),
        label="",
        required=False,
        widget=RadioSelect,
        initial="new",
    )
    from_agent = forms.ModelChoiceField(
        queryset=User.objects.agents().order_by("email"),
        widget=autocomplete.Select2(url="agent-autocomplete"),
        required=False,
        label="",
        help_text=_("(Select of agent is required)"),
    )
    is_gov_linked = forms.CharField(label=_("WK logging"), required=False, disabled=True, widget=GovLinkedWidget)

    class Meta:
        model = User
        fields = "__all__"
        help_texts = {
            "agent_organization_main": _("(Select of institution is required)"),
            "is_staff": _("(Select of institution is not required. Lack of choice makes possible to login to admin panel also.)"),
            "is_superuser": "",
        }
        labels = {
            "is_superuser": _("Admin"),
        }

    class Media:
        js = [
            "admin/js/SelectBoxCustom.js",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            if "is_gov_linked" in self.fields:
                self.fields["is_gov_linked"].initial = self.instance.is_gov_linked
            if "is_academy_admin" in self.fields:
                self.fields["is_academy_admin"].initial = self.instance.is_academy_admin
            if "is_labs_admin" in self.fields:
                self.fields["is_labs_admin"].initial = self.instance.is_labs_admin
            if "extra_agent_of" in self.fields:
                qs = self.fields["extra_agent_of"].queryset.exclude(id=self.instance.pk)
                self.fields["extra_agent_of"].queryset = qs

    def clean_phone_internal(self):
        if self.cleaned_data["phone_internal"] and not self.cleaned_data.get("phone"):
            raise InternalPhoneNumberField.NoMainNumberError
        return self.cleaned_data["phone_internal"]

    def clean(self):  # noqa: C901
        data = super().clean()
        required_msg = _("This field is required!")
        agent_organizations = data.get("agent_organizations")
        agent_org_main = data.get("agent_organization_main")
        is_agent = data.get("is_agent")
        is_agent_opts = data.get("is_agent_opts")
        from_agent = data.get("from_agent")
        extra_agent_of = data.get("extra_agent_of")
        if is_agent:
            if is_agent_opts == "from_agent":
                if not from_agent:
                    self.add_error("from_agent", required_msg)
                data.pop("agent_organizations", None)
            if is_agent_opts in [None, "", "new"]:
                if not agent_organizations:
                    self.add_error(
                        "agent_organizations",
                        _("Organization selection for an agent is obligatory!"),
                    )
                if not agent_org_main:
                    self.add_error("agent_organization_main", required_msg)
            if agent_org_main and agent_org_main not in agent_organizations:
                self.add_error(
                    "agent_organization_main",
                    _("Selected institution must be on selected institutions list!"),
                )
            if extra_agent_of:
                data["extra_agent_of"] = None
        else:
            if agent_organizations:
                data["agent_organizations"] = []
            if agent_org_main:
                data["agent_organization_main"] = None

        is_staff = data.get("is_staff")
        if is_staff is None and self.instance:
            is_staff = self.instance.is_staff

        is_academy_admin = data.get("is_academy_admin")
        is_labs_admin = data.get("is_labs_admin")
        is_superuser = data.get("is_superuser")
        if any([is_academy_admin, is_labs_admin, is_superuser]):
            is_staff = True  # ensure is_staff even if checkbox in form was disabled by jquery.
            data["is_staff"] = True
        if not is_staff:
            data["organizations"] = []
        return data

    def save(self, commit=True):
        super().save(commit=False)
        if commit:
            self.instance.save()
        if self.instance.pk and "organizations" in self.cleaned_data:
            self.instance.organizations.set(self.cleaned_data["organizations"])
        return self.instance


class UserCreationForm(UserForm):
    error_messages = {
        "password_mismatch": _("The two password fields didn't match."),
    }
    password1 = forms.CharField(label=_("Password"), widget=forms.PasswordInput)
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput,
        help_text=_("Enter the same password as above, for verification."),
    )

    class Meta(UserForm.Meta):
        fields = [
            "email",
            "fullname",
            "phone",
            "phone_internal",
            "is_agent",
            "is_staff",
            "is_superuser",
            "state",
            "organizations",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in [
            "email",
            "password1",
            "password2",
        ]:  # https://stackoverflow.com/a/32578659/1845230
            self.fields[name].widget.attrs["readonly"] = True
            self.fields[name].widget.attrs["onfocus"] = "this.removeAttribute('readonly');"

    def clean_email(self):
        email = self.data.get("email", "")
        if email and User.objects.filter(email__iexact=email).exists():
            self.add_error("email", _("Account for this email already exist"))
        return self.data.get("email", "").lower()

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError(
                self.error_messages["password_mismatch"],
                code="password_mismatch",
            )
        return password2

    def save(self, commit=True):
        super().save(commit=False)
        self.instance.set_password(self.cleaned_data["password1"])
        if commit:
            self.instance.save()
        if self.instance.pk:
            self.instance.organizations.set(self.cleaned_data["organizations"])
        return self.instance


class UserChangeForm(UserForm):
    password = auth_forms.ReadOnlyPasswordHashField(
        label=_("Password"),
        help_text=_(
            "Raw passwords are not stored, so there is no way to see "
            "this user's password, but you can change the password "
            'using <a href="../password/">this form</a>.'
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        f = self.fields.get("user_permissions", None)
        if f is not None:
            f.queryset = f.queryset.select_related("content_type")
        if all(
            [
                "state" in self.fields,
                hasattr(self, "_request_user") and self._request_user.is_superuser,
                self.instance.state == "pending",
            ]
        ):
            url = self.instance.send_registration_email_admin_url
            txt = _("Resend the account activation link")
            self.fields["state"].help_text = f'<a href="{url}">{txt}</a>'

    def clean_password(self):
        return self.initial["password"] if "password" in self.initial else None


class AdminLoginForm(admin_forms.AdminAuthenticationForm):
    error_messages = {
        **admin_forms.AdminAuthenticationForm.error_messages,
        "confirm_email": _("You should confirm your email before logging in."),
        "blocked": _("This user is blocked, please contact the administrators."),
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

        super().confirm_login_allowed(user)
