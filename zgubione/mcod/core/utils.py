from __future__ import annotations

import collections
import csv
import datetime
import json
import logging
import re
import shutil
import unicodedata
from abc import ABC, abstractmethod
from collections import OrderedDict, namedtuple
from contextlib import contextmanager
from http.cookies import SimpleCookie
from io import StringIO, TextIOWrapper
from pathlib import Path
from typing import List, Optional, TextIO, Union
from unittest.mock import patch
from xml.dom.minidom import parseString
from xml.sax.saxutils import escape

import json_api_doc
import jsonschema
import pandas as pd
from dicttoxml import dicttoxml
from falcon import Response
from marshmallow import class_registry
from marshmallow.schema import BaseSchema
from pyexpat import ExpatError
from pytz import utc

from mcod import settings

logger = logging.getLogger("mcod")


_iso8601_datetime_re = re.compile(
    r"(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})"
    r"[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})"
    r"(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?"
    r"(?P<tzinfo>|[+-]\d{2}(?::?\d{2})?)?$",
)


class XmlTextInvalid(ValueError):
    """Text contains characters that are not allowed by XML 1.0, or cannot be embedded safely."""


def validate_xml10_text(value: str) -> None:
    """
    Validate that a value can be safely embedded as XML 1.0 character data.

    This function first coerces non-string inputs to string, rejects `None` and
    empty strings, and then escapes several XML-significant characters (such as
    `&`, `<`, and `>`) before attempting to parse the result with `xml.dom.minidom.parseString`.
    Characters that remain illegal in XML 1.0 even after escaping (e.g., control
    characters, invalid Unicode code points, or other disallowed code units) will
    still cause `parseString` to fail; in such cases the value is considered invalid.
    """
    if value is None or value == "":
        raise XmlTextInvalid("Empty strings are not allowed.")
    text = value if isinstance(value, str) else str(value)
    try:
        parseString(f"<data>{escape(text)}</data>")
    except (ExpatError, UnicodeEncodeError) as e:
        raise XmlTextInvalid("Value contains characters illegal for the configured XML 1.0 safe set.") from e


def anonymize_email(value):
    name, domain = value.split("@") if "@" in value else (None, None)
    if name and domain:
        name_len = len(name) - 1
        domain_len = len(domain) - 1
        name = name[0] + "*" * name_len
        domain = domain[0] + "*" * domain_len
        return f"{name}@{domain}"
    return value


def flatten_list(list_, split_delimeter=None):
    def split(el):
        if split_delimeter and isinstance(el, (str, bytes)):
            el = el.split(split_delimeter)
            return el[0] if len(el) == 1 else el
        return el

    for el in list_:
        el = split(el)

        if isinstance(el, collections.Iterable) and not isinstance(el, (str, bytes)):
            yield from flatten_list(el)
        else:
            yield el


def get_limiter_key(req, resp, resource, params):
    """Custom function used to generate limiter key."""
    key = f"{req.path}_{req.access_route[-2] if len(req.access_route) > 1 else req.remote_addr}"
    logger.debug(f"Falcon-Limiter key: {key}")
    return key


def jsonapi_validator(data):
    with open(settings.JSONAPI_SCHEMA_PATH, "r") as schemafile:
        schema = json.load(schemafile)

    try:
        jsonschema.validate(data, schema)
        validated = json_api_doc.parse(data)
        return True, validated, []
    except (jsonschema.ValidationError, AttributeError) as e:
        errors = [t.message for t in e.context]
        return False, None, errors


def isoformat_with_z(dt, localtime=False, *args, **kwargs):
    """Return the ISO8601-formatted UTC representation of a datetime object."""
    if localtime and dt.tzinfo is not None:
        localized = dt
    else:
        if dt.tzinfo is None:
            localized = utc.localize(dt)
        else:
            localized = dt.astimezone(utc)
    return localized.strftime("%Y-%m-%dT%H:%M:%SZ")


