import json
import traceback
from typing import Any, Dict
from uuid import uuid4

import falcon.request
from django.utils.translation import gettext_lazy as _
from falcon import HTTP_500, HTTPError, Response
from flatdict import FlatDict

from mcod import logger, settings
from mcod.core.api.jsonapi.serializers import ErrorsSchema
from mcod.lib.encoders import LazyEncoder
from mcod.lib.schemas import ErrorSchema


def _is_version_one(request: falcon.request.Request) -> bool:
    return getattr(request, "api_version", None) == "1.0"


def update_content_type(request: falcon.request.Request, response: Response):
    if _is_version_one(request):
        response.content_type = "application/json"
    else:
        response.content_type = "application/vnd.api+json"


def error_serializer(req, resp, exc):
    resp.text = exc.to_json()
    update_content_type(req, resp)
    resp.append_header("Vary", "Accept")


def error_handler(request: falcon.request.Request, response: Response, exc: HTTPError, params: Dict[str, Any]) -> None:
    update_content_type(request, response)
    response.status = exc.status
    if _is_version_one(request):
        exc_data = {
            "title": exc.title,
            "description": exc.description,
            "code": getattr(exc, "code") or "error",
        }
        result = ErrorSchema().dump(exc_data)
        response.text = json.dumps(result, cls=LazyEncoder)
    else:
        response.text = json.dumps(_prepare_exception_for_14(request, response, exc), cls=LazyEncoder)


def error_404_handler(
    request: falcon.request.Request, response: Response, exc: falcon.HTTPNotFound, params: Dict[str, Any]
) -> None:
    update_content_type(request, response)
    response.status = exc.status

    if _is_version_one(request):
        exc_data = {
            "title": exc.title,
            "description": exc.description,
            "code": getattr(exc, "code") or "error",
        }
        result = ErrorSchema().dump(exc_data)
        response.text = json.dumps(result, cls=LazyEncoder)
    else:
        _title = _("The requested resource could not be found")
        _code = exc.status.lower().replace(" ", "_")
        error_body = {
            "id": uuid4(),
            "status": exc.status,
            "code": _code,
            "title": _title,
            "detail": _title,
        }
        if exc.title:
            error_body["title"] = exc.title
        if exc.description:
            error_body["detail"] = exc.description
        result = ErrorsSchema().dump(
            {
                "jsonapi": {"version": "1.4"},
                "errors": [
                    error_body,
                ],
            }
        )
        response.text = json.dumps(result, cls=LazyEncoder)


def _prepare_exception_for_14(
    request: falcon.request.Request, response: Response, exc: Exception, **override_fields: str
) -> dict:
    _api_version = getattr(request, "api_version", "1.4")
    _status = getattr(exc, "status", HTTP_500)
    _code = _status.lower().replace(" ", "_")
    error_body = {
        "id": uuid4(),
        "status": _status,
        "code": _code,
        "title": _("An unexpected error occurred. Please try again later."),
        "detail": _("An unexpected error occurred. Please try again later."),
    }
    if settings.DEBUG:
        title = getattr(exc, "title", None)
        if title:
            error_body["title"] = title
        description = getattr(exc, "description", " ".join(str(a).capitalize() for a in exc.args))
        if description:
            error_body["detail"] = description
        error_body["meta"] = {"traceback": traceback.format_exc()}
    error_body.update(override_fields)
    return ErrorsSchema().dump(
        {
            "jsonapi": {"version": _api_version},
            "errors": [
                error_body,
            ],
        }
    )


def error_500_handler(request: falcon.request.Request, response: Response, exc: Exception, params):
    update_content_type(request, response)
    response.status = getattr(exc, "status", HTTP_500)

    if _is_version_one(request):
        code = getattr(exc, "code", None)
        exc_data = {
            "title": _("An unexpected error occurred. Please try again later."),
            "description": _("An unexpected error occurred. Please try again later."),
            "code": code or "server_error",
            "traceback": None,
        }
        if settings.DEBUG:
            title = getattr(exc, "title", None)
            if title:
                exc_data["title"] = title
            description = getattr(exc, "description", " ".join(str(a).capitalize() for a in exc.args))
            exc_data["description"] = description
            exc_data["traceback"] = traceback.format_exc()
        result = ErrorSchema().dump(exc_data)
        response.text = json.dumps(result, cls=LazyEncoder)
    else:
        body = _prepare_exception_for_14(request, response, exc)
        response.text = json.dumps(body, cls=LazyEncoder)

    if settings.DEBUG:
        logger.exception(exc)


def error_422_handler(request: falcon.request.Request, response: Response, exc: HTTPError, params):
    update_content_type(request, response)
    response.status = exc.status

    if _is_version_one(request):
        exc_data = {
            "title": exc.title,
            "description": _("Field value error"),
            "code": getattr(exc, "code") or "entity_error",
        }
        if hasattr(exc, "errors"):
            exc_data["errors"] = exc.errors

        result = ErrorSchema().dump(exc_data)
        response.text = json.dumps(result, cls=LazyEncoder)
    else:
        _exc_code = exc.status.lower().replace(" ", "_")
        _errors = []
        if hasattr(exc, "errors"):
            flat = FlatDict(exc.errors, delimiter="/")
            for field, errors in flat.items():
                if not isinstance(errors, list):
                    errors = [
                        str(errors),
                    ]

                for title in errors:
                    _error = {
                        "id": uuid4(),
                        "title": _("Field error"),
                        "detail": _(title),
                        "status": response.status,
                        "code": getattr(exc, "code") or _exc_code,
                        "source": {"pointer": "/{}".format(field)},
                    }
                    _errors.append(_error)
        else:
            _error = {
                "id": uuid4(),
                "code": getattr(exc, "code") or _exc_code,
                "title": exc.title,
                "detail": _("Field value error"),
                "status": response.status,
            }
            _errors.append(_error)
        result = ErrorsSchema().dump({"errors": _errors})
        response.text = json.dumps(result, cls=LazyEncoder)
