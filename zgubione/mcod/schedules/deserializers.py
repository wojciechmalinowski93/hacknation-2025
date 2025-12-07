from django.conf import settings
from django.utils.translation import gettext_lazy as _
from marshmallow import ValidationError, post_load, validate, validates, validates_schema

from mcod.core.api import fields
from mcod.core.api.jsonapi.deserializers import ObjectAttrs, TopLevel
from mcod.core.api.schemas import CommonSchema, ListingSchema
from mcod.core.api.search import fields as search_fields
from mcod.schedules.models import Schedule, UserScheduleItem

SCHEDULE_STATES = [x[0] for x in Schedule.SCHEDULE_STATES]
SCHEDULE_STATES_STR = ", ".join([str(x) for x in SCHEDULE_STATES])
SUPPORTED_FORMATS = settings.SUPPORTED_FORMATS
USER_SCHEDULE_ITEM_STATES = [x[0] for x in UserScheduleItem.RECOMMENDATION_STATES]


class CommentsApiRequest(ListingSchema):
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "created": "created",
        },
    )

    class Meta:
        strict = True
        ordered = True


class CreateCommentAttrs(ObjectAttrs):
    text = fields.Str(required=True, validate=validate.Length(min=1))

    class Meta:
        object_type = "comment"
        strict = True
        ordered = True


class CreateCommentRequest(TopLevel):
    class Meta:
        attrs_schema = CreateCommentAttrs
        attrs_schema_required = True


class ScheduleAttrs(ObjectAttrs):
    period_name = fields.Str(validate=validate.Length(min=1, max=100))
    end_date = fields.Date(allow_none=True)
    new_end_date = fields.Date(allow_none=True)
    link = fields.Str()
    is_blocked = fields.Bool()

    class Meta:
        object_type = "schedule"
        strict = True
        ordered = True

    @validates("link")
    def validate_link(self, value):
        if value:
            validate.URL()(value)

    @validates_schema
    def validate_data(self, data, **kwargs):
        obj = self.context.get("obj")
        if obj and not obj.end_date and "new_end_date" in data:
            raise ValidationError(
                _("You cannot set new_end_date if end_date is not set yet!"),
                field_name="new_end_date",
            )


class ImplementedScheduleAttrs(ScheduleAttrs):
    state = fields.Str(
        validate=validate.OneOf(
            choices=["archived"],
            error=_("Invalid value! Possible values: %(values)s") % {"values": "archived"},
        )
    )

    class Meta(ScheduleAttrs.Meta):
        fields = (
            "link",
            "state",
        )


class ArchivedScheduleAttrs(ImplementedScheduleAttrs):
    state = fields.Str(
        validate=validate.OneOf(
            choices=["implemented"],
            error=_("Invalid value! Possible values: %(values)s") % {"values": "implemented"},
        )
    )


class CreateUserScheduleItemAttrs(ObjectAttrs):
    institution = fields.Str(attribute="organization_name", required=True, validate=validate.Length(min=1))
    institution_unit = fields.Str(attribute="organization_unit")
    dataset_title = fields.Str(required=True, validate=validate.Length(min=1))
    format = fields.Str(required=True, validate=validate.Length(min=1))
    is_new = fields.Bool(required=True)
    is_openness_score_increased = fields.Bool()
    is_quality_improved = fields.Bool()
    description = fields.Str()

    class Meta:
        object_type = "user_schedule_item"
        strict = True
        ordered = True

    @validates_schema
    def validate_data(self, data, **kwargs):
        is_new = data.get("is_new")
        is_openness_score_increased = data.get("is_openness_score_increased")
        is_quality_improved = data.get("is_quality_improved")
        if is_new:
            if "is_openness_score_increased" in data:
                del data["is_openness_score_increased"]
            if "is_quality_improved" in data:
                del data["is_quality_improved"]
        if is_new is False and is_openness_score_increased is None and is_quality_improved is None:  # False is ok.
            raise ValidationError(
                _("is_openness_score_increased or is_quality_improved is required if value of is_new is False!")
            )


