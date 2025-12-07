from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from mcod.categories.models import Category, CategoryTrash
from mcod.lib.admin_mixins import HistoryMixin, ModelAdmin, TrashMixin


@admin.register(Category)
class CategoryAdmin(HistoryMixin, ModelAdmin):
    prepopulated_fields = {
        "slug": ("title",),
    }
    is_history_with_unknown_user_rows = True
    actions_on_top = True
    lang_fields = True
    list_display = ["title_i18n", "code", "obj_history"]

    fieldsets = [
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": [
                    "code",
                    "title",
                    "slug",
                    "description",
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
                    "image",
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
                    "status",
                ],
            },
        ),
    ]

    def get_fieldsets(self, request, obj=None):
        return self.get_translations_fieldsets() + self.fieldsets

    @property
    def suit_form_tabs(self):
        return (("general", _("General")), *self.get_translations_tabs())


@admin.register(CategoryTrash)
class CategoryTrashAdmin(HistoryMixin, TrashMixin):
    is_history_with_unknown_user_rows = True
    readonly_fields = (
        "code",
        "title",
        "description",
        "image",
        "status",
    )
    fields = [field for field in readonly_fields] + ["is_removed"]
