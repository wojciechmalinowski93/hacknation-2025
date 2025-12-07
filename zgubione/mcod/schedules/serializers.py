from marshmallow import post_dump, pre_dump

from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import ObjectAttrs, Relationship, Relationships, TopLevel
from mcod.core.api.schemas import ExtSchema
from mcod.core.serializers import CSVSchemaRegistrator, CSVSerializer


class UserScheduleApiAggs(ExtSchema):
    pass


class UserScheduleItemApiAggs(ExtSchema):
    pass


class CommentApiRelationships(Relationships):
    user_schedule_item = fields.Nested(
        Relationship,
        many=False,
        _type="user_schedule_item",
        url_template="{api_url}/auth/user_schedule_items/{ident}",
    )


class ScheduleApiRelationships(Relationships):
    user_schedules = fields.Nested(
        Relationship,
        required=True,
        many=False,
        default=[],
        _type="user_schedule",
        url_template="{object_url}/user_schedules",
    )
    user_schedule_items_included = fields.Nested(
        Relationship,
        required=True,
        data_key="user_schedule_items",
        many=False,
        default=[],
        _type="user_schedule_item",
        url_template="{object_url}/user_schedule_items",
    )
    agents = fields.Nested(
        Relationship,
        required=True,
        attribute="total_agents",
        many=False,
        default=[],
        _type="agent",
        url_template="{api_url}/auth/schedule_agents",
    )

    def __init__(self, *args, **kwargs):
        try:
            is_superuser = kwargs["context"]["request"].user.is_superuser
        except (KeyError, AttributeError):
            is_superuser = False
        if not is_superuser:
            kwargs["exclude"] = kwargs.get("exclude", tuple()) + ("agents",)
        super().__init__(*args, **kwargs)

    def filter_data(self, data, **kwargs):
        user = self.context["request"].user if "request" in self.context else None
        if user and not user.is_superuser:
            user = user.extra_agent_of or user
            if "user_schedule_items_included" in data:
                data["user_schedule_items_included"] = data["user_schedule_items_included"].filter(user_schedule__user=user)
            if "user_schedules" in data:
                data["user_schedules"] = data["user_schedules"].filter(user=user)
        return data


class UserScheduleApiRelationships(Relationships):
    schedule = fields.Nested(
        Relationship,
        many=False,
        _type="schedule",
        url_template="{api_url}/auth/schedules/{ident}",
    )
    user = fields.Nested(
        Relationship,
        many=False,
        _type="user",
    )
    user_schedule_items = fields.Nested(
        Relationship,
        many=False,
        default=[],
        _type="user_schedule_item",
        url_template="{object_url}/items",
    )


class UserScheduleItemApiRelationships(Relationships):
    schedule = fields.Nested(
        Relationship,
        many=False,
        _type="schedule",
        url_template="{api_url}/auth/schedules/{ident}",
    )
    user = fields.Nested(
        Relationship,
        many=False,
        _type="user",
    )
    user_schedule = fields.Nested(
        Relationship,
        many=False,
        _type="user_schedule",
        url_template="{api_url}/auth/user_schedules/{ident}",
    )
    comments = fields.Nested(
        Relationship,
        attribute="user_schedule_item_comments",
        many=False,
        default=[],
        _type="comment",
        url_template="{object_url}/comments",
    )


class ScheduleApiAttrs(ObjectAttrs):
    start_date = fields.Date()
    period_name = fields.Str()
    end_date = fields.Date()
    new_end_date = fields.Date()
    link = fields.Url()
    state = fields.Str()
    is_blocked = fields.Bool()
    name = fields.Str()
    total_agents_count = fields.Int()

    class Meta:
        relationships_schema = ScheduleApiRelationships
        object_type = "schedule"
        url_template = "{api_url}/auth/schedules/{ident}"
        ordered = True
        model = "schedules.Schedule"


class UserScheduleApiAttrs(ObjectAttrs):
    email = fields.Email(attribute="user.email")
    institution = fields.Str()
    items_count = fields.Int()
    is_ready = fields.Bool()
    is_blocked = fields.Bool()
    recommended_items_count = fields.Int()
    implemented_items_count = fields.Int()
    state = fields.Str()

    class Meta:
        relationships_schema = UserScheduleApiRelationships
        object_type = "user_schedule"
        url_template = "{api_url}/auth/user_schedules/{ident}"
        ordered = True
        model = "schedules.UserSchedule"


class UserScheduleItemApiAttrs(ObjectAttrs):
    email = fields.Email()
    institution = fields.Str(attribute="organization_name")
    institution_unit = fields.Str(attribute="organization_unit")
    dataset_title = fields.Str()
    created = fields.Date()
    format = fields.Str()
    is_new = fields.Bool()
    is_openness_score_increased = fields.Bool()
    is_quality_improved = fields.Bool()
    description = fields.Str()
    state = fields.Str()
    recommendation_state = fields.Str()
    recommendation_notes = fields.Str()
    is_recommendation_issued = fields.Bool()

    is_accepted = fields.Bool()
    is_completed = fields.Bool()
    is_resource_added = fields.Bool()
    is_resource_added_notes = fields.Str()
    resource_link = fields.Url()

    class Meta:
        relationships_schema = UserScheduleItemApiRelationships
        object_type = "user_schedule_item"
        url_template = "{api_url}/auth/user_schedule_items/{ident}"
        ordered = True
        model = "schedules.UserScheduleItem"

    @post_dump
    def prepare_data(self, data, **kwargs):
        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        if not user or not user.is_superuser:
            del data["recommendation_state"]
            del data["recommendation_notes"]
        return data