class PlannedScheduleApiRequest(TopLevel):
    class Meta:
        attrs_schema = ScheduleAttrs
        attrs_schema_required = True


class ImplementedScheduleApiRequest(PlannedScheduleApiRequest):
    class Meta(PlannedScheduleApiRequest.Meta):
        attrs_schema = ImplementedScheduleAttrs


class ArchivedScheduleApiRequest(PlannedScheduleApiRequest):
    class Meta(PlannedScheduleApiRequest):
        attrs_schema = ArchivedScheduleAttrs


class CreateUserScheduleItemRequest(TopLevel):
    class Meta:
        attrs_schema = CreateUserScheduleItemAttrs
        attrs_schema_required = True


class AdminCreateUserScheduleItemAttrs(CreateUserScheduleItemAttrs):
    recommendation_state = fields.Str(
        validate=validate.OneOf(
            choices=USER_SCHEDULE_ITEM_STATES,
            error=_("Unsupported recommendation state. Supported are: %(states)s") % {"states": USER_SCHEDULE_ITEM_STATES},
        )
    )
    recommendation_notes = fields.Str(allow_none=True)
    is_accepted = fields.Bool()
    is_resource_added = fields.Bool()
    is_resource_added_notes = fields.Str(allow_none=True)
    resource_link = fields.Str(allow_none=True)

    class Meta:
        object_type = "user_schedule_item"
        strict = True
        ordered = True

    @validates("resource_link")
    def validate_resource_link(self, value):
        if value:
            validate.URL()(value)

    @post_load
    def prepare_data(self, data, **kwargs):
        obj = self.context.get("obj")
        if not obj:
            if data.get("recommendation_notes") is None:
                data["recommendation_notes"] = ""
            if data.get("resource_link") is None:
                data["resource_link"] = ""
            if data.get("is_resource_added_notes") is None:
                data["is_resource_added_notes"] = ""
        is_accepted = data.pop("is_accepted", None)
        if is_accepted is True:
            data["recommendation_state"] = "recommended"
        elif is_accepted is False:
            data["recommendation_state"] = "not_recommended"
        return data

    @validates_schema
    def validate_data(self, data, **kwargs):
        is_accepted = data.get("is_accepted")
        recommendation_notes = data.get("recommendation_notes")
        recommendation_state = data.get("recommendation_state")
        if (recommendation_state == "not_recommended" or is_accepted is False) and not recommendation_notes:
            raise ValidationError("This field is required!", field_name="recommendation_notes")


class AdminUserScheduleItemAttrs(AdminCreateUserScheduleItemAttrs):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ["dataset_title", "format", "institution", "is_new"]:
            if name in self._fields:
                self._fields[name].required = False


class AgentImplementedUserScheduleItemAttrs(ObjectAttrs):
    is_resource_added = fields.Bool(required=True)
    is_resource_added_notes = fields.Str()
    resource_link = fields.Str()

    class Meta:
        object_type = "user_schedule_item"
        strict = True
        ordered = True

    @validates("resource_link")
    def validate_resource_link(self, value):
        if value:
            validate.URL()(value)

    @validates_schema
    def validate_data(self, data, **kwargs):
        is_resource_added = data.get("is_resource_added")
        is_resource_added_notes = data.get("is_resource_added_notes")
        resource_link = data.get("resource_link")
        obj = self.context.get("obj")
        if obj:
            if obj.is_accepted:
                if is_resource_added and not resource_link:
                    raise ValidationError("This field is required!", field_name="resource_link")
                if not is_resource_added and not is_resource_added_notes:
                    raise ValidationError("This field is required!", field_name="is_resource_added_notes")
            else:
                data.pop("is_resource_added", None)
                data.pop("is_resource_added_notes", None)
                data.pop("resource_link", None)


class AdminUserScheduleItemRequest(CreateUserScheduleItemRequest):
    class Meta(CreateUserScheduleItemRequest.Meta):
        attrs_schema = AdminUserScheduleItemAttrs


class AdminCreateUserScheduleItemRequest(CreateUserScheduleItemRequest):
    class Meta(CreateUserScheduleItemRequest):
        attrs_schema = AdminCreateUserScheduleItemAttrs


