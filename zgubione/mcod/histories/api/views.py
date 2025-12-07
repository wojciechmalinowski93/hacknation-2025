from functools import partial

import falcon
from django.apps import apps

from mcod.core.api.handlers import RetrieveOneHdlr, SearchHdlr
from mcod.core.api.views import JsonAPIView
from mcod.core.versioning import versioned
from mcod.histories.deserializers import HistoryApiRequest, LogEntryApiSearchRequest
from mcod.histories.documents import LogEntryDoc
from mcod.histories.serializers import LogEntryApiResponse


class HistoriesView(JsonAPIView):
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/histories/histories_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SearchHdlr):
        deserializer_schema = LogEntryApiSearchRequest
        search_document = LogEntryDoc()
        serializer_schema = partial(LogEntryApiResponse, many=True)


class HistoryView(JsonAPIView):
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/histories/history_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        database_model = apps.get_model("histories", "LogEntry")
        deserializer_schema = HistoryApiRequest
        serializer_schema = LogEntryApiResponse

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = (
                        self.database_model.objects.filter(content_type__model="dataset").exclude(actor_id=1).get(pk=id)
                    )
                except self.database_model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance
