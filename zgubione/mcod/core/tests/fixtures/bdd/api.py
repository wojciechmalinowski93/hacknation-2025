import json
from urllib import parse

import dpath.util
import requests_mock
from falcon.testing import Cookie, TestClient
from falcon.util.misc import code_to_http_status
from falcon.util.structures import Context
from pytest_bdd import parsers, then, when
from requests_mock import MockerCore

from mcod import settings
from mcod.api import ApiApp
from mcod.core.utils import jsonapi_validator
from mcod.lib.jwt import get_auth_token


@then(parsers.parse("api request method is {method}"))
@when(parsers.parse("api request method is {method}"))
def api_request_method(method, context):
    context.api.method = method.upper()


@when(parsers.parse("api request mcod_csrf_token is {is_valid}"))
def api_request_csrf_token(is_valid: bool, context: Context, mocker: MockerCore, test_api_instance: ApiApp):
    mocker.patch("mcod.settings.ENABLE_CSRF", True)
    is_valid = True if is_valid == "valid" else False
    csrf_token = None
    if is_valid:
        api_url = parse.urlparse(settings.API_URL)
        kwargs = {
            "method": "GET",
            "path": "/datasets",
            "headers": context.api.headers,
            "params": context.api.params,
            "protocol": api_url.scheme,
            "host": api_url.netloc,
        }
        _app = test_api_instance()
        resp = TestClient(_app).simulate_request(**kwargs)
        csrf_token_cookie: Cookie = resp.cookies.get("mcod_csrf_token")
        assert csrf_token_cookie, "any GET request should return a valid CSRF token in cookie mcod_csrf_token"
        csrf_token = csrf_token_cookie.value

    if csrf_token is not None:
        context.api.cookies[settings.API_CSRF_COOKIE_NAME] = csrf_token
        context.api.headers[settings.API_CSRF_HEADER_NAME] = csrf_token


@when("resource api tabular data endpoint is requested")
def api_request_endpoint(buzzfeed_fakenews_resource, context):
    context.api.path = f"/resources/{buzzfeed_fakenews_resource.id}/data"


@when("resource api tabular data with date and datetime endpoint is requested")
def api_request_data_endpoint(resource_with_date_and_datetime, context):
    context.api.path = f"/resources/{resource_with_date_and_datetime.id}/data"


@when("json api validation is skipped")
def api_validation_skipped(context):
    context.api.skip_validation = True


@then(parsers.parse("api request path from response is {field}"))
def api_request_path_from_response(field, context):
    path = dpath.util.get(context.response.json, field)
    context.api.path = path.replace(settings.API_URL, "")


@then(parsers.parse("api request path substring {from_string} is replaced by {to_string}"))
def api_request_path_substring_replaced(from_string, to_string, context):
    context.api.path = context.api.path.replace(from_string, to_string)


@when(parsers.parse("api request posted data is {req_post_data}"))
def api_request_post_data(context, req_post_data):
    context.obj = json.loads(req_post_data)


@when(parsers.parse("api request {object_type} data has {req_data}"))
def api_request_data(context, object_type, req_data):
    extra = json.loads(req_data)
    default_data = {
        "chart": {
            "is_default": False,
        },
        "comment": {
            "text": "Test comment",
        },
        "dataset_comment": {
            "comment": "Test comment",
        },
        "notification": {},
        "register": {},
        "resource_comment": {},
        "schedule": {
            "end_date": "2021-01-01",
            "link": "http://dane.gov.pl",
        },
        "schedule_state": {"state": "archived"},
        "showcaseproposal": {
            "category": "app",
            "license_type": "free",
            "title": "test",
            "notes": "notes...",
            "url": "https://example.com",
            "applicant_email": "user@example.com",
            "author": "Eric Idle",
            "is_personal_data_processing_accepted": True,
            "is_terms_of_service_accepted": True,
            "is_mobile_app": True,
            "keywords": ["test"],
            "mobile_apple_url": "https://example.com",
            "mobile_google_url": "https://example.com",
            "is_desktop_app": True,
            "desktop_linux_url": "https://example.com",
            "desktop_macos_url": "https://example.com",
            "desktop_windows_url": "https://example.com",
            "external_datasets": [{"title": "example.com", "url": "https://example.com"}],
            "image": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAACXBIWXMAAAsTAAALEwEAmpw"
            "YAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAACoSURBVHgB1ZLBDcIwDEWf3XJCQt2AMAEZgU0YgZEYgRUyAit0"
            "gnKnSnCjckA0OXBAqqVIjq1v+399oRbXoWP7dKAeEYfqnoTlOFlswoMUBdFLaWbLjgE2n1Uh2OS+dozyY/wf2BqXsFC/m"
            "zATx1QGvncmU5L8IMYeTZY31DaevqqNhgwWziXgqlRVDow44+qQOFnuOAslNWC1yc18PGZTd+ZdPw/t7O9fCJAsfc2rOZ"
            "EAAAAASUVORK5CYII=",
            "illustrative_graphics": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAACXBIWXM"
            "AAAsTAAALEwEAmpwYAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAACoSURBVHgB1ZLBDcIwDEWf3XJCQt2AMAEZ"
            "gU0YgZEYgRUyAit0gnKnSnCjckA0OXBAqqVIjq1v+399oRbXoWP7dKAeEYfqnoTlOFlswoMUBdFLaWbLjgE2n1Uh2OS+d"
            "ozyY/wf2BqXsFC/mzATx1QGvncmU5L8IMYeTZY31DaevqqNhgwWziXgqlRVDow44+qQOFnuOAslNWC1yc18PGZTd+ZdPw"
            "/t7O9fCJAsfc2rOZEAAAAASUVORK5CYII=",
        },
        "sparql": {
            "q": "SELECT * WHERE { ?s ?p ?o. }",
            "format": "application/rdf+xml",
        },
        "user_schedule": {
            "is_ready": True,
        },
        "user_schedule_item": {
            "dataset_title": "Test",
            "format": "csv",
            "institution": "Ministerstwo Cyfryzacji",
        },
        "user_schedule_item_admin": {
            "recommendation_state": "recommended",
            "recommendation_notes": "",
        },
        "user_schedule_item_agent": {
            "is_resource_added": False,
            "is_resource_added_notes": "",
        },
    }
    data = default_data.get(object_type, {})
    data.update(extra)
    object_type = "comment" if object_type in ["dataset_comment", "resource_comment"] else object_type
    object_type = "schedule" if object_type == "schedule_state" else object_type
    object_type = "user_schedule_item" if object_type in ["user_schedule_item_admin", "user_schedule_item_agent"] else object_type
    object_type = "user" if object_type == "register" else object_type
    context.obj = {"data": {"type": object_type, "attributes": data}}


@then(parsers.parse("api request path is {request_path}"))
@when(parsers.parse("api request path is {request_path}"))
def api_request_path(request_path, context):
    context.api.path = request_path


@then(parsers.parse("api request param {req_param_name} is {req_param_value}"))
@when(parsers.parse("api request param {req_param_name} is {req_param_value}"))
def api_request_param(req_param_name, req_param_value, context):
    context.api.params[req_param_name] = req_param_value


@when(parsers.parse("api request has params {req_params}"))
def api_request_params(req_params, context):
    context.api.params.update(json.loads(req_params))


@when(parsers.parse("api request language is {lang_code}"))
def api_request_language(context, lang_code):
    context.api.headers["Accept-Language"] = lang_code


@then(parsers.parse("api request header {req_header_name} is {req_header_value}"))
@when(parsers.parse("api request header {req_header_name} is {req_header_value}"))
def api_request_header(req_header_name, req_header_value, context):
    context.api.headers[req_header_name] = req_header_value


@then(parsers.parse("api request body field {field} is of type {field_type}"))
@when(parsers.parse("api request body field {field} is of type {field_type}"))
def api_request_object_of_type(field, field_type, context):
    if field_type == "dict":
        value = {}
    elif field_type == "list":
        value = []
    else:
        value = ""
    dpath.new(context.obj, field, value)


@then(parsers.parse("api request body field {field} is {value}"))
@when(parsers.parse("api request body field {field} is {value}"))
def api_request_object_attribute(field, value, context):
    dpath.new(context.obj, field, value)


