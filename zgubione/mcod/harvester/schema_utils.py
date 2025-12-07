from typing import Optional

from marshmallow import ValidationError
from mimeparse import MimeTypeParseException
from requests import Response

from mcod.lib.exceptions import (
    EmptyDocument,
    InvalidResponseCode,
    InvalidSchema,
    MissingContentType,
    NoResponseException,
    ResourceFormatValidation,
    UnsupportedContentType,
)
from mcod.lib.file_format_from_response import get_resource_format_from_response
from mcod.resources.link_validation import download_file
from mcod.unleash import is_enabled


def get_and_validate_resource_format_from_response(url: str) -> Optional[str]:
    try:
        _, options = download_file(url)
    except (
        InvalidSchema,
        InvalidResponseCode,
        MissingContentType,
        MimeTypeParseException,
        EmptyDocument,
        UnsupportedContentType,
    ) as exc:
        raise ValidationError(str(exc))
    response: Response = options.get("response")
    raise_exception = True if is_enabled("harvester_file_validation.be") else False
    if not response:
        raise NoResponseException(f"Response for url {url} not found")
    try:
        parsed_file_type = get_resource_format_from_response(response, raise_on_unsupported=raise_exception)
    except ResourceFormatValidation as exc:
        raise ValidationError(exc.message)
    return parsed_file_type
