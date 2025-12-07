import datetime
import json
import os
from collections import OrderedDict
from typing import List

import pytest
import pytz
from django.conf import settings
from rdflib import RDF, XSD, ConjunctiveGraph, Literal, URIRef

import mcod.core.api.rdf.namespaces as ns
from mcod.core.api.rdf.profiles.dcat_ap import VOCABULARIES
from mcod.harvester.utils import get_xml_as_dict


@pytest.fixture
def harvester_decoded_xml_1_2_data(harvester_decoded_xml_1_2_import_data):
    return list(harvester_decoded_xml_1_2_import_data["dataset"])


def get_harvested_xml_as_dict(version):
    full_path = os.path.join(settings.TEST_SAMPLES_PATH, "harvester", f"import_example{version}.xml")
    with open(full_path, "r") as xml_file:
        data = get_xml_as_dict(xml_file, version)
    return data


@pytest.fixture
def harvester_decoded_xml_1_2_import_data():
    return get_harvested_xml_as_dict("1.2")


@pytest.fixture
def harvester_decoded_xml_1_4_import_data():
    return get_harvested_xml_as_dict("1.4")


@pytest.fixture
def harvester_decoded_xml_1_5_import_data():
    return get_harvested_xml_as_dict("1.5")


@pytest.fixture
def harvester_decoded_xml_1_6_import_data():
    return get_harvested_xml_as_dict("1.6")


@pytest.fixture
def harvester_decoded_xml_1_7_import_data():
    return get_harvested_xml_as_dict("1.7")


@pytest.fixture
def harvester_decoded_xml_1_8_import_data():
    return get_harvested_xml_as_dict("1.8")


@pytest.fixture
def harvester_decoded_xml_1_9_import_data():
    return get_harvested_xml_as_dict("1.9")


@pytest.fixture
def harvester_decoded_xml_1_11_import_data():
    return get_harvested_xml_as_dict("1.11")


@pytest.fixture
def harvester_decoded_xml_1_11_import_data_dataset_has_high_values_metadata_conflict():
    return get_harvested_xml_as_dict("1.11_dataset_has_high_values_metadata_conflict")


@pytest.fixture
def harvester_decoded_xml_1_12_import_data():
    return get_harvested_xml_as_dict("1.12")


@pytest.fixture
def harvester_decoded_xml_1_13_import_data():
    return get_harvested_xml_as_dict("1.13")


