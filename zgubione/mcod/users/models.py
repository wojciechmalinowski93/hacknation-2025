import logging
import time
from enum import Enum
from typing import List, Union
from uuid import uuid4

from constance import config
from django.apps import apps
from django.conf import settings
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    Permission,
    PermissionsMixin,
)
from django.contrib.auth.signals import user_logged_out
from django.contrib.postgres.fields import JSONField
from django.contrib.sessions.backends.cache import KEY_PREFIX
from django.core.cache import caches
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Case, Count, When
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.crypto import constant_time_compare
from django.utils.functional import cached_property
from django.utils.translation import get_language, gettext_lazy as _, override, pgettext_lazy
from encrypted_fields import fields as enc_fields
from model_utils import FieldTracker
from modeltrans.fields import TranslationField

from mcod.core import storages
from mcod.core.api.search.tasks import update_document_task
from mcod.core.db.mixins import AdminMixin, ApiMixin
from mcod.core.db.models import ExtendedModel, TimeStampedModel, TrashModelBase
from mcod.core.managers import SoftDeletableQuerySet
from mcod.core.models import SoftDeletableModel
from mcod.lib.jwt import decode_jwt_token
from mcod.lib.model_sanitization import SanitizedCharField, SanitizedTextField
from mcod.users.managers import (
    MeetingFileManager,
    MeetingFileTrashManager,
    MeetingManager,
    MeetingTrashManager,
)
from mcod.users.signals import user_changed
from mcod.watchers.models import MODEL_TO_OBJECT_NAME, Notification

TOKEN_TYPES = (
    (0, _("Email validation token")),
    (1, _("Password reset token")),
    (2, _("Charts preview token")),
)

ACADEMY_PERMS_CODENAMES = [
    "add_course",
    "change_course",
    "delete_course",
    "view_course",
    "add_coursemodule",
    "change_coursemodule",
    "delete_coursemodule",
    "view_coursemodule",
    "add_coursetrash",
    "change_coursetrash",
    "delete_coursetrash",
    "view_coursetrash",
]

LABS_PERMS_CODENAMES = [
    "add_labevent",
    "change_labevent",
    "delete_labevent",
    "view_labevent",
    "add_labreport",
    "change_labreport",
    "delete_labreport",
    "view_labreport",
    "add_labeventtrash",
    "change_labeventtrash",
    "delete_labeventtrash",
    "view_labeventtrash",
]


class LoggingMethod(str, Enum):
    """CLass represents different kind of logging to service methods."""

    WK = "WK"
    FORM = _("Form")


session_cache = caches[settings.SESSION_CACHE_ALIAS]

logger = logging.getLogger("mcod")


class UserQuerySet(SoftDeletableQuerySet):

    def autocomplete(self, user, query=None):
        if not user.is_superuser:
            return self.none()
        if query:
            return self.filter(email__icontains=query)
        return self


class UserManager(BaseUserManager):
    _queryset_class = UserQuerySet
    use_in_migrations = True

    def _create_user(self, email, password=None, **extra_fields):
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_official", email.endswith("gov.pl"))
        extra_fields.setdefault("state", "pending")
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_official", True)
        extra_fields.setdefault("state", "active")
        extra_fields.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra_fields)

    def get_or_none(self, *args, **kwargs):
        try:
            return self.get(*args, **kwargs)
        except User.DoesNotExist:
            return None

    def get_by_natural_key(self, username):
        return self.get(**{self.model.USERNAME_FIELD + "__iexact": username})

    def agents(self):
        return self.filter(state="active", is_agent=True).order_by("agent_organization_main__title", "email")

    def autocomplete(self, user, query=None):
        return super().get_queryset().autocomplete(user, query=query)

    def extra_agents(self):
        return self.filter(state="active", extra_agent_of__isnull=False)

    def agents_with_extra(self):
        return self.agents() | self.extra_agents()

    def _get_page(self, queryset, page=1, per_page=20, **kwargs):
        paginator = Paginator(queryset, per_page)
        return paginator.get_page(page)

    def agents_paginated(self, **kwargs):
        qs = self.agents()
        return self._get_page(qs, **kwargs)


