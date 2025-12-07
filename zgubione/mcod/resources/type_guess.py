from collections import defaultdict
from typing import Any, Callable, Generator, Literal, Tuple, TypeVar, Union

from tableschema import Table as TablePre, config

import mcod.lib.cast_types as types

TypeName = str
TypeFormat = Literal["any", "default"]
TypePriority = int
TypeGuessCastResult = Tuple[TypeName, TypeFormat, TypePriority]

T = TypeVar("T", bound=Any)
Error = str
CastResult = Union[T, Error]
CastCallable = Callable[[str, T], Union[T, CastResult]]


class TypeGuesser:
    missing_values = []

    _INFER_TYPE_ORDER: Tuple[TypeName, ...] = (
        "missing",
        "duration",
        "geojson",
        "geopoint",
        "object",
        "array",
        "time",
        "date",
        "datetime",
        "integer",
        "number",
        "boolean",
        "string",
        "any",
    )

    def cast(self, value: T) -> Generator[TypeGuessCastResult, Any, None]:
        priority: TypePriority
        name: TypeName
        for priority, name in enumerate(self._INFER_TYPE_ORDER):
            cast: CastCallable = getattr(types, f"cast_{name}")
            if value not in self.missing_values:
                v = str(value)
                if name in ["integer", "number"] and " " in v:
                    continue
                elif any(
                    (
                        self.check_time_conditions(name, v),
                        self.check_datetime_conditions(name, v),
                        self.check_date_conditions(name, v),
                    )
                ):
                    result: CastResult = cast("any", value)
                    if result != config.ERROR:
                        yield name, "any", priority
                else:
                    result: CastResult = cast("default", value)
                    if result != config.ERROR:
                        yield name, "default", priority

    @staticmethod
    def check_time_conditions(name: str, value: str) -> bool:
        def date_separators_not_in_value(value):
            return all([x not in value for x in "T -/"])

        at_least_one_collon = value.count(":") >= 1
        if not at_least_one_collon:
            return False

        dot_should_be_after_collon = True
        if "." in value:
            dot_should_be_after_collon = value.index(".") > value.index(":")

        return name == "time" and date_separators_not_in_value(value) and dot_should_be_after_collon

    @staticmethod
    def check_date_conditions(name: str, value: str) -> bool:
        return name == "date" and len(value) == 10

    @staticmethod
    def check_datetime_conditions(name: str, value: str) -> bool:
        """Some checks before cast with `any` format."""
        longer_than_date = len(value) > 10  # because we don't won't recognize date (ex: 10-12-2020) as datetime
        if not longer_than_date:
            return False

        n_dots = value.count(".")
        n_colons = value.count(":")

        # 12-12-2012 12:12.123123 is OK but 12.123456789 is NOT
        if n_dots == 1 and value.replace(".", "").isdigit():
            return False  # because it's float

        # thats not OK 12.123123123123:10, so
        if n_dots == 1 and n_colons == 1:
            dot_after_colon = value.rindex(".") > value.rindex(":")
        else:
            dot_after_colon = True

        # Other bad values should raise error durring casting
        return name == "datetime" and longer_than_date and dot_after_colon


class TypeResolver:
    """Get the best matching type/format from a list of possible ones."""

    # Public

    def get(self, results, confidence):
        missing_key = ("missing", "default", 0)
        any_key = ("any", "default", 13)

        variants = set(results)
        # only one candidate... that's easy.
        if len(variants) == 1:
            rv = {"type": results[0][0], "format": results[0][1]}
        elif len(variants) == 2 and missing_key in variants:
            variants.remove(missing_key)
            v = variants.pop()
            rv = {"type": v[0], "format": v[1]}
        else:
            counts = defaultdict(int)
            for result in results:
                counts[result] += 1

            # is there are missings?
            missings = counts[missing_key]
            if missings > 0:
                counts.pop(any_key)
                counts.pop(missing_key)

            # tuple representation of `counts` dict sorted by values
            sorted_counts = sorted(counts.items(), key=lambda item: item[1], reverse=True)
            # Allow also counts that are not the max, based on the confidence
            max_count = sorted_counts[0][1]
            sorted_counts = filter(lambda item: item[1] >= max_count * confidence, sorted_counts)
            # Choose the most specific data type
            sorted_counts = sorted(sorted_counts, key=lambda item: item[0][2])
            rv = {"type": sorted_counts[0][0][0], "format": sorted_counts[0][0][1]}
        return rv


class Table(TablePre):

    def __init__(self, source, schema=None, strict=False, post_cast=[], storage=None, **options):
        super().__init__(source, schema=schema, strict=strict, post_cast=post_cast, storage=storage, **options)

    def infer(self, **kwargs):
        if "missing_values" in kwargs:
            missing_values = kwargs["missing_values"]
            if "" in missing_values:  # empty string is handled by TypeGuesser.cast_missing().
                missing_values.remove("")
            TypeGuesser.missing_values = missing_values
        kwargs["guesser_cls"] = TypeGuesser
        kwargs["resolver_cls"] = TypeResolver
        return super().infer(**kwargs)
