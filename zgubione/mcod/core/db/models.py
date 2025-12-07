import base64
import logging
import os
import uuid
from functools import partial
from mimetypes import guess_extension, guess_type

from constance import config
from django.apps import apps
from django.conf import settings
from django.core import exceptions
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives, get_connection, send_mail
from django.db import models, router
from django.db.models.base import ModelBase
from django.db.models.deletion import get_candidate_relations_to_delete
from django.dispatch import receiver
from django.template.defaultfilters import truncatechars
from django.template.loader import render_to_string
from django.utils.decorators import classproperty
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import get_language, gettext_lazy as _, override
from model_utils import Choices
from model_utils.models import MonitorField, StatusModel, TimeStampedModel as BaseTimeStampedModel

from mcod.core import signals
from mcod.core.api.search import signals as search_signals
from mcod.core.db.mixins import AdminMixin, ApiMixin
from mcod.core.models import SoftDeletableModel
from mcod.core.registries import rdf_serializers_registry as rsr
from mcod.core.serializers import csv_serializers_registry as csr
from mcod.core.signals import permanently_remove_related_objects
from mcod.core.utils import sizeof_fmt
from mcod.watchers.tasks import update_model_watcher_task

signal_logger = logging.getLogger("signals")
logger = logging.getLogger("mcod")

STATUS_CHOICES = [
    ("published", _("Published")),
    ("draft", _("Draft")),
]

_SIGNALS_MAP = {
    "updated": (search_signals.update_document_with_related, signals.notify_updated),
    "published": (
        search_signals.update_document_with_related,
        signals.notify_published,
    ),
    "restored": (search_signals.update_document_with_related, signals.notify_restored),
    "removed": (search_signals.remove_document_with_related, signals.notify_removed),
    "permanently_removed": (signals.permanently_remove_related_objects,),
    "pre_m2m_added": (signals.notify_m2m_added,),
    "pre_m2m_removed": (signals.notify_m2m_removed,),
    "pre_m2m_cleaned": (signals.notify_m2m_cleaned,),
    "post_m2m_added": (search_signals.update_document_related,),
    "post_m2m_removed": (search_signals.update_document_related,),
    "post_m2m_cleaned": (search_signals.update_document_related,),
    "unsupported": [],
}


def default_slug_value():
    return uuid.uuid4().hex


class CustomManagerForeignKey(models.ForeignKey):

    def __init__(self, *args, **kwargs):
        # https://www.hoboes.com/Mimsy/hacks/custom-managers-django-foreignkeys/
        self.manager_name = kwargs.pop("manager_name", None)
        super().__init__(*args, **kwargs)

    def _get_custom_manager(self):
        return self.related_model._meta.managers_map.get(self.manager_name) if self.manager_name else None

    def formfield(self, *args, **kwargs):
        field = super().formfield(*args, **kwargs)
        custom_manager = self._get_custom_manager()
        if custom_manager:
            field.queryset = custom_manager
        return field

    def field_validate(self, value, model_instance):
        """Copy of ForeignKey parent's: Field.validate()."""
        if not self.editable:
            # Skip validation for non-editable fields.
            return

        if self.choices and value not in self.empty_values:
            for option_key, option_value in self.choices:
                if isinstance(option_value, (list, tuple)):
                    # This is an optgroup, so look inside the group for
                    # options.
                    for optgroup_key, optgroup_value in option_value:
                        if value == optgroup_key:
                            return
                elif value == option_key:
                    return
            raise exceptions.ValidationError(
                self.error_messages["invalid_choice"],
                code="invalid_choice",
                params={"value": value},
            )

        if value is None and not self.null:
            raise exceptions.ValidationError(self.error_messages["null"], code="null")

        if not self.blank and value in self.empty_values:
            raise exceptions.ValidationError(self.error_messages["blank"], code="blank")

    def validate(self, value, model_instance):
        if self.remote_field.parent_link:
            return
        self.field_validate(value, model_instance)
        if value is None:
            return

        using = router.db_for_read(self.remote_field.model, instance=model_instance)

        custom_manager = self._get_custom_manager()
        manager = custom_manager or self.remote_field.model._default_manager  # use custom manager.

        qs = manager.using(using).filter(**{self.remote_field.field_name: value})
        qs = qs.complex_filter(self.get_limit_choices_to())
        if not qs.exists():
            raise exceptions.ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={
                    "model": self.remote_field.model._meta.verbose_name,
                    "pk": value,
                    "field": self.remote_field.field_name,
                    "value": value,
                },  # 'pk' is included for backwards compatibility
            )


