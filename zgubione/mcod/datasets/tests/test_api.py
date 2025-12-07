import pytest
from django.utils.translation import gettext_lazy as _
from falcon import HTTP_OK
from pytest_bdd import scenarios

from mcod.datasets.models import Dataset
from mcod.datasets.serializers import _UPDATE_FREQUENCY

scenarios(
    "features/dataset_comment.feature",
    "features/dataset_resources_list_api.feature",
    "features/dataset_details_api.feature",
    "features/dataset_resources_download_csv_api.feature",
    "features/dataset_resources_download_xml_api.feature",
    "features/dataset_licenses.feature",
    "features/dataset_showcases_list_api.feature",
    "features/dataset_bulk_download_files_api.feature",
    "features/datasets_list_api.feature",
)

scenarios("features/dataset_unified_conditions.feature")


@pytest.mark.elasticsearch
def test_dates_in_list_views_api14(dataset_with_run_events, client14):
    resp = client14.simulate_get("/datasets")
    assert HTTP_OK == resp.status
    assert dataset_with_run_events.id
    for d_name in ["created", "modified", "verified"]:
        assert d_name in resp.json["data"][0]["attributes"]


@pytest.mark.elasticsearch
def test_dates_in_detail_views_api14(dataset, client14):
    _rid = dataset.id
    resp = client14.simulate_get("/datasets/{}/".format(_rid))
    assert HTTP_OK == resp.status
    for d_name in ["created", "modified", "verified"]:
        assert d_name in resp.json["data"]["attributes"]

    assert resp.json["data"]["attributes"]["modified"] == dataset.modified.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["created"] == dataset.created.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["verified"] == dataset.created.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.elasticsearch
def test_data_date_with_resource_views_api14(dataset_with_resources, client14):
    dataset = dataset_with_resources
    resource = dataset.resources.first()
    id_ = dataset.id
    resource.revalidate()
    assert set(dataset.types) == set([r.type for r in dataset.resources.all()])

    resp = client14.simulate_get("/datasets/{}/".format(id_))
    assert HTTP_OK == resp.status
    for d_name in ["created", "modified", "verified"]:
        assert d_name in resp.json["data"]["attributes"]

    assert resp.json["data"]["attributes"]["modified"] == dataset.modified.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["created"] == dataset.created.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["verified"] == dataset.resources.last().created.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.elasticsearch
def test_dates_in_list_views_api14_in_path(dataset, resource, client14):
    resp = client14.simulate_get("/1.4/datasets/")
    assert HTTP_OK == resp.status
    assert dataset.id
    for d_name in ["created", "modified", "verified"]:
        assert d_name in resp.json["data"][0]["attributes"]


@pytest.mark.elasticsearch
def test_dates_in_detail_views_api14_in_path(dataset, client14):
    _rid = dataset.id
    resp = client14.simulate_get("/1.4/datasets/{}/".format(_rid))
    assert HTTP_OK == resp.status
    for d_name in ["created", "modified", "verified"]:
        assert d_name in resp.json["data"]["attributes"]

    assert resp.json["data"]["attributes"]["modified"] == dataset.modified.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["created"] == dataset.created.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["verified"] == dataset.verified.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json.get("jsonapi")


@pytest.mark.elasticsearch
def test_datasets_dates_in_list_views(dataset_with_run_events, client):
    resp = client.simulate_get("/datasets/")
    assert HTTP_OK == resp.status
    for d_name in ["created", "modified", "verified"]:
        assert d_name in resp.json["data"][0]["attributes"]


@pytest.mark.elasticsearch
def test_dataset_dates_in_detail_views(dataset, resource, client):
    _id = dataset.id
    resource.revalidate()
    resp = client.simulate_get("/datasets/{}/".format(_id))

    assert HTTP_OK == resp.status
    for d_name in ["created", "modified", "verified"]:
        assert d_name in resp.json["data"]["attributes"]

    ds = Dataset.objects.get(pk=dataset.id)
    assert resp.json["data"]["attributes"]["modified"] == dataset.modified.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["created"] == dataset.created.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["verified"] == ds.verified.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.elasticsearch
