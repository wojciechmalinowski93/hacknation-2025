from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from mcod.lib.admin_mixins import DecisionFilter, HistoryMixin, ModelAdmin, TrashMixin
from mcod.suggestions.forms import (
    AcceptedDatasetSubmissionForm,
    DatasetCommentForm,
    DatasetSubmissionForm,
    ResourceCommentForm,
)
from mcod.suggestions.models import (
    AcceptedDatasetSubmission,
    AcceptedDatasetSubmissionTrash,
    DatasetComment,
    DatasetCommentTrash,
    DatasetSubmission,
    DatasetSubmissionTrash,
    ResourceComment,
    ResourceCommentTrash,
)
from mcod.suggestions.tasks import create_accepted_dataset_suggestion_task


class CommentAdminMixin(HistoryMixin, ModelAdmin):
    export_to_csv = True
    is_history_other = True
    is_history_with_unknown_user_rows = True
    list_filter = [
        DecisionFilter,
    ]
    obj_gender = "f"
    soft_delete = True
    suit_form_tabs = (("general", _("General")),)

    def _comment(self, obj):
        return obj.comment or "-"

    _comment.short_description = _("text of comment")

    def _data_provider_url(self, obj):
        return obj.data_provider_url or "-"

    _data_provider_url.short_description = _("Data provider")

    def decision_label(self, obj):
        return self._format_label(obj, "decision")

    def get_decision_value(self, obj):
        return obj.decision

    def get_decision_label(self, obj):
        return obj.get_decision_display() or _("Decision not taken")

    decision_label.admin_order_field = "decision"
    decision_label.short_description = _("decision")

    def _editor_email(self, obj):
        return obj.editor_email or "-"

    _editor_email.short_description = _("editor e-mail")

    def _truncated_comment(self, obj):
        return obj.truncated_comment or "-"

    _truncated_comment.short_description = _("notes")
    _truncated_comment.admin_order_field = "comment"

    @property
    def admin_url(self):
        return super().admin_url + "?decision=not_taken"

    def get_list_display(self, request):
        decision_date = ["decision_date"] if request.method == "GET" and request.GET.get("decision") == "taken" else []
        self.list_display = [
            "_title",
            "_truncated_comment",
            "report_date",
            "decision_label",
            *decision_date,
        ]
        return super().get_list_display(request)

    def has_add_permission(self, request, obj=None):
        return False


class DatasetCommentAdmin(CommentAdminMixin):
    fieldsets = [
        (
            None,
            {
                "classes": ("suit-tab", "suit-tab-general"),
                "fields": (
                    "_title",
                    "_comment",
                    "_editor_email",
                    "_data_url",
                    "_data_provider_url",
                    "editor_comment",
                    "report_date",
                    "is_data_provider_error",
                    "is_user_error",
                    "is_portal_error",
                    "is_other_error",
                    "decision",
                    "decision_date",
                ),
            },
        ),
    ]
    form = DatasetCommentForm
    list_select_related = ("dataset",)
    readonly_fields = [
        "decision_date",
        "report_date",
        "_comment",
        "_data_url",
        "_data_provider_url",
        "_editor_email",
        "_title",
    ]
    search_fields = ["dataset__title", "comment"]

    def _data_url(self, obj):
        return obj.data_url or "-"

    _data_url.short_description = _("comment reported for dataset")

    def _title(self, obj):
        return obj.dataset.title or "-"

    _title.short_description = _("Title")
    _title.admin_order_field = "dataset__title"

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("datasets.delete_dataset")


class CommentAdminTrashMixin(TrashMixin):
    fieldsets = None
    is_history_other = True
    is_history_with_unknown_user_rows = True
    suit_form_tabs = None
    readonly_fields = [
        "_title",
        "_comment",
        "_editor_email",
        "_data_url",
        "_data_provider_url",
        "editor_comment",
        "report_date",
        "decision",
        "decision_date",
    ]
    fields = [x for x in readonly_fields] + ["is_removed"]