def agents_choices():
    return {"is_agent": True}


def fav_charts_default():
    return {"slot-1": {}, "slot-2": {}}


class User(
    AdminMixin,
    ApiMixin,
    AbstractBaseUser,
    PermissionsMixin,
    SoftDeletableModel,
    TimeStampedModel,
):
    email = models.EmailField(verbose_name=_("Email"), unique=True)
    password = models.CharField(max_length=130, verbose_name=_("Password"))
    fullname = SanitizedCharField(max_length=100, blank=True, null=True, verbose_name=_("Full name"))
    phone = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_("Phone number"),
        db_column="tel",
    )
    phone_internal = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name=_("int."),
        db_column="tel_internal",
    )
    is_staff = models.BooleanField(default=False, verbose_name=_("Editor"))  # is_staff ?
    is_superuser = models.BooleanField(
        verbose_name=_("Admin status"),
        help_text=_("Designates that this user has all permissions " "without explicitly assigning them."),
        default=False,
    )
    is_official = models.BooleanField(default=False, verbose_name=_("Official"))
    is_agent = models.BooleanField(default=False, verbose_name=_("agent"))
    state = models.CharField(
        max_length=20,
        verbose_name=_("State"),
        default="pending",
        choices=settings.USER_STATE_CHOICES,
    )  # wymagane, określone wartości
    email_confirmed = models.DateTimeField(null=True, blank=True, verbose_name=_("Email confirmation date"))
    organizations = models.ManyToManyField(
        "organizations.Organization",
        db_table="user_organization",
        verbose_name=_("Organizations"),
        blank=True,
        related_name="users",
        related_query_name="user",
    )
    agent_organizations = models.ManyToManyField(
        "organizations.Organization",
        verbose_name=_("Organizations"),
        blank=True,
        related_name="agents",
    )
    agent_organization_main = models.ForeignKey(
        "organizations.Organization",
        models.SET_NULL,
        blank=True,
        null=True,
        verbose_name=_("main organization of agent"),
        related_name="agent_organization_main_users",
    )
    extra_agent_of = models.ForeignKey(
        "self",
        models.SET_NULL,
        blank=True,
        null=True,
        limit_choices_to=agents_choices,
        verbose_name=_("extra agent of"),
        related_name="extra_agent",
    )
    from_agent = models.ForeignKey("self", models.SET_NULL, blank=True, null=True)
    followed_datasets = models.ManyToManyField(
        "datasets.Dataset",
        verbose_name=_("Followed datasets"),
        blank=True,
        through="users.UserFollowingDataset",
        through_fields=("follower", "dataset"),
        related_name="users_following",
        related_query_name="user",
    )
    subscriptions_report_opt_in = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Enable daily email report of changes in subscribed objects"),
    )
    rodo_privacy_policy_opt_in = models.DateTimeField(null=True, blank=True, verbose_name=_("RODO & privacy policy accepted"))
    lang = models.CharField(
        max_length=2,
        verbose_name=_("User language"),
        default=settings.LANGUAGE_CODE,
        choices=settings.LANGUAGES,
    )
    discourse_user_name = models.CharField(max_length=100, blank=True, null=True, editable=False)
    discourse_api_key = models.CharField(max_length=100, blank=True, null=True, editable=False)

    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Designates whether this user should be treated as active. " "Unselect this instead of deleting accounts."),
    )
    fav_charts = JSONField(
        blank=True,
        null=True,
        default=fav_charts_default,
        verbose_name=_("Favorite charts"),
    )

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"

    objects = UserManager()

    _pesel = enc_fields.EncryptedCharField(null=True, max_length=11, blank=True)
    pesel = enc_fields.SearchField(
        hash_key=settings.FIELD_ENCRYPTION_KEYS[0],
        encrypted_field_name="_pesel",
    )
    is_gov_auth = models.BooleanField(default=False)
    last_logged_method = models.CharField(
        choices=[(field.value, field.value) for field in LoggingMethod], blank=True, null=True, max_length=50
    )

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        db_table = "user"
        default_manager_name = "objects"

    def update_last_logging_method(self, logging_form: LoggingMethod) -> None:
        """Update user last logging method."""
        self.last_logged_method = logging_form
        self.save()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_from_agent_id = getattr(self.from_agent, "pk", None)

    def __str__(self):
        return self.email

    def check_session_valid(self, auth_header):
        try:
            user_payload = decode_jwt_token(auth_header)["user"]
        except Exception:
            return False

        if "session_key" not in user_payload:
            return False
        session_id = user_payload["session_key"]
        session_data = session_cache.get("%s%s" % (KEY_PREFIX, session_id))
        if not session_data:
            return False

        if not {"_auth_user_hash", "_auth_user_id"} <= set(session_data):
            return False

        if session_data["_auth_user_id"] != str(self.id):
            return False

        session_auth_hash = self.get_session_auth_hash()

        if session_data["_auth_user_hash"] != session_auth_hash:
            return False

        if not constant_time_compare(session_data["_auth_user_hash"], session_auth_hash):
            return False

        return True

    @staticmethod
    def _get_absolute_url(url):
        return f"{settings.BASE_URL}/{get_language()}{url}"

    def _get_active_token(self, token_type):
        return (
            Token.objects.filter(user=self, token_type=token_type, expiration_date__gte=timezone.now())
            .order_by("-expiration_date")
            .first()
        )

    def _get_or_create_token(self, token_type, expiration_delta=None):
        token = self._get_active_token(token_type)
        if not token:
            expiration_delta = expiration_delta or timezone.timedelta(hours=settings.TOKEN_EXPIRATION_TIME)
            token = Token.objects.create(user=self, token_type=token_type, expiration_date=timezone.now() + expiration_delta)
        return token.token

    @property
    def institutions(self):
        return self.organizations

    @cached_property
    def staff_institutions(self):
        return self.institutions if self.is_staff else []

    @property
    def institutions_ids_list_as_str(self):
        objs = self.institutions.all() if self.is_staff else self.institutions.none()
        return ",".join(str(x.id) for x in objs)

    @property
    def is_anonymous(self):
        return False

    @cached_property
    def is_newsletter_receiver(self):
        if hasattr(self, "newsletter_subscription"):
            return self.newsletter_subscription.is_active
        return False

    @property
    def email_validation_token(self):
        return self._get_or_create_token(0)

    @property
    def email_validation_url(self):
        return settings.EMAIL_VALIDATION_PATH % self.email_validation_token

    @property
    def email_validation_absolute_url(self):
        return self._get_absolute_url(self.email_validation_url)

    @property
    def extra_agents_list(self):
        return self.mark_safe(
            ", ".join(
                [
                    '<a href="%s" target="_blank">%s</a>' % (x.admin_change_url, x.email)
                    for x in self.extra_agent.order_by("email")
                ]
            )
        )

    @property
    def password_reset_token(self):
        return self._get_or_create_token(1)

    @property
    def password_reset_confirm_url(self):
        return "/auth/password/reset/%s" % self.password_reset_token

    @property
    def password_reset_url(self):
        return settings.PASSWORD_RESET_PATH % self.password_reset_token

    @property
    def password_reset_absolute_url(self):
        return self._get_absolute_url(self.password_reset_url)

    @cached_property
    def schedule_dashboard_notifications(self):
        if self.is_superuser or self.is_agent or self.extra_agent_of:
            return self.notifications.unread()
        return self.notifications.none()

    @cached_property
    def _planned_user_schedule(self):
        return self.user_schedules.filter(schedule__state="planned").last()

    @property
    def planned_schedule(self):
        schedule_model = apps.get_model("schedules.Schedule")
        return schedule_model.get_current_plan()

    @property
    def planned_user_schedule_items(self):
        return self._planned_user_schedule.user_schedule_items_included if self._planned_user_schedule else None

    @property
    def planned_user_schedule(self):
        return self._planned_user_schedule or {
            "email": self.email,
            "institution": (self.agent_organization_main.title if self.agent_organization_main else ""),
            "items_count": 0,
            "is_ready": False,
            "is_blocked": False,
            "recommended_items_count": 0,
            "implemented_items_count": 0,
            "state": "planned",
        }

    @cached_property
    def schedule_notification_recipients(self):
        return self.__class__.objects.filter(is_agent=True, id=self.id) | self.extra_agent.all()

    @property
    def system_role(self):
        if self.is_superuser:
            return "admin"
        elif self.is_staff:
            return "editor"
        elif self.agent:
            return "representative"
        elif self.is_official:
            return "official"
        return "user"

    @property
    def system_roles(self):
        roles = []
        if self.is_superuser:
            roles.append("admin")
        if self.is_staff:
            roles.append("editor")
        if self.is_official:
            roles.append("official")
        if self.agent:
            roles.append("representative")
        return roles

    @property
    def username(self):
        return self.fullname

    @property
    def count_datasets_created(self):
        return self.datasets_created.all().count()

    @property
    def count_datasets_modified(self):
        return self.datasets_modified.all().count()

    @property
    def is_normal_staff(self):
        return not self.is_superuser and self.is_staff

    @property
    def has_access_to_academy_in_dashboard(self):
        return self.is_superuser or self.is_official or self.agent or self.is_staff or self.is_academy_admin

    @property
    def has_access_to_forum(self):
        _s = True if (self.discourse_user_name and self.discourse_api_key) else False
        return self.is_active and (self.is_superuser or self.agent) and _s

    @property
    def has_access_to_laboratory_in_dashboard(self):
        return self.is_authenticated

    @property
    def has_access_to_meetings_in_dashboard(self):
        return self.is_superuser or self.agent

    @property
    def has_access_to_suggestions_in_dashboard(self):
        return self.is_superuser or self.is_staff or self.agent

    @property
    def has_access_to_public_institutions(self):
        return self.is_superuser or self.organizations.public().exists()

    @property
    def has_access_to_private_institutions(self):
        return self.is_superuser or self.organizations.private().exists()

    @property
    def has_access_to_admin_panel(self) -> bool:
        """Check if the given user has access to the admin panel."""
        return bool(self.is_staff or self.is_superuser)

    @property
    def is_academy_admin(self):
        perms = self.user_permissions.values_list("codename", flat=True)
        return bool(ACADEMY_PERMS_CODENAMES and all([perm in perms for perm in ACADEMY_PERMS_CODENAMES]))

    @property
    def is_editor(self):
        """
        Note: this property is not saying that user is an editor.
        Flag responsible for telling if user is editor is called is_staff
        """
        return all([self.is_staff, not self.is_academy_admin, not self.is_labs_admin])

    @property
    def is_labs_admin(self):
        perms = self.user_permissions.values_list("codename", flat=True)
        return bool(LABS_PERMS_CODENAMES and all([perm in perms for perm in LABS_PERMS_CODENAMES]))

    @property
    def agent(self):
        return bool(self.is_agent or self.extra_agent_of)

    @property
    def agent_organization(self):
        if self.extra_agent_of:
            return self.extra_agent_of.agent_organization_main
        return self.agent_organization_main

    @property
    def agent_organization_id(self):
        return self.agent_organization.id if self.agent_organization else None

    @cached_property
    def agent_institutions(self):
        if self.extra_agent_of:
            return self.extra_agent_of.agent_organizations
        return self.agent_organizations

    @cached_property
    def agent_institutions_included(self):
        return self.agent_institutions.annotate(
            is_main=Case(
                When(id=self.agent_organization_id, then=True),
                default=False,
                output_field=models.BooleanField(),
            )
        ).order_by("-is_main")

    @property
    def has_complete_staff_data(self):
        return all(field is not None for field in (self.phone, self.fullname))

    @property
    def discourse_username(self):
        return self.discourse_user_name

    @property
    def send_registration_email_admin_url(self):
        return self._reverse("admin:send-registration-email", args=[self.id])

    @classmethod
    def accusative_case(cls):
        return _("acc: User")

    def is_editor_of_organization(self, organization):
        return self.is_staff and organization in self.organizations.all()

    def set_academy_perms(self, is_academy_admin=False):
        perms = Permission.objects.filter(content_type__app_label="academy", codename__in=ACADEMY_PERMS_CODENAMES)
        (self.user_permissions.add(*perms) if is_academy_admin else self.user_permissions.remove(*perms))

    def set_labs_perms(self, is_labs_admin=False):
        perms = Permission.objects.filter(content_type__app_label="laboratory", codename__in=LABS_PERMS_CODENAMES)
        (self.user_permissions.add(*perms) if is_labs_admin else self.user_permissions.remove(*perms))

    def get_dashboard_subscriptions(self):
        return {
            "datasets": self.subscriptions.filter(watcher__object_name="datasets.Dataset", watcher__is_active=True).count(),
            "queries": self.subscriptions.filter(watcher__object_name="query", watcher__is_active=True).count(),
        }

    def get_unread_notifications(self):
        result = (
            Notification.objects.filter(subscription__user=self, status="new")
            .values("subscription__watcher__object_name")
            .annotate(total=Count("subscription__watcher__object_name"))
        )
        data = {}
        for item in result:
            _v = MODEL_TO_OBJECT_NAME[item["subscription__watcher__object_name"]]
            key = "queries" if _v == "query" else "{}s".format(_v)
            data[key] = {"new": item["total"]}
        return data

    @property
    def subscriptions_report_enabled(self):
        _enabled = True if self.subscriptions_report_opt_in else False
        return settings.ENABLE_SUBSCRIPTIONS_EMAIL_REPORTS and _enabled

    def can_add_resource_chart(self, resource, is_default, chart=None):
        if self.is_superuser:  # admin dla wszystkich instytucji.
            if any(
                (
                    is_default,
                    not is_default and not chart,
                    chart and chart.created_by == self,
                )
            ):
                return True
            return False
        elif self.is_staff:
            if resource.dataset.organization in self.organizations.all():  # edytor w swojej instytucji.
                if any(
                    (
                        is_default,
                        not is_default and not chart,
                        chart and chart.created_by == self,
                    )
                ):
                    return True
            else:  # edytor poza swoją instytucją.
                if resource.is_chart_creation_blocked:
                    return False
                if any(
                    (
                        not is_default and not chart,
                        chart and chart.is_private and chart.created_by == self,
                    )
                ):
                    return True
            return False
        else:  # zwykły dla wszystkich instytucji.
            if resource.is_chart_creation_blocked:
                return False
            if any(
                (
                    not is_default and not chart,
                    chart and chart.is_private and chart.created_by == self,
                )
            ):
                return True
        return False

    def can_delete_resource_chart(self, chart):
        if self.is_superuser:  # admin dla wszystkich instytucji.
            if any((chart.is_default, chart.is_private and chart.created_by == self)):
                return True
            return False
        elif self.is_staff:
            if chart.organization in self.organizations.all():  # edytor w swojej instytucji.
                if any((chart.is_default, chart.is_private and chart.created_by == self)):
                    return True
            else:  # edytor poza swoją instytucją.
                if chart.is_private and chart.created_by == self:
                    return True
            return False
        else:  # zwykły dla wszystkich instytucji.
            if chart.is_private and chart.created_by == self:
                return True
        return False

    def resend_activation_email(self):
        return self.send_mail(
            "Reset password",
            self.email_validation_absolute_url,
            config.ACCOUNTS_EMAIL,
            [self.email],
        )

    def send_password_reset_email(self):
        context = {"link": self.password_reset_absolute_url, "host": settings.BASE_URL}
        msg_plain = render_to_string("mails/password-reset.txt", context)
        msg_html = render_to_string("mails/password-reset.html", context)

        return self.send_mail(
            "Reset hasła",
            msg_plain,
            config.ACCOUNTS_EMAIL,
            [self.email],
            html_message=msg_html,
        )

    def send_registration_email(self):
        context = {
            "link": self.email_validation_absolute_url,
            "host": settings.BASE_URL,
            "limit": settings.TOKEN_EXPIRATION_TIME,
        }
        msg_plain = render_to_string("mails/confirm-registration.txt", context)
        msg_html = render_to_string("mails/confirm-registration.html", context)

        return self.send_mail(
            "Aktywacja konta",
            msg_plain,
            config.ACCOUNTS_EMAIL,
            [self.email],
            html_message=msg_html,
        )

    def send_subscriptions_report(self, date_from, date_till):
        if self.subscriptions_report_enabled:
            notifications = Notification.objects.filter(
                subscription__user=self, created__gte=date_from, created__lt=date_till
            ).order_by("created")

            if notifications:
                context = {
                    "notifications": notifications,
                    "date_from": date_from,
                    "base_url": settings.BASE_URL,
                }
                with override(self.lang):
                    context["base_url_with_lang"] = f"{settings.BASE_URL}/{self.lang}"
                    msg_plain = render_to_string("mails/subscriptions-daily.txt", context=context)
                    msg_html = render_to_string("mails/subscriptions-daily.html", context=context)

                    self.send_mail(
                        _("Report of activity of observed objects on the dane.gov.pl portal"),
                        msg_plain,
                        config.FOLLOWINGS_EMAIL,
                        [self.email],
                        html_message=msg_html,
                    )

    @property
    def has_from_agent_changed(self):
        return self._original_from_agent_id != getattr(self.from_agent, "pk", None)

    @property
    def is_gov_linked(self) -> bool:
        """Checks if the user is linked to the login.gov.pl service (has updated PESEL)."""
        return bool(self.pesel)

    @property
    def connected_gov_users(self) -> list:
        """Retrieves a list of other active users linked to the login.gov.pl service,
        connected by the same PESEL number. This property only returns users for instances
        that are authenticated via login.gov.pl service and not marked as removed
        or permanently removed.
        """
        other_users = self._meta.model.objects.filter(
            pesel=self.pesel,
            state="active",
            is_active=True,
            is_removed=False,
            is_permanently_removed=False,
        ).exclude(id=self.id)
        return list(other_users) if self.is_gov_linked and self.is_gov_auth else []

    @property
    def connected_gov_users_for_admin_page(self) -> List[Union[str, None]]:
        """
        Returns a list of email addresses for user accounts that are valid for switching on the admin page.

        The validation checks if the users meet the following criteria:
        - They are administrators (i.e., `is_superuser` is `True`).
        - They are editors (i.e., `is_editor` property evaluates to `True`).

        Excludes the current user from the results.
        """
        return [user for user in self.connected_gov_users if user.has_access_to_admin_panel]


