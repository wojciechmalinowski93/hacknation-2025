from operator import itemgetter
from urllib.parse import parse_qsl, urlsplit, urlunsplit

import dpath.util
import requests
from django.apps import apps
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils.functional import cached_property
from django.utils.timezone import now
from django.utils.translation import gettext_lazy as _
from model_utils import FieldTracker

from mcod.core.api.search.tasks import update_document_task
from mcod.core.db.mixins import ApiMixin
from mcod.core.db.models import TimeStampedModel
from mcod.core.versioning import VERSIONS
from mcod.watchers.signals import query_watcher_created
from mcod.watchers.tasks import model_watcher_updated_task, query_watcher_updated_task

CURRENT_VERSION = max(VERSIONS)

OBJECT_NAME_TO_MODEL = {
    "application": "applications.Application",
    "category": "categories.Category",
    "dataset": "datasets.Dataset",
    "resource": "resources.Resource",
    "institution": "organizations.Organization",
    "tag": "tags.Tag",
    "query": "query",
}

DEPRECATED_MODELS = ["articles.Article", "articles.ArticleCategory"]

MODEL_TO_OBJECT_NAME = {model: obj for obj, model in OBJECT_NAME_TO_MODEL.items()}

STATUS_CHOICES = (("active", _("Active")), ("canceled", _("Canceled")))

WATCHER_TYPE_MODEL = "model"
WATCHER_TYPE_SEARCH_QUERY = "query"

WATCHER_TYPES = (
    (WATCHER_TYPE_MODEL, "Model"),
    (WATCHER_TYPE_SEARCH_QUERY, "Search query"),
)

NOTIFICATION_STATUS_CHOICES = (("new", "New"), ("read", "Read"))

NOTIFICATION_TYPES = (
    ("object_restored", _("Object republished")),
    ("object_removed", _("Object withdrawaled")),
    ("object_updated", _("Object updated")),
    ("related_object_publicated", _("Related object publicated")),
    ("related_object_updated", _("Related object updated")),
    ("related_object_restored", _("Related object republished")),
    ("related_object_removed", _("Related object withdrawaled")),
    ("result_count_incresed", _("Results incresed")),
    ("result_count_decresed", _("Results decresed")),
)

OBJ_STATE_2_NOTIFICATION_TYPES = {
    "publicated": "object_updated",
    "updated": "object_updated",
    "removed": "object_removed",
    "restored": "object_restored",
    "m2m_added": "related_object_publicated",
    "m2m_removed": "related_object_removed",
    "m2m_cleaned": "related_object_removed",
    "m2m_updated": "related_object_updated",
    "m2m_restored": "related_object_restored",
    "incresed": "result_count_incresed",
    "decresed": "result_count_decresed",
}


class InvalidRefField(Exception):
    pass


class InvalidRefValue(Exception):
    pass


class ObjectCannotBeWatched(Exception):
    pass


class SubscriptionCannotBeCreated(Exception):
    pass


class SubscribedObjectDoesNotExist(Exception):
    pass


class DuplicateSubscriptionName(Exception):
    pass


class Watcher(TimeStampedModel):
    watcher_type = models.CharField(max_length=15, choices=WATCHER_TYPES, null=False, default=WATCHER_TYPE_MODEL)
    object_name = models.CharField(max_length=128, null=False)
    object_ident = models.CharField(max_length=1000, null=False)
    ref_field = models.CharField(max_length=64, null=False, default="last_modified")
    ref_value = models.TextField(null=False)
    last_ref_change = models.DateTimeField(null=True)
    is_active = models.BooleanField(null=False, default=True)
    tracker = FieldTracker(fields=["ref_value", "is_active"])
    customfields = JSONField(default=dict)

    class Meta:
        indexes = [models.Index(fields=["watcher_type", "object_name", "object_ident"])]
        constraints = [
            models.UniqueConstraint(
                fields=["watcher_type", "object_name", "object_ident"],
                name="unique_model_watcher",
            )
        ]

    @cached_property
    def obj(self):
        if self.watcher_type == "model":
            app_label, model_name = self.object_name.split(".")
            model = apps.get_model(app_label, model_name.title())
            if hasattr(model, "raw"):
                instance = model.raw.filter(pk=self.object_ident).first()
            else:
                instance = model.objects.filter(pk=self.object_ident).first()
            return instance

        return None

    @property
    def obj_type(self):
        return MODEL_TO_OBJECT_NAME.get(self.object_name, "").lower() if self.watcher_type == "model" else "query"

    def get_obj_url(self, api_url):
        if self.watcher_type == "model":
            url = self.obj.get_api_url(base_url=api_url) if self.obj else None
        else:
            url = self.object_ident
        return url

    def get_object_name_display(self):
        return _(MODEL_TO_OBJECT_NAME[self.object_name].title())


