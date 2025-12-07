from django import forms
from django.contrib.admin.widgets import AdminDateWidget
from django.utils.translation import gettext_lazy as _

from mcod.core.widgets import UnescapeTextInput
from mcod.newsletter.models import Newsletter


class PlannedSendingDateWidget(AdminDateWidget):
    class Media(AdminDateWidget.Media):
        css = {"screen": ("admin/css/admin_date_widget_without_today_btn.css",)}


class NewsletterAdminForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = "__all__"
        labels = {
            "title": _("Title of newsletter"),
        }
        widgets = {"planned_sending_date": PlannedSendingDateWidget, "title": UnescapeTextInput()}
