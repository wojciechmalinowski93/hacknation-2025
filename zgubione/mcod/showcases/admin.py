from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from modeltrans.translator import get_i18n_field

from mcod import settings
from mcod.lib.admin_mixins import DecisionFilter, HistoryMixin, ModelAdmin, TrashMixin
from mcod.showcases.forms import ShowcaseForm, ShowcaseProposalForm
from mcod.showcases.models import Showcase, ShowcaseProposal, ShowcaseProposalTrash, ShowcaseTrash
from mcod.showcases.tasks import create_showcase_task


class ShowcaseAdmin(HistoryMixin, ModelAdmin):
    actions_on_top = True
    prepopulated_fields = {"slug": ("title",)}
    autocomplete_fields = ["tags"]
    readonly_fields = ["application_logo", "illustrative_graphics_img", "preview_link"]
    lang_fields = True
    list_display = [
        "category",
        "title",
        "created_by_label",
        "application_logo",
        "modified",
        "main_page_position",
        "status",
        "obj_history",
    ]
    list_display_links = ("title",)
    obj_gender = "n"
    search_fields = ["title", "created_by__email", "url"]
    soft_delete = True
    list_filter = ["status", "main_page_position"]
    list_editable = ["status"]

    @property
    def suit_form_tabs(self):
        return (
            ("general", _("General")),
            *self.get_translations_tabs(),
            ("tags", _("Tags")),
            ("datasets", _("Datasets")),
        )

    form = ShowcaseForm
    is_history_with_unknown_user_rows = True

    def get_translations_fieldsets(self):
        i18n_field = get_i18n_field(self.model)
        fieldsets = []
        for lang_code in settings.MODELTRANS_AVAILABLE_LANGUAGES:
            fields = [f"{f.name}" for f in i18n_field.get_translated_fields() if f.name.endswith(lang_code)]
            if lang_code == settings.LANGUAGE_CODE:
                continue
            tab_name = "general" if lang_code == settings.LANGUAGE_CODE else f"lang-{lang_code}"
            fieldset = (
                None,
                {
                    "classes": (
                        "suit-tab",
                        f"suit-tab-{tab_name}",
                    ),
                    "fields": fields,
                },
            )
            fieldsets.append(fieldset)
        return fieldsets

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj=obj, **kwargs)
        form.recreate_tags_widgets(request=request, db_field=Showcase.tags.field, admin_site=self.admin_site)
        return form

    def get_fieldsets(self, request, obj=None):
        return [
            (
                None,
                {
                    "classes": (
                        "suit-tab",
                        "suit-tab-general",
                    ),
                    "fields": (
                        "preview_link",
                        "category",
                        "title",
                        "slug",
                    ),
                },
            ),
            (
                None,
                {
                    "classes": (
                        "suit-tab",
                        "suit-tab-general",
                    ),
                    "fields": (
                        "is_mobile_app",
                        "mobile_apple_url",
                        "mobile_google_url",
                        "is_desktop_app",
                        "desktop_windows_url",
                        "desktop_linux_url",
                        "desktop_macos_url",
                        "license_type",
                    ),
                },
            ),
            (
                None,
                {
                    "classes": (
                        "suit-tab",
                        "suit-tab-general",
                    ),
                    "fields": (
                        "notes",
                        "author",
                        "external_datasets",
                        "url",
                        "image",
                        "image_alt",
                        "application_logo",
                        "illustrative_graphics",
                        "illustrative_graphics_alt",
                        "illustrative_graphics_img",
                        "main_page_position",
                        "status",
                    ),
                },
            ),
            (
                _("Datasets"),
                {
                    "classes": (
                        "suit-tab",
                        "suit-tab-datasets",
                    ),
                    "fields": ("datasets",),
                },
            ),
            (
                None,
                {
                    "classes": (
                        "suit-tab",
                        "suit-tab-tags",
                    ),
                    "fields": (
                        "tags_pl",
                        "tags_en",
                    ),
                },
            ),
        ] + self.get_translations_fieldsets()

    def application_logo(self, obj):
        return obj.application_logo or "-"

    application_logo.short_description = _("Logo")

    def illustrative_graphics_img(self, obj):
        return obj.illustrative_graphics_img or "-"

    illustrative_graphics_img.short_description = _("Illustrative graphics")

    def preview_link(self, obj):
        return obj.preview_link

    preview_link.allow_tags = True
    preview_link.short_description = _("Preview link")

    def save_model(self, request, obj, form, change):
        if not obj.id:
            obj.created_by = request.user
        obj.modified_by = request.user
        if "external_datasets" in form.cleaned_data:
            obj.external_datasets = form.cleaned_data["external_datasets"]
        super().save_model(request, obj, form, change)


class ShowcaseTrashAdmin(HistoryMixin, TrashMixin):
    list_display = [
        "category",
        "title",
        "author",
        "url",
    ]
    list_display_links = ("title",)
    search_fields = [
        "title",
        "author",
        "url",
    ]

    def _get_fields(self, obj=None):
        app_info = ["app_info"] if obj and obj.is_app else []
        license_type = ["license_type"] if obj and any([obj.is_www, obj.is_app]) else []
        return [
            "category",
            "title",
            "author",
            "datasets",
            *app_info,
            *license_type,
            "image",
            "notes",
            "slug",
            "status",
            "tags_list_pl",
            "tags_list_en",
            "url",
        ]

    def get_readonly_fields(self, request, obj=None):
        return self._get_fields(obj=obj)

    def get_fields(self, request, obj=None):
        return self._get_fields(obj=obj) + ["is_removed"]

    def app_info(self, obj):
        return obj.app_info

    app_info.short_description = _("Application type")

    def tags_list_pl(self, obj):
        return obj.tags_as_str(lang="pl")

    tags_list_pl.short_description = _("Tags") + " (PL)"

    def tags_list_en(self, obj):
        return obj.tags_as_str(lang="en")

    tags_list_en.short_description = _("Tags") + " (EN)"


