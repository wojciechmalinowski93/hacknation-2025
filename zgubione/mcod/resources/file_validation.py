import json
import logging
from contextlib import suppress
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import magic
import rdflib
from mimeparse import parse_mime_type

from mcod import settings
from mcod.lib.file_format_from_response import file_format_from_content_type_extension_map
from mcod.resources import guess
from mcod.resources.archives import (
    ArchiveReader,
    PasswordProtectedArchiveError,
    UnsupportedArchiveError,
    is_archive_file,
)
from mcod.resources.geo import (
    analyze_shapefile,
    archive_contains_geotiff,
    are_shapefiles,
    check_geodata,
)
from mcod.resources.meteo import check_meteo_data

logger = logging.getLogger("mcod")


class UnknownFileFormatError(Exception):
    pass


def _is_json(family, content_type):
    return family == "application" and content_type == "json"


def _is_xml(family, content_type):
    return family == "text" and content_type == "xml"


def _is_office_file(extension, content_type):
    return extension in ("doc", "docx", "xls", "xlsx", "ods", "odt") or content_type == "msword"


def _is_spreadsheet(ext):
    return ext in ("xls", "xlsx", "ods")


def _is_plain_text(family, content_type):
    return family == "text" and content_type == "plain"


def _isnt_text_encoding(encoding):
    return any(
        (
            isinstance(encoding, str) and encoding.startswith("unknown"),
            encoding == "binary",
            not encoding,
        )
    )


def _isnt_msdoc_text(content_type):
    try:
        extensions = next(filter(lambda x: x[1] == content_type, settings.SUPPORTED_CONTENT_TYPES))[2]
        return len({"doc", "docx"} & set(extensions)) == 0
    except StopIteration:
        return False


def _analyze_plain_text(path, extension, encoding):
    backup_encoding = "utf-8"
    if encoding.startswith("unknown") or encoding == "binary":
        encoding, backup_encoding = guess.file_encoding(path)
        logger.debug(f" encoding (guess-plain): {encoding}")
        logger.debug(f" backup_encoding (guess-plain): {backup_encoding}")

    extension = guess.text_file_format(path, encoding or backup_encoding) or extension
    logger.debug(f"  extension (guess-plain): {extension}")

    return extension, encoding


def _analyze_office_file(path, encoding, content_type, extension):
    tmp_extension = path.rsplit(".")[-1]
    if _isnt_text_encoding(encoding):
        encoding, backup_encoding = guess.file_encoding(path)
        logger.debug(f"  encoding (guess-spreadsheet): {encoding}")
        logger.debug(f"  backup_encoding (guess-spreadsheet): {backup_encoding}")
        encoding = encoding or backup_encoding

    spreadsheet_format = None
    try:
        spreadsheet_format = guess.spreadsheet_file_format(path, encoding)
    except Exception as exc:
        logger.debug(f"guess.spreadsheet_file_format error: {exc}")
    if all(
        (
            _is_spreadsheet(tmp_extension),
            _isnt_msdoc_text(content_type),
            spreadsheet_format,
        )
    ):
        extension = spreadsheet_format
        logger.debug(f"  extension (guess-spreadsheet): {extension}")
    elif extension == "zip" and encoding != "binary":
        extension = tmp_extension

    return extension, encoding


def check_support(ext, file_mimetype):
    content_type = file_mimetype.split("/")[-1]
    if _is_office_file(ext, content_type):
        return
    try:
        next(filter(lambda x: x[1] == content_type, settings.SUPPORTED_CONTENT_TYPES))
        return
    except StopIteration:
        if is_archive_file(content_type):
            raise UnsupportedArchiveError("archives-are-not-supported")

    raise UnknownFileFormatError("unknown-file-format")


def get_file_info(path: Union[Path, str]) -> Tuple[str, str, dict]:
    _magic = magic.Magic(mime=True, mime_encoding=True)
    result = _magic.from_file(path)
    return parse_mime_type(result)


