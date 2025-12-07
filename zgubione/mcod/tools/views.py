import falcon
from django.utils.translation import get_language
from elasticsearch import TransportError
from elasticsearch_dsl import DateHistogramFacet, MultiSearch, Search, TermsFacet
from elasticsearch_dsl.aggs import Filter, Nested, Terms
from elasticsearch_dsl.connections import get_connection

from mcod import settings
from mcod.alerts.utils import get_active_alerts
from mcod.core.api.search.facets import NestedFacet
from mcod.core.api.views import JsonAPIView
from mcod.core.schemas import StatsSchema
from mcod.core.versioning import versioned
from mcod.datasets.documents import DatasetDocument
from mcod.lib.handlers import BaseHandler
from mcod.resources.documents import ResourceDocument
from mcod.tools.depricated.serializers import StatsMeta, StatsSerializer

connection = get_connection()


class StatsView(JsonAPIView):
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(BaseHandler):
        deserializer_schema = StatsSchema()
        serializer_schema = StatsSerializer(many=False)
        meta_serializer = StatsMeta()

        def _data(self, request, cleaned, *args, explain=None, **kwargs):
            m_search = MultiSearch()
            search = Search(
                using=connection,
                index=settings.ELASTICSEARCH_COMMON_ALIAS_NAME,
                extra={"size": 0},
            )
            search.aggs.bucket("documents_by_type", TermsFacet(field="model").get_aggregation()).bucket(
                "by_month",
                DateHistogramFacet(field="created", interval="month", min_doc_count=0).get_aggregation(),
            )
            d_search = DatasetDocument().search().extra(size=0).filter("match", status="published")
            r_search = ResourceDocument().search().extra(size=0).filter("match", status="published")

            d_search.aggs.bucket(
                "datasets_by_institution",
                NestedFacet("institution", TermsFacet(field="institution.id")).get_aggregation(),
            )

            d_search.aggs.bucket(
                "datasets_by_categories",
                NestedFacet(
                    "categories",
                    TermsFacet(field="categories.id", min_doc_count=1, size=50),
                ).get_aggregation(),
            )
            d_search.aggs.bucket(
                "datasets_by_category",
                NestedFacet(
                    "category",
                    TermsFacet(field="category.id", min_doc_count=1, size=50),
                ).get_aggregation(),
            )

            d_search.aggs.bucket("datasets_by_tag", TermsFacet(field="tags").get_aggregation())

            d_search.aggs.bucket(
                "datasets_by_keyword",
                Nested(
                    aggs={
                        "inner": Filter(
                            aggs={"inner": Terms(field="keywords.name")},
                            term={"keywords.language": get_language()},
                        )
                    },
                    path="keywords",
                ),
            )

            d_search.aggs.bucket("datasets_by_formats", TermsFacet(field="formats").get_aggregation())
            d_search.aggs.bucket(
                "datasets_by_openness_scores",
                TermsFacet(field="openness_scores").get_aggregation(),
            )
            r_search.aggs.bucket("resources_by_type", TermsFacet(field="type").get_aggregation())
            m_search = m_search.add(search)
            m_search = m_search.add(d_search)
            m_search = m_search.add(r_search)
            if explain == "1":
                return m_search.to_dict()
            try:
                resp1, resp2, resp3 = m_search.execute()
                # TODO: how to concatenate two responses in more elegant way?
                resp1.aggregations.datasets_by_institution = resp2.aggregations.datasets_by_institution
                resp1.aggregations.datasets_by_categories = resp2.aggregations.datasets_by_categories
                resp1.aggregations.datasets_by_category = resp2.aggregations.datasets_by_category
                resp1.aggregations.datasets_by_tag = resp2.aggregations.datasets_by_tag
                resp1.aggregations.datasets_by_keyword = resp2.aggregations.datasets_by_keyword
                resp1.aggregations.datasets_by_formats = resp2.aggregations.datasets_by_formats
                resp1.aggregations.datasets_by_openness_scores = resp2.aggregations.datasets_by_openness_scores
                resp1.aggregations.resources_by_type = resp3.aggregations.resources_by_type
                return resp1
            except TransportError as err:
                try:
                    description = err.info["error"]["reason"]
                except KeyError:
                    description = err.error
                raise falcon.HTTPBadRequest(description=description)

        def _metadata(self, request, data, *args, **kwargs):
            meta = super()._metadata(request, data, *args, **kwargs)
            meta["alerts"] = get_active_alerts(request.language)

            return meta
