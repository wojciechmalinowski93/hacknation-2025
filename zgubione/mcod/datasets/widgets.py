from django.forms import CheckboxInput, TextInput


class LabelMixin:
    def __init__(self, *args, label=None, **kwargs):
        self.label = label
        self.style = kwargs.pop("style", None)
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["label"] = self.label
        context["style"] = self.style
        return context


class CheckboxInputWithLabel(LabelMixin, CheckboxInput):
    template_name = "widgets/checkbox_labeled.html"


class TextInputWithLabel(LabelMixin, TextInput):
    template_name = "widgets/text_labeled.html"
