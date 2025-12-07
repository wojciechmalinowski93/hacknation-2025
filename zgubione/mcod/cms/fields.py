from django import forms
from django.db import models


class CustomTextField(models.TextField):
    def formfield(self, **kwargs):
        kwargs["widget"] = forms.Textarea(attrs={"cols": "75", "rows": "2"})
        return super().formfield(**kwargs)