@then(parsers.parse("api request body field {req_body_field} is {req_body_value}"))
@when(parsers.parse("api request body field {req_body_field} is {req_body_value}"))
def api_request_object_attribute_p(req_body_field, req_body_value, context):
    dpath.new(context.obj, req_body_field, req_body_value)


@when("send api request and fetch the response")
@then("send api request and fetch the response")
def api_send_request(context, mocker, test_api_instance):
    if context.user:
        token = get_auth_token(context.user, session_key=str(context.user.id))
        mocker.patch("mcod.core.api.hooks.get_user", return_value=context.user)
        context.api.headers["Authorization"] = "Bearer %s" % token

    # cookies have to be sent in Cookie header: https://github.com/falconry/falcon/issues/1640
    if context.api.cookies:
        cookies = ""
        for cookie_name, cookie_value in context.api.cookies.items():
            cookies += "%s=%s; " % (cookie_name, cookie_value)

        if cookies:
            if context.api.headers.get("Cookie"):
                context.api.headers["Cookie"] += "; " + cookies
            else:
                context.api.headers["Cookie"] = cookies

    o = parse.urlparse(settings.API_URL)
    kwargs = {
        "method": context.api.method,
        "path": context.api.path,
        "headers": context.api.headers,
        "params": context.api.params,
        "protocol": o.scheme,
        "host": o.netloc,
    }
    if context.api.method in ("POST", "PUT", "PATCH", "DELETE"):
        kwargs["json"] = context.obj

    resp = TestClient(test_api_instance).simulate_request(**kwargs)
    skip_validation = getattr(context.api, "skip_validation", False)
    api_version = resp.headers["x-api-version"]
    if api_version == "1.0":
        skip_validation = True
    if resp.status_code in (202, 204):
        skip_validation = True
    if not skip_validation:
        valid, validated, errors = jsonapi_validator(resp.json)
        assert valid is True, errors
    # TODO: this does not work on gitlab...
    # Counter().save_counters()
    # TODO: check pagination
    context.response = resp
    mocker.stopall()


@when(parsers.parse("send api request and fetch the response with mocked_url {mocked_url} and mocked_rdf_data {mocked_data}"))
@requests_mock.Mocker(kw="mock_request")
def api_send_request_with_mocked_url(context, mocker, mocked_url, mocked_data, test_api_instance, **mock_kwargs):
    if context.user:
        token = get_auth_token(context.user, session_key=str(context.user.id))
        mocker.patch("mcod.core.api.hooks.get_user", return_value=context.user)
        context.api.headers["Authorization"] = "Bearer %s" % token

    # cookies have to be sent in Cookie header: https://github.com/falconry/falcon/issues/1640
    if context.api.cookies:
        cookies = ""
        for cookie_name, cookie_value in context.api.cookies.items():
            cookies += "%s=%s; " % (cookie_name, cookie_value)

        if cookies:
            if context.api.headers.get("Cookie"):
                context.api.headers["Cookie"] += "; " + cookies
            else:
                context.api.headers["Cookie"] = cookies

    o = parse.urlparse(settings.API_URL)
    kwargs = {
        "method": context.api.method,
        "path": context.api.path,
        "headers": context.api.headers,
        "params": context.api.params,
        "protocol": o.scheme,
        "host": o.netloc,
    }
    if context.api.method in ("POST", "PUT", "PATCH", "DELETE"):
        kwargs["json"] = context.obj

    mock_request = mock_kwargs["mock_request"]
    mock_request.post(
        mocked_url,
        headers={"content-type": "application/rdf+xml"},
        content=mocked_data.encode("utf-8"),
    )
    resp = TestClient(test_api_instance).simulate_request(**kwargs)
    skip_validation = False
    api_version = resp.headers["x-api-version"]
    if api_version == "1.0":
        skip_validation = True
    if resp.status_code in (202, 204):
        skip_validation = True
    if not skip_validation:
        valid, validated, errors = jsonapi_validator(resp.json)
        assert valid is True
    # TODO: this does not work on gitlab...
    # Counter().save_counters()
    # TODO: check pagination
    context.response = resp
    mocker.stopall()


