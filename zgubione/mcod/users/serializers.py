from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from marshmallow import post_dump, pre_dump
from rest_framework import serializers

from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import (
    DataRelationship,
    ObjectAttrs,
    Relationship,
    Relationships,
    TopLevel,
)
from mcod.core.serializers import CSVSchemaRegistrator, CSVSerializer
from mcod.schedules.serializers import UserScheduleApiAttrs
from mcod.users.models import Meeting

User = get_user_model()


class ChangePasswordApiAttrs(ObjectAttrs):
    is_password_changed = fields.Bool(required=True)

    class Meta:
        object_type = "user"
        url_template = "{api_url}/auth/password/change"


class ChangePasswordApiResponse(TopLevel):
    class Meta:
        attrs_schema = ChangePasswordApiAttrs


class ConfirmResetPasswordApiAttrs(ObjectAttrs):
    is_confirmed = fields.Bool(required=True)

    class Meta:
        object_type = "user"
        url_template = "{api_url}/auth/password/reset"


class ConfirmResetPasswordApiResponse(TopLevel):
    class Meta:
        attrs_schema = ConfirmResetPasswordApiAttrs


class UserCSVSerializer(CSVSerializer):
    id = fields.Int(data_key=_("id"), required=True, example=77)
    email = fields.Email(data_key=_("Email"), default="", required=True, example="user@example.com")
    fullname = fields.Str(data_key=_("Full name"), default="", example="Jan Kowalski")
    official_phone = fields.Method("get_phone", data_key=_("Official phone"), example="+481234567890")
    role = fields.Method("get_role", data_key=_("Role"), default="", example="+481234567890")
    state = fields.Str(
        data_key=_("State"),
        required=True,
        example="active",
        description="Allowed values: 'active', 'inactive' or 'blocked'",
    )
    institution = fields.Str(
        attribute="institutions_ids_list_as_str",
        data_key=_("Institution"),
        example="1,2",
    )
    institution1 = fields.Str(
        attribute="institutions_ids_list_as_str",
        data_key=_("Institution1"),
        example="1,2",
    )
    institution2 = fields.Int(attribute="agent_organization_id", data_key=_("Institution2"), example=1)
    is_academy_admin = fields.Method("get_is_academy_admin", data_key=_("Admin AOD"), example="Nie")
    is_agent = fields.Method("get_is_agent", data_key=_("Agent"), example="Nie")
    extra_agent_of = fields.Method("get_extra_agent_of", data_key=_("Extra agent"), example=1)
    is_labs_admin = fields.Method("get_is_labs_admin", data_key=_("Admin LOD"), example="Nie")
    is_official = fields.Method("get_is_official", data_key=_("Official"), example="Nie")
    is_staff = fields.Method("get_is_staff", data_key=_("Editor"), example="Nie")
    is_superuser = fields.Method("get_is_superuser", data_key=_("Admin"), example="Nie")
    wk_linked = fields.Method("is_wk_linked", data_key=_("Linked with WK"), example="Nie")
    last_logged_method = fields.Method("logging_method", data_key=_("Last logged method"), example="WK")
    last_login = fields.DateTime(data_key=_("Last login date"), example="2021-01-01T00:00:00Z", default=None)

    @staticmethod
    def get_yes():
        return _("Yes")

    @staticmethod
    def get_no():
        return _("No")

    @staticmethod
    def logging_method(obj: User) -> str:
        """Returns last logged method for specified user."""
        return obj.last_logged_method

    def is_wk_linked(self, obj) -> str:
        """Returns YES if user is connected to WK, otherwise NO."""
        return self.get_yes() if obj.is_gov_linked else self.get_no()

    def get_is_academy_admin(self, obj):
        return self.get_yes() if obj.is_academy_admin else self.get_no()

    def get_is_agent(self, obj):
        return self.get_yes() if obj.is_agent else self.get_no()

    def get_extra_agent_of(self, obj):
        return obj.extra_agent_of.id if obj.extra_agent_of else None

    def get_is_labs_admin(self, obj):
        return self.get_yes() if obj.is_labs_admin else self.get_no()

    def get_is_superuser(self, obj):
        return self.get_yes() if obj.is_superuser else self.get_no()

    def get_is_official(self, obj):
        return self.get_yes() if obj.is_official else self.get_no()

    def get_is_staff(self, obj):
        return self.get_yes() if obj.is_staff else self.get_no()

    def get_phone(self, obj):
        if obj.phone:
            phone = obj.phone
            if obj.phone_internal:
                phone += f".{obj.phone_internal}"
            return phone
        return ""

    def get_role(self, obj):
        if obj.is_superuser:
            return _("Admin")
        elif obj.is_staff:
            return _("Editor")
        else:
            return _("User")

    class Meta:
        ordered = True
        model = "users.User"
        fields = (
            "id",
            "email",
            "fullname",
            "official_phone",
            "is_staff",
            "is_official",
            "is_superuser",
            "is_academy_admin",
            "is_labs_admin",
            "is_agent",
            "extra_agent_of",
            "state",
            "institution1",
            "institution2",
            "wk_linked",
            "last_logged_method",
            "last_login",
        )


