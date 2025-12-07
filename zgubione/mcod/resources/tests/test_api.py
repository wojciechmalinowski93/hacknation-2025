from typing import Any, Dict, Optional

import pytest
from falcon import HTTP_NOT_FOUND, HTTP_OK
from falcon.testing import TestClient
from openapi_core import create_spec
from openapi_core.validation.request.validators import RequestValidator
from openapi_core.validation.response.validators import ResponseValidator
from pytest_bdd import scenarios, then, when

from mcod.core.tests.helpers.openapi_wrappers import FalconOpenAPIWrapper
from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.core.utils import jsonapi_validator
from mcod.resources.factories import AggregatedDGAInfoFactory, DGAResourceFactory
from mcod.resources.models import Resource
from mcod.settings.test import API_URL


@pytest.fixture
def container():
    return {
        "request_data": {
            "method": "GET",
            "path": "",
            "headers": {"X-API-VERSION": "1.4", "Accept-Language": "pl"},
            "query": {"page": 1, "per_page": 20},
        }
    }


@when("I search in tabular data rows")
def setup_query(buzzfeed_fakenews_resource, context):
    context.api.path = "/resources/{}/data".format(buzzfeed_fakenews_resource.id)


@then("check if response is ok")
def validate_response(resource, valid_response):
    _rid = resource.id
    resp = valid_response
    data = resp.json["data"][1]
    assert data["type"] == "row"
    assert data["id"] == "d4ff4c97-5d9e-56a5-9d7c-46547879b7ae"
    assert data["meta"]["row_no"] == 2
    assert data["attributes"]["col3"] == "2,290,000.00"
    assert data["relationships"]["resource"]["data"]["id"] == str(_rid)

    assert resp.json["meta"]["count"] == 1000
    assert len(resp.json["meta"]) == 8
    assert len(resp.json["meta"]["headers_map"]) == 6
    assert "title" in resp.json["meta"]["headers_map"].values()
    assert "published_date" in resp.json["meta"]["headers_map"].values()
    assert resp.json["meta"]["headers_map"]["col4"] == "published_date"
    assert len(resp.json["meta"]["data_schema"]["fields"]) == 6
    links = resp.json["links"]
    assert len(links) == 4
    assert links["self"] == "http://api.test.mcod/resources/{}/data?page=1".format(_rid)
    assert links["first"] == "http://api.test.mcod/resources/{}/data?page=1".format(_rid)
    assert links["last"] == "http://api.test.mcod/resources/{}/data?page=50".format(_rid)
    assert links["next"] == "http://api.test.mcod/resources/{}/data?page=2".format(_rid)


scenarios(
    "features/resource_reindexing.feature",
    "features/resources_list_api.feature",
    "features/resource_list_api_other_files_not_in_res.feature",
    "features/tabular_view_test.feature",
    "features/resource_details_api.feature",
    "features/resource_comment.feature",
)


