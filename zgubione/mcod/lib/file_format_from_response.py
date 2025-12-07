import logging
import os
from collections import namedtuple
from email.parser import HeaderParser
from mimetypes import MimeTypes
from typing import Dict, Optional, Tuple
from urllib import parse

import magic
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from mimeparse import MimeTypeParseException, parse_mime_type
from requests import Response

from mcod.lib.exceptions import ResourceFormatValidation

FormatFromResponse = namedtuple("FormatFromResponse", "url, magic, content_type, content_disposition")
mime = MimeTypes()
logger = logging.getLogger("mcod")

Extension = str


def file_format_from_content_type_extension_map(
    mime_type: str, family: Optional[str] = None, extension: Optional[str] = None
) -> Optional[str]:
    """
    Returns the preferred file extension for a given MIME type and subtype.

    This function searches a predefined mapping of MIME types and subtypes
    to associated file extensions, and returns the most appropriate one.
    You may optionally provide a MIME type family (e.g., "application") to
    narrow the search, and a specific extension to validate.

    Args:
        mime_type (str): The MIME subtype (e.g., "pdf", "json", "csv").
        family (str, optional): The top-level MIME type (e.g., "application", "image").
            If provided, the function will only match entries with this type.
        extension (str, optional): A specific extension to validate. If it is
            listed among the known extensions for the matched type/subtype, it will
            be returned instead of the default.

    Returns:
        str or None: The preferred or validated file extension (e.g., "pdf"),
        or None if no match is found.

    Examples:
        >>> file_format_from_content_type_extension_map("pdf", family="application")
        'pdf'
        >>> file_format_from_content_type_extension_map("json")
        'json'
        >>> file_format_from_content_type_extension_map("json", extension="geojson")
        'json'
        >>> file_format_from_content_type_extension_map("unknown")
        None
    """
    results = []
    for content_family_, mime_subtype_, extensions_ in settings.CONTENT_TYPE_TO_EXTENSION_MAP:
        if family and content_family_ == family and mime_subtype_ == mime_type:
            results.append((content_family_, mime_subtype_, extensions_))
        elif mime_subtype_ == mime_type:
            results.append((content_family_, mime_subtype_, extensions_))

    for mime_subtype_, extension_ in settings.ARCHIVE_TYPE_TO_EXTENSIONS.items():
        if family and family == "application" and mime_subtype_ == mime_type:
            results.append(("application", mime_subtype_, (extension_,)))
        elif mime_subtype_ == mime_type:
            results.append(("application", mime_subtype_, (extension_,)))

    if not results:
        return None

    _, _, extensions = results[0]
    if extension and extension in extensions:
        return extension

    return extensions[0]


def get_extension_from_mime_type(mime_type: str) -> str:
    """
    Return a file extension based on the provided content type (MIME type). For example "video/mp3".

    Tries to determine the most likely file extension from the given MIME type
    using a custom `file_format_from_content_type()` function first. If that fails,
    falls back to using the standard library's `mimetypes.guess_extension()`.
    """
    ext = None
    if mime_type:
        ext = file_format_from_content_type_extension_map(mime_type)
        if not ext:
            ext = mime.guess_extension(mime_type)
            ext = ext.strip(".") if ext else ""

    return ext or "unknown"


def get_file_mime_type_from_chunk(chunk: bytes) -> Optional[str]:
    """
    Determines the MIME type of given binary data chunk.

    This function uses the `python-magic` library to analyze the provided chunk of bytes
    and returns a string representing its MIME type.

    Args:
        chunk (bytes): A binary data chunk representing the start of a file.

    Returns:
        str: The detected MIME type of the file, e.g., 'image/png', 'application/pdf'.
    """
    try:
        mime = magic.Magic(mime=True).from_buffer(chunk)
    except (TypeError, magic.MagicException):
        logger.exception("Handled error getting MIME type from content")
        return None
    return mime


