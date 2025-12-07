from django import forms

from mcod.special_signs.models import SpecialSign


class SpecialSignAdminForm(forms.ModelForm):

    class Meta:
        model = SpecialSign
        fields = ("symbol", "name", "description", "status")