class ShowcaseProposalMixin(HistoryMixin):
    delete_selected_msg = _("Delete selected showcase proposals")
    is_history_other = True
    is_history_with_unknown_user_rows = True
    list_display_links = ("title",)
    obj_gender = "f"
    ordering = ("-report_date",)
    search_fields = ["title"]

    def applicant_email_link(self, obj):
        return obj.applicant_email_link or "-"

    applicant_email_link.short_description = _("applicant email")

    def application_logo(self, obj):
        return obj.application_logo or "-"

    application_logo.short_description = _("Logo")
    application_logo.admin_order_field = "image"

    def app_info(self, obj):
        return obj.app_info

    app_info.short_description = _("Application type")

    def illustrative_graphics_img(self, obj):
        return obj.illustrative_graphics_img or "-"

    illustrative_graphics_img.short_description = _("Illustrative graphics")
    illustrative_graphics_img.admin_order_field = "illustrative_graphics"

    def datasets_admin(self, obj):
        return obj.datasets_links or "-"

    datasets_admin.short_description = _("Datasets being used to build application")

    def decision_label(self, obj):
        return self._format_label(obj, "decision")

    def get_decision_value(self, obj):
        return obj.decision

    def get_decision_label(self, obj):
        return obj.get_decision_display() or _("Decision not taken")

    decision_label.admin_order_field = "decision"
    decision_label.short_description = _("decision")

    def external_datasets_admin(self, obj):
        return obj.external_datasets_links or "-"

    external_datasets_admin.short_description = _("External public data used")
    external_datasets_admin.admin_order_field = "external_datasets"

    def get_list_display(self, request):
        decision_date = ["decision_date"] if request.method == "GET" and request.GET.get("decision") == "taken" else []
        self.list_display = [
            "category",
            "title",
            "author",
            "application_logo",
            "report_date",
            "decision_label",
            *decision_date,
        ]
        return super().get_list_display(request)

    def has_add_permission(self, request, obj=None):
        return False


class ShowcaseProposalAdmin(ShowcaseProposalMixin, ModelAdmin):

    export_to_csv = True
    soft_delete = True

    def get_fieldsets(self, request, obj=None):
        app_info = ["app_info"] if obj and obj.is_app else []
        license_type = ["license_type"] if obj and any([obj.is_www, obj.is_app]) else []
        fields = (
            "category",
            "title",
            "url",
            *app_info,
            *license_type,
            "notes",
            "keywords",
            "author",
            "application_logo",
            "illustrative_graphics_img",
            "datasets_admin",
            "external_datasets_admin",
            "applicant_email_link",
            "comment",
            "report_date",
            ("decision", "decision_date"),
        )
        return [
            (None, {"classes": ("suit-tab", "suit-tab-general"), "fields": fields}),
        ]

    form = ShowcaseProposalForm
    list_filter = [
        DecisionFilter,
    ]
    readonly_fields = [
        "category",
        "title",
        "url",
        "app_info",
        "license_type",
        "notes",
        "applicant_email_link",
        "author",
        "application_logo",
        "illustrative_graphics_img",
        "datasets_admin",
        "external_datasets_admin",
        "keywords",
        "report_date",
        "decision_date",
    ]
    suit_form_tabs = (("general", _("General")),)

    @property
    def admin_url(self):
        return super().admin_url + "?decision=not_taken"

    def save_model(self, request, obj, form, change):
        obj.created_by = request.user if not obj.id and not obj.created_by else obj.created_by
        obj.modified_by = request.user
        create_showcase = (
            obj.tracker.has_changed("decision") and obj.is_accepted and (not obj.showcase or obj.showcase.is_permanently_removed)
        )
        super().save_model(request, obj, form, change)
        if create_showcase:
            create_showcase_task.s(obj.id).apply_async_on_commit()
            self.message_user(
                request,
                _("Showcase creation task was launched!"),
                level=messages.SUCCESS,
            )


class ShowcaseProposalTrashAdmin(ShowcaseProposalMixin, TrashMixin):

    def _get_fields(self, obj=None):
        app_info = ["app_info"] if obj and obj.is_app else []
        license_type = ["license_type"] if obj and any([obj.is_www, obj.is_app]) else []
        return [
            "category",
            "title",
            "url",
            *app_info,
            *license_type,
            "notes",
            "keywords",
            "author",
            "application_logo",
            "illustrative_graphics_img",
            "datasets_admin",
            "external_datasets_admin",
            "applicant_email_link",
            "comment",
            "report_date",
            "decision",
            "decision_date",
        ]

    def get_fields(self, request, obj=None):
        return self._get_fields(obj=obj) + ["is_removed"]

    def get_readonly_fields(self, request, obj=None):
        return self._get_fields(obj=obj)


admin.site.register(Showcase, ShowcaseAdmin)
admin.site.register(ShowcaseTrash, ShowcaseTrashAdmin)
admin.site.register(ShowcaseProposal, ShowcaseProposalAdmin)
admin.site.register(ShowcaseProposalTrash, ShowcaseProposalTrashAdmin)
