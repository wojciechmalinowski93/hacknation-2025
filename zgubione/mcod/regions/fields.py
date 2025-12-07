from dal_select2.widgets import Select2Multiple
from django import forms


class RegionsMultipleChoiceField(forms.MultipleChoiceField):
    widget = Select2Multiple(
        url="regions-autocomplete",
        attrs={"data-minimum-input-length": 3, "style": "width: 50%", "rows": 2},
    )

    def validate(self, value):
        """Do not validate choices but check for empty."""
        super(forms.ChoiceField, self).validate(value)
