import operator

import six
from django.utils.translation import get_language, gettext as _
from elasticsearch_dsl.query import Bool, Q
from flatdict import FlatDict
from marshmallow import fields
from marshmallow.exceptions import ValidationError
from marshmallow.validate import Validator

from mcod import settings
from mcod.core.api.search import constants
from mcod.lib import field_validators

MISSING_ERROR_MESSAGE = (
    "ValidationError raised by `{class_name}`, but error key `{key}` does " "not exist in the `error_messages` dictionary."
)


class TranslatedErrorsMixin:
    def make_error(self, key, **kwargs):
        try:
            msg = _(self.error_messages[key])
        except KeyError:
            class_name = self.__class__.__name__
            msg = _(MISSING_ERROR_MESSAGE).format(class_name=class_name, key=key)
            raise AssertionError(msg)
        if isinstance(msg, (str, bytes)):
            msg = msg.format(**kwargs)
        raise ValidationError(msg)

    def _validate(self, value):
        errors = []
        kwargs = {}
        for validator in self.validators:
            try:
                r = validator(value)
                if not isinstance(validator, Validator) and r is False:
                    self.make_error("validator_failed")
            except ValidationError as err:
                kwargs.update(err.kwargs)
                if isinstance(err.messages, dict):
                    errors.append(err.messages)  # TODO
                else:
                    errors.extend((_(msg) for msg in err.messages))
        if errors:
            raise ValidationError(errors, **kwargs)


class DataMixin:
    def prepare_data(self, name, data):
        return data

    def prepare_queryset(self, queryset, context=None):
        return queryset


class SearchFieldMixin:
    @staticmethod
    def _filter_empty(filter_list):
        return list(filter(lambda el: el != "", filter_list))

    def split_lookup_value(self, value, maxsplit=-1):
        return self._filter_empty(value.split(constants.SEPARATOR_LOOKUP_VALUE, maxsplit))

    def split_lookup_filter(self, value, maxsplit=-1):
        return self._filter_empty(value.split(constants.SEPARATOR_LOOKUP_FILTER, maxsplit))

    def split_lookup_complex_value(self, value, maxsplit=-1):
        return self._filter_empty(value.split(constants.SEPARATOR_LOOKUP_COMPLEX_VALUE, maxsplit))


class Raw(DataMixin, TranslatedErrorsMixin, fields.Raw):
    pass


class Nested(DataMixin, TranslatedErrorsMixin, fields.Nested):
    pass


class List(DataMixin, TranslatedErrorsMixin, fields.List):
    pass


class String(DataMixin, TranslatedErrorsMixin, fields.String):
    pass


Str = String


class UUID(DataMixin, TranslatedErrorsMixin, fields.UUID):
    pass


class Number(DataMixin, TranslatedErrorsMixin, fields.Number):
    pass


class Integer(DataMixin, TranslatedErrorsMixin, fields.Integer):
    pass


Int = Integer


class Decimal(DataMixin, TranslatedErrorsMixin, fields.Decimal):
    pass


class Boolean(DataMixin, TranslatedErrorsMixin, fields.Boolean):
    pass


class Float(DataMixin, TranslatedErrorsMixin, fields.Float):
    pass


class DateField(DataMixin, TranslatedErrorsMixin, fields.DateTime):
    pass


class Time(DataMixin, TranslatedErrorsMixin, fields.Time):
    pass


class Date(DataMixin, TranslatedErrorsMixin, fields.Date):
    pass


class TimeDelta(DataMixin, TranslatedErrorsMixin, fields.TimeDelta):
    pass


class Dict(DataMixin, TranslatedErrorsMixin, fields.Dict):
    pass


class Url(DataMixin, TranslatedErrorsMixin, fields.Url):
    pass


class Email(DataMixin, TranslatedErrorsMixin, fields.Email):
    pass


class Method(DataMixin, TranslatedErrorsMixin, fields.Method):
    pass


class Function(DataMixin, TranslatedErrorsMixin, fields.Function):
    pass


class Constant(DataMixin, TranslatedErrorsMixin, fields.Constant):
    pass


class Base64(String):
    default_error_messages = {
        "invalid_base64": "Invalid data format for base64 encoding.",
        "too_long": "Too long data.",
    }

    def __init__(self, max_size=None, **kwargs):
        super().__init__(**kwargs)
        self.validators.insert(
            0,
            field_validators.Base64(
                max_size=max_size,
                base64_error=self.error_messages["invalid_base64"],
                length_error=self.error_messages["too_long"],
            ),
        )


