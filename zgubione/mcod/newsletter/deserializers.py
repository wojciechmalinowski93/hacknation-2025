from django.utils.translation import gettext_lazy as _
from marshmallow import ValidationError, validates

from mcod.core.api import fields as core_fields
from mcod.core.api.jsonapi.deserializers import ObjectAttrs, TopLevel


class SubscriptionAttrs(ObjectAttrs):
    email = core_fields.Email(required=True)
    newsletter_subscription_info = core_fields.String(
        description="Human readable subscription status",
        example="Your subscription is active",
        required=False,
    )
    is_active = core_fields.Boolean(description="Is newsletter subscription active?", example=True, required=False)

    class Meta:
        object_type = "subscription"
        strict = True
        ordered = True


class NewsletterRulesAttrs(ObjectAttrs):
    personal_data_processing = core_fields.String()
    personal_data_use = core_fields.String()
    personal_data_use_rules = core_fields.String()


class NewsletterRulesApiRequest(TopLevel):
    class Meta:
        attrs_schema = NewsletterRulesAttrs


class UnsubscribeApiRequest(TopLevel):
    activation_code = core_fields.Str(required=True)

    class Meta:
        attrs_schema = SubscriptionAttrs


class SubscribeApiRequest(TopLevel):

    email = core_fields.Email(
        required=True,
        error_messages={"invalid": _("E-mail address you entered is not valid")},
    )
    personal_data_processing = core_fields.Boolean(required=True)
    personal_data_use = core_fields.Boolean(required=True)

    @validates("personal_data_processing")
    def validate_personal_data_processing(self, value):
        if not value:
            raise ValidationError(_("This field is required"))

    @validates("personal_data_use")
    def validate_personal_data_use(self, value):
        if not value:
            raise ValidationError(_("This field is required"))

    class Meta:
        attrs_schema = SubscriptionAttrs
