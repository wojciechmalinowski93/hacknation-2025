import hashlib
import json
import logging
import mimetypes
import uuid
from collections import namedtuple
from functools import partial

import falcon
from django.core.paginator import Paginator
from django.utils.translation import gettext_lazy as _
from elasticsearch_dsl import A, Search

from mcod import settings
from mcod.core.api.cache import app_cache as cache
from mcod.core.api.handlers import BaseHdlr, RetrieveManyHdlr, SearchHdlr, SubscriptionSearchHdlr
from mcod.core.api.hooks import login_optional
from mcod.core.api.limiter import limiter
from mcod.core.api.rdf.namespaces import NAMESPACES
from mcod.core.api.schemas import ListingSchema
from mcod.core.api.views import BaseView, JsonAPIView
from mcod.core.versioning import versioned
from mcod.lib.rdf.store import get_sparql_store
from mcod.search.deserializers import (
    SPARQL_FORMATS,
    ApiSearchRequest,
    ApiSuggestRequest,
    SparqlRequest,
)
from mcod.search.serializers import (
    CommonObjectResponse,
    SparqlApiResponse,
    SparqlNamespaceApiResponse,
    SparqlResponseSchema,
)
from mcod.search.utils import get_sparql_limiter_key

logger = logging.getLogger("mcod")


PLURAL_MODEL_NAMES = {
    "application": "applications",
    "dataset": "datasets",
    "resource": "resources",
    "institution": "institutions",
    "knowledge_base": "knowledge_base",
    "organization": "organizations",
    "searchhistory": "searchhistories",
    "logentry": "logentries",
    "news": "news",
    "showcase": "showcases",
}


ALLOWED_MODELS = [
    "application",
    "dataset",
    "resource",
    "institution",
    "knowledge_base",
    "organization",
    "searchhistory",
    "logentry",
    "news",
    "showcase",
]


class NoneVisualizationCleaner:
    @staticmethod
    def remove_nones(data):
        for obj in data.hits.hits:
            try:
                obj["_source"]["visualization_types"].remove("none")
            except (ValueError, KeyError):
                pass

        return data


class SuggestView(JsonAPIView):
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SearchHdlr, NoneVisualizationCleaner):
        deserializer_schema = ApiSuggestRequest
        serializer_schema = partial(CommonObjectResponse, many=True)

        @property
        def _search_document(self):
            return Search(index=settings.ELASTICSEARCH_COMMON_ALIAS_NAME)

        def clean(self, *args, validators=None, locations=None, **kwargs):
            cleaned = super().clean(*args, validators, locations, **kwargs)
            return cleaned

        def _get_data(self, cleaned, *args, **kwargs):
            data = []

            if cleaned.get("q"):
                multi_data = super()._get_data(cleaned, *args, **kwargs)

                for md in multi_data:
                    data.extend(self.remove_nones(md))
                data = sorted(data, key=lambda hit: hit.meta["score"], reverse=True)
                if "max_length" in cleaned:
                    data = data[: cleaned["max_length"]]

            return data


