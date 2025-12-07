from django.utils.translation import gettext_lazy as _
from marshmallow import pre_dump

from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import ObjectAttrs, TopLevel


class NewsletterRulesApiAttrs(ObjectAttrs):
    personal_data_processing = fields.Str()
    personal_data_use = fields.Str()
    personal_data_use_rules = fields.Str()

    class Meta:
        object_type = "newsletter_rules"
        url_template = "{api_url}/auth/newsletter/subscribe/"


class SubscriptionApiAttrs(ObjectAttrs):
    newsletter_subscription_info = fields.Str(attribute="info")

    class Meta:
        object_type = "subscription"
        url_template = "{api_url}/auth/subscriptions/{ident}"
        fields = ["email", "is_active", "newsletter_subscription_info"]


class NewsletterRulesApiResponse(TopLevel):
    class Meta:
        attrs_schema = NewsletterRulesApiAttrs


class SubscriptionApiResponse(TopLevel):
    class Meta:
        attrs_schema = SubscriptionApiAttrs


class UnsubscribeApiAttrs(ObjectAttrs):
    newsletter_subscription_info = fields.Str()

    class Meta:
        object_type = "unsubscribe_result"
        url_template = "{api_url}/auth/subscriptions/{ident}"
        fields = ["email", "newsletter_subscription_info"]

    @pre_dump
    def prepare_data(self, data, **kwargs):
        data.newsletter_subscription_info = _("Your email address was removed from our mailing list")
        return data


class UnsubscribeApiResponse(TopLevel):
    class Meta:
        attrs_schema = UnsubscribeApiAttrs
