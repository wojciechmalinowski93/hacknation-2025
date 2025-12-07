from dateutil.relativedelta import relativedelta
from django.contrib.auth import get_user_model
from django.db import models
from django.db.models import Q
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker
from modeltrans.fields import TranslationField
from notifications.base.models import AbstractNotification
from notifications.signals import notify

from mcod.core.db.models import ExtendedModel
from mcod.lib.model_sanitization import SanitizedCharField, SanitizedTextField
from mcod.schedules.managers import (
    CommentManager,
    CommentTrashManager,
    NotificationQuerySet,
    ScheduleManager,
    ScheduleTrashManager,
    UserScheduleItemManager,
    UserScheduleItemTrashManager,
    UserScheduleManager,
    UserScheduleTrashManager,
)

YES = _("Yes")
NO = _("No")

NOTIFICATION_TYPES = {
    "admin_comment": _("{author} new comment "),
    "agent_comment": _("{author} new comment "),
    "end_date_changed": _("The end of planning date was added/changed"),
    "end_date_soon": _("7 days until end of planning"),
    "end_date_passed": _("The end of planning date has passed"),
    "new_end_date_changed": _("The new end of planning date was added/changed"),
    "new_end_date_passed": _("The new end of planning date has passed"),
}


class Notification(AbstractNotification):
    objects = NotificationQuerySet.as_manager()
    verb = SanitizedCharField(max_length=255)
    description = SanitizedTextField(blank=True, null=True)

    @property
    def schedule_id(self):
        return self.target.user_schedule.schedule_id if self.target else None

    @property
    def user_schedule_id(self):
        return self.target.user_schedule_id if self.target and self.recipient.is_superuser else None

    @property
    def user_schedule_item_id(self):
        return self.target_object_id

    @property
    def schedule_state(self):
        return self.target.state if self.target else None

    class Meta(AbstractNotification.Meta):
        abstract = False
        app_label = "schedules"


