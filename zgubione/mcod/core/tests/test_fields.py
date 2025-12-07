import pytest
from elasticsearch_dsl import DateHistogramFacet, RangeFacet, TermsFacet

from mcod.core.api.search import constants
from mcod.lib.fields import (
    FacetedFilterField,
    FilteringFilterField,
    HighlightBackend,
    IdsSearchField,
    NestedFilteringField,
    OrderingFilterField,
    SearchFieldMixin,
    SearchFilterField,
    SuggesterFilterField,
)


class TestSearchFieldMixin:
    sfm = SearchFieldMixin()

    @pytest.mark.parametrize(
        ", ".join(["in_val", "out_val"]),
        [
            ("1", ["1"]),
            ("1|24|3", ["1", "24", "3"]),
            ("|12||2|", ["12", "2"]),
        ],
    )
    def test_split_lookup_value(self, in_val, out_val):
        assert self.sfm.split_lookup_value(in_val) == out_val

    @pytest.mark.parametrize(
        ", ".join(["in_val", "out_val"]),
        [
            ("abc", ["abc"]),
            ("abc__d_e_f", ["abc", "d_e_f"]),
            ("__abc__de____ef__", ["abc", "de", "ef"]),
            ("_abc___de_____ef_", ["_abc", "_de", "_ef_"]),
        ],
    )
    def test_split_lookup_filter(self, in_val, out_val):
        assert self.sfm.split_lookup_filter(in_val) == out_val

    @pytest.mark.parametrize(
        ", ".join(["in_val", "out_val"]),
        [
            ("1", ["1"]),
            ("1:24:3", ["1", "24", "3"]),
            (":12::2:", ["12", "2"]),
        ],
    )
    def test_split_lookup_complex_value(self, in_val, out_val):
        assert self.sfm.split_lookup_complex_value(in_val) == out_val


