import json
from functools import partial

import falcon
from apispec import APISpec
from dal import autocomplete
from django.apps import apps
from django.template import loader
from elasticsearch_dsl import A

from mcod import settings
from mcod.core.api.cache import documented_cache
from mcod.core.api.handlers import (
    BaseHdlr,
    CreateOneHdlr,
    RemoveOneHdlr,
    RetrieveManyHdlr,
    RetrieveOneHdlr,
    SearchHdlr,
    ShaclMixin,
    SubscriptionSearchHdlr,
    UpdateOneHdlr,
)
from mcod.core.api.hooks import login_optional, login_required
from mcod.core.api.openapi.plugins import TabularDataPlugin
from mcod.core.api.rdf.vocabs.openness_score import OpennessScoreVocab
from mcod.core.api.rdf.vocabs.special_sign import SpecialSignVocab
from mcod.core.api.schemas import ListingSchema
from mcod.core.api.versions import DOC_VERSIONS
from mcod.core.api.views import JsonAPIView, RDFView, VocabEntryRDFView, VocabRDFView
from mcod.core.versioning import versioned
from mcod.counters.lib import Counter
from mcod.lib.encoders import DateTimeToISOEncoder
from mcod.resources.deserializers import (
    ChartApiRequest,
    CreateCommentRequest,
    GeoApiSearchRequest,
    ResourceApiRequest,
    ResourceApiSearchRequest,
    ResourceRdfApiRequest,
    TableApiRequest,
    TableApiSearchRequest,
)
from mcod.resources.documents import ResourceDocument
from mcod.resources.models import AggregatedDGAInfo
from mcod.resources.serializers import (
    AggregatedDGAInfoApiResponse,
    ChartApiResponse,
    CommentApiResponse,
    GeoApiResponse,
    GeoFeatureRecord,
    ResourceApiResponse,
    ResourceRDFResponseSchema,
    TableApiResponse,
    VocabEntryRDFResponseSchema,
    VocabRDFResponseSchema,
)

Resource = apps.get_model("resources", "Resource")


class ResourcesView(JsonAPIView):
    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/resources/resources_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_optional)
    @on_get.version("1.0")
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SubscriptionSearchHdlr):
        deserializer_schema = ResourceApiSearchRequest
        serializer_schema = partial(ResourceApiResponse, many=True)
        search_document = ResourceDocument()


class ResourceView(JsonAPIView):
    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/resources/resource_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_optional)
    @on_get.version("1.0")
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        deserializer_schema = ResourceApiRequest
        database_model = apps.get_model("resources", "Resource")
        serializer_schema = partial(ResourceApiResponse, many=False)
        include_default = ["dataset", "institution"]


