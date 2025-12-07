import falcon
from elasticapm.base import Client
from elasticapm.conf import constants
from elasticapm.utils import compat, get_url_dict
from elasticapm.utils.wsgi import get_environ, get_headers
from werkzeug.exceptions import ClientDisconnected

from mcod import settings


def get_client():
    if not hasattr(settings, "ELASTIC_APM"):
        return None
    if not settings.DEBUG or settings.ELASTIC_APM.get("DEBUG", False):
        return Client(
            settings.ELASTIC_APM,
            framework_name="falcon",
            framework_version=falcon.__version__,
        )

    return None


def get_data_from_request(request, capture_body=False, capture_headers=True):
    result = {
        "env": dict(get_environ(request.env)),
        "method": request.method,
        "socket": {
            "remote_address": request.env.get("REMOTE_ADDR"),
            "encrypted": True if request.scheme == "https" else False,
        },
        "cookies": request.cookies,
    }
    if capture_headers:
        result["headers"] = dict(get_headers(request.env))
    if request.method in constants.HTTP_WITH_BODY:
        body = None
        if request.content_type == "application/x-www-form-urlencoded":
            body = compat.multidict_to_dict(request.stream.read())
        elif request.content_type and request.content_type.startswith("multipart/form-data"):
            body = compat.multidict_to_dict(request.stream.read())
        else:
            try:
                body = request.stream.read()
            except ClientDisconnected:
                pass

        if body is not None:
            result["body"] = body if capture_body else "[REDACTED]"

    result["url"] = get_url_dict(request.url)
    return result


def get_data_from_response(response, capture_headers=True):
    result = {}

    status_code = get_status_code_number(response.status)

    if isinstance(status_code, compat.integer_types):
        result["status_code"] = status_code

    if capture_headers and getattr(response, "_headers", None):
        result["headers"] = response._headers
    return result


def get_status_code_number(status_code):
    if not status_code:
        return None
    number, message = status_code.split(" ", 1)
    return int(number)
