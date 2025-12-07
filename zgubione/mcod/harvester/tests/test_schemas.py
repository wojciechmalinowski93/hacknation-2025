import os
from pathlib import Path
from pydoc import locate
from typing import Optional
from xml.etree import ElementTree as et
from xml.etree.ElementTree import Element, ElementTree

import pytest
import requests_mock
import xmlschema
from django.conf import settings
from xmlschema.validators.schemas import XMLSchema

from mcod.harvester.utils import get_xml_schema_path
from mcod.lib.utils import get_file_content
from mcod.organizations.models import Organization


def test_xml_schema_deserialization(harvester_decoded_xml_1_2_data, harvester_xml_expected_data, institution):
    schema_path = settings.HARVESTER_IMPORTERS["xml"]["SCHEMA"]
    schema_class = locate(schema_path)
    schema = schema_class(many=True)
    schema.context["organization"] = institution

    from mcod.resources.link_validation import session

    adapter = requests_mock.Adapter()
    adapter.register_uri(
        "GET",
        url="https://mock-resource.com.pl/simple.csv",
        content=get_file_content("csv2jsonld.csv"),
        headers={
            "Content-Type": "text/csv",
        },
    )
    session.mount("https://mock-resource.com.pl/simple.csv", adapter)
    items = schema.load(harvester_decoded_xml_1_2_data)

    assert items == harvester_xml_expected_data


def test_ckan_schema_deserialization(harvester_ckan_data, harvester_ckan_expected_data):
    schema_path = settings.HARVESTER_IMPORTERS["ckan"]["SCHEMA"]
    schema_class = locate(schema_path)
    schema = schema_class(many=True)
    schema.context["new_institution_type"] = Organization.INSTITUTION_TYPE_STATE
    items = schema.load(harvester_ckan_data)
    item = items[0]
    orig_organization_values = item.pop("organization").values()
    orig_resources_values = item.get("resources")[0].values()
    orig_scnd_resources_values = item.pop("resources")[1].values()
    expected_organization = harvester_ckan_expected_data.pop("organization")
    expected_resources = harvester_ckan_expected_data.get("resources")[0]
    expected_scnd_resources = harvester_ckan_expected_data.pop("resources")[1]
    assert list(item.keys()) == list(harvester_ckan_expected_data.keys())
    assert list(item.values()) == list(harvester_ckan_expected_data.values())
    assert all([itm in orig_resources_values for itm in expected_resources.values()])
    assert all([itm in orig_scnd_resources_values for itm in expected_scnd_resources.values()])
    assert all([itm in orig_organization_values for itm in expected_organization.values()])
    assert len(expected_organization.values()) == len(orig_organization_values)
    assert len(expected_resources.values()) == len(orig_resources_values)


def test_dcat_schema_deserialization(harvester_dcat_data, harvester_dcat_expected_data):
    schema_path = settings.HARVESTER_IMPORTERS["dcat"]["SCHEMA"]
    schema_class = locate(schema_path)
    schema = schema_class(many=True)
    deserialized_data = schema.load(harvester_dcat_data)
    deserialized_item = deserialized_data[0]
    deserialized_item["categories"].sort()
    deserialized_item["tags"].sort(key=lambda obj: obj["lang"])
    deserialized_item["resources"].sort(key=lambda obj: obj["ext_ident"])
    harvester_dcat_expected_data["categories"].sort()
    harvester_dcat_expected_data["tags"].sort(key=lambda obj: obj["lang"])
    assert harvester_dcat_expected_data == deserialized_item


@pytest.mark.parametrize(
    "schema_version, update_frequency_value, expected_validation_success",
    [
        ("1.12", "daily", True),
        ("1.12", "weekly", True),
        ("1.12", "monthly", True),
        ("1.12", "quarterly", True),
        ("1.12", "everyHalfYear", True),
        ("1.12", "yearly", True),
        ("1.12", "irregular", False),
        ("1.12", "notPlanned", False),
        ("1.12", "notApplicable", True),
        ("1.13", "daily", True),
        ("1.13", "weekly", True),
        ("1.13", "monthly", True),
        ("1.13", "quarterly", True),
        ("1.13", "everyHalfYear", True),
        ("1.13", "yearly", True),
        ("1.13", "irregular", True),
        ("1.13", "notPlanned", True),
        ("1.13", "notApplicable", False),
    ],
)
def test_xml_schema_deserialization_dataset_update_frequency(
    schema_version: str, update_frequency_value: str, expected_validation_success: bool, tmp_path: Path
):

    # GIVEN
    # XML file for XSD schema version with different updateFrequency values and schema XSD version
    xml_file_name = f"import_example{schema_version}.xml"
    path_xml_for_xsd_version_base: str = os.path.join(settings.TEST_SAMPLES_PATH, "harvester", xml_file_name)

    tree: ElementTree = et.parse(path_xml_for_xsd_version_base)
    root: Element = tree.getroot()

    update_frequency_node: Optional[Element] = root.find(".//dataset/updateFrequency")
    assert update_frequency_node is not None, "No 'updateFrequency' node in XML tree"

    update_frequency_node.text = update_frequency_value

    path_xml_tested_file: Path = tmp_path / "tested.xml"
    tree.write(path_xml_tested_file, encoding="utf-8", xml_declaration=True)

    path_xsd_schema: str = get_xml_schema_path(schema_version)
    xml_schema: XMLSchema = xmlschema.XMLSchema(path_xsd_schema)

    # WHEN
    # call the validation of the XML file against XSD schema
    result = xml_schema.is_valid(path_xml_tested_file)

    # THEN
    assert result is expected_validation_success
