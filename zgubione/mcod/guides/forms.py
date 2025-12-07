from django import forms
from django.utils.translation import gettext_lazy as _

from mcod.guides.models import Guide, GuideItem


class GuideForm(forms.ModelForm):
    class Meta:
        model = Guide
        fields = ["title", "status"]
        labels = {
            "title": _("Name of course (PL)"),
            "title_en": _("Name of course (EN)"),
            "status": "Status",
        }


class GuideItemForm(forms.ModelForm):
    class Meta:
        model = GuideItem
        fields = [
            "title",
            "content",
            "route",
            "css_selector",
            "position",
            "is_optional",
            "is_clickable",
            "is_expandable",
        ]
        labels = {
            "title": _("Title (PL)"),
            "title_en": _("Title (EN)"),
            "content": _("Content"),
            "position": _("Display at"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in [
            "title",
            "title_en",
            "content",
            "content_en",
            "route",
            "css_selector",
        ]:
            if name in self.fields:
                self.fields[name].widget.attrs.update({"class": "input-block-level"})
                if name in ["content", "content_en"]:
                    self.fields[name].widget.attrs.update({"rows": "3"})
