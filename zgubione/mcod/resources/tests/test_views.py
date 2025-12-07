import pytest
from falcon import HTTP_OK

from mcod import settings
from mcod.core.tests.helpers.tasks import run_on_commit_events


@pytest.mark.elasticsearch
def test_links_to_indexed_data(client14, tabular_resource):
    run_on_commit_events()
    response = client14.simulate_get(f"/resources/{tabular_resource.id}")
    assert HTTP_OK == response.status
    body = response.json
    assert "relationships" in body["data"]
    assert "tabular_data" in body["data"]["relationships"]
    assert "links" in body["data"]["relationships"]["tabular_data"]
    assert "related" in body["data"]["relationships"]["tabular_data"]["links"]
    link = body["data"]["relationships"]["tabular_data"]["links"]["related"]
    assert link == f"{settings.API_URL}/1.4/resources/{tabular_resource.id}/data"

    response = client14.simulate_get(f"/resources/?id={tabular_resource.id}")
    assert HTTP_OK == response.status
    body = response.json
    data = body["data"][0]
    assert "relationships" in data
    assert "tabular_data" in data["relationships"]
    assert "links" in data["relationships"]["tabular_data"]
    assert "related" in data["relationships"]["tabular_data"]["links"]
    link = data["relationships"]["tabular_data"]["links"]["related"]
    assert link == f"{settings.API_URL}/1.4/resources/{tabular_resource.id}/data"


@pytest.mark.elasticsearch
def test_links_to_no_data_resource(client14, no_data_resource):
    response = client14.simulate_get(f"/resources/{no_data_resource.id}")
    assert HTTP_OK == response.status
    body = response.json
    assert "relationships" in body["data"]
    assert "tabular_data" not in body["data"]["relationships"]
    assert "geo_data" not in body["data"]["relationships"]