@pytest.fixture
def harvester_xml_expected_data():
    data = [
        OrderedDict(
            [
                ("ext_ident", "zbior_extId_1"),
                ("status", "published"),
                ("title_pl", "Zbiór danych - nowy scheme CC0 1.0"),
                ("title_en", "Zbiór danych - Testy nowych tagów i kategorii - EN"),
                ("notes_pl", "Opis w wersji PL - opis testowy do testow UAT"),
                ("notes_en", "ENGLISH DATASET DESCRIPTION - UAT PHASE TEST"),
                ("url", "https://www.youtube.com/"),
                ("update_frequency", "monthly"),
                ("license_chosen", 1),
                ("license_condition_db_or_copyrighted", "Warunek wymagany"),
                ("license_condition_modification", False),
                ("license_condition_personal_data", None),
                ("license_condition_responsibilities", None),
                ("license_condition_source", False),
                ("modified", datetime.datetime(2021, 1, 1, 0, 0, tzinfo=pytz.utc)),
                ("categories", ["TRAN", "ECON"]),
                (
                    "resources",
                    [
                        OrderedDict(
                            [
                                ("ext_ident", "zasob_extId_zasob_1"),
                                ("status", "published"),
                                ("link", "https://mock-resource.com.pl/simple.csv"),
                                ("title_pl", "ZASOB csv REMOTE"),
                                ("title_en", "ENGLISH TITLE - RESOURCE 1"),
                                (
                                    "description_pl",
                                    "Opis zasobu opublikowane z XMLA - aktualizacja",
                                ),
                                (
                                    "description_en",
                                    "English description of first resource",
                                ),
                                ("availability", "remote"),
                                ("data_date", datetime.date(2021, 10, 10)),
                                (
                                    "modified",
                                    datetime.datetime(2020, 12, 8, 0, 0, tzinfo=pytz.utc),
                                ),
                                ("has_dynamic_data", None),
                                ("has_high_value_data", None),
                                ("has_high_value_data_from_ec_list", None),
                                ("has_research_data", None),
                                ("contains_protected_data", False),
                            ]
                        ),
                        OrderedDict(
                            [
                                ("ext_ident", "zasob_extId_zasob_2"),
                                ("status", "published"),
                                ("link", "https://mock-resource.com.pl/simple.csv"),
                                ("title_pl", "ZASOB CSV LOCAL"),
                                ("title_en", "ENGLISH TITLE - RESOURCE 2"),
                                ("description_pl", "Opis zasobu opublikowane z XMLA"),
                                (
                                    "description_en",
                                    "English description of second resource",
                                ),
                                ("availability", "local"),
                                ("data_date", datetime.date(2020, 10, 10)),
                                (
                                    "modified",
                                    datetime.datetime(2020, 1, 1, 0, 0, tzinfo=pytz.utc),
                                ),
                                ("has_dynamic_data", None),
                                ("has_high_value_data", None),
                                ("has_high_value_data_from_ec_list", None),
                                ("has_research_data", None),
                                ("contains_protected_data", False),
                            ]
                        ),
                    ],
                ),
                ("tags", [OrderedDict([("lang", "pl"), ("name", "2028_tagPL")])]),
                ("has_dynamic_data", None),
                ("has_high_value_data", None),
                ("has_high_value_data_from_ec_list", None),
                ("has_research_data", None),
            ]
        )
    ]
    return data


@pytest.fixture
def harvester_ckan_data():
    full_path = os.path.join(settings.TEST_SAMPLES_PATH, "harvester_ckan_import_example.json")
    with open(full_path, "r") as json_file:
        data = json.load(json_file)
    return data["result"]


@pytest.fixture
def harvester_ckan_expected_data():
    local_timezone = pytz.timezone("Europe/Warsaw")
    return OrderedDict(
        [
            ("license_id", "cc-by"),
            (
                "created",
                datetime.datetime(2020, 5, 27, 15, 44, 27, 733583).astimezone(local_timezone),
            ),
            (
                "modified",
                datetime.datetime(2021, 4, 15, 8, 30, 11, 613188).astimezone(local_timezone),
            ),
            ("slug", "ilosci-odebranych-odpadow-z-podzialem-na-sektory"),
            ("notes", "Wartości w tonach"),
            ("ext_ident", "512cb875-6c54-482f-b11e-69d8c7989fc8"),
            (
                "organization",
                OrderedDict(
                    [
                        ("description", ""),
                        ("title", "Wydział Środowiska"),
                        ("slug", "wydzial-srodowiska"),
                        (
                            "created",
                            datetime.datetime(2020, 5, 27, 17, 41, 22, 430168).astimezone(local_timezone),
                        ),
                        ("uuid", "b97080cc-858d-4763-a751-4b54bf3fb0f0"),
                        (
                            "image_name",
                            "http://otwartedane.gdynia.pl/portal/img/c/gdynia3.png",
                        ),
                    ]
                ),
            ),
            (
                "resources",
                [
                    OrderedDict(
                        [
                            (
                                "title",
                                "Ilości odebranych odpadów z podziałem na sektory",
                            ),
                            ("format", "csv"),
                            (
                                "modified",
                                datetime.datetime(2021, 4, 15, 8, 30, 11, 533597).astimezone(local_timezone),
                            ),
                            (
                                "created",
                                datetime.datetime(2020, 5, 27, 15, 44, 38, 387593).astimezone(local_timezone),
                            ),
                            ("ext_ident", "6db2e083-72b8-4f92-a6ab-678fc8461865"),
                            ("link", "https://mock-resource.com.pl/simple.csv"),
                            ("description", "##Sektory:"),
                            ("has_dynamic_data", None),
                            ("has_high_value_data", None),
                            ("has_high_value_data_from_ec_list", None),
                            ("has_research_data", None),
                            ("contains_protected_data", False),
                        ]
                    ),
                    OrderedDict(
                        [
                            (
                                "title",
                                "Ilości odebranych odpadów z podziałem na sektory ze spacja",
                            ),
                            ("format", "csv"),
                            (
                                "modified",
                                datetime.datetime(2021, 4, 15, 8, 30, 11, 533597).astimezone(local_timezone),
                            ),
                            (
                                "created",
                                datetime.datetime(2020, 5, 27, 15, 44, 38, 387593).astimezone(local_timezone),
                            ),
                            ("ext_ident", "6db2e083-72b8-4f92-a6ab-678fc8461866"),
                            ("link", "https://mock-resource.com.pl/simple.csv"),
                            ("description", "##Sektory:"),
                            ("has_dynamic_data", None),
                            ("has_high_value_data", None),
                            ("has_high_value_data_from_ec_list", None),
                            ("has_research_data", None),
                            ("contains_protected_data", False),
                        ]
                    ),
                ],
            ),
            ("tags", []),
            ("title", "Ilości odebranych odpadów z podziałem na sektory"),
            ("has_dynamic_data", None),
            ("has_high_value_data", None),
            ("has_high_value_data_from_ec_list", None),
            ("has_research_data", None),
        ]
    )