class DatasetSubmissionAdminMixin(HistoryMixin, ModelAdmin):
    is_history_other = True
    is_history_with_unknown_user_rows = True
    obj_gender = "f"
    search_fields = ["title"]
    soft_delete = True
    suit_form_tabs = (("general", _("General")),)

    def has_add_permission(self, request):
        return False


class DatasetSubmissionAdmin(DatasetSubmissionAdminMixin):
    export_to_csv = True
    form = DatasetSubmissionForm
    list_filter = [
        DecisionFilter,
    ]
    fields = (
        "title",
        "notes",
        "organization_name",
        "data_link",
        "potential_possibilities",
        "comment",
        "submission_date",
        ("decision", "decision_date"),
    )
    readonly_fields = (
        "title",
        "notes",
        "organization_name",
        "data_link",
        "potential_possibilities",
        "submission_date",
        "decision_date",
    )

    def decision_label(self, obj):
        return self._format_label(obj, "decision")

    def get_decision_value(self, obj):
        return obj.decision

    def get_decision_label(self, obj):
        return obj.get_decision_display() or _("Decision not taken")

    decision_label.admin_order_field = "decision"
    decision_label.short_description = _("decision")

    def _notes(self, obj):
        return obj.truncated_notes or "-"

    _notes.short_description = _("Data description")
    _notes.admin_order_field = "notes"

    @property
    def admin_url(self):
        return super().admin_url + "?decision=not_taken"

    def get_list_display(self, request):
        decision_date = ["decision_date"] if request.method == "GET" and request.GET.get("decision") == "taken" else []
        self.list_display = [
            "title",
            "_notes",
            "submission_date",
            "decision_label",
            *decision_date,
        ]
        return super().get_list_display(request)

    def save_model(self, request, obj, form, change):
        obj.modified_by = request.user
        create_needed = obj.tracker.has_changed("decision") and obj.is_accepted and not obj.accepted_dataset_submission
        super().save_model(request, obj, form, change)
        if create_needed:
            create_accepted_dataset_suggestion_task.s(obj.id).apply_async_on_commit()
            self.message_user(
                request,
                _("Create accepted dataset suggestion task was launched!"),
                level=messages.SUCCESS,
            )


class AcceptedDatasetSubmissionAdmin(DatasetSubmissionAdminMixin):
    form = AcceptedDatasetSubmissionForm
    lang_fields = True
    list_display = [
        "_title",
        "_notes",
        "submission_date",
        "decision_date",
        "status_label",
    ]

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        self.suit_form_tabs = (("general", _("General")), *self.get_translations_tabs())

    @staticmethod
    def get_readonly_fields(request, obj=None):
        if obj and obj.status == "publication_finished" and not obj.tracker.has_changed("status"):
            return [
                "title",
                "notes",
                "organization_name",
                "data_link",
                "potential_possibilities",
                "comment",
                "decision_date",
                "publication_finished_at",
                "publication_finished_comment",
            ]

        return ["comment", "decision_date"]

    @staticmethod
    def get_fields(request, obj=None):
        fields = [
            "title",
            "notes",
            "organization_name",
            "data_link",
            "potential_possibilities",
            "comment",
            "decision_date",
            "status",
            "publication_finished_comment",
        ]

        if obj and obj.status == "publication_finished" and not obj.tracker.has_changed("status"):
            fields.insert(-1, "publication_finished_at")
            return fields

        fields += [
            "is_published_for_all",
            "is_active",
        ]
        return fields

    def save_model(self, request, obj, form, change):
        if obj.tracker.has_changed("status"):
            if obj.tracker.previous("status") == "publication_finished" and obj.status == "draft":
                obj.is_active = True
                obj.publication_finished_comment = ""
            if obj.status == "publication_finished":
                obj.is_published_for_all = False
                obj.is_active = False
        super().save_model(request, obj, form, change)

    def _title(self, obj):
        return obj.title

    _title.short_description = _("Title")
    _title.admin_order_field = "title"

    def _notes(self, obj):
        return obj.truncated_notes or "-"

    _notes.short_description = _("Notes")
    _notes.admin_order_field = "notes"

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)
        fieldsets = [
            (
                None,
                {
                    "classes": (
                        "suit-tab",
                        "suit-tab-general",
                    ),
                    "fields": fieldsets[0][1]["fields"],
                },
            )
        ]
        translated_fields = self.get_translations_fieldsets()
        translated_fields[0][1]["fields"].remove("slug_en")
        fieldsets += translated_fields
        return fieldsets


