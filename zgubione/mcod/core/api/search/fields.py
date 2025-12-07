import collections
import copy
import functools
import operator
import re
from collections import OrderedDict, namedtuple
from functools import reduce

import six
from django.conf import settings
from django.utils.translation import get_language
from elasticsearch_dsl import A, DateHistogramFacet, Field as DSLField, Q, Search, TermsFacet
from elasticsearch_dsl.aggs import Filter, GeoCentroid, Nested
from elasticsearch_dsl.query import Bool, FunctionScore, Query, Term
from marshmallow import ValidationError, class_registry, utils
from marshmallow.base import SchemaABC

from mcod.core.api import fields
from mcod.core.api.search.facets import FilterFacet, NestedFacet
from mcod.core.query_string_escape import _escape_column_expression, _escape_non_column_expression
from mcod.core.utils import flatten_list

TRUE_VALUES = ("true", "yes", "on", '"true"', "1", '"on"', '"yes"')
FALSE_VALUES = (
    "false",
    '"false"',
    "no",
    "off",
    '"off"',
    '"no"',
    '"0"',
    '""',
    "",
    "0",
    "0.0",
)


class AliasField(DSLField):
    name = "alias"


class ICUSortField(DSLField):
    name = "icu_collation_keyword"


class ElasticField:
    @property
    def _name(self):
        return getattr(self, "data_key") or getattr(self, "name")

    @property
    def _context(self):
        return getattr(self, "context", {})

    @property
    def nested_search(self):
        return self._context.get("nested_search", False)

    @property
    def search_path(self):
        return self._context.get("search_path", None)

    @property
    def query_field_name(self):
        s = self._context.get("query_field", self._name)
        return s

    def q(self, value):
        raise NotImplementedError

    @fields.after_serialize
    def to_es(self, value):
        if isinstance(value, (collections.Iterable, str, bytes)):
            value = None if not value else value

        if value is not None:
            value = self.q(value)

        return self._prepare_queryset, value

    def _prepare_queryset(self, queryset, data):
        if not data:
            return queryset
        return queryset.query("nested", path=self.search_path, query=data) if self.nested_search else queryset.query(data)


class RangeLtField(ElasticField, fields.String):
    def q(self, value):
        return Bool(filter=[Q("range", **{self.query_field_name: {"lt": value}})])


class RangeGtField(ElasticField, fields.String):
    def q(self, value):
        return Bool(filter=[Q("range", **{self.query_field_name: {"gt": value}})])


class RangeLteField(ElasticField, fields.String):
    def q(self, value):
        return Bool(filter=[Q("range", **{self.query_field_name: {"lte": value}})])


class RangeGteField(ElasticField, fields.String):
    def q(self, value):
        return Bool(filter=[Q("range", **{self.query_field_name: {"gte": value}})])


class WildcardField(ElasticField, fields.String):
    @property
    def wildcard(self):
        return self.metadata.get("wildcard", "*{}*")

    def q(self, value):
        return Q("wildcard", **{self.query_field_name: self.wildcard.format(value)})


class PrefixField(ElasticField, fields.String):
    def q(self, value):
        return Q("prefix", **{self.query_field_name: "{}".format(value)})


class TermField(ElasticField, fields.String):
    def q(self, value):
        return Q("term", **{self.query_field_name: value})


class TermsField(ElasticField, fields.List):
    def __init__(self, cls_or_instance=fields.String, **kwargs):
        super().__init__(cls_or_instance, **kwargs)

    @fields.before_deserialize
    def prepare_value(self, value=None, attr=None, data=None):
        if not isinstance(value, collections.Iterable) or isinstance(value, (str, bytes)):
            value = [
                value,
            ]

        value = flatten_list(value, split_delimeter=",")
        value = list(filter(None, value))
        return value, attr, data

    def q(self, value):
        if isinstance(value, (list, tuple)):
            __values = value
        else:
            __values = list(value)

        return Q("terms", **{self.query_field_name: __values})


class ListTermsField(TermsField):

    def q(self, value):
        must = []
        for val in list(set(value)):
            must.append(Q("term", **{self.query_field_name: val}))
        return Q("bool", must=must)


