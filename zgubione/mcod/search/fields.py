from django.utils.translation import get_language
from elasticsearch_dsl import Q
from elasticsearch_dsl.query import Bool, Nested, Term

from mcod.core.api.search.fields import MultiMatchField


def get_advanced_options(adv):
    op = "and" if adv == "all" else "or"
    suffix = ""
    if adv in {"synonyms", "exact"}:
        suffix = "_" + adv
    return op, suffix


def nested_query_with_advanced_opts(query, path, lang, op, suffix="", analyzer=None):
    opts = {"query": query, "operator": op, "fuzzy_transpositions": False}
    if analyzer is not None:
        opts["analyzer"] = analyzer
    return Q(
        "nested",
        path=f"{path}{suffix}",
        query={"match": {f"{path}{suffix}.{lang}": opts}},
    )


def keywords_query(query, lang):
    return Nested(
        path="keywords",
        query=Bool(must=[Term(keywords__name=query), Term(keywords__language=lang)]),
    )


class CommonSearchField(MultiMatchField):
    def __init__(self, **kwargs):
        super().__init__(query_fields={"title": ["title"], "notes": ["notes"]}, **kwargs)

    def _get_advanced_param(self):
        request = self.context.get("request")
        if request:
            return request.params.get("advanced")
        return None

    def q(self, data):
        lang = get_language()
        op, suffix = get_advanced_options(self._get_advanced_param())

        queries = []
        for query in data:
            for path in ["notes", "title"]:
                queries.append(nested_query_with_advanced_opts(query, path, lang, op, suffix))

            queries.append(keywords_query(query, lang))

            for field in ("abbreviation", "author"):
                queries.append(
                    Q(
                        "match",
                        **{
                            field: {
                                "query": query,
                                "operator": op,
                                "fuzzy_transpositions": False,
                            }
                        },
                    )
                )
        return queries

    def highlight_fields(self):
        _, suffix = get_advanced_options(self._get_advanced_param())
        return [key + suffix for key in super().highlight_fields()]