class FilteringFilterField(SearchFieldMixin, DataMixin, TranslatedErrorsMixin, fields.Field):
    def __init__(self, field_name="", lookups=None, translated=False, **metadata):
        super().__init__(**metadata)
        self.lookups = lookups if isinstance(lookups, list) else []
        self.field_name = field_name
        self.trans = translated

    @property
    def _name(self):
        return (self.field_name or self.name) + (f".{get_language()}" if self.trans else "")

    @property
    def _base_name(self):
        return self.field_name or self.name

    def prepare_data(self, name, data):
        data = dict(data)
        if name in data:
            nkey = "%s%s%s" % (
                name,
                constants.SEPARATOR_LOOKUP_FILTER,
                constants.LOOKUP_FILTER_TERM,
            )
            data[nkey] = data.pop(name)
        field_data = {k: v for k, v in data.items() if k.startswith(name)}
        data.update(FlatDict(field_data, delimiter=constants.SEPARATOR_LOOKUP_FILTER).as_dict())
        return data

    def _deserialize(self, value, attr, data):
        if isinstance(value, str):
            return {constants.LOOKUP_FILTER_TERM: value}
        return value

    def _validate(self, values):
        unsupported_lookups = list(set(values.keys() - self.lookups))
        if unsupported_lookups:
            raise ValidationError("Unsupported filter")

    def get_range_params(self, value):
        __values = self.split_lookup_value(value, maxsplit=3)
        __len_values = len(__values)

        if __len_values == 0:
            return {}

        params = {"gte": __values[0]}

        if __len_values == 3:
            params["lte"] = __values[1]
            params["boost"] = __values[2]
        elif __len_values == 2:
            params["lte"] = __values[1]

        return params

    def get_gte_lte_params(self, value, lookup):
        __values = self.split_lookup_value(value, maxsplit=2)
        __len_values = len(__values)

        if __len_values == 0:
            return {}

        params = {lookup: __values[0]}

        if __len_values == 2:
            params["boost"] = __values[1]

        return params

    def prepare_queryset(self, queryset, context=None):  # noqa:C901
        data = context or self.context
        if not data:
            return queryset
        if self.trans:
            _qs = []
            for lookup, value in data.items():
                func = getattr(self, "get_filter_{}".format(lookup), None)
                if not func:
                    continue
                q = func(value)
                if q:
                    _qs.append(q)

            return queryset.query(
                Q(
                    "nested",
                    path=self._base_name,
                    query=six.moves.reduce(operator.and_, _qs),
                )
            )
        else:
            for lookup, value in data.items():
                func = getattr(self, "get_filter_{}".format(lookup), None)
                if not func:
                    continue
                q = func(value)
                if q:
                    queryset = queryset.query(q)

            return queryset

    def get_filter_onlist(self, value):
        if isinstance(value, (list, tuple)):
            __values = value
        else:
            __values = self.split_lookup_value(value)
        must = []
        for value in list(set(__values)):
            must.append(Q("term", **{self._name: value}))
        return Q("bool", must=must)

    def get_filter_term(self, value):
        return Q("term", **{self._name: value})

    def get_filter_terms(self, value):
        if isinstance(value, (list, tuple)):
            __values = value
        else:
            __values = self.split_lookup_value(value)

        return Q("terms", **{self._name: __values})

    def get_filter_range(self, value):
        return Q("range", **{self._name: self.get_range_params(value)})

    def get_filter_exists(self, value):
        _value_lower = value.lower()
        if _value_lower in constants.TRUE_VALUES:
            return Q("exists", field=self._name)
        elif _value_lower in constants.FALSE_VALUES:
            return ~Q("exists", field=self._name)
        return None

    def get_filter_prefix(self, value):
        return Q("prefix", **{self._name: value})

    def get_filter_wildcard(self, value):
        return Q("wildcard", **{self._name: value})

    def get_filter_contains(self, value):
        return Q("wildcard", **{self._name: "*{}*".format(value)})

    def get_filter_startswith(self, value):
        return Q("prefix", **{self._name: "{}".format(value)})

    def get_filter_endswith(self, value):
        return Q("wildcard", **{self._name: "*{}".format(value)})

    def get_filter_in(self, value):
        return self.get_filter_terms(value)

    def get_filter_gt(self, value):
        return Bool(filter=[Q("range", **{self._name: self.get_gte_lte_params(value, "gt")})])

    def get_filter_gte(self, value):
        return Bool(filter=[Q("range", **{self._name: self.get_gte_lte_params(value, "gte")})])

    def get_filter_lt(self, value):
        return Bool(filter=[Q("range", **{self._name: self.get_gte_lte_params(value, "lt")})])

    def get_filter_lte(self, value):
        return Bool(filter=[Q("range", **{self._name: self.get_gte_lte_params(value, "lte")})])

    def get_filter_exclude(self, value):
        __values = self.split_lookup_value(value)

        __queries = []
        for __value in __values:
            __queries.append(~Q("term", **{self._name: __value}))

        if __queries:
            return six.moves.reduce(operator.or_, __queries)

        return None


class NestedFilteringField(FilteringFilterField):
    def __init__(self, path, field_name=None, lookups=None, **kwargs):
        super().__init__(field_name=field_name, lookups=lookups, **kwargs)
        self.path = path

    def prepare_queryset(self, queryset, context=None):  # noqa:C901
        data = context or self.context
        if not data:
            return queryset
        for lookup, value in data.items():
            func = getattr(self, "get_filter_{}".format(lookup), None)
            if not func:
                continue
            q = func(value)
            if q:
                queryset = queryset.query("nested", path=self.path, query=q)

        return queryset


class IdsSearchField(SearchFieldMixin, DataMixin, TranslatedErrorsMixin, fields.Field):
    def prepare_queryset(self, queryset, context=None):
        data = context or self.context
        if not data:
            return queryset
        __ids = []
        for item in data:
            __values = self.split_lookup_value(item)
            __ids += __values

        if __ids:
            __ids = list(set(__ids))
            queryset = queryset.query("ids", **{"values": __ids})
        return queryset


class SuggesterFilterField(SearchFieldMixin, DataMixin, TranslatedErrorsMixin, fields.Field):
    def __init__(self, field, suggesters=None, **metadata):
        self.field_name = field
        self.suggesters = suggesters if isinstance(suggesters, list) else (constants.ALL_SUGGESTERS,)
        super().__init__(**metadata)

    def prepare_data(self, name, data):
        data = dict(data)
        field_data = {k: v for k, v in data.items() if k.startswith(name)}
        data.update(FlatDict(field_data, delimiter=constants.SEPARATOR_LOOKUP_FILTER).as_dict())
        return data

    def apply_suggester_term(self, queryset, value):
        return queryset.suggest(self.name, value, term={"field": self.field_name})

    def apply_suggester_phrase(self, queryset, value):
        return queryset.suggest(self.name, value, phrase={"field": self.field_name})

    def apply_suggester_completion(self, queryset, value):
        return queryset.suggest(self.name, value, completion={"field": self.field_name})

    def prepare_queryset(self, queryset, context=None):
        data = context or self.context
        if not data:
            return queryset
        for suggester_type, value in data.items():
            if suggester_type in self.suggesters:
                if suggester_type == constants.SUGGESTER_TERM:
                    queryset = self.apply_suggester_term(queryset, value)
                elif suggester_type == constants.SUGGESTER_PHRASE:
                    queryset = self.apply_suggester_phrase(queryset, value)
                elif suggester_type == constants.SUGGESTER_COMPLETION:
                    queryset = self.apply_suggester_completion(queryset, value)
        return queryset


class SearchFilterField(SearchFieldMixin, DataMixin, TranslatedErrorsMixin, fields.Field):
    def __init__(
        self,
        search_fields=None,
        search_nested_fields=None,
        search_i18n_fields=None,
        **metadata,
    ):
        self.field_names = search_fields if isinstance(search_fields, (list, tuple, dict)) else ()
        self.search_nested_fields = search_nested_fields if isinstance(search_nested_fields, dict) else {}
        self.search_i18n_fields = search_i18n_fields if isinstance(search_i18n_fields, (list, tuple)) else ()
        super().__init__(**metadata)

    def _deserialize(self, value, attr, data):
        if isinstance(value, str):
            return [
                value,
            ]
        return value

    def construct_nested_search(self, data):
        __queries = []
        for search_term in data:
            for path, _fields in self.search_nested_fields.items():
                queries = []
                for field in _fields:
                    field_key = "{}.{}".format(path, field)
                    queries.append(
                        Q(
                            "match",
                            **{
                                field_key: {
                                    "query": search_term,
                                    "fuzziness": "AUTO",
                                    "fuzzy_transpositions": True,
                                }
                            },
                        )
                    )

                __queries.append(
                    Q(
                        "nested",
                        path=path,
                        query=six.moves.reduce(operator.or_, queries),
                    )
                )

        return __queries

    def construct_translated_search(self, data):
        __queries = []
        for search_term in data:
            for field in self.search_i18n_fields:
                queries = []
                for lang in settings.MODELTRANS_AVAILABLE_LANGUAGES:
                    field_key = f"{field}.{lang}"
                    queries += [
                        Q(
                            "match",
                            **{
                                field_key: {
                                    "query": search_term,
                                    "fuzziness": "AUTO",
                                    "fuzzy_transpositions": True,
                                }
                            },
                        ),
                        Q(
                            "match",
                            **{
                                field_key
                                + ".asciied": {
                                    "query": search_term,
                                    "fuzziness": "AUTO",
                                    "fuzzy_transpositions": True,
                                }
                            },
                        ),
                    ]

                __queries.append(
                    Q(
                        "nested",
                        path=field,
                        query=six.moves.reduce(operator.or_, queries),
                    )
                )
        return __queries

    def _prepare_match_query(self, field, value):
        # Initial kwargs for the match query
        field_kwargs = {
            field: {
                "query": value,
                "fuzziness": "AUTO",
                "fuzzy_transpositions": True,
            }
        }
        # In case if we deal with structure 2
        if isinstance(self.field_names, dict):
            extra_field_kwargs = self.field_names[field]
            if extra_field_kwargs:
                field_kwargs[field].update(extra_field_kwargs)

        return Q("match", **field_kwargs)

    def construct_search(self, data):
        __queries = []

        for search_term in data:
            __values = self.split_lookup_value(search_term, 1)
            __len_values = len(__values)
            if __len_values > 1:
                field, value = __values
                if field in self.field_names:
                    __queries.append(self._prepare_match_query(field, value))

            else:
                for field in self.field_names:
                    __queries.append(self._prepare_match_query(field, search_term))
        return __queries

    def prepare_queryset(self, queryset, context=None):
        data = context or self.context
        if not data:
            return queryset
        __queries = sum(
            (
                self.construct_search(data),
                self.construct_nested_search(data),
                self.construct_translated_search(data),
            ),
            [],
        )

        if __queries:
            queryset = queryset.query("bool", should=__queries)
        return queryset