class ExistsField(ElasticField, fields.String):
    def __init__(self, field_name=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_name = field_name or self.query_field_name

    def q(self, value):
        _value_lower = value.lower()
        if _value_lower in TRUE_VALUES:
            return Q("exists", field=self.field_name)
        elif _value_lower in FALSE_VALUES:
            return ~Q("exists", field=self.field_name)
        return ()


class ExcludeField(ElasticField, fields.List):
    def __init__(self, cls_or_instance=fields.String, **kwargs):
        super().__init__(cls_or_instance, **kwargs)

    @fields.before_deserialize
    def prepare_value(self, value=None, attr=None, data=None):
        if not isinstance(value, collections.Iterable) or isinstance(value, (str, bytes)):
            value = [
                value,
            ]

        value = flatten_list(value, split_delimeter=",")
        return value, attr, data

    def q(self, values):
        if isinstance(values, (list, tuple)):
            __values = values
        else:
            __values = list(values)

        queries = []
        for value in __values:
            queries.append(~Q("term", **{self.query_field_name: value}))

        if queries:
            return reduce(operator.or_, queries)

        return None


class FacetField(ElasticField, fields.Nested):
    def __init__(self, nested, default=utils.missing, exclude=tuple(), only=None, **kwargs):
        super().__init__(nested, default=default, exclude=exclude, only=only, **kwargs)
        self._metadata["explode"] = self._metadata.get("explode", True)
        self._metadata["style"] = self._metadata.get("style", "deepObject")
        self._metadata["_in"] = self._metadata.get("_in", "query")

    def q(self, value):
        return list(value.values())

    def _prepare_queryset(self, queryset, data):
        for f, d in data:
            queryset = f(queryset, d)
        return queryset


class FilterField(ElasticField, fields.Nested):
    def __init__(self, nested, default=utils.missing, exclude=tuple(), only=None, **kwargs):
        self._schema = None
        super().__init__(nested, default=default, exclude=exclude, only=only, **kwargs)
        self._metadata["explode"] = self._metadata.get("explode", True)
        self._metadata["style"] = self._metadata.get("style", "deepObject")
        self._metadata["_in"] = self._metadata.get("_in", "query")
        self._condition = None

    @fields.before_deserialize
    def before_deserialize(self, value=None, attr=None, data=None):
        if not isinstance(value, dict):
            _meta = getattr(self.schema, "Meta")
            if _meta and hasattr(_meta, "default_field"):
                value = {_meta.default_field: value}
            data[attr] = value
        return value, attr, data

    @property
    def extra_context(self):
        def evaluate_callables_in_query_params(query):
            q = type(query)(**query._params)
            for key, value in q._params.items():
                if isinstance(value, Query):
                    q._params[key] = evaluate_callables_in_query_params(value)
                elif callable(value):
                    q._params[key] = value()
            return q

        translated = self._metadata.get("translated", False)
        query_field = self._metadata.get("query_field", self._name)
        condition = self._metadata.get("condition")
        if isinstance(condition, Query):
            self._condition = evaluate_callables_in_query_params(condition)

        lang = get_language()
        context = {
            "query_field": query_field,
            "search_path": self._metadata.get("search_path", None),
            "nested_search": self._metadata.get("nested_search", False),
        }

        if translated:
            context["nested_search"] = True
            context["query_field"] = context["query_field"] + "." + lang

        return context

    @property
    def schema(self):
        """The nested Schema object.

        .. versionchanged:: 1.0.0
            Renamed from `serializer` to `schema`.
        """
        if not self._schema:
            if callable(self.nested) and not isinstance(self.nested, type):
                nested = self.nested()
            else:
                nested = self.nested

            if isinstance(nested, SchemaABC):
                self._schema = copy.copy(nested)
                self._schema.context = getattr(self._schema, "context") or {}
                self._schema.context.update(self.extra_context)
                # Respect only and exclude passed from parent and re-initialize fields
                set_class = self._schema.set_class
                if self.only is not None:
                    if self._schema.only is not None:
                        original = self._schema.only
                    else:  # only=None -> all fields
                        original = self._schema.fields.keys()
                    self._schema.only = set_class(self.only) & set_class(original)
                if self.exclude:
                    original = self._schema.exclude
                    self._schema.exclude = set_class(self.exclude) | set_class(original)
                self._schema._init_fields()
            else:
                if isinstance(nested, type) and issubclass(nested, SchemaABC):
                    schema_class = nested
                elif not isinstance(nested, (str, bytes)):
                    raise ValueError("`Nested` fields must be passed a " "`Schema`, not {}.".format(nested.__class__))
                elif nested == "self":
                    schema_class = self.root.__class__
                else:
                    schema_class = class_registry.get_class(nested)
                self._schema = schema_class(
                    many=self.many,
                    only=self.only,
                    exclude=self.exclude,
                    context=self.extra_context,
                    load_only=self._nested_normalized_option("load_only"),
                    dump_only=self._nested_normalized_option("dump_only"),
                )
        return self._schema

    def q(self, value):
        return list(value.values())

    def _prepare_queryset(self, queryset, data):
        if self._metadata.get("no_prepare", False):
            return queryset
        for f, d in data:
            if self._condition:
                d = Bool(must=[self._condition, d])
            queryset = f(queryset, d)
        return queryset


class MatchPhrasePrefixField(ElasticField, fields.String):
    def q(self, value):
        return Q("match_phrase_prefix", **{self.query_field_name: value})


class MatchPhraseField(ElasticField, fields.String):
    def q(self, value):
        return Q("match_phrase", **{self.query_field_name: value})


class MatchField(ElasticField, fields.String):
    def q(self, value):
        return Q(
            "match",
            **{
                self.query_field_name: {
                    "query": value,
                    "fuzziness": "AUTO",
                    "fuzzy_transpositions": True,
                }
            },
        )


class QueryStringField(ElasticField, fields.String):
    @property
    def query_fields(self):
        return self.metadata.get("query_fields", ["col*"])  # only fields like: col1, col2 and so on.

    def q(self, value):
        query, null_queries = self.escape_es_query_string(value)
        params = {
            "query": query,
            "fuzzy_transpositions": True,
            "fuzziness": "AUTO",
            "fuzzy_prefix_length": 2,
            "lenient": True,  # format based errors, such as providing a text value for a numeric field, are ignored.
        }
        if self.query_fields:
            params["fields"] = self.query_fields
        else:
            params["default_field"] = "*"

        queries = [Q("query_string", **params)] if query else []
        if null_queries:
            queries.extend(null_queries)

        return reduce(operator.or_, queries) if queries else None

    def escape_es_query_string(self, value):
        """
        Escape characters, denoted as "special" in ES docs:
        https://elastic.co/guide/en/elasticsearch/reference/6.8/query-dsl-query-string-query.html#_reserved_characters
        The function tries to detect special expressions, because for them to work they don't have to be escaped.
        Note: characters '<' and '>' should be removed from query string.
        """
        clauses = value.split(" AND ")
        escaped_clauses = []
        null_queries = []
        for clause in clauses:
            match = re.match(r"^(NOT |)(\w[\d\w.]*):(.*)$", clause)
            if match:
                not_, col_name, col_value = match.groups()
                clause = _escape_column_expression(not_, col_name, col_value, index=self.context.get("index"))
            else:
                clause = _escape_non_column_expression(clause)

            match = re.match(r"^(NOT |)(\w[\d\w.]*):(.*)$", clause)
            if match:
                not_, col_name, col_value = match.groups()
                if col_value == "null":
                    query = Q("exists", field=col_name) if not_ else ~Q("exists", field=col_name)
                    null_queries.append(query)
                    clause = None
            if clause:
                escaped_clauses.append(clause)

        return " AND ".join(escaped_clauses), null_queries


class SimpleQueryStringField(ElasticField, fields.String):
    @property
    def query_fields(self):
        return self.metadata.get("query_fields", list(self.query_field_name))

    def q(self, value):
        return Q(
            "simple_query_string",
            **{
                "fields": self.query_fields,
                "query": value,
                "fuzzy_transpositions": True,
                "fuzziness": "AUTO",
            },
        )


class MultiMatchField(ElasticField, fields.List):
    def __init__(self, cls_or_instance=fields.String, **kwargs):
        super().__init__(cls_or_instance, **kwargs)

    @fields.before_deserialize
    def prepare_value(self, value=None, attr=None, data=None):
        if not isinstance(value, collections.Iterable) or isinstance(value, (str, bytes)):
            value = [
                value,
            ]

        value = flatten_list(value, split_delimeter=",")
        return value, attr, data

    @property
    def query_fields(self):
        return self.metadata.get("query_fields", {})

    @property
    def extra_fields(self):
        return self.metadata.get("extra_fields", [])

    @property
    def nested_query_fields(self):
        return self.metadata.get("nested_query_fields", {})

    def q(self, data):
        queries = []
        for query_string in data:
            if len(query_string) > 1:
                for path, _fields in self.query_fields.items():
                    _q = []
                    for _field in _fields:
                        field = re.split(r"\W+", _field)[0]
                        cur_lang = get_language()
                        lang_fields = [f"{field}.{cur_lang}"]
                        for lang_field in lang_fields:
                            _q += [
                                Q(
                                    "match",
                                    **{
                                        lang_field: {
                                            "query": query_string,
                                            "fuzziness": "AUTO",
                                        }
                                    },
                                ),
                                Q(
                                    "match",
                                    **{
                                        lang_field
                                        + ".asciied": {
                                            "query": query_string,
                                            "fuzziness": "AUTO",
                                        }
                                    },
                                ),
                            ]

                    queries.append(Q("nested", path=path, query=six.moves.reduce(operator.or_, _q)))

                for path, _fields in self.nested_query_fields.items():
                    _queries = []
                    q_fields = ["{}.{}".format(path, field) for field in _fields]
                    _queries.append(
                        Q(
                            "multi_match",
                            **{
                                "query": query_string,
                                "fields": q_fields,
                                "fuzziness": "AUTO",
                                "fuzzy_transpositions": True,
                            },
                        )
                    )

                    queries.append(
                        Q(
                            "nested",
                            path=path,
                            query=functools.reduce(operator.or_, _queries),
                        )
                    )

                for field in self.extra_fields:
                    queries.append(
                        Q(
                            "match",
                            **{
                                field: {
                                    "query": query_string,
                                    "fuzziness": "AUTO",
                                    "fuzzy_transpositions": True,
                                }
                            },
                        ),
                    )
        return queries

    def _prepare_queryset(self, queryset, data):
        if data:
            queryset = queryset.query("bool", should=data)
            queryset = self._prepare_highlight(queryset)
        return queryset

    def highlight_fields(self):
        return self.query_fields.keys()

    def _prepare_highlight(self, queryset):
        hl_fields = [f"{field}.{get_language()}" for field in self.highlight_fields()]
        hl_type = "plain"
        boundary_scanner = "word"
        queryset = queryset.highlight(
            *hl_fields,
            type=hl_type,
            boundary_scanner=boundary_scanner,
            pre_tags=["<mark>"],
            post_tags=["</mark>"],
        )
        return queryset


class TableApiMultiMatchField(MultiMatchField):

    @property
    def query_fields(self):
        return ["col*.raw"]

    def q(self, data):
        queries = []
        for query_string in data:
            queries.append(
                Q(
                    "multi_match",
                    **{
                        "query": query_string,
                        "fields": self.query_fields,
                        "fuzziness": "AUTO",
                        "fuzzy_transpositions": True,
                        "lenient": True,
                    },
                )
            )
        return queries


class SortField(ElasticField, fields.List):
    def __init__(self, cls_or_instance=fields.String, **kwargs):
        super().__init__(cls_or_instance, **kwargs)
        self.sort_map = []

    def prepare_data(self, name, params):
        if name not in params and self.missing:
            params[name] = self.missing
        return params

    def _prepare_queryset(self, queryset, data):
        is_sorted_by_date = any(any(key in x for key in ["created", "search_date"]) for x in data)
        if all(
            [
                self.context.get("dataset_promotion_enabled", False),
                is_sorted_by_date,
            ]
        ):
            queryset = queryset.query(
                FunctionScore(
                    boost_mode="multiply",
                    functions=[
                        {
                            "filter": Term(is_promoted=True),
                            "weight": 2,
                        }
                    ],
                )
            )
            data = ["_score", *data]
        return queryset.sort(*data)

    @property
    def _doc_template(self):
        return "docs/generic/fields/sort_field.html"

    @property
    def sort_fields(self):
        return self.sort_map or self.metadata.get("sort_fields", [])

    def q(self, sort_params):
        data = []
        for param in sort_params:
            direction = "-" if param.startswith("-") else "+"
            field_name = param.lstrip(direction).strip()
            if field_name in self.sort_fields:
                field_path = self.sort_fields[field_name]
                opts = {
                    "order": "desc" if direction == "-" else "asc",
                    "unmapped_type": "long",
                }
                if "{lang}" in field_path:
                    field_path = field_path.format(lang=get_language())
                    nested_path = field_path.split(".")[0]
                    opts["nested"] = {"path": nested_path}
                    sort_opt = {field_path: opts}
                else:
                    sort_opt = OrderedDict()
                    sort_opt[field_path] = opts
                    if field_path.startswith("col") and ".val" in field_path:
                        obsolete_field_path = field_path.replace(".val", "")
                        sort_opt[obsolete_field_path] = opts  # sort related on tabular data indexed in the old way.
                data.append(sort_opt)

        return data

    @fields.before_deserialize
    def prepare_value(self, value=None, attr=None, data=None):
        if not isinstance(value, collections.Iterable) or isinstance(value, (str, bytes)):
            value = [
                value,
            ]

        value = flatten_list(value, split_delimeter=",")
        return value, attr, data


class SuggestField(ElasticField, fields.String):
    @property
    def suggester_name(self):
        return self.metadata.get("suggester_name", "suggest-{}".format(self.query_field_name))

    @property
    def suggester_type(self):
        return self.metadata.get("suggester_type", "term")

    def q(self, value):
        return value

    def _prepare_queryset(self, queryset, text):
        return queryset.suggest(
            self.suggester_name,
            text,
            **{self.suggester_type: {"field": self.query_field_name}},
        )


class AggregationField(ElasticField, fields.String):
    def _prepare_queryset(self, queryset, data):
        for name, facet in data:
            agg = facet.get_aggregation()
            agg_filter = Q("match_all")
            agg_name = "_filter_" + name
            queryset.aggs.bucket(agg_name, "filter", filter=agg_filter).bucket(name, agg)
        return queryset

    def q(self, value):
        return value


class MetricRangeAggregationField(ElasticField, fields.String):
    def _prepare_queryset(self, queryset, data):
        _d = self._metadata.get("aggs", {})
        for facet_name in data.split(","):
            if facet_name in _d:
                field_name = _d[facet_name].get("field")
                queryset.aggs.metric(f"{facet_name}_{field_name}", facet_name, field=field_name)
        return queryset

    def q(self, value):
        return value


class DateHistogramAggregationField(AggregationField):
    def q(self, value):
        res = []
        _d = self._metadata.get("aggs", {})
        for facet_name in value.split(","):
            if facet_name in _d:
                _f = dict(_d[facet_name])
                _field = _f["field"]
                _path = _f.get("nested_path", None)
                kw = {
                    "min_doc_count": _f.get("min_doc_count", 1),
                    "interval": _f.get("interval", "month"),
                }
                _order = _f.get("order")
                if _order:
                    kw["order"] = _order
                _format = _f.get("format")
                if _format:
                    kw["format"] = _format
                _missing = _f.get("missing")
                if _missing:
                    kw["missing"] = _missing

                _facet = DateHistogramFacet(field=_field, **kw)
                facet = NestedFacet(_path, _facet) if _path else _facet
                res.append((facet_name, facet))

        return res


class TermsAggregationField(AggregationField):
    def q(self, value):  # noqa: C901
        res = []
        _d = self._metadata.get("aggs", {})
        lang = get_language()
        for facet_name in value.split(","):
            if facet_name in _d:
                _f = dict(_d[facet_name])
                _field = _f["field"]
                _translated = _f.get("translated", False)
                _path = _f.get("nested_path", None)
                _filter = _f.get("filter")
                if isinstance(_filter, dict):
                    _filter = _filter.copy()
                    for key, value in _filter.items():
                        if callable(value):
                            _filter[key] = value()

                if _translated and _field:
                    _field = "{}.{}".format(_field, lang)
                kw = {
                    "size": _f.get("size", 500),
                    "min_doc_count": _f.get("min_doc_count", 1),
                }
                _order = _f.get("order")
                if _order:
                    kw["order"] = _order
                _format = _f.get("format")
                if _format:
                    kw["format"] = _format
                _missing = _f.get("missing")
                if _missing:
                    kw["missing"] = _missing

                terms_facet = TermsFacet(field=_field, **kw)
                filter_facet = FilterFacet(term=_filter, aggs={"inner": terms_facet.get_aggregation()})
                if _filter:
                    inner_facet = filter_facet
                else:
                    inner_facet = terms_facet

                facet = NestedFacet(_path, inner_facet) if _path else inner_facet
                res.append((facet_name, facet))

        return res


class FilteredAggregationField(AggregationField):

    def q(self, value):
        _path = self._metadata.get("nested_path", None)
        _field = self._metadata.get("field")
        facet_name = f"by_{_field}" if _path is None else f'by_{_path.split(".")[-1]}'
        kw = {
            "size": self._metadata.get("size", 500),
            "min_doc_count": self._metadata.get("min_doc_count", 1),
        }
        terms_facet = TermsFacet(field=_field, **kw)
        filter_facet = FilterFacet(term={_field: value}, aggs={"inner": terms_facet.get_aggregation()})
        facet = NestedFacet(_path, filter_facet) if _path else filter_facet
        return [(facet_name, facet)]


class ColumnMetricAggregationField(ElasticField, fields.String):
    def __init__(self, aggregation_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agg_type = aggregation_type

    def _prepare_queryset(self, queryset, data):
        index = self.context.get("index")
        for col in data.split(","):
            field = f"{col}.val" if index and index.resolve_field(f"{col}.val") else col
            queryset.aggs.metric(f"_{self.agg_type}_{col}", A(self.agg_type, field=field))
        return queryset

    def q(self, value):
        return value


class NumberField(ElasticField, fields.Integer):
    def _prepare_queryset(self, queryset, data):
        return queryset

    def q(self, value):
        return value


class StringField(ElasticField, fields.String):
    """Represents TextField and KeywordField from Elasticsearch,
    https://www.elastic.co/blog/strings-are-dead-long-live-strings
    """

    def _prepare_queryset(self, queryset, data):
        return queryset

    def q(self, value):
        return value


MAX_MAP_RATIO = 2


class TileAggregationMixin:

    @staticmethod
    def bound(min_lon, max_lon, min_lat, max_lat, agg_size, **kwargs):
        raise NotImplementedError

    def aggregate_tiles_bbox(self, bbox, aggs, **kwargs):
        lat_side = bbox.max_lat - bbox.min_lat
        lon_side = bbox.max_lon - bbox.min_lon
        side_ratio = lat_side / lon_side
        if side_ratio > 1.0:
            lon_step = lon_side / bbox.divider
            lon_div, lat_div = bbox.divider, min((int(round(lat_side / lon_step)), MAX_MAP_RATIO * bbox.divider))
            lat_step = lat_side / lat_div
        else:
            lat_step = lat_side / bbox.divider
            lon_div, lat_div = (
                min((int(round(lon_side / lat_step)), MAX_MAP_RATIO * bbox.divider)),
                bbox.divider,
            )
            lon_step = lon_side / lon_div

        for i in range(lon_div):
            for j in range(lat_div):
                min_lon = bbox.min_lon + lon_step * i
                max_lon = bbox.min_lon + lon_step * (i + 1)
                min_lat = bbox.max_lat - lat_step * (j + 1)
                max_lat = bbox.max_lat - lat_step * j
                aggs.append(
                    (
                        f"tile{j + 1}{i + 1}",
                        self.bound(min_lon, max_lon, min_lat, max_lat, bbox.agg_size, **kwargs),
                    )
                )

    def get_aggregations(self, bbox, **kwargs):
        aggs = []
        self.aggregate_tiles_bbox(bbox, aggs, **kwargs)
        return aggs

    def _prepare_queryset(self, queryset, data):
        q, aggs = data
        queryset = super()._prepare_queryset(queryset, q)
        for a in aggs:
            queryset.aggs.bucket(*a)
        return queryset


class BaseBboxField(ElasticField, fields.BoundingBox):
    relation_type = "intersects"

    @property
    def query_field_name(self):
        return self._context.get("query_field", self.metadata.get("query_field", self._name))

    def get_geo_shape_query(self, bbox):
        return Q(
            "geo_shape",
            **{
                self.query_field_name: {
                    "shape": {
                        "type": "envelope",
                        "coordinates": [
                            [bbox.min_lon, bbox.max_lat],
                            [bbox.max_lon, bbox.min_lat],
                        ],
                    },
                    "relation": self.relation_type,
                }
            },
        )

    def q(self, value):
        bbox = self.bbox(value)
        if bbox:
            q = self.get_geo_shape_query(bbox)
            aggs = self.get_aggregations(bbox)
            return q, aggs
        else:
            return value


class AggregatedBboxField(TileAggregationMixin, BaseBboxField):
    pass


class GeoShapeField(AggregatedBboxField):

    relation_type = "within"

    def bound(self, min_lon, max_lon, min_lat, max_lat, agg_size, **kwargs):
        bbox_q_dict = {
            "regions.coords": {
                "top_left": {"lon": min_lon, "lat": max_lat},
                "bottom_right": {"lon": max_lon, "lat": min_lat},
            }
        }
        bbox_q = Q("geo_bounding_box", **bbox_q_dict)
        main_bbox_q = self.get_geo_shape_query(kwargs["main_bbox"])
        nested_bbox_q = Q("nested", path="regions", query=bbox_q & main_bbox_q)
        return (
            Filter(filter=nested_bbox_q)
            .metric(
                "resources_regions",
                Nested(path="regions").metric(
                    "tile_regions",
                    A("filter", filter=bbox_q & main_bbox_q).metric("centroid", GeoCentroid(field="regions.coords")),
                ),
            )
            .metric(
                "model_types",
                A(
                    "filters",
                    filters={
                        "resources": Q("match", model="resource"),
                        "datasets": Q("match", model="dataset"),
                    },
                ),
            )
            .metric("others", A("top_hits", size=10))
        )

    def q(self, value):
        bbox = self.bbox(value)
        if bbox:
            q = self.get_geo_shape_query(bbox)
            aggs = self.get_aggregations(bbox, main_bbox=bbox)
            return q, aggs
        else:
            return value


class RegionsGeoShapeField(BaseBboxField):

    relation_type = "within"
    MAP_MIN_ZOOM = 0
    MAP_MAX_ZOOM = 20
    NO_REGION_HIERARCHY = 6.0
    ZOOM_TO_HIERARCHY = [
        ((MAP_MIN_ZOOM, 6), 5),
        ((7, 8), 4),
        ((9, 10), 3),
        ((11, 11), 2),
        ((12, MAP_MAX_ZOOM), 1),
    ]

    @classmethod
    def bbox(cls, value):
        if isinstance(value, str):
            values = value.split(",")
            coords = (float(val) for val in values[:4])
            zoom = int(values[4]) if len(value) > 4 else 0
            ZoomedBBoxTuple = namedtuple("BBox", ("min_lon", "max_lat", "max_lon", "min_lat", "zoom"))
            return ZoomedBBoxTuple(*coords, zoom)
        return super().bbox(value)

    def validate_other_params(self, bbox):
        if hasattr(bbox, "zoom") and (bbox.zoom < self.MAP_MIN_ZOOM or bbox.zoom > self.MAP_MAX_ZOOM):
            raise ValidationError("invalid hierarchy zoom level")

    def aggregate_bbox_regions(self, bbox, nested_agg, main_query):
        nested_bbox_q = Q("nested", path=self.search_path, query=main_query)
        return A("filter", filter=nested_bbox_q).metric(
            "resources_regions",
            Nested(path="regions").metric("bbox_regions", A("filter", filter=main_query).metric(*nested_agg)),
        )

    def q(self, value):
        bbox = self.bbox(value)
        if bbox:
            q = self.get_geo_shape_query(bbox)
            return q, bbox
        return value

    def get_geo_bounding_box_query(self, bbox):
        return Q(
            "geo_bounding_box",
            **{
                f"{self.search_path}.coords": {
                    "top_left": {"lon": bbox.min_lon, "lat": bbox.max_lat},
                    "bottom_right": {"lon": bbox.max_lon, "lat": bbox.min_lat},
                }
            },
        )

    def _prepare_queryset(self, queryset, data):
        q, bbox = data
        cloned_queryset = queryset._clone()
        cloned_queryset = super()._prepare_queryset(cloned_queryset, q)
        top_hierarchy = self.get_top_hierarchy(cloned_queryset, bbox)
        queryset = self.query_top_hierarchy(queryset, top_hierarchy, self.get_geo_bounding_box_query(bbox))
        top_regions_agg = self.get_regions_aggregation(bbox, top_hierarchy)
        queryset.aggs.bucket("regions_agg", top_regions_agg)
        return queryset

    def query_top_hierarchy(self, queryset, top_hierarchy, q):
        nested_hierarchy_q = Q(
            "nested",
            path=self.search_path,
            query=Q("match", **{"regions.hierarchy_level": top_hierarchy}) & q,
        )
        return queryset.query(nested_hierarchy_q)

    def get_top_hierarchy(self, queryset, bbox):
        for r in self.ZOOM_TO_HIERARCHY:
            if r[0][0] <= int(bbox.zoom) <= r[0][1]:
                return r[1]

    def get_regions_aggregation(self, bbox, top_hierarchy):
        top_regions_agg = self.aggregate_bbox_regions(
            bbox,
            (
                "top_regions",
                A(
                    "filter",
                    filter=Q("match", **{"regions.hierarchy_level": int(top_hierarchy)}),
                ).metric(
                    "unique_regions",
                    A("terms", field="regions.region_id")
                    .metric("region_data", A("top_hits", size=1))
                    .metric(
                        "model_types",
                        A(
                            "filters",
                            filters={
                                "resources": Q("match", _index="resources"),
                                "datasets": Q("match", _index="datasets"),
                            },
                        ),
                    ),
                ),
            ),
            self.get_geo_bounding_box_query(bbox),
        )
        return top_regions_agg


class BBoxField(AggregatedBboxField):
    @staticmethod
    def bound(min_lon, max_lon, min_lat, max_lat, agg_size, **kwargs):
        q_bbox = Q(
            "geo_bounding_box",
            **{
                "point": {
                    "top_left": {"lon": min_lon, "lat": max_lat},
                    "bottom_right": {"lon": max_lon, "lat": min_lat},
                }
            },
        )
        q_pts = Q("match", shape_type=1)
        return (
            A("filters", filters={"bound": q_bbox & q_pts})
            .metric("points", A("top_hits", size=agg_size))
            .metric("centroid", A("geo_centroid", field="point"))
        )

    def get_aggregations(self, bbox, **kwargs):
        aggs = [
            (
                "others",
                A("filters", filters={"others": ~Q("match", shape_type=1)}).metric(
                    "others",
                    A(
                        "top_hits",
                        size=int(self._context["request"].params.get("per_page", 20)),
                    ),
                ),
            )
        ]
        return aggs + super().get_aggregations(bbox)


class GeoDistanceField(ElasticField, fields.GeoDistance):
    @property
    def query_field_name(self):
        s = self._context.get("query_field", self.metadata.get("query_field", self._name))
        return s

    def q(self, value):
        lon, lat, distance = value.split(",")
        return Q(
            "geo_distance",
            **{
                "distance": distance,
                self.query_field_name: {"lat": float(lat), "lon": float(lon)},
            },
        )


class TileAggregatedTermsField(TileAggregationMixin, TermsField):

    @staticmethod
    def bound(min_lon, max_lon, min_lat, max_lat, agg_size, **kwargs):
        bbox_q_dict = {
            "regions.coords": {
                "top_left": {"lon": min_lon, "lat": max_lat},
                "bottom_right": {"lon": max_lon, "lat": min_lat},
            }
        }
        bbox_q = Q("geo_bounding_box", **bbox_q_dict)
        region_q = Q("terms", **{"regions.region_id": kwargs["region_id"]})
        nested_bbox_q = Q("nested", path="regions", query=bbox_q & region_q)
        return (
            Filter(filter=nested_bbox_q)
            .metric(
                "resources_regions",
                Nested(path="regions").metric(
                    "tile_regions",
                    A("filter", filter=bbox_q & region_q).metric("centroid", GeoCentroid(field="regions.coords")),
                ),
            )
            .metric(
                "model_types",
                A(
                    "filters",
                    filters={
                        "resources": Q("match", model="resource"),
                        "datasets": Q("match", model="dataset"),
                    },
                ),
            )
            .metric("others", A("top_hits", size=10))
        )

    def q(self, value):
        q = super().q(value)
        query = Search(index=settings.ELASTICSEARCH_COMMON_ALIAS_NAME)
        res = query.filter(Q("terms", **{"region_id": value})).execute()
        try:
            es_bbox = res[0].bbox.coordinates
            bbox = fields.BBoxTuple(es_bbox[0][0], es_bbox[0][1], es_bbox[1][0], es_bbox[1][1], 3, 9)
            aggs = self.get_aggregations(bbox, region_id=value)
        except IndexError:
            aggs = []
        return q, aggs


class RegionAggregatedTermsField(TermsField):

    def get_aggregations(self, q):
        nested_q = Q("nested", path=self.search_path, query=q)
        agg = (
            Filter(filter=nested_q)
            .metric(
                "resources_regions",
                Nested(path="regions").metric(
                    "single_region",
                    A("filter", filter=q).metric("region_data", A("top_hits", size=1)),
                ),
            )
            .metric(
                "model_types",
                A(
                    "filters",
                    filters={
                        "resources": Q("match", model="resource"),
                        "datasets": Q("match", model="dataset"),
                    },
                ),
            )
        )
        return "regions_agg", agg

    def _prepare_queryset(self, queryset, data):
        queryset = super()._prepare_queryset(queryset, data)
        aggs = self.get_aggregations(data)
        queryset.aggs.bucket(*aggs)
        return queryset


class NoDataField(ElasticField, fields.Boolean):
    def __init__(self, **kwargs):
        super().__init__(truthy=set(TRUE_VALUES), falsy=set(FALSE_VALUES), **kwargs)

    def q(self, value):
        return None

    def _prepare_queryset(self, queryset, data):
        return queryset