class TestFilteringFilterField:
    test_field_name = "test_filteringfilter"

    def test_no_lookups(self):
        fld = FilteringFilterField(field_name=self.test_field_name)

        assert fld._name == self.test_field_name
        assert len(fld.lookups) == 0

    @pytest.mark.parametrize(
        ", ".join(["lookup", "context", "valid_query"]),
        [
            (
                [
                    constants.LOOKUP_FILTER_EXISTS,
                ],
                {"exists": "True"},
                {"query": {"exists": {"field": test_field_name}}},
            ),
            (
                [
                    constants.LOOKUP_FILTER_EXISTS,
                ],
                {"exists": "False"},
                {"query": {"bool": {"must_not": [{"exists": {"field": test_field_name}}]}}},
            ),
            (
                [
                    constants.LOOKUP_FILTER_TERM,
                ],
                {"term": "Blabla"},
                {"query": {"term": {test_field_name: "Blabla"}}},
            ),
            (
                [constants.LOOKUP_FILTER_TERMS],
                {"terms": ["one", "two", "three"]},
                {"query": {"terms": {test_field_name: ["one", "two", "three"]}}},
            ),
            (
                [constants.LOOKUP_FILTER_PREFIX],
                {"prefix": "pre"},
                {"query": {"prefix": {test_field_name: "pre"}}},
            ),
            (
                [constants.LOOKUP_FILTER_WILDCARD],
                {"wildcard": "abc*ef?hij"},
                {"query": {"wildcard": {test_field_name: "abc*ef?hij"}}},
            ),
            (
                [constants.LOOKUP_QUERY_CONTAINS],
                {"contains": "abc"},
                {"query": {"wildcard": {test_field_name: "*abc*"}}},
            ),
            (
                [constants.LOOKUP_QUERY_STARTSWITH],
                {"startswith": "pre"},
                {"query": {"prefix": {test_field_name: "pre"}}},
            ),
            (
                [constants.LOOKUP_QUERY_ENDSWITH],
                {"endswith": "ing"},
                {"query": {"wildcard": {test_field_name: "*ing"}}},
            ),
            (
                [constants.LOOKUP_QUERY_EXCLUDE],
                {"exclude": "not_wanted"},
                {"query": {"bool": {"must_not": [{"term": {test_field_name: "not_wanted"}}]}}},
            ),
        ],
    )
    def test_single_queryset(self, lookup, context, valid_query, es_dsl_queryset):
        fld = FilteringFilterField(lookups=lookup, field_name=self.test_field_name)

        qs = fld.prepare_queryset(es_dsl_queryset, context)
        assert qs.to_dict() == valid_query

    @pytest.mark.parametrize(
        ", ".join(["lookup", "context", "valid_query"]),
        [
            (
                [constants.LOOKUP_QUERY_GT],
                {"gt": "100"},
                {"range": {test_field_name: {"gt": "100"}}},
            ),
            (
                [constants.LOOKUP_QUERY_GTE],
                {"gte": "16"},
                {"range": {test_field_name: {"gte": "16"}}},
            ),
            (
                [constants.LOOKUP_QUERY_LT],
                {"lt": "10"},
                {"range": {test_field_name: {"lt": "10"}}},
            ),
            (
                [constants.LOOKUP_QUERY_LTE],
                {"lte": "10"},
                {"range": {test_field_name: {"lte": "10"}}},
            ),
        ],
    )
    def test_range_elem_queryset(self, lookup, context, valid_query, es_dsl_queryset):
        fld = FilteringFilterField(lookups=lookup, field_name=self.test_field_name)

        qs = fld.prepare_queryset(es_dsl_queryset, context)
        assert qs.to_dict() == {"query": {"bool": {"filter": [valid_query]}}}

    @pytest.mark.parametrize(
        ", ".join(["lookup", "context", "valid_query"]),
        [
            (
                [constants.LOOKUP_FILTER_RANGE],
                {"range": "16|67|2.0"},
                {test_field_name: {"gte": "16", "lte": "67", "boost": "2.0"}},
            ),
            (
                [constants.LOOKUP_FILTER_RANGE],
                {"range": "16|67"},
                {test_field_name: {"gte": "16", "lte": "67"}},
            ),
            (
                [constants.LOOKUP_FILTER_RANGE],
                {"range": "16"},
                {test_field_name: {"gte": "16"}},
            ),
            (
                [constants.LOOKUP_FILTER_RANGE],
                {"range": "now|2200-12-31"},
                {test_field_name: {"gte": "now", "lte": "2200-12-31"}},
            ),
        ],
    )
    def test_range_queryset(self, lookup, context, valid_query, es_dsl_queryset):
        fld = FilteringFilterField(lookups=lookup, field_name=self.test_field_name)

        qs = fld.prepare_queryset(es_dsl_queryset, context)
        assert qs.to_dict() == {"query": {"range": valid_query}}

    @pytest.mark.parametrize(
        ", ".join(["lookups", "context", "valid_query"]),
        [
            (
                [constants.LOOKUP_QUERY_GT, constants.LOOKUP_QUERY_LT],
                {"lt": "Something", "gt": "anything"},
                [
                    {"range": {test_field_name: {"lt": "Something"}}},
                    {"range": {test_field_name: {"gt": "anything"}}},
                ],
            ),
            (
                [constants.LOOKUP_QUERY_GTE, constants.LOOKUP_QUERY_LTE],
                {"gte": "10", "lte": "80"},
                [
                    {"range": {test_field_name: {"gte": "10"}}},
                    {"range": {test_field_name: {"lte": "80"}}},
                ],
            ),
        ],
    )
    def test_multiple_filter_queryset(self, lookups, context, valid_query, es_dsl_queryset):
        fld = FilteringFilterField(lookups=lookups, field_name=self.test_field_name)

        qs = fld.prepare_queryset(es_dsl_queryset, context)
        assert qs.to_dict() == {"query": {"bool": {"filter": valid_query}}}

    @pytest.mark.parametrize(
        ", ".join(["lookups", "context"]),
        [
            (
                [
                    constants.LOOKUP_FILTER_EXISTS,
                ],
                {"exists": "IdontKnow", "invalid": "field"},
            ),
        ],
    )
    def test_invalid_data_for_lookups(self, lookups, context, es_dsl_queryset):
        fld = FilteringFilterField(lookups=lookups, field_name=self.test_field_name)

        qs = fld.prepare_queryset(es_dsl_queryset, context)
        assert qs.to_dict() == {}