def from_iso_with_z_datetime(datetimestring):
    if not _iso8601_datetime_re.match(datetimestring):
        raise ValueError("Not a valid ISO8601-formatted datetime string")

    return datetime.datetime.strptime(datetimestring[:19], "%Y-%m-%dT%H:%M:%SZ")


def resolve_schema_cls(schema):
    """ """
    if isinstance(schema, type) and issubclass(schema, BaseSchema):
        return schema
    if isinstance(schema, BaseSchema):
        return type(schema)
    return class_registry.get_class(schema)


def sizeof_fmt(num, suffix="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, "Yi", suffix)


FileMeta = namedtuple("FileMeta", ["created", "modified", "accessed", "size"])


def get_file_metadata(path: Union[str, Path], tz_info: datetime.tzinfo = datetime.timezone.utc) -> FileMeta:
    """
    Get basic file metadata.

    Args:
        path (str): Path to the file.
        tz_info (datetime.tzinfo, optional): Timezone to apply to all datetime fields.
            Defaults to UTC. Can be set to local timezone or any tzinfo object.

    Returns:
        FileMeta: Named tuple with attributes:
            created (datetime): File creation time in specified timezone,
                - On Linux: change time (ctime),
                - On Windows: creation time.
            modified (datetime): Last modification time in specified timezone.
            accessed (datetime): Last access time in specified timezone.
            size (int): File size in bytes.
    """
    file_path = Path(path)
    stat = file_path.stat()

    return FileMeta(
        created=datetime.datetime.fromtimestamp(stat.st_ctime, tz=tz_info),
        modified=datetime.datetime.fromtimestamp(stat.st_mtime, tz=tz_info),
        accessed=datetime.datetime.fromtimestamp(stat.st_atime, tz=tz_info),
        size=stat.st_size,
    )


def route_to_name(route, method="GET"):
    route = "" if not route else route
    route = route.strip("$")
    method = method or "GET"
    return "{} {}".format(method, route)


def order_dict(d):
    return {k: order_dict(v) if isinstance(v, dict) else v for k, v in sorted(d.items())}


class frozendict(collections.Mapping):
    dict_cls = dict

    def __init__(self, *args, **kwargs):
        self._dict = self.dict_cls(*args, **kwargs)
        self._hash = None

    def __getitem__(self, key):
        return self._dict[key]

    def __contains__(self, key):
        return key in self._dict

    def copy(self, **add_or_replace):
        return self.__class__(self, **add_or_replace)

    def __iter__(self):
        return iter(self._dict)

    def __len__(self):
        return len(self._dict)

    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, self._dict)

    def __hash__(self):
        if self._hash is None:
            h = 0
            for key, value in self._dict.items():
                h ^= hash((key, value))
            self._hash = h
        return self._hash


class FrozenOrderedDict(frozendict):
    dict_cls = OrderedDict


class hashabledict(dict):
    def __hash__(self):
        return hash(frozenset(self.items()))


def setpathattr(obj, path, value):
    """
    Sets object subattribute given by path
    Similar to setattr but with path supported.
    eg: setpathattr(data, 'hits.notes.pl', 'polski opis')
    """
    path = path.split(".")
    for step in path[:-1]:
        obj = getattr(obj, step)
    setattr(obj, path[-1], value)


def falcon_set_cookie(
    response: Response,
    name: str,
    value: str,
    same_site: Union[None, str] = "",
    path: str = None,
    secure: bool = True,
    http_only: bool = False,
    domain: str = settings.SESSION_COOKIE_DOMAIN,
):
    cookie = SimpleCookie()
    cookie[name] = value
    if same_site is None or same_site:
        cookie[name]["samesite"] = str(same_site)

    if path:
        cookie[name]["path"] = path

    cookie[name]["secure"] = secure
    cookie[name]["httponly"] = http_only
    cookie[name]["domain"] = domain

    response.append_header("Set-Cookie", cookie[name].output(header=""))


