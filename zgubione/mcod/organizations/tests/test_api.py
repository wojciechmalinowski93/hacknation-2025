import pytest
from falcon import HTTP_OK
from pytest_bdd import scenarios

scenarios(
    "features/organization_datasets_list_api.feature",
    "features/organizations_list_api.feature",
    "features/organization_remove_api.feature",
)


@pytest.mark.elasticsearch
def test_response_institutions_list_slug_in_link(institution, client14):
    resp = client14.simulate_get("/institutions/")
    assert HTTP_OK == resp.status
    assert f"{institution.id},{institution.slug}" in resp.json["data"][0]["links"]["self"]


@pytest.mark.elasticsearch
def test_response_institutions_details_slug_in_link(institution, client14):
    resp = client14.simulate_get(f"/institutions/{institution.id}")
    assert HTTP_OK == resp.status
    assert f"{institution.id},{institution.slug}" in resp.json["data"]["links"]["self"]


@pytest.mark.elasticsearch
def test_routes_id_and_slug_in_link_institution_details(institution, client14):
    resp = client14.simulate_get(f"/institutions/{institution.id},{institution.slug}")
    assert HTTP_OK == resp.status
    assert "institution" == resp.json["data"]["type"]


@pytest.mark.elasticsearch
def test_routes_id_without_slug_in_link_institution_details(institution, client14):
    resp = client14.simulate_get(f"/institutions/{institution.id}")
    assert HTTP_OK == resp.status
    assert "institution" == resp.json["data"]["type"]


@pytest.mark.elasticsearch
def test_routes_id_and_slug_in_link_institution_datasets_list(institution_with_datasets, client14):
    inst = institution_with_datasets
    resp = client14.simulate_get(f"/institutions/{inst.id},{inst.slug}/datasets")
    assert HTTP_OK == resp.status
    assert "dataset" == resp.json["data"][0]["type"]


@pytest.mark.elasticsearch
def test_routes_id_without_slug_in_link_institution_datasets_list(institution_with_datasets, client14):
    inst = institution_with_datasets
    resp = client14.simulate_get(f"/institutions/{inst.id}/datasets")
    assert HTTP_OK == resp.status
    assert "dataset" == resp.json["data"][0]["type"]


@pytest.mark.elasticsearch
def test_response_electronic_delivery_address_in_institution_detail(institution, client14):
    inst_id = institution.id
    resp = client14.simulate_get(f"/institutions/{inst_id}")
    assert HTTP_OK == resp.status
    assert "electronic_delivery_address" in resp.json["data"]["attributes"]
