from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import re
import uuid

import rfc3986.uri
import rfc3986.validators

# Module API
from tableschema.config import ERROR
from tableschema.types.any import cast_any  # noqa
from tableschema.types.array import cast_array  # noqa
from tableschema.types.boolean import cast_boolean  # noqa
from tableschema.types.date import cast_date  # noqa
from tableschema.types.datetime import cast_datetime  # noqa
from tableschema.types.duration import cast_duration  # noqa
from tableschema.types.geojson import cast_geojson  # noqa
from tableschema.types.geopoint import cast_geopoint  # noqa
from tableschema.types.integer import cast_integer  # noqa
from tableschema.types.number import cast_number  # noqa
from tableschema.types.object import cast_object  # noqa
from tableschema.types.time import cast_time  # noqa
from tableschema.types.year import cast_year  # noqa
from tableschema.types.yearmonth import cast_yearmonth  # noqa


def cast_string(format, value, **options):
    if any(
        (
            value == "",
            not isinstance(value, str),
            format == "email" and not re.match(_EMAIL_PATTERN, value),
        )
    ):
        return ERROR
    try:
        if format == "uri":
            uri = _uri_from_string(value)
            _uri_validator.validate(uri)
        elif format == "uuid":
            uuid.UUID(value, version=4)
        elif format == "binary":
            base64.b64decode(value)
    except Exception:
        return ERROR
    return value


def cast_missing(format, value, **options):
    return value if value == "" else ERROR


# Internal

_EMAIL_PATTERN = re.compile(r"[^@]+@[^@]+\.[^@]+")
_uri_from_string = rfc3986.uri.URIReference.from_string
_uri_validator = rfc3986.validators.Validator().require_presence_of("scheme")