class DatasetSubmissionTrashAdmin(TrashMixin):
    readonly_fields = [
        "title",
        "notes",
        "organization_name",
        "data_link",
        "potential_possibilities",
        "comment",
        "submission_date",
        "decision",
        "decision_date",
    ]
    fields = readonly_fields + ["is_removed"]
    list_display = [
        "title",
        "_notes",
        "submission_date",
        "decision_label",
    ]

    def decision_label(self, obj):
        return self._format_label(obj, "decision")

    def get_decision_value(self, obj):
        return obj.decision

    def get_decision_label(self, obj):
        return obj.get_decision_display() or _("Decision not taken")

    decision_label.admin_order_field = "decision"
    decision_label.short_description = _("decision")

    def _notes(self, obj):
        return obj.truncated_notes or "-"

    _notes.short_description = _("Data description")
    _notes.admin_order_field = "notes"


class AcceptedDatasetSubmissionTrashAdmin(TrashMixin):
    list_display = [
        "_title",
        "_notes",
        "submission_date",
        "decision_date",
        "status_label",
    ]

    def get_fields(self, request, obj=None):
        return AcceptedDatasetSubmissionAdmin.get_fields(request, obj=obj) + ["is_removed"]

    def get_readonly_fields(self, request, obj=None):
        return AcceptedDatasetSubmissionAdmin.get_fields(request, obj=obj)

    def _notes(self, obj):
        return obj.truncated_notes or "-"

    _notes.short_description = _("Notes")
    _notes.admin_order_field = "notes"

    def _title(self, obj):
        return obj.title

    _title.short_description = _("Title")
    _title.admin_order_field = "title"


class ResourceCommentAdmin(CommentAdminMixin):
    fieldsets = [
        (
            None,
            {
                "classes": ("suit-tab", "suit-tab-general"),
                "fields": (
                    "_title",
                    "_comment",
                    "_editor_email",
                    "_data_url",
                    "_data_provider_url",
                    "editor_comment",
                    "report_date",
                    "is_data_provider_error",
                    "is_user_error",
                    "is_portal_error",
                    "is_other_error",
                    "decision",
                    "decision_date",
                ),
            },
        ),
    ]
    form = ResourceCommentForm
    list_select_related = ("resource",)
    readonly_fields = [
        "decision_date",
        "report_date",
        "_comment",
        "_data_url",
        "_data_provider_url",
        "_editor_email",
        "_title",
    ]
    search_fields = ["resource__title", "comment"]

    def _data_url(self, obj):
        return obj.data_url or "-"

    _data_url.short_description = _("comment reported for data")

    def _title(self, obj):
        return obj.resource.title or "-"

    _title.short_description = _("Title")
    _title.admin_order_field = "resource__title"

    def has_delete_permission(self, request, obj=None):
        return request.user.has_perm("resources.delete_resource")


class DatasetCommentTrashAdmin(CommentAdminTrashMixin, DatasetCommentAdmin):
    pass


class ResourceCommentTrashAdmin(CommentAdminTrashMixin, ResourceCommentAdmin):
    pass


admin.site.register(DatasetSubmission, DatasetSubmissionAdmin)
admin.site.register(DatasetSubmissionTrash, DatasetSubmissionTrashAdmin)
admin.site.register(AcceptedDatasetSubmission, AcceptedDatasetSubmissionAdmin)
admin.site.register(AcceptedDatasetSubmissionTrash, AcceptedDatasetSubmissionTrashAdmin)

admin.site.register(DatasetComment, DatasetCommentAdmin)
admin.site.register(DatasetCommentTrash, DatasetCommentTrashAdmin)
admin.site.register(ResourceComment, ResourceCommentAdmin)
admin.site.register(ResourceCommentTrash, ResourceCommentTrashAdmin)