class ResourceRDFView(RDFView):
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(ShaclMixin, RetrieveOneHdlr):
        deserializer_schema = ResourceRdfApiRequest
        database_model = apps.get_model("resources", "Resource")
        serializer_schema = ResourceRDFResponseSchema

        def serialize(self, *args, **kwargs):
            if self.use_rdf_db():
                store = self.get_sparql_store()
                return store.get_resource_graph(**kwargs)
            return super().serialize(*args, **kwargs)

        def _get_instance(self, dataset_id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                model = self.database_model
                try:
                    self._cached_instance = model.objects.get(
                        dataset_id=dataset_id,
                        pk=kwargs["res_id"],
                        status=model.STATUS.published,
                    )
                except model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance


class VocabSpecialSignRDFView(VocabRDFView):
    class GET(VocabRDFView.GET):
        serializer_schema = VocabRDFResponseSchema
        vocab_class = SpecialSignVocab


class VocabEntrySpecialSignRDFView(VocabEntryRDFView):
    vocab_class = SpecialSignVocab
    vocab_name = "Special Sign Vocabulary"

    class GET(VocabEntryRDFView.GET):
        serializer_schema = VocabEntryRDFResponseSchema
        vocab_class = SpecialSignVocab


class VocabOpennessScoreRDFView(VocabRDFView):
    class GET(VocabRDFView.GET):
        serializer_schema = VocabRDFResponseSchema
        vocab_class = OpennessScoreVocab


class VocabEntryOpennessScoreRDFView(VocabEntryRDFView):
    vocab_class = OpennessScoreVocab
    vocab_name = "Openness Score Vocabulary"

    class GET(VocabEntryRDFView.GET):
        serializer_schema = VocabEntryRDFResponseSchema
        vocab_class = OpennessScoreVocab


class ResourceTableView(JsonAPIView):
    @versioned
    @documented_cache(timeout=900)
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/tables/list_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    @on_get.version("1.0")
    @documented_cache(timeout=900)
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SearchHdlr):
        deserializer_schema = partial(TableApiSearchRequest)
        database_model = apps.get_model("resources", "Resource")
        serializer_schema = partial(TableApiResponse, many=True)

        def _queryset_extra(self, queryset, *args, **kwargs):
            sort = self.request.context.cleaned_data.get("sort")
            return queryset if sort else queryset.sort("_score", "row_no")

        def _get_resource_instance(self, resource_id):
            cached_resource = getattr(self, "_cached_resource", None)
            if not cached_resource:
                model = self.database_model
                try:
                    self._cached_resource = model.objects.get(pk=resource_id, status="published")

                except model.DoesNotExist:
                    raise falcon.HTTPNotFound

            return self._cached_resource

        def _get_data(self, cleaned, id, *args, **kwargs):
            resource = self._get_resource_instance(id)

            if resource.data and resource.data.available:
                self.search_document = resource.data.doc
                schema_cls = TableApiResponse
                _fields = resource.data.get_api_fields()
                schema_cls.opts.attrs_schema._declared_fields = _fields
                self.serializer_schema = partial(schema_cls, many=True)

                _data = super()._get_data(cleaned, id, *args, **kwargs)
                aggs = {}
                for agg_name in _data.aggregations._d_.keys():
                    _, agg_type, col_name = agg_name.split("_")
                    if agg_type not in aggs:
                        aggs[agg_type] = []
                    aggs[agg_type].append(
                        {
                            "column": col_name,
                            "value": getattr(_data.aggregations, agg_name).value,
                        }
                    )
                for agg_type, value in aggs.items():
                    setattr(_data.aggregations, agg_type, value)
                return _data

            return []

        def _get_meta(self, cleaned, id, *args, **kwargs):
            resource = self._get_resource_instance(id)
            return resource.data_meta

        def _get_queryset(self, cleaned, id, *args, **kwargs):
            resource = self._get_resource_instance(id)
            self.search_document = resource.data.doc
            self.deserializer.fields["sort"].sort_map = resource.data.get_sort_map()
            self.deserializer.context["index"] = resource.data.doc._index
            return super()._get_queryset(cleaned, *args, **kwargs)

        def prepare_context(self, *args, **kwargs):
            cleaned = getattr(self.request.context, "cleaned_data") or {}
            debug_enabled = getattr(self.response.context, "debug", False)
            if debug_enabled:
                self.response.context.query = self._get_debug_query(cleaned, *args, **kwargs)
            result = self._get_data(cleaned, *args, **kwargs)

            self.response.context.data = result
            self.response.context.meta = self._get_meta(result, *args, **kwargs)
            included = self._get_included(result, *args, **kwargs)
            if included:
                self.response.context.included = included


class ResourceTableRowView(JsonAPIView):
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/tables/single_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        deserializer_schema = partial(TableApiRequest)
        serializer_schema = partial(TableApiResponse, many=False)
        database_model = apps.get_model("resources", "Resource")

        def _get_data(self, cleaned, id, row_id, *args, **kwargs):
            resource = self._get_instance(id, *args, **kwargs)
            self.search_document = resource.data.doc

            schema_cls = TableApiResponse
            _fields = resource.data.get_api_fields()
            schema_cls.opts.attrs_schema._declared_fields = _fields
            self.serializer_schema = partial(schema_cls, many=True)
            if resource.data and resource.data.available:
                return self.search_document.get(row_id)

            raise falcon.HTTPNotFound

        def _get_meta(self, cleaned, id, *args, **kwargs):
            resource = self._get_instance(id, *args, **kwargs)
            return resource.data_meta


