from functools import partial

import falcon
from dal import autocomplete
from django.apps import apps
from django.conf import settings
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.http import JsonResponse
from django.utils.translation import get_language
from django.views import View
from elasticsearch_dsl import A, Q

from mcod.core.api.handlers import (
    BaseHdlr,
    CreateOneHdlr,
    RetrieveOneHdlr,
    SearchHdlr,
    ShaclMixin,
    SubscriptionSearchHdlr,
)
from mcod.core.api.hooks import login_optional
from mcod.core.api.views import BaseView, JsonAPIView, RDFView
from mcod.core.versioning import versioned
from mcod.datasets.deserializers import (
    CatalogRdfApiRequest,
    CreateCommentRequest,
    DatasetApiRequest,
    DatasetApiSearchRequest,
    LicenseApiRequest,
)
from mcod.datasets.documents import DatasetDocument
from mcod.datasets.handlers import (
    ArchiveDownloadViewHandler,
    CSVMetadataViewHandler,
    XMLMetadataViewHandler,
)
from mcod.datasets.models import LICENSE_CONDITION_LABELS, Dataset
from mcod.datasets.serializers import (
    CommentApiResponse,
    DatasetApiResponse,
    DatasetRDFResponseSchema,
    LicenseApiResponse,
)
from mcod.resources.deserializers import ResourceApiSearchRequest
from mcod.resources.documents import ResourceDocument
from mcod.resources.serializers import ResourceApiResponse


class DatasetSearchView(JsonAPIView):
    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/datasets/datasets_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_optional)
    @on_get.version("1.0")
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SubscriptionSearchHdlr):
        deserializer_schema = partial(DatasetApiSearchRequest, many=False)
        serializer_schema = partial(DatasetApiResponse, many=True)
        search_document = DatasetDocument()
        include_default = ["institution"]

        def __init__(self, request, response):
            super().__init__(request, response)
            self.deserializer.context["dataset_promotion_enabled"] = True


class DatasetApiView(JsonAPIView):
    @versioned
    @falcon.before(login_optional)
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/datasets/dataset_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_optional)
    @on_get.version("1.0")
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        deserializer_schema = partial(DatasetApiRequest)
        database_model = apps.get_model("datasets", "Dataset")
        serializer_schema = partial(DatasetApiResponse, many=False)
        include_default = ["institution", "resource"]


class CatalogRDFView(RDFView):
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(ShaclMixin, SearchHdlr):
        deserializer_schema = partial(CatalogRdfApiRequest, many=False)
        serializer_schema = partial(DatasetRDFResponseSchema, many=True)
        search_document = DatasetDocument()

        def _queryset_extra(self, queryset, *args, **kwargs):
            queryset.aggs.metric("catalog_modified", A("max", field="last_modified_resource"))
            return queryset

        def serialize(self, *args, **kwargs):
            cleaned = getattr(self.request.context, "cleaned_data", {})
            if self.use_rdf_db():
                store = self.get_sparql_store()
                return store.get_catalog(**cleaned)
            result = self._get_data(cleaned, *args, **kwargs)
            self.serializer.context["datasource"] = "es"
            return self.serializer.dump(result)


class DatasetRDFView(RDFView):
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(ShaclMixin, RetrieveOneHdlr):
        deserializer_schema = partial(DatasetApiRequest)
        database_model = apps.get_model("datasets", "Dataset")
        serializer_schema = partial(DatasetRDFResponseSchema, many=False)

        def serialize(self, *args, **kwargs):
            if self.use_rdf_db():
                store = self.get_sparql_store()
                return store.get_dataset_graph(**kwargs)
            cleaned = getattr(self.request.context, "cleaned_data", {})
            dataset = self._get_data(cleaned, *args, **kwargs)
            self.serializer.context["datasource"] = "db"
            return self.serializer.dump(dataset)


class DatasetResourceSearchApiView(JsonAPIView):
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/datasets/dataset_resources_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    @on_get.version("1.0")
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SearchHdlr):
        deserializer_schema = partial(ResourceApiSearchRequest, many=False)
        serializer_schema = partial(ResourceApiResponse, many=True)
        search_document = ResourceDocument()

        def _queryset_extra(self, queryset, id=None, **kwargs):
            if id:
                queryset = queryset.query("nested", path="dataset", query=Q("term", **{"dataset.id": id}))
            return queryset.filter("term", status=Dataset.STATUS.published)