def _get_extension_from_magic(response_content: bytes) -> Optional[Extension]:
    """
    Determine the file type (extension) from raw file content using MIME type detection.

    This function attempts to infer the file extension based on the MIME type detected from
    a chunk of the given byte content. It uses `get_file_mime_type_from_chunk` to retrieve the
    MIME type, then parses it and maps the MIME subtype to a common file extension.

    Returns:
        Optional[str]: The inferred file extension (e.g., "csv", "pdf"), or `None` if the
        MIME type could not be parsed or mapped to a known file type.
    """
    mime_type_from_magic: Optional[str] = get_file_mime_type_from_chunk(response_content)
    try:
        _, mime_type, _ = parse_mime_type(mime_type_from_magic)
        parsed_extension_from_mime_type: str = get_extension_from_mime_type(mime_type)
        if parsed_extension_from_mime_type == "unknown":
            file_extension = None
        else:
            file_extension = parsed_extension_from_mime_type
    except (MimeTypeParseException, TypeError):
        file_extension = None

    return file_extension


def _get_mime_type_from_content_disposition(headers: Dict[str, str]) -> Optional[Extension]:
    """
    Extract the file extension from the Content-Disposition header, if present.

    Parses the Content-Disposition header to retrieve the filename and infers the extension
    by extracting the part after the last dot in the filename.

    Examples:
        >>> _get_mime_type_from_content_disposition({"Content-Disposition": "attachment; filename=some.csv"})
        'csv'

        >>> _get_mime_type_from_content_disposition({"Content-Disposition": "attachment"})
        None

    :param headers: A dictionary of HTTP headers.
    :return: The extracted file extension (e.g., 'csv'), or None if unavailable.
    """
    content_disposition = headers.get("Content-Disposition")
    extension_from_content_disposition = None
    if not content_disposition:
        return extension_from_content_disposition
    parsed_header = HeaderParser().parsestr(f"Content-disposition: {content_disposition}")
    filename = parsed_header.get_filename()
    if filename:
        extension_from_content_disposition = filename.split(".")[-1]
    return extension_from_content_disposition


def _get_mime_type_from_content_type(headers: Dict[str, str]) -> Optional[Extension]:
    """
    Extract the file extension from the Content-Type header, if present.

    Parses the Content-Type header and maps the MIME subtype (e.g. 'csv', 'xml') to a known file extension.
    If the mapping is not known, returns None.

    Examples:
        >>> _get_mime_type_from_content_type({"Content-Type": "text/csv"})
        'csv'

        >>> _get_mime_type_from_content_type({"Content-Type": "application/octet-stream"})
        None

    :param headers: A dictionary of HTTP headers.
    :return: The mapped file extension (e.g., 'csv'), or None if unknown.
    """
    extensions_from_content_type = None
    content_type = headers.get("Content-Type")
    if not content_type:
        return extensions_from_content_type
    parsed_header = HeaderParser().parsestr(f"Content-type: {content_type}")
    from_content_type = get_extension_from_mime_type(parsed_header.get_content_subtype())
    extensions_from_content_type = from_content_type if from_content_type != "unknown" else None
    return extensions_from_content_type


def _filename_from_url(url: str) -> Tuple[str, str]:
    """
    Extract the base filename and file extension from a URL path.

    This function parses the path portion of a URL and attempts to extract a filename and extension.
    If the filename is missing, is a dot-only name like '.csv', or has no extension at all, it returns
    'unknown' as the filename and an empty string as the extension.

    Examples:
        >>> _filename_from_url("https://mcod.local/some.csv")
        ('some', 'csv')
        >>> _filename_from_url("https://example.com/data/.csv")
        ('unknown', '')
        >>> _filename_from_url("https://example.com/download")
        ('unknown', '')

    :return: A tuple of (filename, extension), both strings.
    """
    file_name_from_url = os.path.basename(parse.urlparse(url).path)
    if file_name_from_url.startswith(".") and file_name_from_url.count(".") == 1:
        return "unknown", ""
    else:
        filename, ext = os.path.splitext(file_name_from_url)

    return filename.strip(".") or "unknown", ext.strip(".")


