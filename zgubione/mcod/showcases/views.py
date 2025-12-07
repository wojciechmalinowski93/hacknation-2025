from collections import namedtuple
from functools import partial
from uuid import uuid4

import falcon
from django.apps import apps
from elasticsearch_dsl import Q

from mcod.core.api.handlers import CreateOneHdlr, RetrieveOneHdlr, SearchHdlr
from mcod.core.api.hooks import login_optional
from mcod.core.api.views import JsonAPIView
from mcod.core.versioning import versioned
from mcod.datasets.deserializers import DatasetApiSearchRequest
from mcod.datasets.documents import DatasetDocument
from mcod.datasets.serializers import DatasetApiResponse
from mcod.showcases.deserializers import (
    CreateShowcaseProposalRequest,
    ShowcaseApiRequest,
    ShowcasesApiRequest,
)
from mcod.showcases.documents import ShowcaseDocument
from mcod.showcases.models import Showcase
from mcod.showcases.serializers import ShowcaseApiResponse, ShowcaseProposalApiResponse
from mcod.showcases.tasks import create_showcase_proposal_task


class ShowcasesSearchHdlr(SearchHdlr):
    deserializer_schema = ShowcasesApiRequest
    serializer_schema = partial(ShowcaseApiResponse, many=True)
    search_document = ShowcaseDocument()

    def _queryset_extra(self, queryset, id=None, **kwargs):
        if id:
            queryset = queryset.query("nested", path="datasets", query=Q("term", **{"datasets.id": id}))
        return queryset.filter("term", status=Showcase.STATUS.published)


class ShowcasesApiView(JsonAPIView):
    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/showcases/showcases_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(ShowcasesSearchHdlr):
        pass


class DatasetShowcasesApiView(JsonAPIView):

    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/datasets/dataset_showcases_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(ShowcasesSearchHdlr):
        pass


class ShowcaseApiView(JsonAPIView):
    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/showcases/showcase_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        deserializer_schema = ShowcaseApiRequest
        database_model = apps.get_model("showcases.Showcase")
        serializer_schema = ShowcaseApiResponse

        def _get_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                model = self.database_model
                try:
                    user = getattr(self.request, "user", None)
                    data = {"id": id, "status": "published"}
                    if user and user.is_superuser:
                        data = {"id": id, "status__in": ["draft", "published"]}
                    self._cached_instance = model.objects.get(**data)
                except model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance


class ShowcaseDatasetsView(JsonAPIView):
    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/showcases/showcase_datasets_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SearchHdlr):
        deserializer_schema = DatasetApiSearchRequest
        serializer_schema = partial(DatasetApiResponse, many=True)
        search_document = DatasetDocument()
        include_default = ["institution"]

        def _queryset_extra(self, queryset, id=None, **kwargs):
            queryset = queryset.query("nested", path="showcases", query=Q("term", **{"showcases.id": id})) if id else queryset
            return queryset.filter("term", status="published")


class ShowcaseProposalView(JsonAPIView):
    @versioned
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    class POST(CreateOneHdlr):
        database_model = apps.get_model("showcases.ShowcaseProposal")
        deserializer_schema = CreateShowcaseProposalRequest
        serializer_schema = ShowcaseProposalApiResponse

        def _get_data(self, cleaned, *args, **kwargs):
            _data = cleaned["data"]["attributes"]
            _data.pop("is_personal_data_processing_accepted", None)
            _data.pop("is_terms_of_service_accepted", None)
            create_showcase_proposal_task.s(_data).apply_async()
            fields, values = [], []
            for field, val in _data.items():
                fields.append(field)
                values.append(val)
            fields.append("id")
            values.append(str(uuid4()))
            result = namedtuple("Submission", fields)(*values)
            return result