class FacetedFilterField(SearchFieldMixin, DataMixin, TranslatedErrorsMixin, fields.Field):
    def __init__(self, facets=None, **metadata):
        self.facets = facets if isinstance(facets, dict) else {}
        super().__init__(**metadata)

    def _deserialize(self, value, attr, data):
        if isinstance(value, str):
            return value.split(",")
        return value

    def prepare_queryset(self, queryset, context=None):
        data = context or self.context
        if not data:
            return queryset

        for __field, __facet in self.facets.items():
            if __field in data:
                agg = __facet.get_aggregation()
                agg_filter = Q("match_all")

                queryset.aggs.bucket("_filter_" + __field, "filter", filter=agg_filter).bucket(__field, agg)
        return queryset


class OrderingFilterField(SearchFieldMixin, DataMixin, TranslatedErrorsMixin, fields.Field):
    ordering_param = "sort"

    def __init__(self, ordering_fields=None, default_ordering=None, **metadata):
        self.ordering_fields = ordering_fields if isinstance(ordering_fields, dict) else {}
        self.ordering_fields["_score"] = "_score"
        self.default_ordering = default_ordering or []
        super().__init__(**metadata)

    def prepare_fields_data(self, data):
        sort_params = data or self.default_ordering
        if isinstance(sort_params, str):
            sort_params = [
                sort_params,
            ]
        __sort_params = []
        for param in sort_params:
            __key = param.lstrip("-")
            __direction = "-" if param.startswith("-") else ""
            if __key in self.ordering_fields:
                __field_name = self.ordering_fields[__key] or __key
                if "{lang}" in __field_name:
                    __field_name = __field_name.format(lang=get_language())
                    nested_path = __field_name.split(".")[0]
                    __sort_params.append(
                        {
                            __field_name: {
                                "order": "desc" if __direction == "-" else "asc",
                                "nested": {"path": nested_path},
                            }
                        }
                    )
                else:
                    __sort_params.append("{}{}".format(__direction, __field_name.format(lang=get_language())))
        return __sort_params

    def prepare_queryset(self, queryset, context=None):
        data = context or self.context
        if not data:
            return queryset

        return queryset.sort(*self.prepare_fields_data(data))


class HighlightBackend(SearchFieldMixin, DataMixin, TranslatedErrorsMixin, fields.Field):
    _ALL = "_all"
    _ES_ALL_KEY = _ALL

    def __init__(self, highlight_fields=None, **metadata):
        self.highlight_fields = highlight_fields or {}
        super().__init__(**metadata)

    def prepare_fields_data(self, data):
        highlight_fields = data or []
        __params = {}
        if isinstance(highlight_fields, str):
            highlight_fields = [
                highlight_fields,
            ]

        if self._ALL in self.highlight_fields:
            __params[self._ES_ALL_KEY] = self.highlight_fields[self._ALL]
            __params[self._ES_ALL_KEY]["enabled"] = True

        for field in highlight_fields:
            if field in self.highlight_fields:
                if "enabled" not in self.highlight_fields[field]:
                    self.highlight_fields[field]["enabled"] = False

                if "options" not in self.highlight_fields[field]:
                    self.highlight_fields[field]["options"] = {}
                __params[field] = self.highlight_fields[field]
        return __params

    def prepare_queryset(self, queryset, context=None):
        data = context or self.context
        if not data:
            return queryset

        params = self.prepare_fields_data(data)

        for __field, __options in params.items():
            if __options["enabled"]:
                queryset = queryset.highlight(__field, **__options["options"])

        return queryset