class LogMixin:
    @classmethod
    def log_debug(cls, instance, msg, signal, state=None):
        extra = {
            "sender": "{}.{}".format(cls._meta.model_name, cls._meta.object_name),
            "instance": "{}.{}".format(instance._meta.model_name, instance._meta.object_name),
            "instance_id": instance.id,
            "signal": signal,
        }
        if state:
            extra["state"] = state
        signal_logger.debug(msg, extra=extra, exc_info=1)


class MailMixin:
    @classmethod
    def send_mail_message(
        cls,
        subject,
        context,
        template,
        html_template,
        from_email=None,
        attachments=None,
    ):
        context["host"] = settings.BASE_URL
        from_email = from_email or config.NO_REPLY_EMAIL
        to = [config.TESTER_EMAIL] if settings.DEBUG and config.TESTER_EMAIL else [config.CONTACT_MAIL]
        with override("pl"):
            mail = EmailMultiAlternatives(
                subject,
                render_to_string(template, context),
                from_email=from_email,
                to=to,
                connection=get_connection(settings.EMAIL_BACKEND),
            )
            mail.mixed_subtype = "related"
            mail.attach_alternative(render_to_string(html_template, context), "text/html")
            if attachments:
                for item in attachments:
                    mail.attach(item)
            return mail.send()

    @classmethod
    def send_mail_messages(cls, data):
        messages = []
        for item in data:
            message = EmailMultiAlternatives(
                item["subject"],
                item["body"],
                item["from_email"],
                item["to"],
                alternatives=item["alternatives"],
            )
            messages.append(message)
        connection = get_connection(settings.EMAIL_BACKEND)
        return connection.send_messages(messages)

    def send_mail(self, *args, **kwargs):
        kwargs["connection"] = get_connection(settings.EMAIL_BACKEND)
        return send_mail(*args, **kwargs)


class Model(MailMixin, models.Model):

    class Meta:
        abstract = True


class TimeStampedModel(MailMixin, BaseTimeStampedModel):

    @classproperty
    def has_created_field(cls):
        try:
            field = cls._meta.get_field("created")
        except exceptions.FieldDoesNotExist:
            field = None
        return bool(field)

    class Meta:
        abstract = True


