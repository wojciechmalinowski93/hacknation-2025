import marshmallow as ma

from mcod.lib.serializers import BasicSerializer
from mcod.schedules.serializers import NotificationSerializer


class Schema(ma.Schema):
    class Meta:
        ordered = True


class ServiceUrlSerializer(Schema):
    name = ma.fields.Str()
    url = ma.fields.Url()


class SubscriptionsAggregationSerializer(Schema):
    datasets = ma.fields.Integer()
    queries = ma.fields.Integer()


class AcademyAggregationsSerializer(Schema):
    planned = ma.fields.Integer()
    current = ma.fields.Integer()
    finished = ma.fields.Integer()


class LabAggregationSerializer(Schema):
    analyses = ma.fields.Integer()
    researches = ma.fields.Integer()


class SuggestionsAggregationSerializer(Schema):
    active = ma.fields.Integer()
    inactive = ma.fields.Integer()


class MeetingsAggregationSerializer(Schema):
    finished = ma.fields.Integer()
    planned = ma.fields.Integer()


class SchedulesAggregationSerializer(Schema):
    started = ma.fields.Integer()
    ready = ma.fields.Integer()
    recommended = ma.fields.Integer()
    schedule_items = ma.fields.Integer()
    state = ma.fields.Str()
    notifications_count = ma.fields.Integer()
    notifications = ma.fields.Nested(NotificationSerializer, many=True)


class DashboardAggregationsSerializer(Schema):
    academy = ma.fields.Nested(AcademyAggregationsSerializer)
    lab = ma.fields.Nested(LabAggregationSerializer)
    meetings = ma.fields.Nested(MeetingsAggregationSerializer)
    schedules = ma.fields.Nested(SchedulesAggregationSerializer)
    subscriptions = ma.fields.Nested(SubscriptionsAggregationSerializer)
    suggestions = ma.fields.Nested(SuggestionsAggregationSerializer)
    fav_charts = ma.fields.Raw()
    analytical_tools = ma.fields.Nested(ServiceUrlSerializer, many=True)
    cms_url = ma.fields.Url()


class DashboardMetaSerializer(Schema):
    aggregations = ma.fields.Nested(DashboardAggregationsSerializer)


class DashboardSerializer(BasicSerializer, ma.Schema):
    id = ma.fields.Integer()

    class Meta:
        strict = True
        type_ = "dashboard"