class Schedule(ExtendedModel):
    SCHEDULE_STATES = (
        ("planned", _("Planned")),
        ("implemented", _("Implemented")),
        ("archived", _("Archived")),
    )
    state = models.CharField(
        max_length=11,
        choices=SCHEDULE_STATES,
        default="planned",
        verbose_name=_("type"),
    )
    start_date = models.DateField(verbose_name=_("start date"), null=True, blank=True)
    period_name = models.CharField(max_length=100, verbose_name=_("period name"), blank=True)
    end_date = models.DateField(verbose_name=_("end date"), null=True, blank=True)
    new_end_date = models.DateField(verbose_name=_("new end date"), null=True, blank=True)
    link = models.URLField(verbose_name=_("schedule link"))
    is_blocked = models.BooleanField(default=False, verbose_name=_("is blocked?"))
    created_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        verbose_name=_("created by"),
        related_name="schedules_created",
    )
    modified_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        null=True,
        blank=True,
        verbose_name=_("modified by"),
        related_name="schedules_modified",
    )

    objects = ScheduleManager()
    trash = ScheduleTrashManager()
    i18n = TranslationField()
    tracker = FieldTracker()

    def __str__(self):
        return f"{self.period_name}-{self.get_state_display()}"

    class Meta:
        default_manager_name = "objects"
        verbose_name = _("schedule")
        verbose_name_plural = _("schedules")

    @classmethod
    def create(cls, **kwargs):
        current_plan = cls.get_current_plan()
        if current_plan:
            if current_plan.awaiting_user_schedule_items.exists():
                msg = _('No recommendation for "%(email)s"') % {
                    "email": current_plan.awaiting_user_schedule_items.first().user.email
                }
                raise Exception(msg)
            start_date = current_plan.start_date + relativedelta(months=6)
        else:
            today = timezone.now().date()
            kw = {"day": 1, "month": 1} if today.month in range(1, 7) else {"day": 1, "month": 7}
            start_date = today.replace(**kw)
        kwargs["start_date"] = start_date
        schedule = cls.objects.create(**kwargs)
        if current_plan:
            current_plan.state = "implemented"
            current_plan.is_blocked = False
            current_plan.save()
        return schedule

    @classmethod
    def get_current_plan(cls):
        return cls.objects.planned().order_by("-created").first()

    @classmethod
    def get_dashboard_aggregations_for(cls, user):
        schedule = cls.get_current_plan() if (user.is_superuser or user.agent) else None
        if user.is_superuser:
            return {
                "started": schedule.get_started_count() if schedule else 0,
                "ready": schedule.get_ready_count() if schedule else 0,
                "recommended": schedule.get_recommended_count() if schedule else 0,
            }
        schedule = schedule.schedule_for_user(user) if schedule else None
        return UserSchedule.get_dashboard_aggregations(schedule)

    def get_default_period_name(self):
        if self.start_date:
            return "%(part)s półrocze %(year)s" % {
                "part": "I" if self.start_date.month in range(1, 7) else "II",
                "year": self.start_date.year,
            }

    def schedule_for_user(self, user):
        user = user if user.is_agent else user.extra_agent_of if user.extra_agent_of else None
        if user:
            return self.user_schedules.filter(user=user).first()

    def send_admin_notification(self, msg, notification_type="all"):
        agents = self.total_agents
        if notification_type == "late":
            ready_agents_ids = [obj.user.id for obj in self.user_schedules.filter(is_ready=True)]
            agents = agents.exclude(id__in=ready_agents_ids)
        count = 0
        for agent in agents:
            notify.send(self, recipient=agent.schedule_notification_recipients, verb=msg)
            count += agent.schedule_notification_recipients.count()
        return count

    def send_schedule_notifications(self):
        today = timezone.now().date()
        yesterday = today - relativedelta(days=1)
        next_week = today + relativedelta(days=7)
        verb = None
        if self.planning_end_date == yesterday:
            verb = NOTIFICATION_TYPES["end_date_passed"]
        elif self.planning_end_date == next_week:
            verb = NOTIFICATION_TYPES["end_date_soon"]
        if verb:
            not_ready_user_schedules = self.user_schedules.filter(is_ready=False)
            for obj in not_ready_user_schedules:
                notify.send(self, recipient=obj.user.schedule_notification_recipients, verb=verb)

    @property
    def name(self):
        return _("Data sharing schedule on %(period)s") % {"period": self.get_default_period_name()}

    @property
    def planning_end_date(self):
        return self.new_end_date or self.end_date

    @cached_property
    def total_agents(self):
        return get_user_model().objects.agents()

    @property
    def total_agents_count(self):
        return self.total_agents.count()

    @cached_property
    def user_schedules_included(self):
        return self.user_schedules.all()

    @cached_property
    def user_schedule_items_included(self):
        return UserScheduleItem.objects.filter(user_schedule__schedule=self)

    @cached_property
    def awaiting_user_schedule_items(self):
        return UserScheduleItem.objects.filter(user_schedule__schedule=self, recommendation_state="awaits").order_by(
            "user_schedule__user__email"
        )

    def get_started_count(self):
        return self.user_schedules.filter(is_ready=False).count()

    def get_ready_count(self):
        return self.user_schedules.filter(is_ready=True).count()

    def get_recommended_count(self):
        counter = 0
        for user_schedule in self.user_schedules.all():
            if user_schedule.is_recommended():
                counter += 1
        return counter


class UserSchedule(ExtendedModel):
    STATE_READY = "gotowy"
    STATE_NOT_READY = "w przygotowaniu"

    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.CASCADE,
        verbose_name=_("schedule"),
        related_name="user_schedules",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        verbose_name=_("user"),
        related_name="user_schedules",
    )
    is_ready = models.BooleanField(
        default=False,
        verbose_name=_("is ready?"),
        help_text=_("assign schedule as ready"),
    )
    created_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        verbose_name=_("created by"),
        related_name="user_schedules_created",
    )
    modified_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        null=True,
        blank=True,
        verbose_name=_("modified by"),
        related_name="user_schedules_modified",
    )

    objects = UserScheduleManager()
    trash = UserScheduleTrashManager()
    i18n = TranslationField()
    tracker = FieldTracker()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["schedule", "user"], name="schedule_user_unique_together"),
        ]
        default_manager_name = "objects"
        ordering = ["created"]
        verbose_name = _("user schedule")
        verbose_name_plural = _("user schedules")

    def __str__(self):
        return f"{self.schedule} - {self.user}"

    @cached_property
    def items_count(self):
        return self.user_schedule_items.count()

    @cached_property
    def recommended_items_count(self):
        return self.user_schedule_items.filter(recommendation_state__in=["recommended", "not_recommended"]).count()

    @cached_property
    def implemented_items_count(self):
        return self.user_schedule_items.exclude(Q(is_resource_added_notes="") | Q(resource_link="")).distinct().count()

    @cached_property
    def is_blocked(self):
        return self.user_schedule_items.filter(recommendation_state__in=["recommended", "not_recommended"]).exists()

    @property
    def state(self):
        return self.schedule.state

    @property
    def institution(self):
        return self.user.agent_organization_main

    @cached_property
    def user_schedule_items_included(self):
        return self.user_schedule_items.all()

    @property
    def period_name(self):
        return self.schedule.period_name

    @property
    def is_ready_str(self):
        return self.STATE_READY if self.is_ready else self.STATE_NOT_READY

    def is_recommended(self):
        return self.recommended_items_count > 0 and self.recommended_items_count == self.items_count

    @classmethod
    def get_dashboard_aggregations(cls, schedule=None):
        return {
            "schedule_items": schedule.items_count if schedule else 0,
            "state": schedule.is_ready_str if schedule else cls.STATE_NOT_READY,
        }