def get_example_triple_data():
    example_base_uri = "https://example-uri.com"
    resource_uri = f"{example_base_uri}/distribution/999"
    second_resource_uri = f"{example_base_uri}/distribution/1000"
    resource_ref = URIRef(resource_uri)
    second_resource_ref = URIRef(second_resource_uri)
    vocab = VOCABULARIES
    created = datetime.datetime(2021, 1, 1, 12, 0, 0, 0, tzinfo=pytz.utc)
    modified = datetime.datetime(2021, 1, 1, 13, 0, 0, 0, tzinfo=pytz.utc)
    dataset_uri = f"{example_base_uri}/dataset/1"
    dataset_ref = URIRef(dataset_uri)
    return [
        # Dataset
        (dataset_ref, RDF.type, ns.DCAT.Dataset),
        (dataset_ref, ns.DCT.identifier, Literal("1")),
        (dataset_ref, ns.DCT.title, Literal("Dataset title")),
        (dataset_ref, ns.DCT.description, Literal("DESCRIPTION")),
        (dataset_ref, ns.DCT.issued, Literal(created, datatype=XSD.dateTime)),
        (dataset_ref, ns.DCT.modified, Literal(modified, datatype=XSD.dateTime)),
        (dataset_ref, ns.DCAT.theme, URIRef(f'{vocab["theme"]}GOV')),
        (dataset_ref, ns.DCAT.theme, URIRef(f'{vocab["theme"]}ECON')),
        (
            dataset_ref,
            ns.DCT.accrualPeriodicity,
            URIRef(f'{vocab["frequency"]}MONTHLY'),
        ),
        (dataset_ref, ns.DCAT.keyword, Literal("jakis tag", lang="pl")),
        (dataset_ref, ns.DCAT.keyword, Literal("tagggg", lang="en")),
        (dataset_ref, ns.DCAT.distribution, resource_ref),
        (dataset_ref, ns.DCAT.distribution, second_resource_ref),
        # Distribution
        (resource_ref, RDF.type, ns.DCAT.Distribution),
        (resource_ref, ns.DCT.identifier, Literal("999")),
        (resource_ref, ns.DCT.title, Literal("Distribution title")),
        (resource_ref, ns.DCT.description, Literal("Some distribution description")),
        (resource_ref, ns.DCT.issued, Literal(created, datatype=XSD.dateTime)),
        (resource_ref, ns.DCT.modified, Literal(modified, datatype=XSD.dateTime)),
        (resource_ref, ns.DCT["format"], URIRef(f'{vocab["file-type"]}xlsx')),
        (resource_ref, ns.DCAT.accessURL, resource_ref),
        (resource_ref, ns.DCT.license, Literal("CC_BY_SA_4.0")),
        # 2nd Distribution
        (second_resource_ref, RDF.type, ns.DCAT.Distribution),
        (second_resource_ref, ns.DCT.identifier, Literal("1000")),
        (
            second_resource_ref,
            ns.DCT.title,
            Literal("    Second distribution title      "),
        ),
        (
            second_resource_ref,
            ns.DCT.description,
            Literal("Some other distribution description"),
        ),
        (second_resource_ref, ns.DCT.issued, Literal(created, datatype=XSD.dateTime)),
        (
            second_resource_ref,
            ns.DCT.modified,
            Literal(modified, datatype=XSD.dateTime),
        ),
        (second_resource_ref, ns.DCT["format"], URIRef(f'{vocab["file-type"]}xlsx')),
        (second_resource_ref, ns.DCAT.accessURL, second_resource_ref),
        (second_resource_ref, ns.DCT.license, Literal("CC_BY_SA_4.0")),
    ]


