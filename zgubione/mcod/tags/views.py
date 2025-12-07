from django.contrib.admin.views.autocomplete import AutocompleteJsonView


class TagAutocompleteJsonView(AutocompleteJsonView):
    def get(self, request, *args, **kwargs):
        self.language = request.GET.get("lang", "pl")
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(language=self.language)
