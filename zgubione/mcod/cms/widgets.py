from django import forms


class ColorPickerWidget(forms.TextInput):
    input_type = "color"

    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = "#ffffff"
        rendered = super().render(name, value, attrs, renderer)
        return rendered