class XmlTagIterator:
    def __init__(self, iterator, close_tags=False):
        self.iterator = iterator
        self.iter = None
        self.tag = None
        self.phrase = None
        self.pos = None
        self.cut = 2 if close_tags else 1
        self.move_forward()

    def move_forward(self):
        try:
            self.iter = next(self.iterator)
            self.tag = self.iter.string[self.iter.span()[0] + self.cut : self.iter.span()[1] - 1]
            self.pos = self.iter.span()[0]
        except StopIteration:
            self.pos = float("inf")
            self.tag = None
            raise

    def __lt__(self, other):
        return self.pos < other.pos

    def __eq__(self, other):
        if isinstance(other, XmlTagIterator):
            return self.tag == other.tag
        return False


def complete_invalid_xml(phrase):
    open_re = re.compile(r"<\w+>")
    close_re = re.compile(r"</\w+>")

    open_tag = XmlTagIterator(open_re.finditer(phrase))
    close_tag = XmlTagIterator(close_re.finditer(phrase), True)

    openings_missing = []
    opened_tags = []

    while True:
        try:
            if close_tag < open_tag:
                if opened_tags and opened_tags[-1] == close_tag.tag:
                    opened_tags.pop()
                else:
                    openings_missing.append(close_tag.tag)
                close_tag.move_forward()
            else:
                if close_tag == open_tag:
                    close_tag.move_forward()
                else:
                    opened_tags.append(open_tag.tag)
                open_tag.move_forward()
        except StopIteration:
            if open_tag.tag is None and close_tag.tag is None:
                break

    return "".join(
        (
            "".join("<{}>".format(tag) for tag in openings_missing[::-1]),
            phrase,
            "".join("</{}>".format(tag) for tag in opened_tags[::-1]),
        )
    )


def save_as_csv(file_object, headers, data, delimiter=";"):
    csv_writer = csv.DictWriter(file_object, fieldnames=headers, delimiter=delimiter)
    csv_writer.writeheader()
    for row in data:
        csv_writer.writerow(row)


def prepare_error_folder(path: str) -> str:
    """
    Prepares a folder to store parsing errors at the specified path.

    Args:
    - path (str): The path where the error folder will be created.

    Returns:
    - str: The path of the created error folder.

    This function creates a folder named 'parsing_errors' within the given 'path'.
    If the folder already exists, it removes the entire folder and its contents
    before creating a new one. The function then returns the path of the created folder.
    """
    folder_path = Path(path) / "parsing_errors"

    if folder_path.exists() and folder_path.is_dir():
        # Remove the entire folder and its contents
        shutil.rmtree(folder_path)

    folder_path.mkdir()

    return str(folder_path)


class WriterInterface(ABC):
    """
    Abstract base class defining an interface for different file writers.

    Methods:
        save(self, file_object: TextIO, file_path, data):
            Abstract method to be implemented by subclasses for saving data to files.
    """

    @abstractmethod
    def save(
        self,
        file_object: Union[StringIO, TextIOWrapper, TextIO],
        data: Union[list, dict],
        language_catalog_path: Optional[str] = None,
    ):
        """
        Abstract method defining the protocol for saving data to files.

        Args:
            file_object (TextIO): File object to write the data.
            language_catalog_path: Path to the file.
            data: Data to be written to the file.
        """
        raise NotImplementedError


class CSVWriter(WriterInterface):
    """
    Concrete class implementing WriterInterface for CSV file writing.

    Methods:
        __init__(self, delimiter: str = ";", headers: Optional[List[str]]):
            Constructor method initializing CSVWriter instance with delimiter
            and headers.

        save(self, file_object, file_path, data):
            Method to save data to a CSV file.
    """

    def __init__(self, headers: List[str], delimiter: str = ";"):
        self.headers = headers
        self.delimiter = delimiter

    def save(
        self,
        file_object: Union[StringIO, TextIOWrapper],
        data: List[dict],
        language_catalog_path: Optional[str] = None,
    ):
        """Save data as csv file."""
        csv_writer = csv.DictWriter(file_object, fieldnames=self.headers, delimiter=self.delimiter)
        csv_writer.writeheader()
        for row in data:
            csv_writer.writerow(row)