class UserScheduleItem(ExtendedModel):
    FORMATS = [
        "csv",
        "doc",
        "docx",
        "html",
        "jpeg",
        "json",
        "ods",
        "pdf",
        "API",
        _("WMS service"),
        "xls",
        "xlsx",
        "xml",
        "csv,xls",
        "csv,xlsx",
    ]
    RECOMMENDATION_STATES = (
        ("awaits", _("awaits")),
        ("recommended", _("recommended")),
        ("not_recommended", _("not recommended")),
    )
    user_schedule = models.ForeignKey(
        UserSchedule,
        on_delete=models.CASCADE,
        verbose_name=_("schedule"),
        related_name="user_schedule_items",
    )

    organization_name = models.CharField(max_length=150, blank=True, verbose_name=_("institution"))
    organization_unit = models.CharField(max_length=150, blank=True, verbose_name=_("institution unit"))
    dataset_title = models.CharField(max_length=300, verbose_name=_("dataset title"))
    format = models.CharField(max_length=150, verbose_name=_("format"))
    is_new = models.BooleanField(default=False, verbose_name=_("is new?"))
    is_openness_score_increased = models.NullBooleanField(verbose_name=_("is openness score increased?"))
    is_quality_improved = models.NullBooleanField(verbose_name=_("is quality improved?"))
    description = models.TextField(blank=True, verbose_name=_("description"))

    recommendation_state = models.CharField(
        max_length=15,
        choices=RECOMMENDATION_STATES,
        default="awaits",
        verbose_name=_("recommendation state"),
    )
    recommendation_notes = models.TextField(blank=True, verbose_name=_("recommendation notes"))

    is_resource_added = models.BooleanField(default=False, verbose_name=_("is resource added?"))
    is_resource_added_notes = models.TextField(blank=True, verbose_name=_("is resource added notes"))
    resource_link = models.URLField(blank=True, verbose_name=_("resource link"))

    created_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        verbose_name=_("created by"),
        related_name="user_schedule_items_created",
    )
    modified_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        null=True,
        blank=True,
        verbose_name=_("modified by"),
        related_name="user_schedule_items_modified",
    )

    objects = UserScheduleItemManager()
    trash = UserScheduleItemTrashManager()
    i18n = TranslationField()
    tracker = FieldTracker()

    class Meta:
        default_manager_name = "objects"
        verbose_name = _("user schedule item")
        verbose_name_plural = _("user schedule items")

    def __str__(self):
        return self.dataset_title

    @property
    def comments(self):
        return self.user_schedule_item_comments

    @cached_property
    def comments_included(self):
        return self.user_schedule_item_comments.all()

    @property
    def period_name(self):
        return self.user_schedule.period_name

    @property
    def schedule(self):
        return self.user_schedule.schedule

    @property
    def user(self):
        return self.user_schedule.user

    @property
    def is_accepted(self):
        return self.recommendation_state == "recommended"

    @property
    def is_completed(self):
        return self.resource_link or self.is_resource_added_notes  # ODSOFT-1257

    @property
    def is_new_yes_no(self):
        return YES if self.is_new else NO

    @property
    def is_openness_score_increased_yes_no(self):
        return YES if self.is_openness_score_increased else NO

    @property
    def is_recommendation_issued(self):
        return self.recommendation_state in ["recommended", "not_recommended"]

    @property
    def is_resource_added_yes_no(self):
        return YES if self.is_resource_added else NO

    @property
    def is_quality_improved_yes_no(self):
        return YES if self.is_quality_improved else NO

    @property
    def recommendation_state_name(self):
        return self.get_recommendation_state_display()

    @property
    def state(self):
        return self.user_schedule.schedule.state

    def can_be_deleted_by(self, user):
        if user.is_superuser:
            return True
        _user = user.extra_agent_of or user
        if self.user == _user:
            if self.recommendation_state != "awaits":
                return False
            return True
        return False

    def can_be_updated_by(self, user):
        if user.is_superuser:
            return True
        _user = user.extra_agent_of or user
        if self.user == _user:
            if self.state == "archived":
                return False
            return True
        return False

    @classmethod
    def _get_included(cls, ids, **kwargs):
        qs = super()._get_included(ids, **kwargs)
        return qs.order_by("-created")

    @classmethod
    def create(cls, **kwargs):
        user = kwargs.pop("user", None)
        user_schedule = kwargs.get("user_schedule")
        if user and not user_schedule:
            schedule = Schedule.get_current_plan()
            if not schedule:
                raise Exception("There is no currently planned schedule yet!")
            user_schedule, created = UserSchedule.objects.get_or_create(
                user=user,
                schedule=schedule,
                defaults={"created_by": kwargs["created_by"]},
            )
            if user_schedule:
                kwargs["user_schedule"] = user_schedule
        return cls.objects.create(**kwargs)


