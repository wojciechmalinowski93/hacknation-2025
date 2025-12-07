from django.contrib.admin.widgets import AutocompleteSelectMultiple, RelatedFieldWidgetWrapper


class TagAutocompleteSelectMultiple(AutocompleteSelectMultiple):
    def __init__(self, *args, **kwargs):
        self.language = kwargs.pop("language")
        super().__init__(*args, **kwargs)

    def get_url(self):
        return super().get_url() + f"?lang={self.language}"


class TagRelatedFieldWidgetWrapper(RelatedFieldWidgetWrapper):
    def __init__(self, *args, **kwargs):
        self.language = kwargs.pop("language")
        super().__init__(*args, **kwargs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["url_params"] += f"&lang={self.language}"
        return context