@receiver(pre_save, sender=User)
def pre_save_handler(sender, instance, *args, **kwargs):
    instance.full_clean()
    if instance.is_removed or instance.is_permanently_removed:
        instance.email = f"{time.time()}_{uuid4()}@dane.gov.pl"
        instance.fullname = ""
        instance.status = "blocked"
        instance.is_staff = False
        instance.is_superuser = False

    if instance.from_agent and not instance.is_agent:
        instance.from_agent = None


@receiver(post_save, sender=User)
def post_save_handler(
    sender,
    instance,
    signal,
    created=False,
    raw=False,
    update_fields=None,
    using="default",
    *args,
    **kwargs,
):
    if not instance.is_agent and instance.extra_agent.exists():
        instance.extra_agent.update(extra_agent_of=None)
    if instance.has_from_agent_changed:
        obj = instance.from_agent
        if instance.is_agent and obj:
            with transaction.atomic():
                User.objects.filter(id=instance.id).update(agent_organization_main=obj.agent_organization_main)
                obj.user_schedules.filter(schedule__state__in=["planned", "implemented"]).update(user=instance)
                obj.extra_agent.update(extra_agent_of=instance)
                obj.notifications.filter(unread=True).update(recipient=instance)
                instance.agent_organizations.set(obj.agent_organizations.all())
                obj.is_agent = False
                obj.save()

    user_changed.send(sender=User, user=instance, created=created)


