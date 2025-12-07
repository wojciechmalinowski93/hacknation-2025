from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _

from mcod.lib.admin_mixins import HistoryMixin, ModelAdmin
from mcod.newsletter.forms import NewsletterAdminForm
from mcod.newsletter.models import Newsletter, Submission, Subscription


class NewsletterAdmin(HistoryMixin, ModelAdmin):
    search_fields = ["title"]
    list_display = (
        "email_title",
        "status_label",
        "planned_sending_date",
        "sending_date",
    )
    readonly_fields = ["status"]
    exclude = ["lang", "sending_date", "created_by", "modified_by"]
    actions = ["send_newsletter_now"]
    actions_on_top = True
    delete_selected_msg = _("Delete selected newsletters")
    form = NewsletterAdminForm
    fieldsets = [
        (
            None,
            {
                "classes": (
                    "suit-tab",
                    "suit-tab-general",
                ),
                "fields": (
                    "title",
                    "planned_sending_date",
                    "file",
                ),
            },
        ),
    ]
    is_history_other = True
    suit_form_tabs = (("general", _("General")),)

    def get_status_label(self, obj):
        status_indexes = {"awaits": 0, "sent": 1, "error": 2}
        return obj.NEWSLETTER_STATUS_CHOICES[status_indexes[obj.status]][1]

    def email_title(self, obj):
        return obj.title

    email_title.short_description = _("Title of newsletter")
    email_title.admin_order_field = "title"

    def send_newsletter_now(self, request, queryset):
        if not Subscription.objects.filter(is_active=True).count():
            self.message_user(request, _("No active subscriptions."), level=messages.ERROR)
        if queryset.filter(status="sent").count():
            self.message_user(request, _("Select only unsent newsletters."), level=messages.ERROR)
        else:
            for newsletter in queryset:
                newsletter.send()
            self.message_user(request, _("Selected newsletters were successfully sent."))

    send_newsletter_now.short_description = _("Send newsletter now")

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = super().get_readonly_fields(request, obj=obj)
        if obj and obj.is_sent:
            return ["title", "planned_sending_date", "sending_date", "status", "file"]
        return readonly_fields

    def has_change_permission(self, request, obj=None):
        if obj and obj.is_sent:
            return False
        return super().has_change_permission(request, obj=obj)

    def has_history_permission(self, request, obj):
        return super().has_change_permission(request, obj=obj)

    def save_model(self, request, obj, form, change):
        if obj.is_sent:
            return
        if not obj.id:
            obj.created_by = request.user
        if change:
            obj.modified_by = request.user
        super().save_model(request, obj, form, change)


class SubscriptionAdmin(ModelAdmin):
    actions_on_top = True
    delete_selected_msg = _("Delete selected subscriptions")
    list_select_related = ("user",)
    list_display = ("__str__", "is_active", "subscribe_date")
    raw_id_fields = ("user",)
    search_fields = ["user__email"]
    exclude = ("created_by", "modified_by")

    def save_model(self, request, obj, form, change):
        if not obj.id:
            obj.created_by = request.user
        if change:
            obj.modified_by = request.user
        super().save_model(request, obj, form, change)


class SubmissionAdmin(ModelAdmin):
    actions_on_top = True
    search_fields = ["subscription__email", "newsletter__title"]
    list_select_related = ("newsletter", "subscription")
    list_display = ("newsletter", "subscription", "created")
    raw_id_fields = ("newsletter", "subscription")
    readonly_fields = ("newsletter", "subscription", "message")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Newsletter, NewsletterAdmin)
admin.site.register(Subscription, SubscriptionAdmin)
admin.site.register(Submission, SubmissionAdmin)