class TestNestedFilteringField:
    test_field_name = "test_nestedfilteringfield"

    @pytest.mark.parametrize(
        ", ".join(["path", "lookups", "context", "valid_query"]),
        [
            (
                "subobject",
                [
                    constants.LOOKUP_FILTER_EXISTS,
                ],
                {"exists": "True"},
                {"path": "subobject", "query": {"exists": {"field": test_field_name}}},
            ),
        ],
    )
    def test_queryset(self, path, lookups, context, valid_query, es_dsl_queryset):
        fld = NestedFilteringField(path=path, lookups=lookups, field_name=self.test_field_name)

        qs = fld.prepare_queryset(es_dsl_queryset, context)
        assert qs.to_dict() == {"query": {"nested": valid_query}}


class TestIdsSearchField:
    test_field_name = "test_idssearch"

    @pytest.mark.parametrize(
        ", ".join(["context", "valid_ids"]),
        [
            (
                ["1"],
                {
                    "1",
                },
            ),
            (["123", "45"], {"123", "45"}),
            (["1|2|3"], {"1", "3", "2"}),
            (["1|2|3", "4|3"], {"1", "2", "4", "3"}),
            (["1|2|3", "45||3|", "2|45|5"], {"1", "2", "3", "45", "5"}),
        ],
    )
    def test_queryset(self, context, valid_ids, es_dsl_queryset):
        fld = IdsSearchField(field_name=self.test_field_name)
        qs = fld.prepare_queryset(es_dsl_queryset, context).to_dict()

        assert "query" in qs
        assert "ids" in qs["query"]
        assert "values" in qs["query"]["ids"]
        assert type(qs["query"]["ids"]["values"]) == list  # noqa

        qs_ids = set(qs["query"]["ids"]["values"])
        assert qs_ids == valid_ids


class TestSuggesterFilterField:
    test_field_name = "test_suggesterfilter"
    suggest_field = "suggest_field"
    text = "suggest test text"

    def test_apply_suggester_term(self, es_dsl_queryset):
        fld = SuggesterFilterField(field=self.suggest_field)
        fld.name = self.test_field_name

        qs = fld.apply_suggester_term(es_dsl_queryset, self.text).to_dict()

        assert {
            "suggest": {
                self.test_field_name: {
                    "text": self.text,
                    "term": {"field": self.suggest_field},
                }
            }
        } == qs

    def test_apply_suggester_phrase(self, es_dsl_queryset):
        fld = SuggesterFilterField(field=self.suggest_field)
        fld.name = self.test_field_name

        qs = fld.apply_suggester_phrase(es_dsl_queryset, self.text).to_dict()
        assert {
            "suggest": {
                self.test_field_name: {
                    "text": self.text,
                    "phrase": {"field": self.suggest_field},
                }
            }
        } == qs

    @pytest.mark.parametrize(
        ", ".join(["suggesters", "context", "suggest_dict"]),
        [
            ([], {"None": ""}, {}),
            (
                [constants.SUGGESTER_TERM],
                {"term": text},
                {
                    "suggest": {
                        test_field_name: {
                            "text": text,
                            "term": {"field": suggest_field},
                        }
                    }
                },
            ),
            (
                [constants.SUGGESTER_PHRASE],
                {"phrase": text},
                {
                    "suggest": {
                        test_field_name: {
                            "text": text,
                            "phrase": {"field": suggest_field},
                        }
                    }
                },
            ),
            (
                [constants.SUGGESTER_COMPLETION],
                {"completion": text},
                {
                    "suggest": {
                        test_field_name: {
                            "text": text,
                            "completion": {"field": suggest_field},
                        }
                    }
                },
            ),
            ([constants.SUGGESTER_COMPLETION], {"phrase": text}, {}),
            (
                [
                    constants.SUGGESTER_PHRASE,
                    constants.SUGGESTER_COMPLETION,
                    constants.SUGGESTER_TERM,
                ],
                {"term": text, "phrase": text, "completion": text},
                {
                    "suggest": {
                        test_field_name: {
                            "text": text,
                            "completion": {"field": suggest_field},
                        }
                    }
                },
            ),
        ],
    )
    def test_queryset(self, suggesters, context, suggest_dict, es_dsl_queryset):
        fld = SuggesterFilterField(field=self.suggest_field, suggesters=suggesters)
        fld.name = self.test_field_name

        qs = fld.prepare_queryset(es_dsl_queryset, context).to_dict()
        valid_query = {}
        valid_query.update(suggest_dict)
        assert qs == valid_query

    def test_apply_suggester_completion(self, es_dsl_queryset):
        fld = SuggesterFilterField(field=self.suggest_field)
        fld.name = self.test_field_name

        qs = fld.apply_suggester_completion(es_dsl_queryset, self.text).to_dict()
        assert {
            "suggest": {
                self.test_field_name: {
                    "text": self.text,
                    "completion": {"field": self.suggest_field},
                }
            }
        } == qs


