from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from django.utils.translation import gettext as _
from elasticsearch_dsl import Q
from marshmallow import ValidationError, post_load, validate, validates_schema

from mcod.core.api import fields
from mcod.core.api.jsonapi.deserializers import ObjectAttrs, TopLevel
from mcod.core.api.schemas import ListingSchema, ListTermsSchema, NumberTermSchema
from mcod.core.api.search import fields as search_fields

MEETING_STATE_CHOICES = ["finished", "planned"]


class ChangePasswordApiAttrs(ObjectAttrs):
    old_password = fields.Str(required=True)
    new_password1 = fields.Str(required=True)
    new_password2 = fields.Str(required=True)

    class Meta:
        strict = True
        object_type = "user"


class ChangePasswordApiRequest(TopLevel):
    class Meta:
        attrs_schema = ChangePasswordApiAttrs
        attrs_schema_required = True


class LoginApiAttrs(ObjectAttrs):
    email = fields.Email(required=True, default=None)
    password = fields.Str(required=True, default=None)

    class Meta:
        strict = True
        ordered = True
        object_type = "user"


class MeetingStateField(search_fields.ListTermsField):

    def q(self, value):
        today = timezone.now().date()
        states = list(set(value))
        should = []
        for state in states:
            if state == "planned":
                should.append(Q("range", **{"start_date": {"gte": today}}))
            elif state == "finished":
                should.append(Q("range", **{"start_date": {"lt": today}}))

        return Q("bool", should=should, minimum_should_match=1)


class MeetingStateTermsSchema(ListTermsSchema):
    terms = MeetingStateField(
        example="finished,planned",
        validate=validate.ContainsOnly(
            choices=MEETING_STATE_CHOICES,
            error=_("Invalid choice! Valid are: %(choices)s.") % {"choices": MEETING_STATE_CHOICES},
        ),
    )

    class Meta:
        default_field = "terms"


class MeetingApiSearchRequest(ListingSchema):
    id = search_fields.FilterField(
        NumberTermSchema,
        doc_template="docs/generic/fields/number_term_field.html",
        doc_base_url="/meetings",
        doc_field_name="ID",
    )
    sort = search_fields.SortField(
        sort_fields={
            "id": "id",
            "start_date": "start_date",
        },
        doc_base_url="/meetings",
        missing="id",
    )
    state = search_fields.FilterField(
        MeetingStateTermsSchema,
        doc_template="docs/generic/fields/string_term_field.html",
        doc_base_url="/meetings",
        doc_field_name="state",
    )

    class Meta:
        strict = True
        ordered = True


class UserUpdateApiAttrs(ObjectAttrs):
    fullname = fields.Str()
    phone = fields.Str()
    subscriptions_report_opt_in = fields.Boolean()
    rodo_privacy_policy_opt_in = fields.Boolean()

    class Meta:
        strict = True
        ordered = True
        object_type = "user"

    @post_load
    def prepare_data(self, data, **kwargs):
        # TODO: change field names: is_rodo_accepted, is_privacy_policy_accepted or similar.
        se = data.get("subscriptions_report_opt_in", None)
        pp = data.get("rodo_privacy_policy_opt_in", None)
        now = timezone.now()
        if se is not None:
            data["subscriptions_report_opt_in"] = now if se else None
        if pp is not None:
            data["rodo_privacy_policy_opt_in"] = now if pp else None
        return data


class RegistrationApiAttrs(UserUpdateApiAttrs):
    email = fields.Email(required=True, default=None)
    password1 = fields.Str(required=True)
    password2 = fields.Str(required=True)

    class Meta:
        strict = True
        ordered = True
        object_type = "user"

    @validates_schema
    def validate_data(self, data, **kwargs):
        if "password1" in data:
            try:
                validate_password(data["password1"])
            except DjangoValidationError as e:
                raise ValidationError(
                    e.error_list[0].message,
                    field_name="password1",
                    code=e.error_list[0].code,
                    field_names=[
                        "password1",
                    ],
                )
            if "password2" in data and data["password1"] != data["password2"]:
                raise ValidationError(
                    _("Passwords not match"),
                    field_name="password1",
                    field_names=["password1", "password2"],
                )

    @post_load
    def prepare_data(self, data, **kwargs):
        data = super().prepare_data(data)
        data["password"] = data["password1"]
        data.pop("password1")
        data.pop("password2")
        data.pop("subscriptions_report_opt_in", None)
        return data


class ResendActivationEmailApiAttrs(ObjectAttrs):
    email = fields.Email(required=True, default=None)

    class Meta:
        strict = True
        ordered = True
        object_type = "user"


class ResetPasswordApiAttrs(ResendActivationEmailApiAttrs):
    pass


class LoginApiRequest(TopLevel):
    class Meta:
        attrs_schema = LoginApiAttrs
        attrs_schema_required = True


class RegistrationApiRequest(TopLevel):
    class Meta:
        attrs_schema = RegistrationApiAttrs
        attrs_schema_required = True


class ResendActivationEmailApiRequest(TopLevel):
    class Meta:
        attrs_schema = ResendActivationEmailApiAttrs
        attrs_schema_required = True


class ResetPasswordApiRequest(TopLevel):
    class Meta:
        attrs_schema = ResetPasswordApiAttrs
        attrs_schema_required = True


class UserUpdateApiRequest(TopLevel):
    class Meta:
        attrs_schema = UserUpdateApiAttrs
        attrs_schema_required = True


class ConfirmResetPasswordApiAttrs(ObjectAttrs):
    new_password1 = fields.Str(required=True)
    new_password2 = fields.Str(required=True)

    class Meta:
        strict = True
        ordered = True
        object_type = "user"

    @validates_schema()
    def validate_passwords(self, data, **kwargs):
        if "new_password1" in data:
            try:
                validate_password(data["new_password1"])
            except DjangoValidationError as e:
                raise ValidationError(
                    e.error_list[0].message,
                    field_name="new_password1",
                    code=e.error_list[0].code,
                )
            if "new_password2" in data:
                if data["new_password1"] != data["new_password2"]:
                    raise ValidationError(
                        _("Passwords not match"),
                        field_name="new_password1",
                        field_names=["new_password1", "new_password2"],
                    )


class ConfirmResetPasswordApiRequest(TopLevel):
    class Meta:
        attrs_schema = ConfirmResetPasswordApiAttrs
        attrs_schema_required = True