class BaseExtendedModel(LogMixin, AdminMixin, ApiMixin, StatusModel, TimeStampedModel):
    STATUS = Choices(*STATUS_CHOICES)
    slug = models.SlugField(max_length=600, null=False, blank=True)
    uuid = models.UUIDField(default=uuid.uuid4)

    published_at = MonitorField(
        monitor="status",
        when=[
            "published",
        ],
    )

    views_count = models.PositiveIntegerField(default=0)

    def _get_basename(self, name):
        return os.path.basename(name)

    def _get_translated_field_dict(self, field_name):
        _i18n = self._meta.get_field("i18n")
        if field_name not in _i18n.fields:
            raise ValueError(f"Field {field_name} does not support translations.")
        return {
            _lang: getattr(self, f"{field_name}_{_lang}") or getattr(self, f"{field_name}_i18n")
            for _lang in settings.MODELTRANS_AVAILABLE_LANGUAGES
        }

    @property
    def object_name(self):
        return self._meta.object_name.lower()

    @property
    def display_name(self):
        if self.id:
            return "{}-{}".format(self._meta.object_name.lower(), self.id)
        return None

    @property
    def subscription(self):
        _cached_subscription = getattr(self, "_cached_subscription", None)
        return _cached_subscription

    def set_subscription(self, usr):
        model_watcher_model = apps.get_model("watchers.ModelWatcher")
        subscription_model = apps.get_model("watchers.Subscription")
        try:
            watcher = model_watcher_model.objects.get_from_instance(self)
            self._cached_subscription = subscription_model.objects.get(watcher=watcher, user=usr)
        except (subscription_model.DoesNotExist, model_watcher_model.DoesNotExist):
            self._cached_subscription = None

    @classmethod
    def get_csv_serializer_schema(cls):
        return csr.get_serializer(cls)

    @classmethod
    def get_rdf_serializer_schema(cls):
        return rsr.get_serializer(cls)

    @classmethod
    def sizeof_fmt(cls, file_size):
        return sizeof_fmt(file_size)

    def to_csv(self, _schema=None):
        _schema = _schema or self.get_csv_serializer_schema()
        return _schema(many=False).dump(self)

    def truncatechars(self, field, chars=20):
        return truncatechars(field, chars)

    @property
    def signals_map(self):
        _map = dict(_SIGNALS_MAP)
        _map.update(getattr(self, "SIGNALS_MAP", {}))
        return _map

    @property
    def is_indexable(self):
        return True

    @property
    def is_watchable(self):
        return True

    @cached_property
    def users_following_list(self):
        # TODO: refactor this to new mechanism
        return [user.id for user in self.users_following.all()]

    @property
    def is_created(self):
        return True if not self._get_pk_val(self._meta) else False

    @property
    def prev_status(self):
        return self.tracker.previous("status")

    @property
    def was_published(self):
        return True if self.tracker.previous("published_at") else False

    @property
    def search_type(self):
        if getattr(self, "is_news", False):
            return "news"
        elif getattr(self, "is_knowledge_base", False):
            return "knowledge_base"
        if self.object_name == "organization":
            return "institution"
        return self.object_name

    @property
    def state_published(self):
        if self.status == self.STATUS.published:
            if self.is_created:
                return True
            else:
                if not self.was_published:
                    if self.prev_status in (None, self.STATUS.draft):
                        return True
        return False

    @property
    def state_removed(self):
        if all([not self.is_created, self.prev_status == self.STATUS.published]):
            if self.status == self.STATUS.draft:
                return True
        return False

    @property
    def state_permanently_removed(self):
        return False

    @property
    def state_restored(self):
        if all(
            [
                self.status == self.STATUS.published,
                not self.is_created,
                self.was_published,
            ]
        ):
            if self.prev_status == self.STATUS.draft:
                return True
        return False

    @property
    def state_updated(self):
        if all(
            [
                self.status == self.STATUS.published,
                not self.is_created,
                self.prev_status == self.STATUS.published,
            ]
        ):
            return True
        return False

    def get_state(self):
        for state in self.signals_map:
            result = getattr(self, "state_{}".format(state), None)
            if result:
                return state

        return None

    def get_unique_slug(self):
        field_name = getattr(self, "slugify_field", "title")
        value = getattr(self, field_name)
        if value:
            origin_slug = slugify(value)
            unique_slug = origin_slug
            c = 1
            qs = self._meta.model.objects.filter(slug=unique_slug)
            if not self.is_created and unique_slug:
                qs = qs.exclude(pk=self.pk)
            while qs.exists():
                unique_slug = "%s-%d" % (origin_slug, c)
                c += 1
            value = unique_slug
        else:
            value = str(uuid.uuid4())
        return value

    @staticmethod
    def _get_absolute_url(url, base_url=settings.BASE_URL, use_lang=True):
        return f"{base_url}/{get_language()}{url}" if use_lang else f"{base_url}{url}"

    def _get_api_url(self, url):
        return self._get_absolute_url(url, base_url=settings.API_URL, use_lang=False)

    def _get_internal_url(self, url, use_lang=False):
        return self._get_absolute_url(url, base_url=settings.API_URL_INTERNAL, use_lang=use_lang)

    @staticmethod
    def on_class_prepared(sender, *args, **kwargs):
        def prop_func(self, field_name):
            obj = type(
                "{}_translated".format(field_name),
                (object,),
                self._get_translated_field_dict(field_name),
            )
            return obj()

        if not issubclass(sender, BaseExtendedModel) or sender._meta.proxy or sender.without_i18_fields():
            return

        _i18n = sender._meta.get_field("i18n")
        if "slug" not in _i18n.fields:
            fields = list(_i18n.fields)
            fields.append("slug")
            _i18n.fields = tuple(fields)

        for field_name in _i18n.fields:
            setattr(
                sender,
                "{}_translated".format(field_name),
                property(partial(prop_func, field_name=field_name)),
            )

    @staticmethod
    def on_pre_init(sender, *args, **kwargs):
        pass

    @staticmethod
    def on_post_init(sender, instance, **kwargs):
        pass

    @staticmethod
    def on_pre_save(sender, instance, raw, using, update_fields, **kwargs):
        if not instance.slug:
            field_name = getattr(instance, "slugify_field", "title")
            value = getattr(instance, field_name, None)
            instance.slug = slugify(value) if value else instance.get_unique_slug()

    @staticmethod
    def on_post_save(sender, instance, created, raw, using, update_fields, **kwargs):
        state = instance.get_state()
        if state:
            for _signal in instance.signals_map[state]:
                _signal.send(sender, instance, state=state)

    @staticmethod
    def on_pre_delete(sender, instance, using, **kwargs):
        state = instance.get_state()
        if state:
            for _signal in instance.signals_map[state]:
                _signal.send(sender, instance)

    @staticmethod
    def on_post_delete(sender, instance, using, **kwargs):
        pass

    @staticmethod
    def on_m2m_changed(sender, instance, action, reverse, model, pk_set, using, **kwargs):
        if action == "pre_add":
            state = "pre_m2m_added"
        elif action == "pre_remove":
            state = "pre_m2m_removed"
        elif action == "pre_clean":
            state = "pre_m2m_cleaned"
        elif action == "post_add":
            state = "post_m2m_added"
        elif action == "post_remove":
            state = "post_m2m_removed"
        elif action == "post_clean":
            state = "post_m2m_cleaned"
        else:
            # Unsupported signals
            state = "unsupported"
        for _signal in instance.signals_map[state]:
            _signal.send(sender, instance, model, pk_set, state=state)

    @classmethod
    def decode_b64_image(cls, encoded_img, img_name):
        data_parts = encoded_img.split(";base64,")
        img_data = data_parts[-1].encode("utf-8")
        try:
            extension = guess_extension(guess_type(encoded_img)[0])
        except Exception:
            extension = None
        name = f"{img_name}{extension}" if extension else img_name
        try:
            decoded_img = base64.b64decode(img_data)
        except Exception:
            decoded_img = None
        return ContentFile(decoded_img, name=name) if decoded_img else None

    @classmethod
    def slugify(cls, value, **kwargs):
        return slugify(value, **kwargs)

    @classmethod
    def without_i18_fields(cls):
        return False

    class Meta:
        abstract = True