class XMLWriter(WriterInterface):
    """
    Concrete class implementing WriterInterface for XML file writing.

    Methods:
        save(self, file_object: Union[StringIO, TextIOWrapper], file_path, data):
            Method to save data to an XML file.

        - Writes data in XML format using the provided file_object and data.
        - Converts data to XML using dicttoxml and writes formatted XML to file_object.
    """

    @staticmethod
    def custom_item_func(parent: str) -> str:
        """Returns xml tag. by given key. Basically it's a tag mapping function."""
        return {
            "catalog": "dataset",
            "tags": "tag",
            "sources": "source",
            "formats": "format",
            "keywords": "keyword",
            "visualization_types": "visualization_type",
            "openness_scores": "openness_score",
            "resources": "resource",
            "categories": "category",
            "types": "type",
            "special_signs": "special_sign",
            "regions": "region",
            "supplements": "supplement",
        }.get(parent, "item")

    def save(
        self,
        file_object: Union[StringIO, TextIOWrapper],
        data: Union[dict, List[dict]],
        language_catalog_path: Optional[str] = None,
    ):

        try:
            xml = dicttoxml(
                data,
                attr_type=False,
                item_func=self.custom_item_func,
                custom_root="catalog",
            )
            dom = parseString(xml)
            file_object.write(dom.toprettyxml())
        except (UnicodeError, ExpatError) as exc:
            logger.error(f"XML parsing failed: {exc}")
            if language_catalog_path:
                error_path: str = prepare_error_folder(language_catalog_path)
                abs_error_file_path = f"{error_path}/data.json"
                with open(abs_error_file_path, "w") as file:
                    json.dump(data, file)
                logger.info(f"Failing dataset has been saved to file: {language_catalog_path} " f"as a json dump")
            # We want still rise exception to log it in sentry.
            raise ExpatError from exc


def clean_filename(filename, limit=220):
    forbidden_chars_map = dict((ord(char), None) for char in '<>:"/|?*~#%&+{}-^\\')
    cleaned_filename = "".join(ch for ch in filename if unicodedata.category(ch)[0] != "C")
    cleaned_filename = cleaned_filename.translate(forbidden_chars_map)
    cleaned_filename = unicodedata.normalize("NFKD", cleaned_filename).encode("ASCII", "ignore").decode("ascii")
    cleaned_filename = cleaned_filename[:limit]
    return cleaned_filename.strip()


def save_df_to_xlsx(
    df: pd.DataFrame,
    file_path: Path,
    sheet_name: str = "Arkusz1",
) -> None:
    with pd.ExcelWriter(file_path, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        writer.save()


def clean_columns_in_dataframe(df: pd.DataFrame, *columns: str) -> pd.DataFrame:
    """
    Removes rows in specified columns from the DataFrame where values are
    None, empty, or contain only whitespace.
    """
    existing_columns: List[str] = [col for col in columns if col in df.columns]
    if not existing_columns:
        return df.copy()

    # Build a condition for non-empty and non-NaN values across specified columns
    non_empty_conditions: pd.Series = (
        df[existing_columns].apply(lambda col: col.str.strip().replace("", pd.NA).notna(), axis=0).all(axis=1)
    )

    # Filter DataFrame based on the condition
    df_cleaned: pd.DataFrame = df[non_empty_conditions]
    return df_cleaned


@contextmanager
def disable_modeltracker():
    """
    Helper to disable a time-consuming tracker functionalities if not needed,
    e.g. in read-only flows.
    """
    with patch("model_utils.tracker.FieldTracker.initialize_tracker", lambda *a, **kw: None), patch(
        "model_utils.tracker.FieldInstanceTracker.set_saved_fields", lambda self: None
    ):
        yield
