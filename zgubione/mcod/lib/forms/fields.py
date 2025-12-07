from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


class PhoneNumberWidget(forms.TextInput):
    def format_value(self, value):
        return value.replace(" ", "") if isinstance(value, str) else ""

    def render(self, name, value, attrs=None, renderer=None):
        return "+48 %s" % super().render(name, value, attrs, renderer)


class PhoneNumberField(forms.CharField):
    widget = PhoneNumberWidget
    default_validators = [RegexValidator(r"^\d{7,9}$")]

    def __init__(self, *, strip=True, empty_value="", **kwargs):
        super().__init__(min_length=7, max_length=9, strip=strip, empty_value=empty_value, **kwargs)

    def prepare_value(self, value):
        if value:
            if value[:3] == "+48":
                return value[3:]
            if value[:4] == "0048":
                return value[4:]
        return value

    def clean(self, value):
        value = super().clean(value)
        if value:
            return "0048%s" % value
        return None


class InternalPhoneNumberWidget(forms.TextInput):
    def __init__(self, attrs=None):
        super().__init__(attrs)
        self.attrs["style"] = "width: 5em;"


class InternalPhoneNumberField(forms.CharField):
    widget = InternalPhoneNumberWidget
    default_validators = [RegexValidator(r"^\d{1,4}$")]

    NoMainNumberError = forms.ValidationError(_("Internal number cannot be given without the main number"))

    def clean(self, value):
        value = super().clean(value)
        return value or None
