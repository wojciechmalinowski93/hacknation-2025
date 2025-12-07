import io
import json
import os
import xml
from typing import Optional, Union
from zipfile import BadZipFile

import cchardet
import jsonschema
import rdflib
from bs4 import BeautifulSoup
from lxml import etree
from tabulator import Stream
from tabulator.exceptions import EncodingError, FormatError

from mcod import settings
from mcod.resources.geo import is_json_stat

GUESS_FROM_BUFFER = (
    "application/octetstream",
    "application/octet-stream",
    "octet-stream",
    "octetstream",
    "application octet-stream",
)


def is_octetstream(content_type):
    return content_type in GUESS_FROM_BUFFER


def file_encoding(path):
    iso_unique = (b"\xb1", b"\xac", b"\xbc", b"\xa1", b"\xb6", b"\xa6")
    cp_unique = (b"\xb9", b"\xa5", b"\x9f", b"\x8f", b"\x8c", b"\x9c")

    iso_counter = 0
    cp_counter = 0

    _detector = cchardet.UniversalDetector()

    with open(path, "rb") as f:
        for line in f:
            for c in iso_unique:
                iso_counter += line.count(c)
            for c in cp_unique:
                cp_counter += line.count(c)

            _detector.feed(line)
            if _detector.done:
                break
    _detector.close()

    backup_encoding = "utf-8"
    encoding = _detector.result.get("encoding")
    confidence = _detector.result.get("confidence") or 0.0
    if confidence < 0.95 and (cp_counter or iso_counter):
        backup_encoding = "Windows-1250" if cp_counter > iso_counter else "iso-8859-2"
    return encoding, backup_encoding


def spreadsheet_file_format(path: os.PathLike, encoding: Optional[str]) -> Optional[str]:
    encoding = encoding or "utf-8"
    _s = Stream(path, encoding=encoding)
    _s.open()
    _s.close()
    return _s.format if _s.format != "inline" else None


def _csv(path: Union[str, bytes, io.BytesIO], encoding: Optional[str]) -> Optional[str]:
    path = os.path.realpath(path.name) if hasattr(path, "name") else path
    try:
        return spreadsheet_file_format(path, encoding)
    except (
        FormatError,
        UnicodeDecodeError,
        FileNotFoundError,
        BadZipFile,
        EncodingError,
    ):
        return None


def _json(source: Union[str, bytes, io.BytesIO], encoding: Optional[str]) -> Optional[str]:
    try:
        if isinstance(source, str):
            with open(source, encoding=encoding) as f:
                json.load(f)
        elif isinstance(source, bytes):
            data = io.BytesIO(source)
            data.seek(0)
            json.load(data, encoding=encoding)
        _format = "json"
        if _format == "json" and is_json_stat(source):
            _format = "jsonstat"
        return _format
    except (json.decoder.JSONDecodeError, UnicodeDecodeError):
        return None


def _xml(source: Union[str, bytes, io.BytesIO], encoding: Optional[str]) -> Optional[str]:
    try:
        if isinstance(source, bytes):
            source = io.BytesIO(source)
            source.seek(0)
        etree.parse(source, etree.XMLParser())
        return "xml"
    except etree.XMLSyntaxError:
        return None


def _html(source: Union[str, bytes, io.BytesIO], encoding: Optional[str]) -> Optional[str]:
    try:
        if isinstance(source, str):
            source = open(os.path.realpath(source), "rb")
        elif isinstance(source, bytes):
            source = io.BytesIO(source)
            source.seek(0)
        file_source = BeautifulSoup(source.read(), "html.parser")
        # there are resources with links to web pages containing only iframes loading some content
        is_html = bool(file_source.find("html") or file_source.find("iframe"))
        return "html" if is_html else None
    except Exception:
        return None


def _rdf(
    source: Union[str, io.BytesIO],
    encoding: Optional[str],
    extensions=(
        "rdf",
        "n3",
        "nt",
        "nq",
        "trig",
        "trix",
        "rdfa",
        "xml",
        "ttl",
        "jsonld",
    ),
) -> Optional[str]:
    """
    Try to parse source using rdflib. If the source is a file-like object, assume content-type=application/rdf+xml.
    Returns a matching extension, or None.
    """
    ext = None
    if isinstance(source, str):
        ext = source.split(".")[-1]
    else:
        source.seek(0)
    _format = settings.RDF_FORMAT_TO_MIMETYPE.get(ext) if ext in extensions else "xml"
    try:
        graph = rdflib.ConjunctiveGraph()
        graph.parse(source, format=_format)
        if len(graph):
            if ext in ("nt", "nq", "n3", "trig", "trix", "ttl", "jsonld"):
                return ext
            elif ext == "nquads":
                return "nq"
            elif ext == "turtle":
                return "ttl"
            return "rdf"
        return None
    except (
        TypeError,
        rdflib.exceptions.ParserError,
        xml.sax._exceptions.SAXParseException,
    ):
        return None


def _jsonapi(source, encoding, content_type=None):
    if _json(source, encoding):
        if isinstance(source, bytes):
            source = io.BytesIO(source)
        elif isinstance(source, str):
            source = open(os.path.realpath(source))
        try:
            with open(settings.JSONAPI_SCHEMA_PATH) as schemafile:
                schema = json.load(schemafile)
            source.seek(0)
            jsonschema.validate(json.load(source), schema)
            return "jsonapi"
        except jsonschema.ValidationError:
            pass
    return None


def _openapi(path, encoding, content_type=None):
    # TODO
    pass


def api_format(source):
    for func in (_jsonapi, _openapi, _json, _xml):
        res = func(source, "utf-8")
        if res:
            return res
    return None


def web_format(source):
    return _html(source, None)


def text_file_format(source: Union[str, bytes, io.BytesIO], encoding: Optional[str]) -> Optional[str]:
    encoding = encoding or "utf-8"
    for func in (_rdf, _json, _html, _xml, _csv):
        matching_file_format = func(source, encoding)
        if matching_file_format:
            return matching_file_format
    return None