class TestSearchFilterField:
    @pytest.mark.parametrize(
        ", ".join(["search_fields", "context", "valid_query"]),
        [
            (
                ["title"],
                ["something"],
                [
                    {
                        "match": {
                            "title": {
                                "fuzziness": "AUTO",
                                "fuzzy_transpositions": True,
                                "query": "something",
                            }
                        }
                    }
                ],
            ),
            (
                ["title", "other_field"],
                ["title|something"],
                [
                    {
                        "match": {
                            "title": {
                                "fuzziness": "AUTO",
                                "fuzzy_transpositions": True,
                                "query": "something",
                            }
                        }
                    }
                ],
            ),
            (
                ["title", "description"],
                ["something"],
                [
                    {
                        "match": {
                            "title": {
                                "fuzziness": "AUTO",
                                "fuzzy_transpositions": True,
                                "query": "something",
                            }
                        }
                    },
                    {
                        "match": {
                            "description": {
                                "fuzziness": "AUTO",
                                "fuzzy_transpositions": True,
                                "query": "something",
                            }
                        }
                    },
                ],
            ),
            (
                ["title", "description"],
                ["title|something", "description|anything"],
                [
                    {
                        "match": {
                            "title": {
                                "fuzziness": "AUTO",
                                "fuzzy_transpositions": True,
                                "query": "something",
                            }
                        }
                    },
                    {
                        "match": {
                            "description": {
                                "fuzziness": "AUTO",
                                "fuzzy_transpositions": True,
                                "query": "anything",
                            }
                        }
                    },
                ],
            ),
            (
                ["title", "description"],
                ["title|something", "anything"],
                [
                    {
                        "match": {
                            "title": {
                                "fuzziness": "AUTO",
                                "fuzzy_transpositions": True,
                                "query": "something",
                            }
                        }
                    },
                    {
                        "match": {
                            "title": {
                                "fuzziness": "AUTO",
                                "fuzzy_transpositions": True,
                                "query": "anything",
                            }
                        }
                    },
                    {
                        "match": {
                            "description": {
                                "fuzziness": "AUTO",
                                "fuzzy_transpositions": True,
                                "query": "anything",
                            }
                        }
                    },
                ],
            ),
        ],
    )
    def test_queryset(self, search_fields, context, valid_query, es_dsl_queryset):
        fld = SearchFilterField(search_fields=search_fields)

        qs = fld.prepare_queryset(es_dsl_queryset, context).to_dict()
        assert qs == {"query": {"bool": {"should": valid_query}}}


