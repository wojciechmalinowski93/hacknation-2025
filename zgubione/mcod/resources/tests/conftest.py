import pytest  # noqa
from django.core.files import File  # noqa
from django.test import Client  # noqa
from pytest_bdd import given, parsers, then  # noqa

from mcod.core.tests.fixtures import *  # noqa
from mcod.core.tests.fixtures import requests_mock
from mcod.core.tests.fixtures.bdd.common import prepare_file
from mcod.datasets.factories import DatasetFactory
from mcod.resources.models import Resource, ResourceFile
from mcod.tags.factories import TagFactory


@pytest.fixture
def tabular_resource(buzzfeed_fakenews_resource):
    buzzfeed_fakenews_resource = Resource.objects.get(pk=buzzfeed_fakenews_resource.pk)
    return buzzfeed_fakenews_resource


@given("I have buzzfeed resource with tabular data")
def create_tabular_resource(tabular_resource):
    return tabular_resource


@given("I have resource with date and datetime")
def tabular_date_resource(resource_with_date_and_datetime):
    return resource_with_date_and_datetime


@then(parsers.parse("items count should be equal to {items_count:d}"))
def valid_items_count(context, tabular_resource, items_count):
    meta = context.response.json["meta"]
    assert meta["count"] == items_count


@pytest.fixture
def table_resource_with_invalid_schema(dataset):
    resource = Resource()
    resource.url = "http://smth.smwhere.com"
    resource.title = "File resource name"
    resource.type = "file"
    resource.format = "XLSX"
    resource.file = File(open(prepare_file("wrong_schema_table.xlsx"), "rb"))
    resource.file.open("rb")
    resource.dataset = dataset
    resource.save()
    return resource


@pytest.fixture
def no_data_resource():
    dataset = DatasetFactory.create()
    TagFactory.create_batch(2, datasets=(dataset,))
    resource = Resource()
    resource.title = "No data resource"
    resource.type = "file"
    resource.format = "JPG"
    resource.dataset = dataset
    resource.save()
    ResourceFile.objects.create(
        file=File(open(prepare_file("buzzfeed-logo.jpg"), "rb")),
        is_main=True,
        resource=resource,
        format="JPG",
    )
    resource = Resource.objects.get(pk=resource.pk)
    return resource


@then(parsers.parse("all list items should be of type {item_type}"))
def valid_items_type(context, item_type):
    for item in context.response.json["data"]:
        assert item["type"] == item_type


@given(parsers.parse("resource is created for link {link} with {media_type} content"))
def create_resource_for_link(
    admin_context,
    admin,
    link,
    media_type,
    buzzfeed_dataset,
    document_docx_pack,
    example_xls_file,
    file_xml,
    file_json,
    multi_file_zip_pack,
):
    request_params = {
        "html": {
            "content": b"<html>test</html>",
            "headers": {"Content-Type": "text/html"},
        },
        "json": {"body": file_json},
        "zip": {"body": multi_file_zip_pack},
        "xls": {"body": example_xls_file},
        "xml": {"body": file_xml},
    }
    with requests_mock.mock() as m:
        params = request_params.get(media_type)
        m.get(link, **params)
        data = {
            "switcher": "link",
            "file": "",
            "link": link,
            "title": "Test resource",
            "description": "description...",
            "data_date": "02.07.2019",
            "status": "published",
            "Resource_file_tasks-TOTAL_FORMS": 3,
            "Resource_file_tasks-INITIAL_FORMS": 0,
            "Resource_file_tasks-MIN_NUM_FORMS": 0,
            "Resource_file_tasks-MAX_NUM_FORMS": 1000,
            "Resource_data_tasks-TOTAL_FORMS": 3,
            "Resource_data_tasks-INITIAL_FORMS": 0,
            "Resource_data_tasks-MIN_NUM_FORMS": 0,
            "Resource_data_tasks-MAX_NUM_FORMS": 1000,
            "Resource_link_tasks-TOTAL_FORMS": 3,
            "Resource_link_tasks-INITIAL_FORMS": 0,
            "Resource_link_tasks-MIN_NUM_FORMS": 0,
            "Resource_link_tasks-MAX_NUM_FORMS": 1000,
            "dataset": buzzfeed_dataset.id,
        }
        client = Client()
        client.force_login(admin)
        response = client.post("/resources/resource/add/", data=data, follow=True)
        admin_context.response = response