def _get_extension_from_url(url: str) -> Optional[Extension]:
    """
    This function extracts the file name and extension from a given URL and returns the extension
    if one is found.

    Examples:
    >>> _get_extension_from_url("https://mcod.local/some.csv")
        ("some", "csv")
     >>> _get_extension_from_url("https://example.com/data/.csv")
        ('unknown', 'csv')
    >>> _get_extension_from_url("https://example.com/download")
    ('unknown', '')

    Returns:
        Optional[str]: The file extension (e.g., "csv", "json") if present in the URL,
        otherwise `None`.
    """

    filename, extension_from_url = _filename_from_url(url)
    if extension_from_url:
        return extension_from_url


def _get_resource_formats_from_response(response: Response) -> FormatFromResponse:
    """
    Extracts potential file formats from an HTTP response using multiple strategies.

    This function attempts to infer the file format of a remote resource by:
    - Parsing the file extension from the URL.
    - Detecting MIME type via magic number inspection (`python-magic` or equivalent).
    - Extracting the filename and extension from the Content-Disposition header.
    - Inferring extension from the Content-Type header.

    The results from all sources are returned in a `FormatFromResponse` namedtuple:
    (from_url, from_magic, from_content_type, from_content_disposition).
    """
    extension_from_url = _get_extension_from_url(response.url)
    extension_from_magic = _get_extension_from_magic(response.content)
    extension_from_content_type = _get_mime_type_from_content_type(dict(response.headers))
    extension_from_content_disposition = _get_mime_type_from_content_disposition(dict(response.headers))

    logger.info(
        f"Validated formats from: url - {extension_from_url} "
        f"--- magic: {extension_from_magic}"
        f"--- content_type: {extension_from_content_type}"
        f"--- content_disposition: {extension_from_content_disposition}"
    )

    return FormatFromResponse(
        extension_from_url, extension_from_magic, extension_from_content_type, extension_from_content_disposition
    )


def get_resource_format_from_response(
    response: Response, raise_on_unknown: bool = False, raise_on_unsupported=False
) -> Optional[Extension]:
    """
    Determines the most reliable file format from an HTTP response.

    The function attempts to detect the file format using a sequence of heuristics,
    in the following order of priority:
        1. File extension extracted from the URL.
        2. MIME type detected from the response content (via the `magic` library).
        3. Format inferred from HTTP headers (`Content-Type` and `Content-Disposition`).

    The first match found that is also supported (i.e., listed in `settings.SUPPORTED_FILE_EXTENSIONS`)
    is returned as the result.

    If a format is detected but not supported and `raise_on_unsupported` is True, a
    `ResourceFormatValidation` exception is raised.

    If no format can be determined and `raise_on_unknown` is True, a `ResourceFormatValidation`
    exception is raised as well.

    Args:
        response (Response): The HTTP response object to analyze.
        raise_on_unknown (bool, optional): If True, raise an exception when no format
            could be determined. Defaults to False.
        raise_on_unsupported (bool, optional): If True, raise an exception when a format
            is detected but not supported. Defaults to False.

    Returns:
        Optional[str]: The detected and supported file format (e.g., 'pdf', 'jpeg'),
        or None if no valid format could be determined and no exception was raised.
    """
    result: FormatFromResponse = _get_resource_formats_from_response(response)
    extension_candidates = (result.url, result.magic, result.content_type, result.content_disposition)

    if set(extension_candidates) == {None}:
        if raise_on_unknown:
            raise ResourceFormatValidation("Format unknown.")
        else:
            return None

    supported_file_extensions = [ext.replace(".", "") for ext in settings.SUPPORTED_FILE_EXTENSIONS]
    for ext in extension_candidates:
        if ext and ext in supported_file_extensions:
            return ext
        if ext and ext not in settings.SUPPORTED_FILE_EXTENSIONS and raise_on_unsupported:
            raise ResourceFormatValidation(_("Invalid file extension: %(ext)s.") % {"ext": ext or "-"})