class ResourceGeoView(JsonAPIView):
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SearchHdlr):
        deserializer_schema = GeoApiSearchRequest
        database_model = apps.get_model("resources", "Resource")
        serializer_schema = partial(GeoApiResponse, many=True)

        def _get_resource_instance(self, resource_id):
            cached_resource = getattr(self, "_cached_resource", None)
            if not cached_resource:
                model = self.database_model
                try:
                    self._cached_resource = model.objects.get(pk=resource_id, status="published")

                except model.DoesNotExist:
                    raise falcon.HTTPNotFound

                if not self._cached_resource.data:
                    raise falcon.HTTPNotFound

            return self._cached_resource

        def _get_data(self, cleaned, id, *args, **kwargs):
            resource = self._get_resource_instance(id)
            if resource.data and resource.data.available:
                self.search_document = resource.data.doc

                schema_cls = GeoFeatureRecord
                schema_cls.opts.fields = resource.data.get_api_fields()
                self.serializer_schema = partial(GeoApiResponse, many=True)

                data = super()._get_data(cleaned, id, *args, **kwargs)

                tiles = []
                for agg_name in data.aggregations._d_.keys():
                    if agg_name.startswith("tile"):
                        agg = getattr(data.aggregations, agg_name)
                        tile = {
                            "tile_name": agg_name,
                            "doc_count": agg.buckets.bound.doc_count,
                            "shapes": agg.buckets.bound.points.hits,
                        }
                        if agg.buckets.bound.doc_count != 0:
                            tile["centroid"] = [
                                agg.buckets.bound.centroid.location.lon,
                                agg.buckets.bound.centroid.location.lat,
                            ]
                            tiles.append(tile)
                    elif agg_name == "bounds" and hasattr(data.aggregations.bounds, "bounds"):
                        data.aggregations.bounds = {
                            "top_left": [
                                data.aggregations.bounds.bounds.top_left.lon,
                                data.aggregations.bounds.bounds.top_left.lat,
                            ],
                            "bottom_right": [
                                data.aggregations.bounds.bounds.bottom_right.lon,
                                data.aggregations.bounds.bounds.bottom_right.lat,
                            ],
                        }
                    elif agg_name == "others":
                        data._hits = data.aggregations.others.buckets.others.others.hits

                if tiles:
                    data.aggregations.tiles = tiles
                return data

            raise falcon.HTTPNotFound

        def _queryset_extra(self, queryset, *args, **kwargs):
            queryset.aggs.metric("bounds", A("geo_bounds", field="point"))
            return queryset

        def _get_queryset(self, cleaned, id, *args, **kwargs):
            if cleaned.get("no_data", False):
                cleaned["per_page"] = 0
            resource = self._get_resource_instance(id)
            self.deserializer.fields["sort"].sort_map = resource.data.get_sort_map()
            return super()._get_queryset(cleaned, *args, **kwargs)

        def _get_meta(self, cleaned, id, *args, **kwargs):
            resource = self._get_resource_instance(id)
            return resource.data_meta

        def prepare_context(self, *args, **kwargs):
            cleaned = getattr(self.request.context, "cleaned_data") or {}
            result = self._get_data(cleaned, *args, **kwargs)
            self.response.context.meta = {}
            if any(bool(getattr(result, attr, False)) for attr in ["hits", "aggregations"]):
                self.response.context.data = result
                self.response.context.meta = self._get_meta(result, *args, **kwargs)
                included = [x for x in self._get_included(result, *args, **kwargs) if x]
                if included:
                    self.response.context.included = included


