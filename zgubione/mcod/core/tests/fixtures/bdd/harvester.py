import hashlib
import json
import os
from datetime import datetime
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
import pytz
import requests_mock
from django.conf import settings
from django.db.models.query import QuerySet
from django.test import Client
from django_celery_beat.models import PeriodicTask
from pytest_bdd import given, parsers, then, when

from mcod.core.registries import factories_registry
from mcod.datasets.models import Dataset
from mcod.harvester.factories import CKANDataSourceFactory
from mcod.harvester.models import DataSource, DataSourceImport
from mcod.resources.models import Resource


@given(parsers.parse("CKAN datasource with id {obj_id:d} active"))
def active_ckan_datasource_with_id(obj_id):
    return CKANDataSourceFactory.create(pk=obj_id, status="active")


@given(parsers.parse("CKAN datasource with id {obj_id:d} inactive"))
def inactive_ckan_datasource_with_id(obj_id):
    return CKANDataSourceFactory.create(pk=obj_id, status="inactive")


@given(parsers.parse("datasource with id {obj_id:d} attribute {attr_name} is set to {attr_value}"))
def datasource_with_id_attribute_is(obj_id, attr_name, attr_value):
    attr_value = None if attr_value == "None" else attr_value
    DataSource.objects.filter(id=obj_id).update(**{attr_name: attr_value})


@then(parsers.parse("datasource with id {obj_id:d} is activated and last_activation_date is updated"))
def datasource_with_id_activation(obj_id):
    obj = DataSource.objects.get(id=obj_id)
    obj.status = "active"
    obj.save()
    assert obj.last_activation_date is not None


@then(parsers.parse("datasource with id {obj_id:d} is deactivated and last_activation_date is not updated"))
def datasource_with_id_deactivation(obj_id):
    obj = DataSource.objects.get(id=obj_id)
    assert obj.last_activation_date is None
    obj.status = "inactive"
    obj.save()
    assert obj.last_activation_date is None


@given(parsers.parse("active {datasource_type} with id {obj_id:d} for data{data_str}"))
def active_datasource_by_type_for_data(datasource_type, obj_id, data_str):
    _factory = factories_registry.get_factory(datasource_type)
    data = json.loads(data_str)
    data["status"] = "active"
    data["id"] = obj_id
    return _factory.create(**data)


@when(parsers.parse("ckan datasource with id {obj_id:d} finishes importing objects using {json_file}"))
@requests_mock.Mocker(kw="mock_request")
def datasource_finishes_import(obj_id, json_file, **kwargs):
    mock_request = kwargs["mock_request"]
    obj = DataSource.objects.get(pk=obj_id)
    example_image_path = os.path.join(settings.TEST_SAMPLES_PATH, "example.jpg")
    simple_csv_path = os.path.join(settings.TEST_SAMPLES_PATH, "simple.csv")
    with open(simple_csv_path, "rb") as tmp_file:
        mock_request.get(
            "http://mock-resource.com.pl/simple.csv",
            headers={"content-type": "application/csv"},
            content=tmp_file.read(),
        )
    mock_request.post(settings.SPARQL_UPDATE_ENDPOINT)
    ckan_data_path = os.path.join(settings.TEST_SAMPLES_PATH, json_file)
    with open(ckan_data_path, "rb") as json_resp_data:
        mock_request.get(obj.api_url, headers={"content-type": "application/json"}, content=json_resp_data.read())
    with patch("mcod.harvester.utils.retrieve_to_file") as mock_retrieve_to_file:
        mock_retrieve_to_file.return_value = example_image_path, {}
        obj.import_data()


@then(parsers.parse("ckan datasource with id {obj_id:d} created all data in db"))
def datasource_imported_resources(obj_id):
    dataset = Dataset.objects.get(source_id=obj_id)
    resources = Resource.objects.filter(dataset__source_id=obj_id).order_by("ext_ident")
    res: Resource = resources[0]
    second_res: Resource = resources[1]
    org = dataset.organization
    source_import = DataSourceImport.objects.get(datasource_id=obj_id)
    assert source_import.error_desc == ""
    assert source_import.status == "ok"
    assert source_import.datasets_count == 1
    assert source_import.datasets_created_count == 1
    assert source_import.resources_count == 2
    assert source_import.resources_created_count == 2
    assert org.title == "Wydział Środowiska"
    assert org.uuid.urn == "urn:uuid:b97080cc-858d-4763-a751-4b54bf3fb0f0"
    assert dataset.title == "Ilości odebranych odpadów z podziałem na sektory"
    assert dataset.notes == "Wartości w tonach"
    assert dataset.license_chosen == 2
    assert res.title == "Ilości odebranych odpadów z podziałem na sektory"
    assert res.ext_ident == "6db2e083-72b8-4f92-a6ab-678fc8461865"
    assert res.description == "##Sektory:"
    assert res.format == "csv"
    assert res.openness_score == 3
    assert second_res.title == "Ilości odebranych odpadów z podziałem na sektory ze spacja"
    assert second_res.ext_ident == "6db2e083-72b8-4f92-a6ab-678fc8461866"
    assert second_res.openness_score == 3