class ExtendedModel(SoftDeletableModel, BaseExtendedModel):
    removed_at = MonitorField(
        monitor="is_removed",
        when=[
            True,
        ],
    )

    @property
    def was_removed(self):
        return True if self.tracker.previous("is_removed") else False

    @property
    def was_permanently_removed(self):
        return True if self.tracker.previous("is_permanently_removed") else False

    @property
    def state_published(self):
        if all(
            [
                self.status == self.STATUS.published,
                not self.is_removed,
            ]
        ):
            if self.is_created:
                return True
            else:
                if not self.was_published:
                    if self.was_removed:
                        return True
                    else:
                        if self.prev_status in (None, self.STATUS.draft):
                            return True
        return False

    @property
    def state_removed(self):
        if all(
            [
                not self.is_created,
                not self.was_removed,
                self.prev_status == self.STATUS.published,
            ]
        ):
            if self.status == self.STATUS.draft:
                return True
            elif self.status == self.STATUS.published and self.is_removed:
                return True
        return False

    @property
    def state_permanently_removed(self):
        return not self.was_permanently_removed and self.is_permanently_removed

    @property
    def state_restored(self):
        if all(
            [
                self.status == self.STATUS.published,
                not self.is_removed,
                not self.is_created,
                self.was_published,
            ]
        ):
            if self.was_removed:
                return True
            elif self.prev_status == self.STATUS.draft:
                return True
        return False

    @property
    def state_updated(self):
        if all(
            [
                self.status == self.STATUS.published,
                not self.is_removed,
                not self.is_created,
                self.prev_status == self.STATUS.published,
                not self.was_removed,
            ]
        ):
            return True
        return False

    class Meta:
        abstract = True


models.signals.class_prepared.connect(BaseExtendedModel.on_class_prepared)


def update_watcher(sender, instance, *args, state=None, **kwargs):
    if hasattr(sender, "log_debug"):
        sender.log_debug(
            instance,
            "{} {}".format(sender._meta.object_name, state),
            "notify_{}".format(state),
            state,
        )
    update_model_watcher_task.s(
        instance._meta.app_label,
        instance._meta.object_name,
        instance.id,
        obj_state=state,
    ).apply_async_on_commit()


class TrashModelBase(ModelBase):

    def __new__(cls, name, bases, attrs, **kwargs):
        new_class = super().__new__(cls=cls, name=name, bases=bases, attrs=attrs, **kwargs)
        new_class.is_trash = True
        for base_class in bases:
            if isinstance(base_class, ModelBase):
                base_class.trash_class = new_class
        for base in bases:
            if hasattr(base, "_meta") and isinstance(base, ModelBase):
                new_class._meta.verbose_name = _("{} - trash").format(base._meta.verbose_name)
                new_class._meta.verbose_name_plural = _("{} - trash").format(base._meta.verbose_name_plural)
        return new_class


@receiver(permanently_remove_related_objects)
def permanently_remove_related_objects_after_instance_removal(sender, instance, *args, **kwargs):
    if hasattr(sender, "log_debug"):
        sender.log_debug(
            instance,
            f"Permanently removing objects related to {sender.__name__} with id {instance.id}",
            "permanently_remove_related_objects",
        )

    opts = sender._meta
    for relation in get_candidate_relations_to_delete(opts):
        field = relation.field
        if issubclass(field.remote_field.related_model, SoftDeletableModel):
            if field.remote_field.on_delete == models.CASCADE:
                related_model = field.remote_field.related_model
                counter = 0
                for obj in related_model.raw.filter(**{field.name: instance}):
                    if not obj.is_removed:
                        obj.delete()
                    obj.delete(permanent=True)
                    counter += 1

                if counter:
                    logger.debug(
                        f"Removed {counter} {related_model.__name__}s related " f"to {sender.__name__} with id {instance.id}"
                    )
