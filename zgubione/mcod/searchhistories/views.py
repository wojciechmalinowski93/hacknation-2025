from functools import partial

import falcon
from elasticsearch_dsl import Q

from mcod.core.api.handlers import SearchHdlr
from mcod.core.api.hooks import login_required
from mcod.core.api.views import JsonAPIView
from mcod.core.versioning import versioned
from mcod.searchhistories.deserializers import SearchHistoryApiSearchRequest
from mcod.searchhistories.documents import SearchHistoriesDoc
from mcod.searchhistories.serializers import SearchHistoryApiResponse


class SearchHistoriesView(JsonAPIView):

    @falcon.before(login_required)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SearchHdlr):
        deserializer_schema = partial(SearchHistoryApiSearchRequest, many=False)
        serializer_schema = partial(SearchHistoryApiResponse, many=True)
        search_document = SearchHistoriesDoc()

        def _queryset_extra(self, queryset, *args, **kwargs):
            qs = super()._queryset_extra(queryset, *args, **kwargs)
            return qs.filter(
                "nested",
                path="user",
                query=Q("match", **{"user.id": self.request.user.id}),
            )