@then(parsers.parse("ckan datasource with id {obj_id:d} created all data in db with has metadata"))
def datasource_imported_resources_with_has_metadata(obj_id):
    dataset = Dataset.objects.get(source_id=obj_id)
    resources: QuerySet = Resource.objects.filter(dataset__source_id=obj_id).order_by("ext_ident")
    first_res: Resource = resources[0]
    second_res: Resource = resources[1]

    assert dataset.title == "Ilości odebranych odpadów z podziałem na sektory"
    assert dataset.notes == "Wartości w tonach"
    assert dataset.license_chosen == 2
    assert dataset.has_dynamic_data is None
    assert dataset.has_high_value_data is True
    assert dataset.has_high_value_data_from_ec_list is True
    assert dataset.has_research_data is False

    assert first_res.title == "Ilości odebranych odpadów z podziałem na sektory"
    assert first_res.ext_ident == "6db2e083-72b8-4f92-a6ab-678fc8461865"
    assert first_res.description == "##Sektory:"
    assert first_res.format == "csv"
    assert first_res.has_dynamic_data is True
    assert first_res.has_high_value_data is True
    assert first_res.has_high_value_data_from_ec_list is False
    assert first_res.has_research_data is None

    assert second_res.title == "Ilości odebranych odpadów z podziałem na sektory ze spacja"
    assert second_res.ext_ident == "6db2e083-72b8-4f92-a6ab-678fc8461866"
    assert second_res.has_dynamic_data is None
    assert second_res.has_high_value_data is None
    assert second_res.has_high_value_data_from_ec_list is None
    assert second_res.has_research_data is None


@then(parsers.parse("ckan datasource with id {obj_id:d} import not successful"))
def ckan_datasource_imported_resources_not_successful(obj_id):
    DataSourceImport.objects.get(datasource_id=obj_id)

    with pytest.raises(Dataset.DoesNotExist):
        Dataset.objects.get(source_id=obj_id)