@receiver(user_logged_out)
def handle_logout(sender, request, user, **kwargs) -> None:
    if user:
        user.is_gov_auth = False
        user.save()


def get_token_expiration_date():
    return timezone.now() + timezone.timedelta(hours=settings.TOKEN_EXPIRATION_TIME)


class Token(TimeStampedModel):
    user = models.ForeignKey(
        "User",
        on_delete=models.CASCADE,
        blank=False,
        verbose_name=_("User"),
        related_name="tokens",
    )
    token = models.UUIDField(default=uuid4, editable=False, blank=False, verbose_name=_("Token"))
    token_type = models.IntegerField(default=0, choices=TOKEN_TYPES, blank=False, verbose_name=_("Token type"))
    expiration_date = models.DateTimeField(
        default=get_token_expiration_date,
        null=False,
        blank=False,
        editable=False,
        verbose_name=_("Expiration date"),
    )

    class Meta:
        verbose_name = _("Token")
        verbose_name_plural = _("Tokens")
        db_table = "token"

    @property
    def is_valid(self):
        return True if timezone.now() <= self.expiration_date else False

    def invalidate(self):
        if self.is_valid:
            self.expiration_date = timezone.now()
            self.save()


class FollowingModel(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE)

    @property
    def object_id(self):
        return getattr(self, self.object_type).id

    @property
    def object_type(self):
        return self._meta.db_table[len("user_following_") :]

    class Meta:
        abstract = True