class SearchView(JsonAPIView):
    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/search/search_view.yml
        """
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(SubscriptionSearchHdlr, NoneVisualizationCleaner):
        deserializer_schema = ApiSearchRequest
        serializer_schema = partial(CommonObjectResponse, many=True)

        def __init__(self, request, response):
            super().__init__(request, response)
            self.deserializer.context["dataset_promotion_enabled"] = True

        def _get_model_names(self, field="models"):
            models_query = self.request.context.cleaned_data.get(field, {})
            models = None
            if "term" in models_query:
                models = (models_query["term"],)
            elif "terms" in models_query:
                models = models_query["terms"]

            models = models or ALLOWED_MODELS

            return models

        @property
        def _search_document(self):
            return Search(index=settings.ELASTICSEARCH_COMMON_ALIAS_NAME)

        def _queryset_extra(self, queryset, *args, **kwargs):
            queryset = super()._queryset_extra(queryset, *args, **kwargs)
            filters = {PLURAL_MODEL_NAMES[field]: {"match": {"model": field}} for field in self._get_model_names()}
            queryset.aggs.metric("counters", A("filters", filters=filters))
            models = self.request.context.cleaned_data.get("model", {})
            for key, value in models.items():
                queryset = queryset.post_filter(key, model=value)
            return queryset

        def _get_data(self, cleaned, *args, **kwargs):
            data = super()._get_data(cleaned, *args, **kwargs)
            data = self.remove_nones(data)
            data.aggregations.counters = {
                model: val["doc_count"] for model, val in data.aggregations.counters.buckets.to_dict().items()
            }
            search_date_range = {}

            for limit in ("min", "max"):
                agg_name = f"{limit}_search_date"
                if agg_name in data.aggregations:
                    search_date_range[limit] = data.aggregations[agg_name]["value_as_string"][:10]
            if search_date_range:
                data.aggregations["search_date_range"] = search_date_range
            return data


class SparqlView(BaseView):

    @falcon.before(login_optional)
    @versioned
    @limiter.limit(limits=settings.FALCON_LIMITER_SPARQL_LIMITS, key_func=get_sparql_limiter_key)
    def on_post(self, request, response, *args, **kwargs):
        """
        ---
        doc_template: docs/search/search_view.yml
        """
        self.handle(request, response, self.POST, *args, **kwargs)

    @falcon.before(login_optional)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        deserializer_schema = ListingSchema
        serializer_schema = partial(SparqlNamespaceApiResponse, many=True)

        def _get_debug_query(self, cleaned, *args, **kwargs):
            return {}

        def _get_data(self, cleaned, *args, **kwargs):
            Namespace = namedtuple("namespace", "id prefix url")
            return [Namespace(id=idx, prefix=x[0], url=x[1]) for idx, x in enumerate(NAMESPACES.items(), start=1)]

    class POST(BaseHdlr):
        deserializer_schema = SparqlRequest
        serializer_schema = SparqlApiResponse

        def clean(self, *args, **kwargs):
            return super().clean(*args, locations=("headers", "json"), **kwargs)

        def _get_data(self, cleaned, *args, **kwargs):
            data = cleaned["data"]["attributes"]
            # https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-success
            updated = json.dumps(data)
            cache_key = hashlib.md5()
            cache_key.update(updated.encode("utf-8"))
            cache_key = str(uuid.UUID(cache_key.hexdigest()))
            cached = cache.get(cache_key)
            sparql_resp = json.loads(cached) if cached else None
            if not sparql_resp:
                sparql_resp = self.make_sparql_request(data)
                cache.set(
                    cache_key,
                    json.dumps(sparql_resp),
                    timeout=settings.SPARQL_CACHE_TIMEOUT,
                )
            result = sparql_resp["page_result"] if "page_result" in sparql_resp else sparql_resp["result"]
            SparqlResponse = namedtuple(
                "SparqlResponse",
                "id result has_previous has_next content_type download_url count",
            )
            return SparqlResponse(
                id=cache_key,
                result=result,
                has_previous=sparql_resp.get("has_previous", False),
                has_next=sparql_resp.get("has_next", False),
                content_type=sparql_resp["content_type"],
                download_url=f"{settings.API_URL}/sparql/{cache_key}",
                count=sparql_resp["count"],
            )

        def _get_meta(self, cleaned, *args, **kwargs):
            meta = super()._get_meta(cleaned, *args, **kwargs)
            meta["count"] = self.response.context.data.count
            return meta

        def make_sparql_request(self, data):
            query = data["q"]
            sparql_format = data["format"]
            return_format = SPARQL_FORMATS[sparql_format]
            try:
                store = get_sparql_store(
                    readonly=True,
                    return_format=return_format,
                    external_sparql_endpoint=data.get("external_sparql_endpoint"),
                )
                response = store.query(query, initNs=NAMESPACES)
                _format = "xml" if return_format == "application/rdf+xml" else return_format
                _format = sparql_format if response.graph else _format
                result = response.serialize(format=_format, encoding="utf-8")
                content_type = sparql_format if len(result) else None
                resp = {
                    "result": result.decode("utf-8"),
                    "content_type": content_type,
                    "count": len(response),
                }
                if response.type == "SELECT":
                    paginator = Paginator(response.bindings, data.get("per_page", 20))
                    page = paginator.get_page(data.get("page", 1))
                    response.bindings = page
                    page_result = response.serialize(format=_format)
                    resp.update(
                        {
                            "page_result": page_result.decode("utf-8"),
                            "has_previous": page.has_previous(),
                            "has_next": page.has_next(),
                        }
                    )
                return resp
            except Exception as exc:
                logger.debug(exc)
                raise falcon.HTTPBadRequest(description=_("Bad request"))


class SparqlDownloadView(BaseView):

    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHdlr):
        deserializer_schema = ListingSchema
        serializer_schema = SparqlResponseSchema

        def _get_data(self, cleaned, *args, **kwargs):
            cached = cache.get(str(kwargs["token"]))
            data = json.loads(cached) if cached else None
            if not data:
                raise falcon.HTTPNotFound
            result = data.get("result")
            content_type = data.get("content_type")
            if result:
                self.response.context.data = result.encode("utf-8")
            if content_type:
                self.response.content_type = content_type
                ext = self._get_extension_for_content_type(content_type)
                self.response.downloadable_as = "result{}".format(ext)

        def serialize(self, *args, **kwargs):
            setattr(self.response.context, "debug", False)
            self.prepare_context(*args, **kwargs)
            return self.response.context.data

        @staticmethod
        def _get_extension_for_content_type(content_type):
            ext = mimetypes.guess_extension(content_type.split(";")[0], strict=True)
            if not ext:
                if "application/sparql-results+json" in content_type:
                    ext = ".srj"
                elif "application/sparql-results+xml" in content_type:
                    ext = ".srx"
            return ext
