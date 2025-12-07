from marshmallow import pre_dump

from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import (
    ObjectAttrs,
    Relationship,
    RelationshipData,
    RelationshipLinks,
    RelationshipMeta,
    Relationships,
    TopLevel,
)
from mcod.core.api.schemas import ExtSchema
from mcod.watchers.models import Subscription


class SubscriptionMixin:
    @pre_dump
    def prepare_subscriptions(self, c, **kwargs):
        request = self.context["request"]
        is_listing = self.context["is_listing"]
        usr = getattr(request, "user", None)
        if usr and usr.is_authenticated:
            if is_listing:
                c.data = getattr(c, "data", [])
                for item in c.data:
                    if hasattr(item.meta, "inner_hits") and hasattr(item.meta.inner_hits, "subscriptions"):
                        if item.meta.inner_hits.subscriptions.hits.total > 0:
                            try:
                                subscription_id = item.meta.inner_hits.subscriptions[0].subscription_id
                            except AttributeError:
                                # Legacy, for elasticsearch_dsl < 6.4.2 to be removed
                                subscription_id = item.meta.inner_hits.subscriptions[0]._source["subscription_id"]

                            item.subscription = {"id": subscription_id}

            else:
                c.data = getattr(c, "data", {})
                c.data.set_subscription(usr)

            try:
                subscription = Subscription.objects.get_from_data(
                    usr,
                    {"object_name": "query", "object_ident": request.url},
                    headers=request.headers,
                )
                c.meta = getattr(c, "meta", {})
                c.meta["subscription_url"] = subscription.api_url
            except Subscription.DoesNotExist:
                pass

        return c


class SubscriptionRelationship(ExtSchema):
    data = fields.Nested(RelationshipData)
    links = fields.Nested(RelationshipLinks, required=True, many=False)
    meta = fields.Nested(RelationshipMeta, many=False)

    @pre_dump
    def prepare_data(self, data, **kwargs):
        return {
            "data": {"id": str(data.object_ident), "_type": data.obj_type},
            "links": {"related": data.get_obj_url(self.api_url)},
        }


class SubscriptionApiRelationships(Relationships):
    subscribed_object = fields.Nested(SubscriptionRelationship, attribute="watcher", many=False)
    notifications = fields.Nested(
        Relationship,
        many=False,
        default=[],
        _type="notification",
        url_template="{object_url}/notifications",
    )


class SubscriptionApiAggs(ExtSchema):
    pass


class SubscriptionApiAttrs(ObjectAttrs):
    created = fields.DateTime()
    modified = fields.DateTime()
    title = fields.Str(attribute="display_name")
    customfields = fields.Dict(missing={}, default={})

    def get_object_url(self, obj):
        if obj.watcher.watcher_type == "model":
            instance = obj.watcher.obj
            return instance.api_url
        return ""

    class Meta:
        relationships_schema = SubscriptionApiRelationships
        object_type = "subscription"
        url_template = "{api_url}/auth/subscriptions/{ident}"


class SubscriptionApiResponse(TopLevel):
    class Meta:
        attrs_schema = SubscriptionApiAttrs
        aggs_schema = SubscriptionApiAggs


class NotificationApiRelationships(Relationships):
    subscribed_object = fields.Nested(SubscriptionRelationship, attribute="subscription.watcher", many=False)
    subscription = fields.Nested(
        Relationship,
        many=False,
        _type="subscription",
        url_template="{api_url}/auth/subscriptions/{ident}",
    )


class NotificationApiAggs(ExtSchema):
    pass


class NotificationApiAttrs(ObjectAttrs):
    _type = fields.Str(data_key="type", attribute="type")
    status = fields.Str()
    notification_type = fields.Str()
    created = fields.DateTime()
    ref_value = fields.Str(default="")

    class Meta:
        relationships_schema = NotificationApiRelationships
        object_type = "notification"
        url_template = "{api_url}/auth/notifications/{ident}"


class NotificationApiResponse(TopLevel):
    class Meta:
        attrs_schema = NotificationApiAttrs
        aggs_schema = NotificationApiAggs