class Comment(ExtendedModel):
    user_schedule_item = models.ForeignKey(
        UserScheduleItem,
        on_delete=models.CASCADE,
        verbose_name=_("user schedule item"),
        related_name="user_schedule_item_comments",
    )
    text = models.TextField(verbose_name=_("text"))
    created_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        verbose_name=_("created by"),
        related_name="user_schedule_item_comments_created",
    )
    modified_by = models.ForeignKey(
        "users.User",
        models.DO_NOTHING,
        null=True,
        blank=True,
        verbose_name=_("modified by"),
        related_name="user_schedule_item_comments_modified",
    )

    objects = CommentManager()
    trash = CommentTrashManager()
    i18n = TranslationField()
    tracker = FieldTracker()

    class Meta:
        default_manager_name = "objects"
        ordering = ["created"]
        verbose_name = _("comment")
        verbose_name_plural = _("comments")

    def __str__(self):
        return self.text[:100]

    @property
    def author(self):
        return self.created_by.email


@receiver(pre_save, sender=Schedule)
def handle_schedule_pre_save(sender, instance, *args, **kwargs):
    if not instance.period_name:
        instance.period_name = instance.get_default_period_name()


@receiver(post_save, sender=Comment)
def handle_comment_post_save(sender, instance, *args, **kwargs):
    created = kwargs.get("created", False)
    if created:
        verb = None
        recipients = None
        if instance.created_by.is_superuser:
            verb = NOTIFICATION_TYPES["admin_comment"]
            recipients = instance.user_schedule_item.user_schedule.user.schedule_notification_recipients
        elif instance.created_by.agent:
            verb = NOTIFICATION_TYPES["agent_comment"]
            recipients = get_user_model().objects.filter(is_superuser=True)
        if verb and recipients:
            verb = verb.format(author=instance.author.split("@")[0])
            notify.send(
                instance.created_by,
                recipient=recipients,
                verb=verb,
                action_object=instance,
                target=instance.user_schedule_item,
            )


@receiver(post_save, sender=Schedule)
def handle_schedule_post_save(sender, instance, *args, **kwargs):
    if any(
        [
            instance.tracker.has_changed("end_date"),
            instance.tracker.has_changed("new_end_date"),
        ]
    ):
        recipients = get_user_model().objects.agents_with_extra()
        if instance.tracker.has_changed("end_date"):
            notify.send(
                instance,
                recipient=recipients,
                verb=NOTIFICATION_TYPES["end_date_changed"],
            )
        if instance.tracker.has_changed("new_end_date"):
            notify.send(
                instance,
                recipient=recipients,
                verb=NOTIFICATION_TYPES["new_end_date_changed"],
            )