class TestFacetedFilterField:
    test_field_name = "faceted_filter_field"

    @pytest.mark.parametrize(
        ", ".join(["facets", "context", "aggs_query"]),
        [
            (None, ["date"], {}),
            (
                {
                    "status": TermsFacet(field="status"),
                    "date": DateHistogramFacet(field="date", interval="year"),
                    "range": RangeFacet(field="height", ranges=[("few", (None, 2)), ("lots", (2, None))]),
                },
                ["unknown"],
                {},
            ),
            (
                {"status": TermsFacet(field="status")},
                ["status"],
                {
                    "aggs": {
                        "_filter_status": {
                            "aggs": {"status": {"terms": {"field": "status"}}},
                            "filter": {"match_all": {}},
                        }
                    }
                },
            ),
            (
                {"date": DateHistogramFacet(field="date", interval="year")},
                ["date"],
                {
                    "aggs": {
                        "_filter_date": {
                            "aggs": {
                                "date": {
                                    "date_histogram": {
                                        "field": "date",
                                        "interval": "year",
                                        "min_doc_count": 0,
                                    }
                                }
                            },
                            "filter": {"match_all": {}},
                        }
                    },
                },
            ),
            (
                {"range": RangeFacet(field="height", ranges=[("few", (None, 2)), ("lots", (2, None))])},
                ["range"],
                {
                    "aggs": {
                        "_filter_range": {
                            "aggs": {
                                "range": {
                                    "range": {
                                        "field": "height",
                                        "keyed": False,
                                        "ranges": [
                                            {"key": "few", "to": 2},
                                            {"key": "lots", "from": 2},
                                        ],
                                    }
                                }
                            },
                            "filter": {"match_all": {}},
                        }
                    }
                },
            ),
        ],
    )
    def test_queryset(self, facets, context, aggs_query, es_dsl_queryset):
        fld = FacetedFilterField(facets=facets, field_name=self.test_field_name)

        valid_query = {}
        valid_query.update(aggs_query)

        qs = fld.prepare_queryset(es_dsl_queryset, context)
        ret = qs.to_dict()
        assert ret == valid_query


class TestOrderingFilterField:
    test_field_name = "test_orderingfilter"

    @pytest.mark.parametrize(
        ", ".join(["ordering_fields", "default_ordering", "context", "valid_query"]),
        [
            ({"id": "id"}, ["id"], ["id"], ["id"]),
            (
                {"id": "id", "title": "title.sort"},
                ["id"],
                ["-title"],
                [{"title.sort": {"order": "desc"}}],
            ),
            (
                {"id": "id", "date": None, "title": "title.sort"},
                ["_score"],
                ["-date", "title", "_score", "-wrong_field_name"],
                [
                    {"date": {"order": "desc"}},
                    "title.sort",
                    "_score",
                ],
            ),
        ],
    )
    def test_queryset(self, ordering_fields, default_ordering, context, valid_query, es_dsl_queryset):
        fld = OrderingFilterField(ordering_fields=ordering_fields, default_ordering=default_ordering)

        qs = fld.prepare_queryset(es_dsl_queryset, context).to_dict()
        assert qs == {"sort": valid_query}


class TestHighlightBackend:
    test_field_name = "test_highlightbackend"

    @pytest.mark.parametrize(
        ", ".join(["highlight_fields", "context", "highlight_query"]),
        [
            (
                {"anything": {"enabled": True}},
                ["anything"],
                {"highlight": {"fields": {"anything": {}}}},
            ),
            ({"anything": {"enabled": True}}, ["none"], {}),
            (
                {
                    "_all": {
                        "options": {"pre_tags": ["-+*"], "post_tags": ["*+-"]},
                    },
                    "title": {"enabled": True},
                    "description": {"enabled": False},
                },
                ["title", "description"],
                {
                    "highlight": {
                        "fields": {
                            "_all": {"pre_tags": ["-+*"], "post_tags": ["*+-"]},
                            "title": {},
                        }
                    }
                },
            ),
            (
                {
                    "title": {
                        "enabled": True,
                        "options": {"pre_tags": ["<em>"], "post_tags": ["</em>"]},
                    },
                    "description": {
                        "options": {"pre_tags": ["/*"], "post_tags": ["*/"]},
                        "enabled": True,
                    },
                },
                ["title", "description"],
                {
                    "highlight": {
                        "fields": {
                            "title": {"pre_tags": ["<em>"], "post_tags": ["</em>"]},
                            "description": {"pre_tags": ["/*"], "post_tags": ["*/"]},
                        }
                    }
                },
            ),
        ],
    )
    def test_queryset(self, highlight_fields, context, highlight_query, es_dsl_queryset):
        fld = HighlightBackend(highlight_fields=highlight_fields)

        valid_query = {}
        valid_query.update(highlight_query)

        qs = fld.prepare_queryset(es_dsl_queryset, context).to_dict()
        assert qs == valid_query