def analyze_file(path: Union[Path, str]):  # noqa: C901
    logger.debug(f"analyze_resource_file({path})")
    path = str(path.absolute()) if isinstance(path, Path) else path
    family, content_type, options = get_file_info(path)
    extracted_extension = None
    extracted_mimetype = None
    extracted_encoding = None
    is_extracted = False
    is_password_protected_archive = False
    if is_archive_file(content_type):
        is_extracted = True
        try:
            with ArchiveReader(path) as archive:
                if len(archive) == 1:
                    # single compressed geotiff goes here
                    extracted_path = archive.extract_single()
                    extracted_family, extracted_content_type, extracted_options = get_file_info(extracted_path)
                    logger.debug(f"  extracted file {extracted_path}")
                    extracted_extension, _, extracted_encoding, _, extracted_mimetype, _ = evaluate_file_details(
                        extracted_content_type,
                        extracted_family,
                        extracted_options,
                        extracted_path,
                        is_extracted=True,
                    )
                    logger.debug(f"  extracted extension: {extracted_extension}")
                    logger.debug(f"  extracted mimetype: {extracted_mimetype}")
                elif are_shapefiles(archive):
                    shp_file = next(archive.get_by_extension("shp"))
                    shp_type, options = analyze_shapefile(shp_file)
                    content_type = "shapefile"
                elif archive_contains_geotiff(archive):
                    family = "image"
                    content_type = "tiff;application=geotiff"
                extension, file_info, encoding, path, file_mimetype, analyze_exc = evaluate_file_details(
                    content_type,
                    family,
                    options,
                    path,
                    is_extracted,
                )
        except PasswordProtectedArchiveError:
            is_password_protected_archive = True
    extension, file_info, encoding, path, file_mimetype, analyze_exc = evaluate_file_details(
        content_type,
        family,
        options,
        path,
        is_extracted,
    )

    if is_password_protected_archive and not analyze_exc:
        analyze_exc = PasswordProtectedArchiveError()

    logger.debug(f"  finally: extension = {extension}, file_info = {file_info}, encoding = {encoding}")

    return (
        extension,
        file_info,
        encoding,
        path,
        file_mimetype,
        analyze_exc,
        extracted_extension,
        extracted_mimetype,
        extracted_encoding,
    )


def _json_suspected_as_jsonld(path: Union[Path, str]) -> bool:
    """Check if json file contains `@context` key as top-level key. This is characteristic of the json-ld format."""
    if isinstance(path, Path):
        path = str(path.absolute())
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return "@context" in data
    except (json.JSONDecodeError, Exception):
        return False


def check_rdf(path: Union[Path, str], family: str, sub_type: str) -> Tuple[str, str]:
    """Since RDF files can arrive in many different formats we need to proactively try to parse
    them.
    See the function at mcod.resources.guess._rdf, which may or may not be in use. (TODO).
    Returns a tuple of family, content_type, for example
    ("application", "rdf+xml")
    """
    if sub_type in ("html", "xhtml"):
        return family, sub_type

    if sub_type == "json" and not _json_suspected_as_jsonld(path):
        return family, sub_type

    for extension, content_type in settings.RDF_FORMAT_TO_MIMETYPE.items():
        with suppress(Exception):
            graph = rdflib.ConjunctiveGraph()
            graph.parse(path, format=content_type)
            has_triples = any([len(g) for g in graph.store.contexts()])
            if has_triples:
                family, sub_type = content_type.split("/")
                return family, sub_type
    return family, sub_type


def evaluate_file_details(content_type: str, family: str, options: Dict[str, str], path: Union[Path, str], is_extracted: bool):
    """
    Second level of file type inference - we parse the file here and try to assign an extension.
    Args:
        content_type: Mime sub-type, e.g. html
        family: Mime family, e.g. text
        options: Additional info from magic content-type, known keys: charset, q
        path: actual filesystem path to the file under evaluation
        is_extracted: flag, true if the file was a part of an archive (zip, tar, etc.)

    Returns:
        6-tuple of:
        extension: Guessed extension
        file_info: String describing the file's content from magic
        encoding: File encoding (e.g. utf-8)
        path: Same as the arg
        file_mimetype: Full mimetype
        analyze_exception: Optional Exception, if worth passing up (not every exception is - for example parsing errors
            are caught and logged.
    """
    path = str(path)
    analyze_exception: Optional[Exception] = None
    try:
        content_type, family = check_geodata(path, content_type, family, is_extracted=is_extracted)
    except Exception as exc:
        analyze_exception = Exception(
            [
                {
                    "code": "geodata-error",
                    "message": "Błąd podczas analizy pliku: {}.".format(exc.message),
                }
            ]
        )
    file_info = magic.from_file(path)
    content_type = check_meteo_data(content_type, path, file_info)  # returns a content type family

    family, content_type = check_rdf(path, family, content_type)

    file_mimetype = f"{family}/{content_type}"
    logger.debug(f"  parsed mimetype: {file_mimetype});{options}")
    logger.debug(f"  file info: {file_info}")
    encoding = options.get("charset", "unknown")
    logger.debug(f"  encoding: {encoding}")

    extension = file_format_from_content_type_extension_map(content_type, family=family) or path.rsplit(".")[-1]

    logger.debug(f"  extension: {extension}")

    if _is_plain_text(family, content_type) or _is_json(family, content_type) or _is_xml(family, content_type):
        extension, encoding = _analyze_plain_text(path, extension, encoding)

    if _is_office_file(extension, content_type):
        extension, encoding = _analyze_office_file(path, encoding, content_type, extension)
    return extension, file_info, encoding, path, file_mimetype, analyze_exception