class DefaultUserCSVSerializer(UserCSVSerializer, metaclass=CSVSchemaRegistrator):
    """
    To register in csv_serializers_registry.
    """

    pass


class UserLocalTimeCSVSerializer(UserCSVSerializer):
    last_login = fields.LocalDateTime(data_key=_("Last login date"), example="2021-01-01T00:00:00+02:00")


class UserApiRelationships(Relationships):
    institutions = fields.Nested(
        DataRelationship,
        attribute="staff_institutions",
        many=False,
        _type="institution",
        path="institutions",
        show_data=True,
        required=True,
    )
    agent_institutions = fields.Nested(
        DataRelationship,
        attribute="agent_institutions_included",
        many=False,
        _type="institution",
        path="institutions",
        show_data=True,
        required=False,
    )
    agent_organization = fields.Nested(
        Relationship,
        data_key="agent_institution_main",
        many=False,
        _type="institution",
    )


class AgentApiRelationships(UserApiRelationships):
    planned_schedule = fields.Nested(
        Relationship,
        many=False,
        _type="schedule",
        url_template="{api_url}/auth/schedules/{ident}",
    )
    planned_user_schedule = fields.Nested(
        Relationship,
        many=False,
        _type="user_schedule",
        attribute="_planned_user_schedule",
        url_template="{object_url}",
    )
    planned_user_schedule_items = fields.Nested(
        DataRelationship,
        many=False,
        default=[],
        _type="user_schedule_item",
        show_data=True,
        url_template="{object_url}",
    )

    class Meta:
        ordered = True

    def prepare_object_url(self, data):
        obj = data.get("_planned_user_schedule")
        if obj:
            url = f"{self.api_url}/auth/user_schedules/{obj.id}"
            self._fields["planned_user_schedule"].schema.context.update(object_url=url)
            self._fields["planned_user_schedule_items"].schema.context.update(object_url=f"{url}/items")
        else:
            self._fields["planned_user_schedule"].schema.context.update(object_url="")
            self._fields["planned_user_schedule_items"].schema.context.update(object_url="")


class UserSchemaMixin:
    state = fields.Str(
        required=True,
        faker_type="userstate",
        example="active",
        description="Allowed values: 'active', 'inactive' or 'blocked'",
    )
    email = fields.Email(required=True, faker_type="email", example="user@example.com")
    fullname = fields.Str(missing=None, faker_type="name", example="Jan Kowalski")
    about = fields.Str(missing=None, faker_type="sentence", example="I am a very talented programmer.")
    created = fields.Date()
    subscriptions_report_opt_in = fields.Boolean()
    rodo_privacy_policy_opt_in = fields.Boolean()
    count_datasets_created = fields.Int()
    count_datasets_modified = fields.Int()
    is_gov_linked = fields.Boolean()
    connected_gov_users = fields.List(fields.Str())

    @post_dump
    def prepare_data(self, data, **kwargs):
        data["subscriptions_report_opt_in"] = True if data.get("subscriptions_report_opt_in") is not None else False
        data["rodo_privacy_policy_opt_in"] = True if data.get("rodo_privacy_policy_opt_in") is not None else False
        return data


class UserApiAttrs(UserSchemaMixin, ObjectAttrs):
    is_newsletter_receiver = fields.Bool(required=False, faker_type="boolean", example=True)

    class Meta:
        relationships_schema = UserApiRelationships
        object_type = "user"
        api_path = "/auth/user"
        url_template = "{api_url}/auth/user"
        model = "users.User"