@when(parsers.parse("xml datasource with id {obj_id:d} of version {version} finishes importing objects"))
@requests_mock.Mocker(kw="mock_request")
def xml_datasource_finishes_import(
    obj_id,
    version,
    harvester_decoded_xml_1_2_import_data,
    harvester_decoded_xml_1_4_import_data,
    harvester_decoded_xml_1_5_import_data,
    harvester_decoded_xml_1_6_import_data,
    harvester_decoded_xml_1_7_import_data,
    harvester_decoded_xml_1_8_import_data,
    harvester_decoded_xml_1_9_import_data,
    harvester_decoded_xml_1_11_import_data,
    harvester_decoded_xml_1_11_import_data_dataset_has_high_values_metadata_conflict,
    harvester_decoded_xml_1_12_import_data,
    harvester_decoded_xml_1_13_import_data,
    mocked_geocoder_responses_for_xml_import,
    **kwargs,
):
    mock_request = kwargs["mock_request"]
    obj = DataSource.objects.get(pk=obj_id)
    simple_csv_path = os.path.join(settings.TEST_SAMPLES_PATH, "simple.csv")
    with open(simple_csv_path, "rb") as tmp_file:
        mock_request.get(
            "https://mock-resource.com.pl/simple.csv",
            headers={"content-type": "application/csv"},
            content=tmp_file.read(),
        )

    dga_xls_path = os.path.join(settings.TEST_SAMPLES_PATH, "example_dga_xls_file.xls")
    with open(dga_xls_path, "rb") as tmp_file_dga_xls:
        mock_request.get(
            "https://mock-resource.com.pl/remote-dga.xls",
            headers={"content-type": "application/vnd.ms-excel"},
            content=tmp_file_dga_xls.read(),
        )

    txt_path = os.path.join(settings.TEST_SAMPLES_PATH, "example.txt")
    with open(txt_path, "rb") as txt:
        mock_request.get(
            "https://mock-resource.com.pl/example.txt",
            headers={"content-type": "text/plain"},
            content=txt.read(),
        )
    mock_request.get(
        "https://mock-resource.com.pl/json-api",
        headers={"content-type": "application/json"},
        json={"some_attr": "some_val"},
    )
    mock_request.post(settings.SPARQL_UPDATE_ENDPOINT)
    xml_data_path = os.path.join(settings.TEST_SAMPLES_PATH, "harvester", f"import_example{version}.xml")
    with open(xml_data_path, "rb") as xml_resp_data:
        xml_request_kwargs = {
            "url": obj.xml_url,
            "headers": {"content-type": "application/xml"},
            "content": xml_resp_data.read(),
        }

    mock_request.get(**xml_request_kwargs)
    md5_url = xml_request_kwargs["url"].replace(".xml", ".md5")
    mock_request.get(
        md5_url,
        content=hashlib.md5(xml_request_kwargs["content"]).hexdigest().encode("utf-8"),
    )
    mock_request.head(**xml_request_kwargs)
    xml_map = {
        "1.2": harvester_decoded_xml_1_2_import_data,
        "1.4": harvester_decoded_xml_1_4_import_data,
        "1.5": harvester_decoded_xml_1_5_import_data,
        "1.6": harvester_decoded_xml_1_6_import_data,
        "1.7": harvester_decoded_xml_1_7_import_data,
        "1.8": harvester_decoded_xml_1_8_import_data,
        "1.9": harvester_decoded_xml_1_9_import_data,
        "1.11": harvester_decoded_xml_1_11_import_data,
        "1.11_dataset_has_high_values_metadata_conflict": harvester_decoded_xml_1_11_import_data_dataset_has_high_values_metadata_conflict,  # noqa: E501
        "1.12": harvester_decoded_xml_1_12_import_data,
        "1.13": harvester_decoded_xml_1_13_import_data,
    }
    for resp in mocked_geocoder_responses_for_xml_import:
        mock_request.get(resp[0], json=resp[1])
    with patch("mcod.harvester.utils.retrieve_to_file") as mock_retrieve_to_file:
        with patch("mcod.harvester.utils.decode_xml") as mock_to_dict:
            mock_retrieve_to_file.return_value = xml_data_path, {}
            mock_to_dict.return_value = xml_map[version]
            obj.import_data()


@then(parsers.parse("xml datasource with id {obj_id:d} of version {version} created all data in db"))
def xml_datasource_imported_resources(obj_id, version):
    ver_no = int(version.split(".")[1])  # version as string ('1.4') to version number (4)
    obj = DataSourceImport.objects.get(datasource_id=obj_id)
    if ver_no < 8:
        res_count = 2
        created_res_count = 2
        res_idents = {"zasob_extId_zasob_1", "zasob_extId_zasob_2"}
        res_titles = {"ZASOB CSV LOCAL", "ZASOB csv REMOTE"}
    else:
        res_count = 4
        created_res_count = 4
        res_idents = {
            "zasob_extId_zasob_1",
            "zasob_extId_zasob_2",
            "zasob_extId_zasob_3",
            "zasob_extId_zasob_4",
        }
        res_titles = {
            "ZASOB CSV LOCAL",
            "ZASOB csv REMOTE",
            "ZASOB json API",
            "ZASOB csv REMOTE 2",
        }
    assert obj.error_desc == ""
    assert obj.status == "ok"
    assert obj.datasets_count == 1
    assert obj.datasets_created_count == 1
    assert obj.resources_count == res_count
    assert obj.resources_created_count == created_res_count
    dataset = Dataset.objects.get(source_id=obj_id)
    res = Resource.objects.filter(dataset__source_id=obj_id)
    assert dataset.ext_ident == "zbior_extId_1"
    assert dataset.title == "Zbiór danych - nowy scheme CC0 1.0"
    assert dataset.notes == "Opis w wersji PL - opis testowy do testow UAT"
    assert dataset.license_chosen == 1
    assert set(dataset.categories.values_list("code", flat=True)) == {"TRAN", "ECON"}
    assert dataset.keywords_list == [{"name": "2028_tagPL", "language": "pl"}]
    assert set(res.values_list("ext_ident", flat=True)) == res_idents
    assert set(res.values_list("title", flat=True)) == res_titles
    if ver_no == 4:  # from 1.4 version special_signs of resources are imported also.
        for resource in res.filter(ext_ident__in={"zasob_extId_zasob_1", "zasob_extId_zasob_2"}):
            assert resource.special_signs_symbols_list == ["-"]
    if ver_no >= 5:  # from 1.5 version: has_high_value_data, has_dynamic_data attrs are imported also.
        assert dataset.has_high_value_data
        assert dataset.has_dynamic_data
        assert set(res.values_list("has_dynamic_data", flat=True)) == {True, None}
        assert set(res.values_list("has_high_value_data", flat=True)) == {False, None}
    if ver_no >= 6:  # from 1.6 has_research_data is imported.
        assert dataset.has_research_data
        assert set(res.values_list("has_research_data", flat=True)) == {True, None}
    if ver_no >= 7:  # from 1.7 supplements are imported.
        assert dataset.supplements.count() == 1
        assert res.get(title="ZASOB csv REMOTE").supplements.count() == 1
    if ver_no >= 8:  # from 1.8 auto data date update meta data are imported
        warsaw_tz = pytz.timezone("Europe/Warsaw")
        third_res = res.get(ext_ident="zasob_extId_zasob_3")
        fourth_res = res.get(ext_ident="zasob_extId_zasob_4")
        assert PeriodicTask.objects.all().count() == 2
        p_task = PeriodicTask.objects.get(name=third_res.data_date_task_name)
        second_p_task = PeriodicTask.objects.get(name=fourth_res.data_date_task_name)
        assert second_p_task.crontab is not None
        assert p_task.interval is not None
        assert p_task.start_time.astimezone(warsaw_tz).date() == datetime(2021, 10, 10).date()
    if ver_no >= 9:  # from 1.9 regions are imported
        first_res = res.get(ext_ident="zasob_extId_zasob_1")
        assert first_res.all_regions.count() == 5
        assert first_res.all_regions.filter(region_id="0918123", resourceregion__is_additional=False).exists()