@then(parsers.parse("api's response status code is {status_code:d}"))
def api_response_status_code(status_code, context):
    status = code_to_http_status(status_code)
    if status != context.response.status:
        print(context.response.json)
    assert status == context.response.status, 'API response status should be "%s", is "%s"' % (status, context.response.status)


@then(parsers.parse("size of api's response body field {field} is {num:d}"))
def api_response_body_field_size(field, num, context):
    size = len(dpath.util.get(context.response.json, field))
    assert size == int(num), f"{size} is not a {num}"


@then(parsers.parse("api's response body field {field} is sorted by {key}"))
def api_response_body_field_sorted_by(context, field, key):
    items = dpath.util.values(context.response.json, f"/data/*/attributes/{key}")
    assert items == sorted(items)


@then(parsers.parse("api's response list is sorted by {sort} {sort_order}"))
def api_response_list_sorted_by(context, sort, sort_order):
    assert sort_order in ["asc", "ascendingly", "desc", "descendingly"]
    items = context.response.json["data"]
    reverse = True if sort_order in ["desc", "descendingly"] else False

    def key(obj, field):
        if field == "id":
            return obj[field]
        elif field == "title":
            return obj["attributes"][field].lower()
        else:
            return obj["attributes"][field]

    sorted_items = sorted(items, key=lambda obj: key(obj, sort), reverse=reverse)
    assert items == sorted_items, f"{items} is not equal {sorted_items}"


@then(parsers.parse("api's response {aggregation} aggregation column {column} is {value:d}"))
def api_response_aggregation_column_is_value(aggregation, column, value, context):
    data_path = f"meta/aggregations/{aggregation}/*"
    columns_data = {row["column"]: row["value"] for row in dpath.util.values(context.response.json, data_path)}
    assert columns_data[column] == value, f'Value of column  is not a "{value}" but is "{columns_data[column]}"'


@then(parsers.parse("api's response body field {resp_body_field} is not {resp_body_value}"))
def api_response_body_field_not(resp_body_field, resp_body_value, context):
    values = [str(value) for value in dpath.util.values(context.response.json, resp_body_field)]
    assert set(values) != {resp_body_value}


@then(parsers.parse("api's response body field {field} contains {value}"))
def api_response_body_field_in(field, value, context):
    values = [x.strip() for x in value.split(",")]
    for value in values:
        assert [
            str(v) for v in dpath.util.values(context.response.json, field) if str(v) == value
        ], f"{value} not found in {context.response.json}"


@then(parsers.parse("api's response body included types contains {value}"))
def api_response_body_included_contains(value, context):
    return api_response_body_field_in("included/*/type", value, context)


@then(parsers.parse("api's response body field {field} startswith {value}"))
def api_response_body_field_startswith(field, value, context):
    values = [str(v) for v in dpath.util.values(context.response.json, field) if str(v).startswith(value)]
    assert values


@then(parsers.parse("api's response body field {resp_body_field} endswith {resp_body_value}"))
def api_response_body_field_endswith(resp_body_field, resp_body_value, context):
    values = [str(v) for v in dpath.util.values(context.response.json, resp_body_field) if str(v).endswith(resp_body_value)]
    assert values, (
        f'API response field "{resp_body_field}" should end with "{resp_body_value}'
        f' but response has values {context.response.json}"'
    )


@then(parsers.parse("api's response body field {field} does not contain {value}"))
def api_response_body_field_not_in(field, value, context):
    values = [str(v) for v in dpath.util.values(context.response.json, field) if str(v) == value]
    assert not values


@then(parsers.parse("api's response body field {resp_body_field} is {resp_body_value}"))
def api_response_body_field(resp_body_field, resp_body_value, context):
    values = [str(value) for value in dpath.util.values(context.response.json, resp_body_field)]
    assert set(values) == {resp_body_value}, "value should be {}, but is {}. Full response: {}".format(
        {resp_body_value}, set(values), context.response.json
    )


@then(parsers.parse("api's response body list {field_name} contains {field_value:d}"))
def api_response_body_list_contains(field_name, field_value, context):
    items = [list(value) for value in dpath.util.values(context.response.json, field_name)]
    for values_list in items:
        assert field_value in values_list


