from django.contrib import admin
from django.db.models import Case, CharField, Value, When
from django.forms import ModelForm, ValidationError
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from suit.widgets import SuitSplitDateTimeWidget

from mcod.alerts.models import DISPLAY_STATUS, Alert
from mcod.core.widgets import UnescapeTextarea
from mcod.lib.admin_mixins import ModelAdmin
from mcod.lib.widgets import CKEditorWidget


class DisplayStatusFilter(admin.SimpleListFilter):
    title = _("Display")
    parameter_name = "display_status"
    qs_param = "display_status"

    def lookups(self, request, model_admin):
        result = [(key, item[-1]) for key, item in DISPLAY_STATUS.items()]
        return result

    def queryset(self, request, queryset):
        val = self.value()
        if not val:
            return queryset
        return queryset.filter(**{self.qs_param: val})


class AlertForm(ModelForm):
    class Meta:
        model = Alert
        exclude = (
            "title",
            "title_i18n",
            "description",
            "description_i18n",
            "status_changed",
        )

        widgets = {
            "title_pl": UnescapeTextarea(attrs={"style": "width: 99%", "rows": 2}),
            "title_en": UnescapeTextarea(attrs={"style": "width: 99%", "rows": 2}),
            "description_pl": CKEditorWidget(config_name="alert_description"),
            "description_en": CKEditorWidget(config_name="alert_description"),
            "start_date": SuitSplitDateTimeWidget(),
            "finish_date": SuitSplitDateTimeWidget(),
        }

    def clean(self):
        cleaned = super().clean()
        finish_date = cleaned.get("finish_date")
        start_date = cleaned.get("start_date")
        if start_date and finish_date and start_date > finish_date:
            raise ValidationError(_("Start date cannot be greater than finish date."))

        return cleaned

    def clean_finish_date(self):
        now = timezone.now()
        finish_date = self.cleaned_data["finish_date"]
        if finish_date < now:
            raise ValidationError(_("Finish date cannot be in the past."))
        return finish_date


@admin.register(Alert)
class AlertAdmin(ModelAdmin):
    list_display = (
        "title_i18n",
        "display_status_str",
        "created_by_label",
        "start_date",
        "finish_date",
        "status_label",
    )
    search_fields = ("title_i18n",)
    lang_fields = True
    list_filter = (
        ("start_date", admin.DateFieldListFilter),
        ("finish_date", admin.DateFieldListFilter),
        DisplayStatusFilter,
    )
    form = AlertForm
    actions_on_top = True

    fieldsets = [
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": [
                    "title_pl",
                ],
            },
        ),
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": [
                    "start_date",
                    "finish_date",
                ],
            },
        ),
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": [
                    "description_pl",
                ],
            },
        ),
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": ["status"],
            },
        ),
    ]

    @property
    def suit_form_tabs(self):
        return (("general", _("General")), *self.get_translations_tabs())

    def get_fieldsets(self, request, obj=None):
        return self.fieldsets + self.get_translations_fieldsets()

    def display_status_str(self, obj):
        css_class, label = DISPLAY_STATUS[obj.display_status]
        return format_html('<span class="label label-{}">{}</i>'.format(css_class, label.lower()))

    display_status_str.short_description = _("Display")
    display_status_str.admin_order_field = "display_status"

    def save_model(self, request, obj, form, change):
        if not obj.id:
            obj.created_by = request.user
        obj.modified_by = request.user
        obj.save()

    def get_queryset(self, request):
        now = timezone.now()
        qs = super().get_queryset(request)
        return qs.annotate(
            display_status=Case(
                When(status="draft", then=Value("n/a")),
                When(finish_date__lt=now, then=Value("finished")),
                When(start_date__gt=now, then=Value("waiting")),
                default=Value("ongoing"),
                output_field=CharField(),
            )
        )