@receiver(pre_save, sender=Watcher)
def lower_object_name(sender, instance, *args, **kwargs):
    instance.object_name = instance.object_name.lower()


class ModelWatcherManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(watcher_type=WATCHER_TYPE_MODEL)

    def create(self, **kwargs):
        return super().create(watcher_type=WATCHER_TYPE_MODEL, **kwargs)

    def create_from_instance(self, instance):
        if not instance.is_watchable:
            raise ObjectCannotBeWatched("Watcher for this object cannot be created.")

        watched_field = getattr(instance, "watcher_ref_field", "modified")
        if not hasattr(instance, watched_field):
            raise InvalidRefField("Watcher reference field is invalid.")

        watched_field_value = str(getattr(instance, watched_field))
        is_active = True if instance.status == "published" and instance.is_removed is False else False
        object_name = "{}.{}".format(instance._meta.app_label, instance._meta.object_name)
        return self.create(
            object_name=object_name,
            object_ident=str(instance.id),
            ref_field=watched_field,
            ref_value=watched_field_value,
            last_ref_change=now(),
            is_active=is_active,
        )

    def update_from_instance(self, instance, obj_state="updated", notify_subscribers=True, force=False, **kwargs):
        watcher = self.get_from_instance(instance)
        instance = instance or watcher.obj

        watcher.ref_value = str(getattr(instance, watcher.ref_field))
        watcher.is_active = True if instance.status == "published" and instance.is_removed is False else False
        changed = force if force else watcher.tracker.has_changed("ref_value") or watcher.tracker.has_changed("is_active")
        if changed:
            prev_value = watcher.tracker.previous("ref_value")
            ModelWatcher.objects.filter(pk=watcher.id).update(
                last_ref_change=now(),
                ref_value=watcher.ref_value,
                is_active=watcher.is_active,
            )
            if notify_subscribers and (obj_state == "removed" or watcher.is_active):
                _type = OBJ_STATE_2_NOTIFICATION_TYPES[obj_state]

                model_watcher_updated_task.s(watcher.id, _type, prev_value).apply_async()

            return True

        return False

    def get_from_instance(self, instance):
        meta = instance._meta
        _object_name = meta.concrete_model._meta.object_name if meta.proxy else meta.object_name
        object_name = "{}.{}".format(meta.app_label, _object_name)

        return self.get(object_name=object_name, object_ident=str(instance.id))

    def get_or_create_from_instance(self, instance):
        created = False
        try:
            watcher = self.get_from_instance(instance)
        except ModelWatcher.DoesNotExist:
            watcher = self.create_from_instance(instance)
            created = True
        return watcher, created


class ModelWatcher(Watcher):
    objects = ModelWatcherManager()

    class Meta:
        proxy = True


class SearchQueryWatcherManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(watcher_type=WATCHER_TYPE_SEARCH_QUERY)

    def create(self, **kwargs):
        return super().create(watcher_type=WATCHER_TYPE_SEARCH_QUERY, **kwargs)

    @staticmethod
    def _normalize_url(url):
        url_split = urlsplit(url)
        parts = parse_qsl(url_split.query)
        parts.sort(key=itemgetter(0, 1))
        new_query = "&".join("{}={}".format(*part) for part in parts)
        url_split = url_split._replace(query=new_query)
        return urlunsplit(url_split)

    @staticmethod
    def _prepare_headers(headers=None):
        headers = headers or {}
        _headers = {}
        _headers["lang"] = headers.get("Accept-Language", settings.LANGUAGE_CODE)
        _headers["api_version"] = str(headers.get("X-API-VERSION", CURRENT_VERSION))

        return _headers

    def reload(self):
        query = self.filter(object_name="query", is_active=True, ref_field__isnull=False)
        for watcher in query:
            int_url, ext_url = urlsplit(settings.API_URL_INTERNAL), urlsplit(watcher.object_ident)
            ext_url = ext_url._replace(scheme=int_url.scheme)._replace(netloc=int_url.netloc)
            _url = urlunsplit(ext_url)
            _headers = watcher.customfields.get("headers") or {}
            headers = {
                "User-Agent": "mcod-internal",
                "Accept-Language": _headers.get("lang") or settings.LANGUAGE_CODE,
                "X-API-VERSION": _headers.get("api_version") or str(CURRENT_VERSION),
            }
            response = requests.get(_url, headers=headers, verify=False, timeout=(3.0, 5.0))
            if response.status_code != 200:
                continue

            try:
                field_value = dpath.util.get(response.json(), watcher.ref_field)
                new_value = int(field_value)
                old_value = int(watcher.ref_value)

                if new_value != old_value:
                    obj_state = "incresed" if new_value > old_value else "decresed"
                    SearchQueryWatcher.objects.update_from_url(
                        watcher.object_ident,
                        new_value,
                        headers=headers,
                        obj_state=obj_state,
                        notify_subscribers=True,
                    )
            except (KeyError, ValueError, InvalidRefValue):
                continue

    def create_from_url(self, url, objects_count, headers=None):
        _headers = self._prepare_headers(headers)
        _url = self._normalize_url(url)
        watcher = self.create(
            object_name="query",
            object_ident=_url,
            ref_field="/meta/count",
            ref_value=objects_count,
            last_ref_change=now(),
            customfields={"headers": _headers},
        )
        query_watcher_created.send(watcher._meta.model, instance=watcher, created_at=now())

        return watcher

    def update_from_url(
        self,
        url,
        new_value,
        headers=None,
        obj_state="incresed",
        notify_subscribers=True,
        force=False,
    ):
        watcher = self.get_from_url(url, headers=headers)

        try:
            new_value = int(new_value)
        except TypeError:
            raise InvalidRefValue("Value must be a number")
        prev_value = int(watcher.ref_value)
        changed = force if force else prev_value != new_value

        if changed:
            self.filter(id=watcher.id).update(last_ref_change=now(), ref_value=new_value)
            if notify_subscribers and watcher.is_active:
                _type = OBJ_STATE_2_NOTIFICATION_TYPES[obj_state]

                query_watcher_updated_task.s(watcher.id, _type, prev_value).apply_async()

            return True

        return False

    def get_from_url(self, url, headers=None):
        _headers = self._prepare_headers(headers)
        api_version = _headers["api_version"]

        url = self._normalize_url(url)

        return self.get(
            object_name="query",
            object_ident=url,
            customfields__headers__isnull=False,
            customfields__headers__api_version__isnull=False,
            customfields__headers__api_version=api_version,
        )

    def get_or_create_from_url(self, url, objects_count, headers=None):
        created = False
        try:
            watcher = self.get_from_url(url, headers=headers)
        except SearchQueryWatcher.DoesNotExist:
            watcher = self.create_from_url(url, objects_count, headers=headers)
            created = True
        return watcher, created


class SearchQueryWatcher(Watcher):
    objects = SearchQueryWatcherManager()

    class Meta:
        proxy = True


class SubscriptionManager(models.Manager):
    def __get_instance(self, name, ident):
        app_label, model_name = OBJECT_NAME_TO_MODEL[name].split(".")
        model = apps.get_model(app_label, model_name.title())
        try:
            return model.objects.get(pk=ident)
        except model.DoesNotExist:
            raise SubscribedObjectDoesNotExist()

    def create_from_data(self, user, data, headers=None, force_id=None, skip_validation=False):
        _name = data["object_name"]
        _ident = data["object_ident"]
        if _name == "query":
            watcher, _ = SearchQueryWatcher.objects.get_or_create_from_url(_ident, data.get("objects_count", 0), headers=headers)
        else:
            instance = self.__get_instance(_name, _ident)
            can_create = True
            if not instance.is_watchable:
                can_create = False
            if not skip_validation:
                if hasattr(instance, "is_removed") and instance.is_removed:
                    can_create = False
                if hasattr(instance, "status") and instance.status != "published":
                    can_create = False

            if not can_create:
                raise SubscriptionCannotBeCreated("Subscription for this object cannot be created.")

            watcher, _ = ModelWatcher.objects.get_or_create_from_instance(instance)

        name = data.get("name") or "{}-{}".format(_name, _ident)
        kwargs = {
            "watcher": watcher,
            "user": user,
            "name": name,
            "customfields": data.get("customfields") or None,
            "reported_till": now(),
        }

        if force_id:
            kwargs["id"] = force_id

        try:
            inst = Subscription(**kwargs)
            inst.validate_unique()
        except ValidationError:
            raise DuplicateSubscriptionName("Subscription with given name already exist.")

        return Subscription.objects.create(**kwargs)

    def update_from_data(self, id, user, data):
        instance = Subscription.objects.get(pk=id)
        for attr, value in data.items():
            setattr(instance, attr, value)
        try:
            instance.validate_unique()
        except ValidationError:
            raise DuplicateSubscriptionName("Subscription with given name already exist.")

        Subscription.objects.filter(id=id, user=user).update(**data)
        instance.refresh_from_db()
        return instance

    def get_from_data(self, user, data, headers=None):
        _name = data["object_name"]
        _ident = data["object_ident"]
        if _name == "query":
            try:
                watcher = SearchQueryWatcher.objects.get_from_url(_ident, headers=headers)
            except SearchQueryWatcher.DoesNotExist:
                raise Subscription.DoesNotExist
        else:
            instance = self.__get_instance(_name, _ident)
            try:
                watcher = ModelWatcher.objects.get_from_instance(instance)
            except ModelWatcher.DoesNotExist:
                raise Subscription.DoesNotExist

        return Subscription.objects.get(watcher=watcher, user=user)

    def get_paginated_results(self, data):
        filters = {"watcher__is_active": True}
        object_name = (data.get("object_name") or "").lower()
        _name = object_name if object_name == WATCHER_TYPE_SEARCH_QUERY else OBJECT_NAME_TO_MODEL.get(object_name)

        if _name:
            filters["watcher__object_name"] = _name

        object_id = data.get("object_id", None)
        if object_id:
            filters["watcher__object_ident"] = object_id

        qs = self.get_queryset().filter(**filters).order_by("-modified")
        page, per_page = data.pop("page", 1), data.pop("per_page", 20)

        paginator = Paginator(qs, per_page)
        return paginator.get_page(page)