class ResourceCommentsView(JsonAPIView):
    def on_post(self, request, response, *args, **kwargs):
        self.handle(request, response, self.POST, *args, **kwargs)

    class POST(CreateOneHdlr):
        deserializer_schema = CreateCommentRequest
        serializer_schema = partial(CommentApiResponse, many=False)
        database_model = apps.get_model("resources", "Resource")

        def _get_resource(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_resource", None)
            if not instance:
                model = self.database_model
                try:
                    self._cached_resource = self.database_model.objects.get(pk=id, status="published")
                except model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_resource

        def clean(self, id, *args, **kwargs):
            cleaned = super().clean(id, *args, **kwargs)
            self._get_resource(id, *args, **kwargs)
            return cleaned

        def _get_data(self, cleaned, id, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            model = apps.get_model("suggestions.ResourceComment")
            self.response.context.data = model.objects.create(resource_id=id, **data)


class ResourceFileDownloadView:
    """
    Download file view. Preparing an url link for specified resource file.
    Increments download counter for resource.
    """

    def __init__(self, file_type=None):
        super().__init__()
        self.file_type = file_type

    def on_request(self, request, response, id, *args, **kwargs):
        try:
            resource = Resource.objects.get(pk=id, status="published")
        except Resource.DoesNotExist:
            raise falcon.HTTPNotFound

        if not resource.type == "file" or (not resource.file_url and not resource.link):
            raise falcon.HTTPNotFound

        if request.method == "GET":
            counter = Counter()
            counter.incr_download_count(id)

        response.location = resource.get_location(self.file_type)
        response.status = falcon.HTTP_302

    def on_get(self, request, response, id, *args, **kwargs):
        self.on_request(request, response, id, *args, **kwargs)

    def on_head(self, request, response, id, *args, **kwargs):
        self.on_request(request, response, id, *args, **kwargs)


class ResourceTableSpecView:
    def on_get(self, req, resp, id, version=None):
        version = version or str(max(DOC_VERSIONS))

        if version and version not in DOC_VERSIONS:
            raise falcon.HTTPBadRequest(description="Unsupported API version")

        try:
            resource = Resource.objects.get(pk=id)
        except Resource.DoesNotExist:
            raise falcon.HTTPNotFound

        if not resource.tabular_data_schema:
            raise falcon.HTTPNotFound

        if not resource.data.available:
            raise falcon.HTTPNotFound

        template = loader.get_template("docs/tables/description.html")
        context = {"resource": resource, "headers_map": resource.data.headers_map}
        description = template.render(context)

        spec = APISpec(
            title=resource.title_truncated,
            version=version,
            openapi_version="3.0.0",
            plugins=[TabularDataPlugin(version)],
            info={
                "description": description,
            },
        )

        schema_cls = TableApiResponse
        _fields = resource.data.get_api_fields()
        schema_cls.opts.attrs_schema._declared_fields = _fields

        spec.components.schema("Rows", schema_cls=schema_cls, many=True)
        spec.components.schema("Row", schema_cls=schema_cls, many=False)
        spec.path(path="/resources/%s/data" % resource.id, resource=ResourceTableView)
        spec.path(path="/resources/%s/data/{id}" % resource.id, resource=ResourceTableRowView)

        resp.text = json.dumps(spec.to_dict(), cls=DateTimeToISOEncoder)
        resp.status = falcon.HTTP_200


class ResourceSwaggerView:
    def on_get(self, request, response, id):
        try:
            resource = Resource.objects.get(pk=id)
        except Resource.DoesNotExist:
            raise falcon.HTTPNotFound

        template = loader.get_template("swagger_ui/index.html")
        versions = sorted(DOC_VERSIONS, reverse=True)
        spec_url_mask = "{}/resources/{}/data/spec/{}"
        context = {
            "spec_url": spec_url_mask.format(settings.API_URL, id, str(versions[0])),
            "spec_urls": [
                {
                    "url": spec_url_mask.format(settings.API_URL, id, str(version)),
                    "name": "DANE.GOV.PL - {} API v{}".format(resource.title_truncated, str(version)),
                }
                for version in versions
            ],
            "custom_css": "custom.css",
        }

        response.status = falcon.HTTP_200
        response.content_type = "text/html"
        response.text = template.render(context)


class ResourceDownloadCounter:
    def on_put(self, req, resp, id=None, **kwargs):
        if id:
            counter = Counter()
            counter.incr_download_count(id)
        resp.status = falcon.HTTP_200
        resp.content_type = "text/html"
        resp.text = json.dumps({}, cls=DateTimeToISOEncoder)


class CHART_POST(CreateOneHdlr):
    deserializer_schema = ChartApiRequest
    serializer_schema = ChartApiResponse
    database_model = apps.get_model("resources", "Resource")

    def clean(self, *args, **kwargs):
        self.deserializer.context.update(
            {
                "resource": self._get_instance(*args, **kwargs),
                "user": self.request.user,
            }
        )
        return super().clean(*args, **kwargs)

    def _get_instance(self, *args, **kwargs):
        instance = getattr(self, "_cached_instance", None)
        if not instance:
            try:
                self._cached_instance = self.database_model.objects.get(
                    pk=kwargs["id"],
                    status=self.database_model.STATUS.published,
                )
            except self.database_model.DoesNotExist:
                raise falcon.HTTPNotFound
        return self._cached_instance

    def _get_data(self, cleaned, *args, **kwargs):
        resource = self._get_instance(*args, **kwargs)
        try:
            self.response.context.data = resource.save_chart(self.request.user, cleaned["data"]["attributes"])
        except Exception as exc:
            raise falcon.HTTPForbidden(title=exc)


class ChartView(JsonAPIView):
    @falcon.before(login_required)
    def on_delete(self, request, response, *args, **kwargs):
        self.handle_delete(request, response, self.DELETE, *args, **kwargs)

    @falcon.before(login_optional)
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/resources/chart_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required)
    def on_patch(self, request, response, *args, **kwargs):
        self.handle_patch(request, response, self.PATCH, *args, **kwargs)

    @falcon.before(login_required)
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, CHART_POST, *args, **kwargs)

    class DELETE(RemoveOneHdlr):
        database_model = apps.get_model("resources", "Chart")

        def clean(self, *args, **kwargs):
            try:
                instance = self.database_model.objects.published().get(id=kwargs.get("chart_id"))
            except self.database_model.DoesNotExist:
                raise falcon.HTTPNotFound
            if not self.request.user.can_delete_resource_chart(instance):
                raise falcon.HTTPForbidden
            return instance

        def run(self, *args, **kwargs):
            instance = self.clean(*args, **kwargs)
            instance.delete(modified_by=self.request.user)
            return {}

    class GET(RetrieveOneHdlr):
        deserializer_schema = ChartApiResponse
        serializer_schema = ChartApiResponse
        chart_model = apps.get_model("resources", "Chart")
        database_model = apps.get_model("resources", "Resource")

        def _get_chart_instance(self, id, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = self.chart_model.objects.published().get(pk=kwargs["chart_id"], resource_id=id)
                except self.chart_model.DoesNotExist:
                    raise falcon.HTTPNotFound
            if not self._cached_instance.is_visible_for(self.request.user):
                raise falcon.HTTPForbidden
            return self._cached_instance

        def _get_instance(self, id, *args, **kwargs):
            if "chart_id" in kwargs:
                return self._get_chart_instance(id, *args, **kwargs)
            resource = super()._get_instance(id, *args, **kwargs)
            return resource.charts.chart_for_user(self.request.user)

    class PATCH(UpdateOneHdlr):
        database_model = apps.get_model("resources", "Chart")
        deserializer_schema = ChartApiRequest
        serializer_schema = ChartApiResponse

        def clean(self, *args, **kwargs):
            chart = self._get_instance(*args, **kwargs)
            if not chart.can_be_updated_by(self.request.user):
                raise falcon.HTTPForbidden(title="You have no permission to update the resource!")
            self.deserializer.context.update(
                {
                    "chart": chart,
                    "resource": chart.resource,
                    "user": self.request.user,
                }
            )
            return super().clean(validators=None, *args, **kwargs)

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = self.database_model.objects.published().get(
                        pk=kwargs["chart_id"], resource_id=kwargs["id"]
                    )
                except self.database_model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

        def _get_data(self, cleaned, id, *args, **kwargs):
            chart = self._get_instance(*args, **kwargs)
            try:
                chart.update(self.request.user, cleaned["data"]["attributes"])
                return chart
            except Exception as exc:
                raise falcon.HTTPForbidden(title=exc)


class ChartsView(JsonAPIView):
    @falcon.before(login_optional)
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/resources/charts_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    @falcon.before(login_required)
    def on_post(self, request, response, *args, **kwargs):
        self.handle_post(request, response, CHART_POST, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        database_model = apps.get_model("resources", "Resource")
        deserializer_schema = ListingSchema
        serializer_schema = partial(ChartApiResponse, many=True)

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = self.database_model.objects.get(
                        pk=kwargs["id"],
                        status=self.database_model.STATUS.published,
                    )
                except self.database_model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance

        def clean(self, *args, **kwargs):
            self.serializer.context["named_charts"] = True
            self._get_instance(*args, **kwargs)
            return super().clean(*args, **kwargs)

        def _get_queryset(self, cleaned, *args, **kwargs):
            resource = self._get_instance(*args, **kwargs)
            return resource.charts_for_user(self.request.user, **cleaned)


class AggregatedDGAInfoView(JsonAPIView):

    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/resources/aggregated_dga_info_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        database_model = apps.get_model("resources", "AggregatedDGAInfo")
        serializer_schema = AggregatedDGAInfoApiResponse

        def _get_data(self, cleaned, *args, **kwargs) -> AggregatedDGAInfo:
            data: AggregatedDGAInfo = (
                self.database_model.objects.select_related("resource", "resource__dataset")
                .only(
                    "resource__id",
                    "resource__slug",
                    "resource__dataset__id",
                    "resource__dataset__slug",
                    "resource__status",
                    "resource__is_removed",
                )
                .first()
            )

            if not data or data.resource is None or data.resource.is_removed or not data.resource.is_published:
                raise falcon.HTTPNotFound
            return data

        def serialize(self, *args, **kwargs):
            self.prepare_context(*args, **kwargs)
            return self.serializer.dump(self.response.context.data)


class ResourceAutocompleteView(autocomplete.Select2QuerySetView):
    def get_result_label(self, result):
        return result.label_from_instance

    def get_queryset(self):
        return Resource.raw.autocomplete(self.request.user, self.q, self.forwarded)