class DatasetCommentsView(JsonAPIView):
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, self.POST, *args, **kwargs)

    class POST(CreateOneHdlr):
        deserializer_schema = CreateCommentRequest
        serializer_schema = partial(CommentApiResponse, many=False)
        database_model = apps.get_model("datasets", "Dataset")

        def _get_resource(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_resource", None)
            if not instance:
                try:
                    self._cached_resource = self.database_model.objects.get(pk=id, status="published")
                except self.database_model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_resource

        def clean(self, id, *args, **kwargs):
            cleaned = super().clean(id, *args, **kwargs)
            self._get_resource(id, *args, **kwargs)
            return cleaned

        def _get_data(self, cleaned, id, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            model = apps.get_model("suggestions.DatasetComment")
            self.response.context.data = model.objects.create(dataset_id=id, **data)


class CSVMetadataView(BaseView):

    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(CSVMetadataViewHandler):

        def _get_queryset(self, cleaned, *args, **kwargs):
            return self.database_model.objects.filter(pk=kwargs["id"])

    def on_get_catalog(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GETCatalog, *args, **kwargs)

    class GETCatalog(BaseHdlr):

        def serialize(self, *args, **kwargs):
            try:
                with open(f"{settings.METADATA_MEDIA_ROOT}/{get_language()}/katalog.csv", "rb") as f:
                    catalog_file = f.read()
            except FileNotFoundError:
                raise falcon.HTTPNotFound
            self.response.downloadable_as = "katalog.csv"
            return catalog_file

    def set_content_type(self, resp, **kwargs):
        return settings.EXPORT_FORMAT_TO_MIMETYPE["csv"]


class XMLMetadataView(BaseView):

    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(XMLMetadataViewHandler):

        def _get_queryset(self, cleaned, *args, **kwargs):
            return self.database_model.objects.filter(id=kwargs["id"])

    def on_get_catalog(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GETCatalog, *args, **kwargs)

    class GETCatalog(BaseHdlr):

        def serialize(self, *args, **kwargs):
            try:
                with open(f"{settings.METADATA_MEDIA_ROOT}/{get_language()}/katalog.xml", "rb") as f:
                    catalog_file = f.read()
            except FileNotFoundError:
                raise falcon.HTTPNotFound
            self.response.downloadable_as = "katalog.xml"
            return catalog_file

    def set_content_type(self, resp, **kwargs):
        return settings.EXPORT_FORMAT_TO_MIMETYPE["xml"]


class LicenseView(JsonAPIView):

    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        deserializer_schema = LicenseApiRequest
        database_model = apps.get_model("datasets", "Dataset")
        serializer_schema = LicenseApiResponse

        def _get_data(self, cleaned, *args, **kwargs):
            data = self.database_model.get_license_data(kwargs["name"])
            if not data:
                raise falcon.HTTPNotFound
            return data


class DatasetResourcesFilesBulkDownloadView(BaseView):

    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    def on_head(self, request, response, *args, **kwargs):
        self.handle(request, response, self.HEAD, *args, **kwargs)

    class GET(ArchiveDownloadViewHandler):
        pass

    class HEAD(ArchiveDownloadViewHandler):
        pass

    def set_content_type(self, resp, **kwargs):
        return "application/zip"


class ConditionLabelsAdminView(PermissionRequiredMixin, View):
    http_method_names = ["get"]

    def has_permission(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def get(self, request, *args, **kwargs):
        req_organization_type = request.GET.get("organization_type")
        org_type = req_organization_type if req_organization_type in LICENSE_CONDITION_LABELS else "public"
        labels = LICENSE_CONDITION_LABELS[org_type]
        article_url = (
            f"{settings.BASE_URL}{settings.PUBLIC_LICENSES_ARTICLE_URL}"
            if org_type == "public"
            else f"{settings.BASE_URL}{settings.PRIVATE_LICENSES_ARTICLE_URL}"
        )
        return JsonResponse({"condition_labels": labels, "article_url": article_url})


class DatasetAutocompleteView(autocomplete.Select2QuerySetView):
    def get_queryset(self):
        return Dataset.objects.autocomplete(self.request.user, self.q)
