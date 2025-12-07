from mcod.core.api import fields
from mcod.core.api.jsonapi.serializers import HighlightObjectMixin, ObjectAttrs, TopLevel
from mcod.core.api.schemas import ExtSchema
from mcod.watchers.serializers import SubscriptionMixin


class UserAttrs(ExtSchema):
    id = fields.Str()


class SearchHistoryApiAttrs(ObjectAttrs, HighlightObjectMixin):
    url = fields.Str()
    query_sentence = fields.Str()
    user = fields.Nested(UserAttrs, many=False)
    modified = fields.Str()

    class Meta:
        object_type = "searchhistory"
        url_template = "{api_url}/searchhistories/{ident}"
        model = "searchhistories.SearchHistory"


class SearchHistoryApiResponse(SubscriptionMixin, TopLevel):
    class Meta:
        attrs_schema = SearchHistoryApiAttrs