@pytest.fixture
def harvester_dcat_data():
    graph = ConjunctiveGraph()
    example_triples = get_example_triple_data()
    for triple in example_triples:
        graph.add(triple)
    return graph


@pytest.fixture
def harvester_dcat_expected_data():
    return OrderedDict(
        [
            ("ext_ident", "1"),
            ("title_pl", "Dataset title"),
            ("title_en", None),
            ("notes_pl", "DESCRIPTION"),
            ("notes_en", None),
            ("created", datetime.datetime(2021, 1, 1, 12, 0, tzinfo=pytz.utc)),
            ("modified", datetime.datetime(2021, 1, 1, 13, 0, tzinfo=pytz.utc)),
            (
                "tags",
                [
                    OrderedDict([("name", "jakis tag"), ("lang", "pl")]),
                    OrderedDict([("name", "tagggg"), ("lang", "en")]),
                ],
            ),
            (
                "resources",
                [
                    OrderedDict(
                        [
                            ("ext_ident", "1000"),
                            ("title_pl", "Second distribution title"),
                            ("title_en", None),
                            ("description_pl", "Some other distribution description"),
                            ("description_en", None),
                            (
                                "created",
                                datetime.datetime(2021, 1, 1, 12, 0, tzinfo=pytz.utc),
                            ),
                            (
                                "modified",
                                datetime.datetime(2021, 1, 1, 13, 0, tzinfo=pytz.utc),
                            ),
                            ("link", "https://example-uri.com/distribution/1000"),
                            ("format", "xlsx"),
                            ("file_mimetype", None),
                        ]
                    ),
                    OrderedDict(
                        [
                            ("ext_ident", "999"),
                            ("title_pl", "Distribution title"),
                            ("title_en", None),
                            ("description_pl", "Some distribution description"),
                            ("description_en", None),
                            (
                                "created",
                                datetime.datetime(2021, 1, 1, 12, 0, tzinfo=pytz.utc),
                            ),
                            (
                                "modified",
                                datetime.datetime(2021, 1, 1, 13, 0, tzinfo=pytz.utc),
                            ),
                            ("link", "https://example-uri.com/distribution/999"),
                            ("format", "xlsx"),
                            ("file_mimetype", None),
                        ]
                    ),
                ],
            ),
            ("categories", ["GOV", "ECON"]),
            ("update_frequency", None),
            ("license_chosen", "CC_BY_SA_4.0"),
        ]
    )


@pytest.fixture
def harvester_ckan_data_with_no_resource_format() -> List[dict]:
    return [
        {
            "id": "10000000-202b-402d-92a5-445d8ba6fd7z",
            "title": "MM - Dataset Title 2.1",
            "license_id": "cc-by",
            "organization": {"title": "MM Organization", "image_url": "some_image.png"},
            "name": "some_name",
            "resources": [
                {
                    "id": "10000001-mmmm-402d-92a5-445d8ba6fd7a",
                    "name": "MM - Resource Title 2.1",
                    "contains_protected_data": False,
                    "url": "https://mock-endpoint.local",
                }
            ],
        }
    ]