@then(parsers.parse("api's response body list {field_name} contains any from {values}"))
def api_response_body_list_contains_any_from(field_name, values, context):
    items = [list(value) for value in dpath.util.values(context.response.json, field_name)]
    assert len(items) > 0
    values = values.split(",")
    for values_list in items:
        assert any([val in values_list for val in values])


@then(parsers.parse("api's response body field {field} has items {items_str}"))
def api_response_body_field_has_items(field, items_str, context):
    field = dpath.util.get(context.response.json, field)
    items = json.loads(items_str)
    assert items.items() <= field.items()  # true only if `first` is a subset of `second`.


@then(parsers.parse("api's search response contains items {items_str} in results"))
def api_search_response_contains_items(items_str, context):
    results = dpath.util.values(context.response.json, "/data/*/attributes")
    items = json.loads(items_str)
    result = any([items.items() <= result.items() for result in results])
    assert result


@then(parsers.parse("api's search response objects have fields {fields_str}"))
def api_search_response_objects_have_fields(fields_str, context):
    results = dpath.util.values(context.response.json, "/data/*/attributes")
    fields = fields_str.split(",")
    for result in results:
        assert all(field in result for field in fields), "result: %s should have fields: %s" % (result, fields)


@then(parsers.parse("api's response body field {field} has fields {fields}"))
def api_response_body_field_has_fields(field, fields, context):
    item = dpath.util.get(context.response.json, field)
    for x in fields.split(","):
        assert x in item, f"{x} must be in {item}"


@then(parsers.parse("api's response body fields {field} have fields {fields}"))
def api_response_body_fields_have_fields(field, fields, context):
    items = dpath.util.values(context.response.json, field)
    for item in items:
        for key in fields.split(","):
            assert key in item, f"{key} must be in {item}"


@then(parsers.parse("api's response body field {field} has no fields {fields}"))
def api_response_body_field_has_no_fields(field, fields, context):
    item = dpath.util.get(context.response.json, field)
    for x in fields.split(","):
        assert x not in item, f"{x} cannot be in {item}"


@then(parsers.parse("api's response body has field {field}"))
def api_response_body_has_field(field, context):
    assert dpath.util.search(context.response.json, field), context.response.json


@then(parsers.parse("api's response body has no field {field}"))
def api_response_body_no_field(field, context):
    assert not dpath.util.search(context.response.json, field)


@then(parsers.parse("api's response aggregations contains fields {fields}"))
def api_response_aggregations_fields(fields, context):
    aggregations = dpath.util.get(context.response.json, "/meta/aggregations/type")
    items = fields.split(",")
    aggregated_items = [x for x in aggregations.keys()]
    for item in items:
        assert item in aggregated_items


@then(parsers.parse("api's response data contains {document_type} objects only"))
def api_response_data_contains_document_type_objects(document_type, context):
    data = dpath.util.get(context.response.json, "data")
    for item in data:
        assert item["type"] == document_type


@then(parsers.parse("api's response header {resp_header_name} is {resp_header_value}"))
def api_response_header_value_is(context, resp_header_name, resp_header_value):
    value = dpath.util.get(context.response.headers, resp_header_name)
    assert value == resp_header_value, "value should be {}, but is {}".format(resp_header_value, value)


@then(parsers.parse("api's response header {resp_header_name} contains {resp_header_value}"))
def api_response_header_value_contains(context, resp_header_name, resp_header_value):
    value = dpath.util.get(context.response.headers, resp_header_name)
    assert resp_header_value in value, "Substring {} was not found in value of header {}: {}".format(
        resp_header_value, resp_header_name, value
    )


@then(
    parsers.parse(
        "api's jsonld response body with rdf type {rdf_type} has field {field_name} with attribute {identifier}"
        " that equals {expected_value}"
    )
)
def api_dcat_response_body_specific_class_field(rdf_type, field_name, identifier, expected_value, context):
    nodes = context.response.json["@graph"]
    selected_node = None
    for node in nodes:
        if node["@type"] == rdf_type or isinstance(node["@type"], list) and rdf_type in node["@type"]:
            selected_node = node
            break

    value = selected_node[field_name]
    if isinstance(value, list):
        values = [field[identifier] for field in value]
    else:
        values = [value[identifier]]

    assert expected_value in values