class UserFollowingDataset(FollowingModel):
    dataset = models.ForeignKey("datasets.Dataset", on_delete=models.CASCADE)

    class Meta:
        db_table = "user_following_dataset"


class Meeting(ExtendedModel):
    MEETING_STATES = {
        "planned": pgettext_lazy("Planned", "meeting state"),
        "finished": pgettext_lazy("Finished", "meeting state"),
    }
    title = SanitizedCharField(max_length=300, verbose_name=_("title"))
    venue = SanitizedCharField(max_length=300, verbose_name=_("venue"))
    description = SanitizedTextField(verbose_name=_("agenda"))
    start_date = models.DateField(null=True, verbose_name=_("meeting date"))
    start_time = models.TimeField(null=True, verbose_name=_("start time"))
    end_time = models.TimeField(null=True, verbose_name=_("end time"))

    members = models.ManyToManyField("users.User", related_name="meetings", verbose_name=_("members"))

    objects = MeetingManager()
    trash = MeetingTrashManager()
    i18n = TranslationField()
    tracker = FieldTracker()

    def __str__(self):
        return self.title

    class Meta:
        default_manager_name = "objects"
        verbose_name = _("meeting")
        verbose_name_plural = _("meetings")

    @property
    def duration_hours(self):
        return f"{self.start_time_str}-{self.end_time_str}"

    @property
    def start_time_str(self):
        return f"{self.start_time:%H:%M}"

    @property
    def end_time_str(self):
        return f"{self.end_time:%H:%M}"

    @property
    def materials(self):
        return self.files.order_by("id")