class ScheduleApiResponse(TopLevel):
    class Meta:
        attrs_schema = ScheduleApiAttrs


class NotificationSerializer(ExtSchema):
    id = fields.Int()
    verb = fields.Str()
    timestamp = fields.DateTime()
    unread = fields.Bool()
    description = fields.Str()
    user_schedule_id = fields.Int()
    user_schedule_item_id = fields.Int()
    schedule_state = fields.Str()
    schedule_id = fields.Int()


class CommentApiAttrs(ObjectAttrs):
    text = fields.Str()
    created = fields.DateTime()
    author = fields.Email()
    modified = fields.DateTime()

    class Meta:
        relationships_schema = CommentApiRelationships
        object_type = "comment"
        ordered = True
        model = "schedules.Comment"

    @staticmethod
    def self_api_url(data):
        return None


class CommentApiResponse(TopLevel):
    class Meta:
        attrs_schema = CommentApiAttrs


class CreateNotificationsApiAttrs(ObjectAttrs):
    result = fields.Str()
    success = fields.Bool()

    class Meta:
        object_type = "result"
        ordered = True


class CreateNotificationsApiResponse(TopLevel):
    class Meta:
        attrs_schema = CreateNotificationsApiAttrs


class NotificationApiAttrs(NotificationSerializer, ObjectAttrs):

    class Meta:
        object_type = "notification"
        url_template = "{api_url}/auth/schedule_notifications/{ident}"
        ordered = True


class NotificationApiResponse(TopLevel):
    class Meta:
        attrs_schema = NotificationApiAttrs


class UserScheduleApiResponse(TopLevel):
    class Meta:
        attrs_schema = UserScheduleApiAttrs
        aggs_schema = UserScheduleApiAggs


class UserScheduleItemApiResponse(TopLevel):
    class Meta:
        attrs_schema = UserScheduleItemApiAttrs
        aggs_schema = UserScheduleItemApiAggs


class UserScheduleItemFormatApiAttrs(ObjectAttrs):
    name = fields.Str()

    class Meta:
        object_type = "format"
        ordered = True

    @staticmethod
    def self_api_url(data):
        return None


class UserScheduleItemInstitutionApiAttrs(ObjectAttrs):
    title = fields.Str()

    class Meta:
        object_type = "institution"
        url_template = "{api_url}/institutions/{ident}"


class UserScheduleItemFormatApiResponse(TopLevel):
    class Meta:
        attrs_schema = UserScheduleItemFormatApiAttrs


class UserScheduleItemInstitutionApiResponse(TopLevel):
    class Meta:
        attrs_schema = UserScheduleItemInstitutionApiAttrs


class ExportUrlApiAttrs(ObjectAttrs):
    url = fields.URL()

    class Meta:
        object_type = "export"
        ordered = True

    @staticmethod
    def self_api_url(data):
        return None


class ExportUrlApiResponse(TopLevel):
    class Meta:
        attrs_schema = ExportUrlApiAttrs


class UserScheduleItemCSVSerializer(CSVSerializer, metaclass=CSVSchemaRegistrator):
    row_no = fields.Int(data_key="L.p.", required=True, example=1, allow_none=True)
    organization_name = fields.Str(data_key="Ministerstwo (instytucja)", example="Ministerstwo Cyfryzacji")
    organization_unit = fields.Str(data_key="Jednostka podległa/nadzorowana")
    dataset_title = fields.Str(data_key="Zasoby danych", example="Imiona nadawane dzieciom w Polsce")
    format = fields.Str(data_key="Format danych", example="xlsx")
    is_new_yes_no = fields.Str(data_key="Nowy zasób (tak/nie)", example="Tak")
    is_openness_score_increased_yes_no = fields.Str(
        data_key="Wyższy poziom otwartości (tak/nie) - wypełnić w przypadku aktualizacji zbioru",
        example="Tak",
    )
    is_quality_improved_yes_no = fields.Str(
        data_key="Poprawiona jakość np. dezagregacja danych adresowych, poprawiona struktura danych (tak/nie) - "
        "wypełnić w przypadku aktualizacji zbioru",
        example="Tak",
    )
    description = fields.Str(data_key="Uwagi", example="treść uwag...")
    recommendation_state_name = fields.Str(data_key="Rekomendacja", example="awaits")
    recommendation_notes = fields.Str(data_key="Komentarz do rekomendacji", example="treść komentarza...")
    is_resource_added_yes_no = fields.Str(data_key="Realizacja", example="Tak")
    resource_link = fields.Str(data_key="Link do zasobu", example="http://example.com")
    is_resource_added_notes = fields.Str(data_key="Komentarz do realizacji", example="treść komentarza...")

    class Meta:
        ordered = True
        model = "schedules.UserScheduleItem"

    @pre_dump(pass_many=True)
    def prepare_row_no(self, data, many, **kwargs):
        for idx, item in enumerate(data, start=1):
            setattr(item, "row_no", idx)
        return data