def test_datasets_dates_in_list_views_api_1_0_in_path(dataset_with_run_events, client):
    resp = client.simulate_get("/1.0/datasets/")
    assert HTTP_OK == resp.status
    for d_name in ["created", "modified", "verified"]:
        assert d_name in resp.json["data"][0]["attributes"]


@pytest.mark.elasticsearch
def test_dataset_dates_in_detail_views_api_1_0_in_path(dataset, resource, client):
    _id = dataset.id
    resource.revalidate()
    resp = client.simulate_get("/1.0/datasets/{}/".format(_id))

    assert HTTP_OK == resp.status
    for d_name in ["created", "modified", "verified"]:
        assert d_name in resp.json["data"]["attributes"]

    ds = Dataset.objects.get(pk=dataset.id)
    assert resp.json["data"]["attributes"]["modified"] == dataset.modified.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["created"] == dataset.created.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert resp.json["data"]["attributes"]["verified"] == ds.verified.strftime("%Y-%m-%dT%H:%M:%SZ")


@pytest.mark.elasticsearch
def test_dataset_update_frequency_in_detail_views_api_1_0(dataset, client):
    resp = client.simulate_get("/1.0/datasets/{}/".format(dataset.id))
    assert HTTP_OK == resp.status
    assert resp.json["data"]["attributes"]["update_frequency"] == _(_UPDATE_FREQUENCY[dataset.update_frequency])


@pytest.mark.elasticsearch
def test_dataset_update_frequency_in_detail_views_api_1_4(dataset, client):
    resp = client.simulate_get("/1.4/datasets/{}/".format(dataset.id))
    assert HTTP_OK == resp.status
    assert resp.json["data"]["attributes"]["update_frequency"] == _(_UPDATE_FREQUENCY[dataset.update_frequency])


@pytest.mark.elasticsearch
def test_slug_in_organization_link_datasets_list(dataset_with_run_events, client):
    resp = client.simulate_get("/1.4/datasets/")
    assert HTTP_OK == resp.status
    assert resp.json["data"][0]["relationships"]["institution"]["links"]["related"].endswith(
        f"{dataset_with_run_events.institution.id},{dataset_with_run_events.institution.slug}"
    )


@pytest.mark.elasticsearch
def test_slug_in_organization_link_dataset_details(dataset, client):
    resp = client.simulate_get(f"/1.4/datasets/{dataset.id}")
    assert HTTP_OK == resp.status
    assert resp.json["data"]["relationships"]["institution"]["links"]["related"].endswith(
        f"{dataset.institution.id},{dataset.institution.slug}"
    )


@pytest.mark.elasticsearch
def test_datasets_routes(dataset, client):
    paths = [
        "/1.4/datasets",
        f"/1.4/datasets/{dataset.id}",
        f"/1.4/datasets/{dataset.id},{dataset.slug}",
        f"/1.4/datasets/{dataset.id}/resources",
        f"/1.4/datasets/{dataset.id},{dataset.slug}/resources",
    ]

    for p in paths:
        resp = client.simulate_get(p)
        assert resp.status == HTTP_OK


@pytest.mark.elasticsearch
def test_response_datasets_list_slug_in_link(dataset_with_run_events, client14):
    resp = client14.simulate_get("/datasets/")
    assert HTTP_OK == resp.status
    assert f"{dataset_with_run_events.id},{dataset_with_run_events.slug}" in resp.json["data"][0]["links"]["self"]


@pytest.mark.elasticsearch
def test_response_dataset_details_slug_in_link(dataset, client14):
    resp = client14.simulate_get(f"/datasets/{dataset.id}")
    assert HTTP_OK == resp.status
    assert f"{dataset.id},{dataset.slug}" in resp.json["data"]["links"]["self"]


@pytest.mark.elasticsearch
def test_response_dataset_image_uri_in_details(dataset, client, small_image):
    dataset.image = small_image
    dataset.save()
    resp = client.simulate_get("/1.4/datasets/{}/".format(dataset.id))
    assert HTTP_OK == resp.status
    assert resp.json["data"]["attributes"]["image_url"] == f"/media/images/datasets/{dataset.image.name}"