@then(parsers.parse("xml datasource with id {obj_id:d} of version {version} created all data in db - version xsd 1.11 and over"))
def xml_datasource_imported_resources_version_1_11_and_over(obj_id: int, version: str):
    ver_number: int = int(version.split(".")[1])  # version as string ('1.11') to version number (11)
    datasource_import: Optional[DataSourceImport] = DataSourceImport.objects.get(datasource_id=obj_id)
    dataset: Optional[Dataset] = Dataset.objects.get(source_id=obj_id)
    resources: QuerySet = Resource.objects.filter(dataset__source_id=obj_id)

    assert datasource_import.error_desc == ""
    assert datasource_import.status == "ok"
    assert datasource_import.datasets_count == 1
    assert datasource_import.datasets_created_count == 1
    assert datasource_import.resources_count == 4
    assert datasource_import.resources_created_count == 4

    if ver_number == 11:
        assert dataset.title == "Zbiór danych - z nową metadaną hasHighValueDataFromEuropeanCommissionList"
        assert dataset.notes == "Opis zbioru danych"
        assert dataset.license_chosen == 1
        assert dataset.ext_ident == "dataset_extId_ver1.11"
        assert set(resources.values_list("ext_ident", flat=True)) == {
            "dataset_extId_ver1.11_res_1",
            "dataset_extId_ver1.11_res_2",
            "dataset_extId_ver1.11_res_3",
            "dataset_extId_ver1.11_res_4",
        }

        first_resource: Optional[Resource] = resources.get(ext_ident="dataset_extId_ver1.11_res_1")
        assert first_resource.has_high_value_data_from_ec_list
        assert dataset.keywords_list == [{"name": "2028_tagPL", "language": "pl"}]
        assert set(resources.values_list("title", flat=True)) == {"zasób 1", "zasób 2", "zasób 3", "zasób 4"}

        # from 1.5 version: has_high_value_data, has_dynamic_data are imported for resource and dataset
        assert dataset.has_high_value_data
        assert not dataset.has_dynamic_data
        assert first_resource.has_dynamic_data
        assert first_resource.has_high_value_data

        # from 1.6 version: has_research_data is imported for resource and dataset
        assert dataset.has_research_data
        assert first_resource.has_research_data

        # from 1.7 version: supplements are imported for resource and dataset
        assert dataset.supplements.count() == 1
        assert first_resource.supplements.count() == 1

        # from 1.8 version: auto data date update meta data are imported
        warsaw_tz = pytz.timezone("Europe/Warsaw")
        third_resource = resources.get(ext_ident="dataset_extId_ver1.11_res_3")
        fourth_resource = resources.get(ext_ident="dataset_extId_ver1.11_res_4")
        assert PeriodicTask.objects.all().count() == 2
        p_task = PeriodicTask.objects.get(name=third_resource.data_date_task_name)
        second_p_task = PeriodicTask.objects.get(name=fourth_resource.data_date_task_name)
        assert second_p_task.crontab is not None
        assert p_task.interval is not None
        assert p_task.start_time.astimezone(warsaw_tz).date() == datetime(2021, 10, 10).date()

        # from 1.9 version: regions are imported
        assert first_resource.all_regions.count() == 5
        assert first_resource.all_regions.filter(region_id="0918123", resourceregion__is_additional=False).exists()

        # from 1.11 version: has_high_value_data_from_ec_list is imported for resource and dataset
        assert dataset.has_high_value_data_from_ec_list
        assert first_resource.has_high_value_data_from_ec_list