@pytest.mark.elasticsearch
def test_tabular_data_api14(buzzfeed_fakenews_resource, client14, mocker, test_api_instance):
    run_on_commit_events()
    _rid = buzzfeed_fakenews_resource.id

    resp = client14.simulate_get(f"/resources/{_rid}/data/spec/1.4")
    assert HTTP_OK == resp.status
    spec = create_spec(resp.json)

    # Test tabular data format
    req = FalconOpenAPIWrapper(
        test_api_instance,
        method="GET",
        path=f"/resources/{_rid}/data",
        headers={"X-API-VERSION": "1.4", "Accept-Language": "pl"},
    )

    validator = RequestValidator(spec)
    result = validator.validate(req)
    assert not result.errors

    validator = ResponseValidator(spec)
    result = validator.validate(req, req)
    assert not result.errors

    resp = req.request

    assert HTTP_OK == resp.status
    valid, validated_data, errors = jsonapi_validator(resp.json)

    assert valid is True
    assert len(validated_data) == 20
    assert validated_data[0]["type"] == "row"
    assert validated_data[0]["resource"]["id"] == str(_rid)
    data = resp.json["data"][1]
    assert data["type"] == "row"
    assert data["id"] == "a20713b6-2a0b-582e-b1c2-75a095bace86"
    assert data["meta"]["row_no"] == 2
    assert data["attributes"]["col3"]["val"] == "2,290,000.00"
    assert data["relationships"]["resource"]["data"]["id"] == str(_rid)

    assert resp.json["meta"]["count"] == 1000
    assert len(resp.json["meta"]) == 9
    assert len(resp.json["meta"]["headers_map"]) == 6
    assert "title" in resp.json["meta"]["headers_map"].values()
    assert "published_date" in resp.json["meta"]["headers_map"].values()
    assert resp.json["meta"]["headers_map"]["col4"] == "published_date"
    assert len(resp.json["meta"]["data_schema"]["fields"]) == 6
    links = resp.json["links"]
    assert len(links) == 3
    assert links["self"] == "http://api.test.mcod/resources/{}/data?page=1".format(_rid)
    assert links["last"] == "http://api.test.mcod/resources/{}/data?page=50".format(_rid)
    assert links["next"] == "http://api.test.mcod/resources/{}/data?page=2".format(_rid)

    # Test search
    req = FalconOpenAPIWrapper(
        test_api_instance,
        method="GET",
        path="/resources/{}/data".format(_rid),
        query={"q": "col5:Crime", "per_page": 25},
        headers={"X-API-VERSION": "1.4", "Accept-Language": "pl"},
    )

    validator = RequestValidator(spec)
    result = validator.validate(req)
    assert not result.errors

    validator = ResponseValidator(spec)
    result = validator.validate(req, req)
    assert not result.errors

    resp = req.request

    assert HTTP_OK == resp.status
    valid, validated_data, errors = jsonapi_validator(resp.json)
    assert valid is True
    assert len(validated_data) == 21
    meta = resp.json["meta"]
    assert meta["count"] == 21
    links = resp.json["links"]
    assert len(links) == 1
    assert links["self"] == "http://api.test.mcod/resources/{}/data?per_page=25&q=col5%3ACrime&page=1".format(_rid)

    req = FalconOpenAPIWrapper(
        test_api_instance,
        method="GET",
        path="/resources/{}/data".format(_rid),
        query={"q": "col1:President AND col5:Norwegian", "per_page": 5},
        headers={"X-API-VERSION": "1.4", "Accept-Language": "pl"},
    )

    validator = RequestValidator(spec)
    result = validator.validate(req)
    assert not result.errors

    validator = ResponseValidator(spec)
    result = validator.validate(req, req)
    assert not result.errors

    resp = req.request

    assert HTTP_OK == resp.status
    valid, validated_data, errors = jsonapi_validator(resp.json)
    assert valid is True
    assert len(validated_data) == 1
    assert validated_data[0]["col3"]["val"] == "4347"
    assert validated_data[0]["col5"]["val"] == "Norwegian Lawmakers"
    links = resp.json["links"]
    assert len(links) == 1
    assert "self" in links

    resp = client14.simulate_get(
        "/resources/{}/data".format(_rid),
        query_string="q=col4.date:[2018-12-01 TO *]&per_page=10&page=2",
    )
    assert HTTP_OK == resp.status
    valid, validated_data, errors = jsonapi_validator(resp.json)
    assert valid is True
    assert len(validated_data) == 10
    meta = resp.json["meta"]
    assert meta["count"] == 61
    links = resp.json["links"]
    assert len(links) == 5
    assert (
        links["first"] == "http://api.test.mcod/resources/{}/"
        "data?page=1&per_page=10&q=col4.date%3A%5B2018"
        "-12-01%20TO%20%2A%5D".format(_rid)
    )
    assert (
        links["next"] == "http://api.test.mcod/resources/{}/"
        "data?page=3&per_page=10&q=col4.date%3A%5B2018"
        "-12-01%20TO%20%2A%5D".format(_rid)
    )
    assert (
        links["prev"] == "http://api.test.mcod/resources/{}/"
        "data?page=1&per_page=10&q=col4.date%3A%5B2018"
        "-12-01%20TO%20%2A%5D".format(_rid)
    )
    assert (
        links["last"] == "http://api.test.mcod/resources/{}/"
        "data?page=7&per_page=10&q=col4.date%3A%5B2018"
        "-12-01%20TO%20%2A%5D".format(_rid)
    )
    assert (
        links["self"] == "http://api.test.mcod/resources/{}/"
        "data?page=2&per_page=10&q=col4.date%3A%5B2018"
        "-12-01%20TO%20%2A%5D".format(_rid)
    )

    row_id = validated_data[0]["id"]
    # Test single row
    req = FalconOpenAPIWrapper(
        test_api_instance,
        method="GET",
        path="/resources/{}/data/{}".format(_rid, row_id),
        path_params={"id": row_id},
        path_pattern="/resources/%s/data/{id}" % _rid,
        headers={"X-API-VERSION": "1.4", "Accept-Language": "pl"},
    )

    validator = RequestValidator(spec)
    result = validator.validate(req)
    assert not result.errors

    validator = ResponseValidator(spec)
    result = validator.validate(req, req)
    assert not result.errors

    resp = req.request

    assert HTTP_OK == resp.status
    valid, validated_data, errors = jsonapi_validator(resp.json)
    assert valid is True
    assert len(validated_data) == 10
    assert validated_data["col1"]["val"] == "Mums across Britain preparing to strum one off over CBeebies Bedtime Story tonight"
    assert validated_data["resource"]["id"] == str(_rid)
    data = resp.json["data"]
    assert data["type"] == "row"
    assert data["meta"]["row_no"] == 357
    assert data["relationships"]["resource"]["data"]["id"] == str(_rid)
    meta = resp.json["meta"]
    assert len(meta) == 7
    assert len(meta["headers_map"]) == 6
    assert "title" in meta["headers_map"].values()
    assert "published_date" in meta["headers_map"].values()
    assert meta["headers_map"]["col4"] == "published_date"
    assert len(meta["data_schema"]["fields"]) == 6

    links = resp.json["links"]
    assert len(links) == 1
    assert links["self"] == "http://api.test.mcod/resources/{}/" "data/{}".format(_rid, row_id)


