from urllib.parse import urlsplit

from django.utils.translation import gettext as _
from marshmallow import ValidationError, post_load, pre_load, validate, validates_schema

from mcod import settings
from mcod.core.api import fields as core_fields, schemas as core_schemas
from mcod.core.api.jsonapi.deserializers import ObjectAttrs, ObjectWithId, TopLevel
from mcod.core.api.search import fields as search_fields
from mcod.watchers.models import (
    NOTIFICATION_STATUS_CHOICES,
    NOTIFICATION_TYPES,
    OBJECT_NAME_TO_MODEL,
)

ALLOWED_NOTIFICATION_TYPES = [i[0] for i in NOTIFICATION_TYPES]
ALLOWED_STATUS_CHOICES = [i[0] for i in NOTIFICATION_STATUS_CHOICES]

ALLOWED_OBJECT_NAMES = list(OBJECT_NAME_TO_MODEL.keys()) + [
    "query",
]
ALLOWED_MODELS = list(OBJECT_NAME_TO_MODEL.values()) + [
    "query",
]


class SubscriptionListApiRequest(core_schemas.ListingSchema):
    object_name = search_fields.StringField(
        description="Object name",
        example="resource",
        required=False,
        validate=validate.OneOf(choices=ALLOWED_OBJECT_NAMES, error=_("Unsupported object name")),
    )
    object_id = search_fields.StringField(description="Object ID", example="3776", required=False)

    class Meta:
        strict = True
        ordered = True


class UpdateSubscriptionAttrs(ObjectAttrs):
    name = core_fields.String(description="Subscription name", example="my query 1", required=False)
    customfields = core_fields.Raw()

    class Meta:
        strict = True
        ordered = True
        object_type = "subscription"


class CreateSubscriptionAttrs(ObjectAttrs):
    object_name = core_fields.String(
        description="Object name",
        example="resource",
        required=True,
        validate=validate.OneOf(choices=ALLOWED_OBJECT_NAMES, error=_("Unsupported object name")),
    )
    object_ident = core_fields.String(description="Object ID or query url.", example="12342", required=True)
    objects_count = core_fields.Integer(description="Objects count.", example="2", required=False, default=0)
    name = core_fields.String(description="Subscription name", example="my query 1", required=False)
    customfields = core_fields.Raw()

    @pre_load
    def prepare_data(self, data, **kwargs):
        object_ident = data.get("object_ident")
        data["object_ident"] = str(object_ident) if object_ident else None
        object_name = data.get("object_name")
        if object_name and isinstance(object_name, str):
            data["object_name"] = object_name.lower()
        return data

    @validates_schema
    def validate_url(self, data, **kwargs):
        if data["object_name"] == "query":
            url_split = urlsplit(data["object_ident"])
            api_split = urlsplit(settings.API_URL)
            if url_split.scheme != api_split.scheme or url_split.netloc != api_split.netloc:
                raise ValidationError(_("Invalid url address"), field_name="object_ident")

    class Meta:
        object_type = "subscription"
        strict = True
        ordered = True


class SubscriptionCreateApiRequest(TopLevel):
    class Meta:
        attrs_schema = CreateSubscriptionAttrs
        attrs_schema_required = True


class SubscriptionUpdateApiRequest(TopLevel):
    class Meta:
        attrs_schema = UpdateSubscriptionAttrs
        object_schema = ObjectWithId


class SubscriptionApiRequest(core_schemas.CommonSchema):
    id = search_fields.NumberField(_in="path", description="Subscription ID", example="447", required=True)

    class Meta:
        strict = True
        ordered = True


class NotificationApiListRequest(core_schemas.ListingSchema):
    object_name = search_fields.StringField(
        description="Object name",
        example="resource",
        required=False,
        validate=validate.OneOf(choices=ALLOWED_OBJECT_NAMES, error=_("Unsupported object name")),
    )
    object_id = search_fields.StringField(description="Object ID", example="3776", required=False)

    notification_type = search_fields.StringField(
        description="Type of notificaton",
        example="object_updated",
        required=False,
        validate=validate.OneOf(choices=ALLOWED_NOTIFICATION_TYPES, error=_("Invalid notification type")),
    )
    status = search_fields.StringField(
        description="Message status (new or read)",
        example="new",
        required=False,
        validate=validate.OneOf(choices=ALLOWED_STATUS_CHOICES, error=_("Invalid notification status")),
    )

    class Meta:
        strict = True
        ordered = True

    @pre_load
    def prepare_object_name(self, data, **kwargs):
        if "object_name" in data:
            data["object_name"] = data["object_name"].lower()
        return data

    @post_load
    def replace_object_name_with_model(self, data, **kwargs):
        _attr = "subscription__watcher__object_name__endswith"
        if _attr in data:
            data[_attr] = OBJECT_NAME_TO_MODEL[data[_attr]]
        return data


class NotificationApiRequest(core_schemas.CommonSchema):
    id = search_fields.NumberField(_in="path", description="Notification ID", example="447", required=True)

    class Meta:
        strict = True
        ordered = True


class ChangeNotificationAttrs(ObjectAttrs):
    status = core_fields.String(
        required=True,
        validate=validate.OneOf(choices=ALLOWED_STATUS_CHOICES, error=_("Invalid notification status")),
    )

    class Meta:
        strict = True
        ordered = True
        object_type = "notification"


class ChangeNotificationStatus(TopLevel):
    class Meta:
        attrs_schema = ChangeNotificationAttrs
        object_schema = ObjectWithId


class ChangeNotificationsStatus(TopLevel):
    class Meta:
        attrs_schema = ChangeNotificationAttrs
        attrs_schema_many = True
        object_schema = ObjectWithId


class DeleteNotificationsAttrs(ObjectAttrs):
    class Meta:
        strict = True
        ordered = True
        object_type = "notification"


class DeleteNotifications(TopLevel):
    class Meta:
        attrs_schema = DeleteNotificationsAttrs
        attrs_schema_many = True
        object_schema = ObjectWithId
