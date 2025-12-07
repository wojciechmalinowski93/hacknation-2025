from django.contrib import admin
from django.utils.translation import gettext_lazy as _, pgettext_lazy

from mcod.guides.forms import GuideForm, GuideItemForm
from mcod.guides.models import Guide, GuideItem, GuideTrash
from mcod.lib.admin_mixins import HistoryMixin, ModelAdmin, SortableStackedInline, TrashMixin


class GuideAdminMixin:
    is_history_other = True
    form = GuideForm
    search_fields = ["title"]
    list_display = ("title", "created_by_label", "_created", "status_label")

    def _created(self, obj):
        return obj.created_localized if obj.pk else "-"

    _created.short_description = _("creation date")
    _created.admin_order_field = "created"

    def _created_by(self, obj):
        return obj.created_by if obj.pk else "-"

    _created_by.short_description = pgettext_lazy("masculine", "created by")
    _created_by.admin_order_field = "created_by"

    def save_model(self, request, obj, form, change):
        if not obj.id:
            obj.created_by = request.user
        obj.modified_by = request.user
        return super().save_model(request, obj, form, change)


class GuideItemInline(SortableStackedInline):
    add_text = _("Add next element")
    fields = [
        "title",
        "title_en",
        "content",
        "content_en",
        "route",
        "css_selector",
        "position",
        "is_optional",
        "is_clickable",
        "is_expandable",
    ]
    extra = 0
    form = GuideItemForm
    min_num = 1
    model = GuideItem
    verbose_name = _("communique")
    verbose_name_plural = ""


@admin.register(Guide)
class GuideAdmin(GuideAdminMixin, HistoryMixin, ModelAdmin):
    delete_selected_msg = _("Delete selected elements")
    fieldsets = [
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-course",
                ),
                "fields": (
                    (
                        "title",
                        "title_en",
                        "status",
                        "_created_by",
                        "_created",
                    ),
                ),
            },
        ),
    ]
    inlines = (GuideItemInline,)
    readonly_fields = (
        "_created",
        "_created_by",
    )
    soft_delete = True
    suit_form_includes = (("admin/guides/guide/tourpicker_button.html", "middle", "course"),)
    suit_form_tabs = (("course", _("General")),)


@admin.register(GuideTrash)
class GuideTrashAdmin(GuideAdminMixin, HistoryMixin, TrashMixin):
    delete_selected_msg = _("Delete selected elements")
    readonly_fields = (
        "title_pl",
        "title_en",
        "status",
        "_created_by",
        "_created",
    )
    fields = (
        "title_pl",
        "title_en",
        "status",
        "_created_by",
        "_created",
        "is_removed",
    )