@then(parsers.parse("xml datasource with id {obj_id:d} import not successful"))
def xml_datasource_imported_resources_not_successful(obj_id):
    DataSourceImport.objects.get(datasource_id=obj_id)

    with pytest.raises(Dataset.DoesNotExist):
        Dataset.objects.get(source_id=obj_id)


@patch("rdflib.plugins.stores.sparqlconnector.urlopen")
def mock_sparqlconnector_requests(obj_id, harvester_dcat_data, *args):
    obj = DataSource.objects.get(pk=obj_id)
    urlopen_mock = args[0]
    mocked_response = MagicMock()
    mocked_response.read.return_value = harvester_dcat_data.serialize(format="xml", encoding="utf-8")
    mocked_response.headers = {"Content-Type": "application/rdf+xml"}
    urlopen_mock.return_value = mocked_response
    with requests_mock.Mocker() as mock_request:
        mock_request.post(settings.SPARQL_UPDATE_ENDPOINT)
        simple_csv_path = os.path.join(settings.TEST_SAMPLES_PATH, "simple.csv")
        with open(simple_csv_path, "rb") as tmp_file:
            mock_request.get(
                "http://example-uri.com/distribution/999",
                headers={"content-type": "application/csv"},
                content=tmp_file.read(),
            )
        obj.import_data()


@when(parsers.parse("dcat datasource with id {obj_id:d} finishes importing objects"))
def dcat_datasource_finishes_import(obj_id, harvester_dcat_data):
    mock_sparqlconnector_requests(obj_id, harvester_dcat_data)


@then(parsers.parse("dcat datasource with id {obj_id:d} created all data in db"))
def dcat_datasource_imported_resources(obj_id):
    source_import = DataSourceImport.objects.get(datasource_id=obj_id)
    assert source_import.error_desc == ""
    assert source_import.status == "ok"
    assert source_import.datasets_count == 1
    assert source_import.datasets_created_count == 1
    assert source_import.resources_count == 2
    assert source_import.resources_created_count == 2
    dataset = Dataset.objects.get(source_id=obj_id)
    resources = Resource.objects.filter(dataset__source_id=obj_id).order_by("-ext_ident")
    res = resources[0]
    second_res = resources[1]
    assert res.title == "Distribution title"
    assert res.description == "Some distribution description"
    assert res.ext_ident == "999"
    assert second_res.title == "Second distribution title"
    assert second_res.description == "Some other distribution description"
    assert second_res.ext_ident == "1000"
    assert dataset.title == "Dataset title"
    assert dataset.notes == "DESCRIPTION"
    assert dataset.ext_ident == "1"
    assert set(dataset.categories.values_list("code", flat=True)) == {"ECON"}
    assert {"name": "jakis tag", "language": "pl"} in dataset.keywords_list
    assert {"name": "tagggg", "language": "en"} in dataset.keywords_list


@when(parsers.parse("admin's harvester page {page_url} is requested"))
@requests_mock.Mocker(kw="mock_request")
def admin_harvester_page_is_requested(admin_context, page_url, **kwargs):
    mock_request = kwargs["mock_request"]
    client = Client()
    client.force_login(admin_context.admin.user)
    if admin_context.admin.method == "POST":
        api_url = admin_context.obj["api_url"]
        if isinstance(api_url, list):
            api_url = api_url[0]
        if "ckan" in admin_context.obj["source_type"]:
            mock_request.get(api_url, json={}, headers={"Content-Type": "application/json"})
            mock_request.head(api_url, json={}, headers={"Content-Type": "application/json"})
        response = client.post(page_url, data=getattr(admin_context, "obj", None), follow=True)
    else:
        response = client.get(page_url, follow=True)
    admin_context.response = response
