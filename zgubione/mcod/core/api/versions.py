import decimal
from datetime import date
from decimal import Decimal
from typing import Tuple


class Version:
    def __init__(self, version, release_date, doc_enabled=True):
        self.version_tuple = version.split(".")
        if len(self.version_tuple) != 2:
            raise ValueError("Invalid version format")
        self.release_date = release_date
        self.doc_enabled = doc_enabled
        self._version = self.as_string

    def __repr__(self):
        return str(self.as_string)

    @property
    def as_string(self):
        return "{}.{}".format(*self.version_tuple)

    @property
    def as_number(self):
        return self.__tuple_2_decimal(self.version_tuple)

    @staticmethod
    def __tuple_2_decimal(version_tuple: Tuple[str, str]) -> Decimal:
        if len(version_tuple) != 2:
            raise ValueError("Version tuple must have exactly two items")
        try:
            return Decimal("{}.{:>05}".format(*version_tuple))
        except decimal.DecimalException:
            raise ValueError("Version tuple must have exactly two numbers")

    def __to_decimal(self, value):
        if isinstance(value, str):
            value = self.__tuple_2_decimal(value.split("."))
        elif isinstance(value, (tuple, list)):
            value = self.__tuple_2_decimal(value)
        elif isinstance(self, self.__class__):
            value = value.as_number
        else:
            raise ValueError("Unsupported value type {}, {}".format(value, type(value)))
        return value

    def __gt__(self, other):
        return self.as_number > self.__to_decimal(other)

    def __ge__(self, other):
        return self.as_number >= self.__to_decimal(other)

    def __lt__(self, other):
        return self.as_number < self.__to_decimal(other)

    def __le__(self, other):
        return self.as_number <= self.__to_decimal(other)

    def __eq__(self, other):
        return self.as_number == self.__to_decimal(other)


VERSIONS = [
    Version("1.0", date(2018, 9, 14), doc_enabled=False),
    Version("1.4", date(2019, 2, 2), doc_enabled=True),
]

DOC_VERSIONS = [v for v in VERSIONS if v.doc_enabled]


def get_latest_version():
    return max(VERSIONS)


def get_version(version):
    return VERSIONS[VERSIONS.index(version)]