def meeting_file_path(instance, filename):
    return f"{instance.uuid}/{filename}"


class MeetingFile(ExtendedModel):
    file = models.FileField(
        verbose_name=_("file"),
        storage=storages.get_storage("meetings"),
        max_length=2000,
        upload_to=meeting_file_path,
    )
    meeting = models.ForeignKey(Meeting, on_delete=models.DO_NOTHING, related_name="files")

    objects = MeetingFileManager()
    trash = MeetingFileTrashManager()
    i18n = TranslationField()
    tracker = FieldTracker()

    @property
    def download_url(self):
        return self._get_absolute_url(self.file.url, use_lang=False) if self.file else None

    @property
    def name(self):
        return self._get_basename(self.file.name)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = _("meeting file")
        verbose_name_plural = _("meeting files")
        default_manager_name = "objects"


class MeetingTrash(Meeting, metaclass=TrashModelBase):
    class Meta:
        proxy = True
        verbose_name = _("Trash (Meeting)")
        verbose_name_plural = _("Trash (Meetings)")


@receiver(post_delete, sender=UserFollowingDataset)
@receiver(post_save, sender=UserFollowingDataset)
def es_refresh(sender, instance, *args, **kwargs):
    resource_name = sender.__name__[13:].lower()
    resource = getattr(instance, resource_name)
    update_document_task.delay(resource._meta.app_label, resource._meta.object_name, resource.id)
