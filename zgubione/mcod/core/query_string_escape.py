"""
This module takes care of escaping the expressions,
that are meant to go to the ElasticSearch
query_string's "query" parameter.

Made with following documentation in mind:
https://www.elastic.co/guide/en/elasticsearch/reference/6.7/query-dsl-query-string-query.html
"""

import re
from typing import Optional

ES_QUERYSTRING_ESCAPE_RULES = {
    "+": r"\+",
    "-": r"\-",
    "&": r"\&",
    "!": r"\!",
    "(": r"\(",
    ")": r"\)",
    "{": r"\{",
    "}": r"\}",
    "[": r"\[",
    "]": r"\]",
    "^": r"\^",
    "~": r"\~",
    "*": r"\*",
    "?": r"\?",
    '"': r"\"",
    "\\": r"\\;",
    "/": r"\/",
    "<": r"",
    ">": r"",
    ":": r"\:",
}


def _escape_column_expression(not_, col_name, col_value, index=None):
    """
    "Column" expressions are any expressions
    that have the column name followed by a colon (":")
    and the expression that can be escaped.

    Note: there is no known way or reason to escape the following:
    - things like [* TO 10] or (2018-05-01 TO *)
    - ranges, like col3:>=300, col2:<7
    """
    surrounding = _get_surrounding_char(col_value)

    if col_name.startswith("col") and index:
        mappings = index.get_field_mapping(fields=f"{col_name}.*")[index._name]["mappings"]
        mappings = mappings["doc"].keys() if "doc" in mappings else []
        col_name_parts = col_name.split(".")
        if len(col_name_parts) == 1:
            if f"{col_name}.val.date" in mappings:
                col_name = f"{col_name}.val.date"
            elif f"{col_name}.val.time" in mappings:
                col_name = f"{col_name}.val.time"
            elif f"{col_name}.val" in mappings:
                col_name = f"{col_name}.val"
        elif "val" not in col_name_parts:
            col_name_parts.insert(1, "val")
            col_name = ".".join(col_name_parts)
        if surrounding == "*" and f"{col_name}.keyword" in mappings:
            col_name = f"{col_name}.keyword"

    if surrounding:
        col_value = surrounding + _escape_query_string(col_value[1:-1]) + surrounding
    elif not any(
        (
            re.match(r"^[{(\[].*[\])}]$", col_value),
            re.match(r"^(>=|<=|>|<|=)", col_value),
        )
    ):
        col_value = _escape_query_string(col_value)
        col_value = f"{col_value[:-2]}*" if col_value.endswith("\\*") else col_value  # ODSOFT-1548.
    clause = f"{not_}{col_name}:{col_value}"
    return clause


def _escape_non_column_expression(clause):
    surrounding = _get_surrounding_char(clause)
    if surrounding:
        clause = surrounding + _escape_query_string(clause[1:-1]) + surrounding
    else:
        clause = _escape_query_string(clause)

    return clause


def _get_surrounding_char(clause: str) -> Optional[str]:
    """
    Returns the character that surrounds the ElasticSearch query clause,
    or None if there's no surrounding character or the clause is empty.
    """
    surrounding_chars = {"*", '"', "/"}  # *abcde*  # "hello, world"  # /RegExp/
    if len(clause) <= 1:
        return None

    for surrounding_char in surrounding_chars:
        if clause.startswith(surrounding_char) and clause.endswith(surrounding_char):
            return surrounding_char


def _escape_query_string(value: str) -> str:
    """Replace all special characters to with escaped versions of them."""
    return "".join([ES_QUERYSTRING_ESCAPE_RULES.get(char, char) for char in value])