class AgentApiAttrs(UserApiAttrs):
    planned_user_schedule = fields.Nested(UserScheduleApiAttrs)

    class Meta(UserApiAttrs.Meta):
        relationships_schema = AgentApiRelationships
        url_template = "{api_url}/auth/schedule_agents/{ident}"


class UserApiResponse(TopLevel):
    class Meta:
        attrs_schema = UserApiAttrs


class AgentApiResponse(TopLevel):
    class Meta:
        attrs_schema = AgentApiAttrs


class LoginApiAttrs(UserSchemaMixin, ObjectAttrs):
    token = fields.Str(required=True)

    class Meta:
        relationships_schema = UserApiRelationships
        object_type = "user"
        path = "/auth/login"
        url_template = "{api_url}/auth/login"


class LoginApiResponse(TopLevel):
    class Meta:
        attrs_schema = LoginApiAttrs


class LogoutApiAttrs(ObjectAttrs):
    is_logged_out = fields.Bool(required=True)

    class Meta:
        object_type = "user"
        url_template = "{api_url}/auth/logout"


class LogoutApiResponse(TopLevel):
    class Meta:
        attrs_schema = LogoutApiAttrs


class MeetingFileSchema(ObjectAttrs):
    id = fields.Int()
    download_url = fields.Str()
    name = fields.Str()

    class Meta:
        ordered = True


class MeetingApiAttrs(ObjectAttrs):
    title = fields.Str()
    venue = fields.Str()
    description = fields.Str()
    start_date = fields.Date()
    start_time = fields.Str()
    end_time = fields.Str()
    materials = fields.Nested(MeetingFileSchema, many=True)
    state = fields.Str()
    state_name = fields.Str()

    class Meta:
        object_type = "meeting"
        api_path = "meetings"
        model = "users.Meeting"
        ordered = True

    @staticmethod
    def self_api_url(data):
        return None

    @pre_dump
    def prepare_data(self, data, **kwargs):
        today = timezone.now().date()
        start_date = data.start_date.date()
        _state = None
        if start_date < today:
            _state = "finished"
        elif start_date >= today:
            _state = "planned"
        if _state:
            setattr(data, "state", _state)
            setattr(data, "state_name", Meeting.MEETING_STATES.get(_state))
        return data


class MeetingApiResponse(TopLevel):
    class Meta:
        attrs_schema = MeetingApiAttrs


class ResendActivationEmailAttrs(ObjectAttrs):
    is_activation_email_sent = fields.Bool(required=True)

    class Meta:
        object_type = "user"
        url_template = "{api_url}/auth/registration/resend-email"


class ResetPasswordAttrs(ObjectAttrs):
    is_password_reset_email_sent = fields.Bool(required=True)

    class Meta:
        object_type = "user"
        url_template = "{api_url}/auth/password/reset"


class RegistrationAttrs(UserSchemaMixin, ObjectAttrs):
    class Meta:
        object_type = "user"
        url_template = "{api_url}/auth/registration"


class RegistrationApiResponse(TopLevel):
    class Meta:
        attrs_schema = RegistrationAttrs


class ResendActivationEmailApiResponse(TopLevel):
    class Meta:
        attrs_schema = ResendActivationEmailAttrs


class ResetPasswordApiResponse(TopLevel):
    class Meta:
        attrs_schema = ResetPasswordAttrs


class VerifyEmailAttrs(ObjectAttrs):
    is_verified = fields.Bool(required=True)

    class Meta:
        object_type = "user"
        url_template = "{api_url}/registration/verify-email/"


class VerifyEmailApiResponse(TopLevel):
    class Meta:
        attrs_schema = VerifyEmailAttrs


class ACSResponse(serializers.Serializer):
    """Serialize the response from the ogin.gov.pl service."""

    SAMLart = serializers.CharField(required=True, allow_blank=False)
    RelayState = serializers.CharField(required=False, allow_blank=True)


class ACSTemplateResponse(serializers.Serializer):
    """Serialize the response from the template mocking the login.gov.pl service."""

    in_response_to = serializers.CharField(required=True, allow_blank=False)
    first_name = serializers.CharField(required=True, allow_blank=False)
    last_name = serializers.CharField(required=True, allow_blank=False)
    dob = serializers.CharField(required=True, allow_blank=False)
    pesel = serializers.CharField(required=True, allow_blank=False)