@pytest.mark.elasticsearch
def test_dates_in_detail_views_api14(buzzfeed_fakenews_resource, client14):
    _rid = buzzfeed_fakenews_resource.id
    resp = client14.simulate_get("/resources/{}/".format(_rid))
    assert HTTP_OK == resp.status
    for d_name in ["created", "modified", "verified", "data_date"]:
        assert d_name in resp.json["data"]["attributes"]

    rs = Resource.objects.get(pk=buzzfeed_fakenews_resource.id)

    assert resp.json["data"]["attributes"]["modified"] == rs.modified.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["created"] == rs.created.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["verified"] == rs.verified.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["data_date"] == rs.data_date.strftime("%Y-%m-%d")


@pytest.mark.elasticsearch
def test_dates_in_detail_views(buzzfeed_fakenews_resource, client):
    _rid = buzzfeed_fakenews_resource.id

    assert buzzfeed_fakenews_resource.data_date is not None
    resp = client.simulate_get("/resources/{}/".format(_rid))

    assert HTTP_OK == resp.status
    for d_name in ["created", "modified", "verified"]:
        assert d_name in resp.json["data"]["attributes"]

    rs = Resource.objects.get(pk=buzzfeed_fakenews_resource.id)

    assert resp.json["data"]["attributes"]["modified"] == rs.modified.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["created"] == rs.created.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["verified"] == rs.verified.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["data_date"] == rs.data_date.strftime("%Y-%m-%d")


def test_remote_file_download_redirection(remote_file_resource, client):
    response = client.simulate_get(f"/resources/{remote_file_resource.id}/file")
    assert response.headers["location"].startswith("http://127.0.0.1")


def test_local_file_download_redirection(local_file_resource, client):
    response = client.simulate_get(f"/resources/{local_file_resource.id}/file")
    assert response.headers["location"].startswith(API_URL)


@pytest.mark.elasticsearch
@pytest.mark.feat_dga
@pytest.mark.parametrize(
    "contains_protected_data",
    (
        True,
        False,
    ),
)
def test_response_dga_flag_in_details(local_file_resource: Resource, client: TestClient, contains_protected_data: bool):
    local_file_resource.contains_protected_data = contains_protected_data
    local_file_resource.save()
    resp = client.simulate_get(f"/resources/{local_file_resource.id}/")
    assert HTTP_OK == resp.status, resp.json
    assert resp.json["data"]["attributes"]["contains_protected_data"] == contains_protected_data


@pytest.mark.feat_dga
@pytest.mark.parametrize(
    "dga_info_params, status_code",
    [
        (dict(views_count=100, downloads_count=50), HTTP_OK),
        (dict(views_count=100, downloads_count=50, resource=None), HTTP_NOT_FOUND),
        (None, HTTP_NOT_FOUND),
    ],
)
def test_api_aggregated_dga_info(client: TestClient, dga_info_params: Optional[Dict[str, Any]], status_code: str):

    if dga_info_params is not None:
        AggregatedDGAInfoFactory.create(**dga_info_params)

    resp = client.simulate_get("/dga-aggregated/")
    assert status_code == resp.status, resp.json


@pytest.mark.feat_dga
@pytest.mark.parametrize(
    "resource_params, status_code",
    [
        (dict(is_removed=True), HTTP_NOT_FOUND),
        (dict(is_removed=False), HTTP_OK),
        (dict(status="draft"), HTTP_NOT_FOUND),
        (dict(status="published"), HTTP_OK),
    ],
)
def test_api_aggregated_dga_info_resource_removed_draft(client: TestClient, resource_params: Dict[str, Any], status_code: str):
    resource: Resource = DGAResourceFactory.create(**resource_params)
    AggregatedDGAInfoFactory.create(resource=resource)

    resp = client.simulate_get("/dga-aggregated/")
    assert status_code == resp.status, resp.json