class AgentImplementedUserScheduleItemRequest(TopLevel):
    class Meta:
        attrs_schema = AgentImplementedUserScheduleItemAttrs
        attrs_schema_required = True


class CreateNotificationsAttrs(ObjectAttrs):
    message = fields.Str(required=True, validate=validate.Length(min=1, max=60))
    notification_type = fields.Str(
        required=True,
        validate=validate.OneOf(
            choices=["all", "late"],
            error=_("Unsupported notification type. Supported are: %(types)s") % {"types": "all, late"},
        ),
    )

    class Meta:
        object_type = "notification"
        strict = True
        ordered = True


class CreateNotificationsApiRequest(TopLevel):
    class Meta:
        attrs_schema = CreateNotificationsAttrs
        attrs_schema_required = True


class NotificationAttrs(ObjectAttrs):
    unread = fields.Bool(required=True)

    class Meta:
        object_type = "notification"
        strict = True
        ordered = True


class UpdateNotificationApiRequest(TopLevel):
    class Meta:
        attrs_schema = NotificationAttrs
        attrs_schema_required = True


class NotificationsApiRequest(ListingSchema):
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "timestamp": "timestamp",
        },
        doc_base_url="/auth/schedule_notifications",
    )
    unread = search_fields.NoDataField()

    class Meta:
        strict = True
        ordered = True


class UserScheduleAttrs(ObjectAttrs):
    is_ready = fields.Bool(required=True)

    class Meta:
        object_type = "user_schedule"
        strict = True
        ordered = True

    @validates_schema
    def validate_data(self, data, **kwargs):
        obj = self.context.get("obj")
        if obj and obj.is_blocked:
            raise ValidationError(
                _("User schedule's readiness state cannot be changed!"),
                field_name="is_ready",
            )


class UpdateUserScheduleRequest(TopLevel):
    class Meta:
        attrs_schema = UserScheduleAttrs
        attrs_schema_required = True


class ScheduleApiRequest(CommonSchema):
    include = search_fields.StringField(
        description="Allow the client to customize which related resources should be returned in included section.",
        allowEmptyValue=True,
    )
    full = search_fields.NoDataField()

    class Meta:
        strict = True
        ordered = True


class NotificationApiRequest(ScheduleApiRequest):
    pass


class UserScheduleApiRequest(ScheduleApiRequest):
    pass


class UserScheduleItemApiRequest(ScheduleApiRequest):
    pass


class UserScheduleItemFormatApiRequest(ListingSchema):
    pass


class UserScheduleItemInstitutionApiRequest(ListingSchema):
    pass


class ListingRequest(ListingSchema):
    state = search_fields.StringField(
        description="State of schedule",
        example="planned",
        required=False,
        validate=validate.OneOf(
            choices=SCHEDULE_STATES,
            error=_("Invalid value! Possible values: %(values)s") % {"values": SCHEDULE_STATES_STR},
        ),
    )
    full = search_fields.NoDataField()


class SchedulesApiRequest(ListingRequest):
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "created": "created",
            "end_date": "end_date",
            "new_end_date": "new_end_date",
        },
    )


class UserScheduleItemsApiRequest(SchedulesApiRequest):
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "created": "created",
            "institution": "institution",
        },
    )
    q = fields.Str(validate=validate.Length(min=2))
    exclude_id = fields.Int()


class UserSchedulesApiRequest(ListingRequest):
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "created": "created",
            "email": "email",
            "institution": "institution",
        },
    )
    is_ready = search_fields.NoDataField()


def get_schedule_deserializer_schema(instance):
    if instance.state == "implemented":
        return ImplementedScheduleApiRequest
    elif instance.state == "archived":
        return ArchivedScheduleApiRequest
    return PlannedScheduleApiRequest


def get_user_schedule_item_deserializer_schema(instance, user):
    if user.is_superuser:
        return AdminUserScheduleItemRequest
    if instance.state == "implemented":
        return AgentImplementedUserScheduleItemRequest
    return CreateUserScheduleItemRequest