class Subscription(ApiMixin, TimeStampedModel):
    watcher = models.ForeignKey(
        Watcher,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        editable=False,
        related_name="subscriptions",
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        editable=False,
        related_name="subscriptions",
    )
    name = models.CharField(max_length=100, null=False, blank=False)
    customfields = JSONField(null=True)
    reported_till = models.DateTimeField(null=True)

    objects = SubscriptionManager()

    @property
    def display_name(self):
        return self.name or getattr(self.watcher.obj, "display_name", None) or "Undefined"

    @property
    def api_url_base(self):
        return "auth/subscriptions"

    @property
    def object_name(self):
        return self._meta.object_name.lower()

    def get_subscribed_obj_title_display(self):
        if self.watcher.watcher_type == "model":
            return self.watcher.obj.title
        return self.watcher.obj.title if self.watcher.watcher_type == "model" else self.name.title()

    def to_jsonapi(self, api_version=None):
        if self.watcher.obj:
            return self.watcher.obj.to_jsonapi(api_version=api_version)

    class Meta:
        unique_together = [["user", "watcher"], ["user", "name"]]


@receiver(post_save, sender=Subscription)
@receiver(post_delete, sender=Subscription)
def update_subscribed_object(sender, instance, *args, **kwargs):
    if instance.watcher.watcher_type == "model":
        obj = instance.watcher.obj
        update_document_task.s(obj._meta.app_label, obj._meta.object_name, obj.id).apply_async_on_commit()


class NotificationManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().exclude(subscription__watcher__object_name__in=DEPRECATED_MODELS)

    def get_paginated_results(self, user, data, subscription_id=None):
        filters = {
            "subscription__user": user,
            # "subscription__watcher__is_active": True
        }
        object_name = (data.get("object_name") or "").lower()
        _name = object_name if object_name == WATCHER_TYPE_SEARCH_QUERY else OBJECT_NAME_TO_MODEL.get(object_name)

        if _name:
            filters["subscription__watcher__object_name"] = _name

        object_id = data.get("object_id", None)
        if object_id:
            filters["subscription__watcher__object_ident"] = object_id

        if "notification_type" in data:
            filters["notification_type"] = data["notification_type"]

        if "status" in data:
            filters["status"] = data["status"]

        if subscription_id:
            filters["subscription_id"] = subscription_id

        qs = Notification.objects.filter(**filters).order_by(("-modified"))
        page, per_page = data.pop("page", 1), data.pop("per_page", 20)

        paginator = Paginator(qs, per_page)
        result = paginator.get_page(page)
        return result


class Notification(ApiMixin, TimeStampedModel):
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.CASCADE,
        null=False,
        blank=False,
        editable=False,
        related_name="notifications",
    )
    notification_type = models.CharField(max_length=30, choices=NOTIFICATION_TYPES)
    status = models.CharField(max_length=20, choices=NOTIFICATION_STATUS_CHOICES)
    ref_value = models.TextField(null=True)

    objects = NotificationManager()

    @property
    def api_url_base(self):
        return "auth/notifications"

    @property
    def object_name(self):
        return self._meta.object_name.lower()
