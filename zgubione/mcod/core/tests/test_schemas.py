from elasticsearch_dsl import TermsFacet

from mcod.core.api.search import constants
from mcod.core.tests.helpers.elasticsearch import QuerysetTestHelper
from mcod.lib import fields
from mcod.lib.schemas import List


class TestListSchema:
    def test_query(self, es_dsl_queryset):
        class SomeSchema(QuerysetTestHelper, List):
            ids = fields.IdsSearchField()
            q = fields.SearchFilterField(
                search_fields=["title", "body"],
            )
            filtered_field = fields.FilteringFilterField(
                lookups=[
                    constants.LOOKUP_FILTER_TERM,
                    constants.LOOKUP_QUERY_ENDSWITH,
                    constants.LOOKUP_QUERY_EXCLUDE,
                    constants.LOOKUP_QUERY_LTE,
                    constants.LOOKUP_FILTER_RANGE,
                ]
            )
            nested_field = fields.NestedFilteringField(
                "nested_field",
                field_name="nested_field.id",
                lookups=[constants.LOOKUP_FILTER_TERM],
            )

        schema = SomeSchema()

        context = {
            "invalid_field": 123,
            "q": ["title|abc", "ghi"],
            "filtered_field": {
                "term": "abc",
                "endswith": "xyz",
                "exclude": "not_wanted",
                "invalidfilter": "123",
                "lte": "10",
                "range": "now|2200-12-31",
            },
            "nested_field": {"exists": "True"},
        }

        valid_query = {
            "query": {
                "bool": {
                    "minimum_should_match": 1,
                    "must": [
                        {
                            "nested": {
                                "path": "nested_field",
                                "query": {"exists": {"field": "nested_field.id"}},
                            }
                        },
                        {"term": {"filtered_field": "abc"}},
                        {"wildcard": {"filtered_field": "*xyz"}},
                        {"range": {"filtered_field": {"gte": "now", "lte": "2200-12-31"}}},
                    ],
                    "must_not": [{"term": {"filtered_field": "not_wanted"}}],
                    "filter": [{"range": {"filtered_field": {"lte": "10"}}}],
                    "should": [
                        {
                            "match": {
                                "title": {
                                    "fuzziness": "AUTO",
                                    "fuzzy_transpositions": True,
                                    "query": "abc",
                                }
                            }
                        },
                        {
                            "match": {
                                "title": {
                                    "fuzziness": "AUTO",
                                    "fuzzy_transpositions": True,
                                    "query": "ghi",
                                }
                            }
                        },
                        {
                            "match": {
                                "body": {
                                    "fuzziness": "AUTO",
                                    "fuzzy_transpositions": True,
                                    "query": "ghi",
                                }
                            }
                        },
                    ],
                },
            }
        }

        qs = schema.prepare_queryset(es_dsl_queryset, context).to_dict()

        assert "query" in qs
        assert "bool" in qs["query"]
        vqb = valid_query["query"]["bool"]
        cqb = qs["query"]["bool"]
        assert cqb.keys() == vqb.keys()
        assert cqb.get("minimum_should_match") == vqb["minimum_should_match"]
        for arr_key, arr in ((k, vqb[k]) for k in vqb.keys() if type(vqb[k]) == list):  # noqa
            assert len(cqb[arr_key]) == len(arr)
            for el in cqb[arr_key]:
                assert el in arr

    def test_sort(self, es_dsl_queryset):
        class SomeSchema(QuerysetTestHelper, List):
            sort = fields.OrderingFilterField(
                default_ordering=[
                    "-modified",
                ],
                ordering_fields={
                    "id": "id",
                    "title": "title.sort",
                    "modified": "modified",
                    "created": "created",
                },
            )

        schema = SomeSchema()
        context = {"sort": "title"}
        valid_query = {"sort": ["title.sort"]}
        qs = schema.prepare_queryset(es_dsl_queryset, context).to_dict()
        assert qs == valid_query

    def test_aggs(self, es_dsl_queryset):
        class SomeSchema(QuerysetTestHelper, List):
            facet = fields.FacetedFilterField(
                facets={
                    "somefield": TermsFacet(field="somefield"),
                },
            )

        schema = SomeSchema()

        context = {"facet": ["somefield"]}

        valid_query = {
            "aggs": {
                "_filter_somefield": {
                    "aggs": {
                        "somefield": {
                            "terms": {
                                "field": "somefield",
                            }
                        }
                    },
                    "filter": {"match_all": {}},
                }
            }
        }
        qs = schema.prepare_queryset(es_dsl_queryset, context).to_dict()
        assert qs == valid_query

    def test_highlight(self, es_dsl_queryset):
        class SomeSchema(QuerysetTestHelper, List):
            highlight = fields.HighlightBackend(
                highlight_fields={
                    "somefield": {
                        "options": {"post_tags": ["-*"], "pre_tags": ["*-"]},
                        "enabled": True,
                    }
                }
            )

        schema = SomeSchema()
        context = {"highlight": ["somefield"]}
        valid_query = {"highlight": {"fields": {"somefield": {"post_tags": ["-*"], "pre_tags": ["*-"]}}}}
        qs = schema.prepare_queryset(es_dsl_queryset, context).to_dict()
        assert qs == valid_query

    def test_full_query(self, es_dsl_queryset):
        class SomeSchema(QuerysetTestHelper, List):
            q = fields.SearchFilterField(
                search_fields=["body"],
            )
            sort = fields.OrderingFilterField(
                default_ordering=[
                    "-modified",
                ],
                ordering_fields={
                    "id": "id",
                    "title": "title.sort",
                    "modified": "modified",
                    "created": "created",
                },
            )
            facet = fields.FacetedFilterField(
                facets={"somefield": TermsFacet(field="somefield")},
            )
            highlight = fields.HighlightBackend(
                highlight_fields={
                    "somefield": {
                        "options": {"post_tags": ["-*"], "pre_tags": ["*-"]},
                        "enabled": True,
                    }
                }
            )

        schema = SomeSchema()
        context = {
            "q": ["title|abc", "ghi"],
            "highlight": ["somefield"],
            "facet": ["somefield"],
            "sort": "title",
        }
        valid_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "match": {
                                "body": {
                                    "fuzziness": "AUTO",
                                    "fuzzy_transpositions": True,
                                    "query": "ghi",
                                }
                            }
                        }
                    ]
                }
            },
            "highlight": {"fields": {"somefield": {"post_tags": ["-*"], "pre_tags": ["*-"]}}},
            "aggs": {
                "_filter_somefield": {
                    "aggs": {
                        "somefield": {
                            "terms": {
                                "field": "somefield",
                            }
                        }
                    },
                    "filter": {"match_all": {}},
                }
            },
            "sort": ["title.sort"],
        }
        qs = schema.prepare_queryset(es_dsl_queryset, context).to_dict()
        assert qs == valid_query
