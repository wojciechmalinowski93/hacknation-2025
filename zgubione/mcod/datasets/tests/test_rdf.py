import hashlib
import io

import pytest
from falcon import HTTP_BAD_REQUEST, HTTP_OK
from pyshacl import validate as shacl_validate
from pytest_bdd import scenarios
from rdflib import SH, XSD, BNode, Literal, URIRef

import mcod.core.api.rdf.namespaces as ns
from mcod import settings
from mcod.core.api.rdf.profiles.common import CATALOG_URL
from mcod.core.api.rdf.profiles.dcat_ap import VOCABULARIES as DCAT_AP_VOCABULARIES
from mcod.core.api.rdf.profiles.dcat_ap_pl import VOCABULARIES as DCAT_AP_PL_VOCABULARIES
from mcod.core.api.rdf.vocabs.openness_score import OpennessScoreVocab
from mcod.datasets.serializers import UPDATE_FREQUENCY_TO_DCAT
from mcod.lib.extended_graph import ExtendedGraph

scenarios("features/dataset_rdf.feature")
scenarios("features/dataset_sparql.feature")


@pytest.mark.elasticsearch
def test_catalog_rdf_in_default_profile(dataset_with_supplements_plus_resource_with_supplements, client14, constance_config):
    dataset = dataset_with_supplements_plus_resource_with_supplements
    response = client14.simulate_get("/catalog.rdf")
    expected_rdf = get_dataset_dcat_ap_expected_rdf(dataset, config=constance_config, catalog=True)
    assert expected_rdf == response.text
    assert HTTP_OK == response.status
    assert is_dcat_ap_conformant(response.text, ignore_warnings=True)


@pytest.mark.elasticsearch
def test_catalog_rdf_in_dcat_ap_profile(dataset_with_supplements_plus_resource_with_supplements, client14, constance_config):
    dataset = dataset_with_supplements_plus_resource_with_supplements
    response = client14.simulate_get("/catalog.rdf?profile=dcat_ap")
    expected_rdf = get_dataset_dcat_ap_expected_rdf(dataset, catalog=True, config=constance_config)
    assert expected_rdf == response.text
    assert HTTP_OK == response.status
    assert is_dcat_ap_conformant(response.text, ignore_warnings=True)


@pytest.mark.elasticsearch
def test_catalog_rdf_in_dcat_ap_pl_profile(dataset_with_resource_with_special_signs, client14, constance_config):
    dataset = dataset_with_resource_with_special_signs
    response = client14.simulate_get("/catalog.rdf?profile=dcat_ap_pl")
    expected_rdf = get_dataset_dcat_ap_pl_expected_rdf(dataset, catalog=True, config=constance_config)
    print("response.text", response.text)
    assert expected_rdf == response.text
    assert HTTP_OK == response.status
    assert is_dcat_ap_conformant(response.text, ignore_warnings=True)


@pytest.mark.elasticsearch
def test_catalog_rdf_in_schemaorg_profile(dataset_with_resource, client14, constance_config):
    dataset = dataset_with_resource
    response = client14.simulate_get("/catalog.rdf?profile=schemaorg")
    expected_rdf = get_dataset_schemaorg_expected_rdf(dataset, catalog=True, config=constance_config)
    print()
    print(expected_rdf)
    print("-" * 30)
    print(response.text)
    assert expected_rdf == response.text
    assert HTTP_OK == response.status


@pytest.mark.elasticsearch
def test_catalog_rdf_in_unsupported_profile(dataset_with_resource, client14, constance_config):
    response = client14.simulate_get("/catalog.rdf?profile=unsupported")
    assert HTTP_BAD_REQUEST == response.status


@pytest.mark.elasticsearch
def test_dataset_rdf_in_default_profile(dataset_with_supplements_plus_resource_with_supplements, client14, constance_config):
    dataset = dataset_with_supplements_plus_resource_with_supplements
    response = client14.simulate_get(f"/catalog/dataset/{dataset.id}.rdf")
    expected_rdf = get_dataset_dcat_ap_expected_rdf(dataset, config=constance_config)
    assert expected_rdf == response.text
    assert HTTP_OK == response.status
    assert is_dcat_ap_conformant(expected_rdf, ignore_warnings=True)


@pytest.mark.elasticsearch
def test_dataset_rdf_in_dcat_ap_profile(dataset_with_supplements_plus_resource_with_supplements, client14, constance_config):
    dataset = dataset_with_supplements_plus_resource_with_supplements
    response = client14.simulate_get(f"/catalog/dataset/{dataset.id}.rdf?profile=dcat_ap")
    expected_rdf = get_dataset_dcat_ap_expected_rdf(dataset, config=constance_config)
    assert expected_rdf == response.text
    assert HTTP_OK == response.status
    assert is_dcat_ap_conformant(response.text, ignore_warnings=True)


@pytest.mark.elasticsearch
def test_dataset_rdf_in_schemaorg_profile(dataset_with_resource, client14):
    dataset = dataset_with_resource
    response = client14.simulate_get(f"/catalog/dataset/{dataset.id}.rdf?profile=schemaorg")
    expected_rdf = get_dataset_schemaorg_expected_rdf(dataset)
    assert expected_rdf == response.text
    assert HTTP_OK == response.status


@pytest.mark.elasticsearch
def test_dataset_rdf_in_unsupported_profile(dataset_with_resource, client14):
    response = client14.simulate_get(f"/catalog/dataset/{dataset_with_resource.id}.rdf?profile=unsupported")
    assert HTTP_BAD_REQUEST == response.status


def is_dcat_ap_conformant(rdf_content, ignore_warnings=False):
    graph = ExtendedGraph(ordered=True)
    file = io.StringIO(rdf_content)
    graph.parse(file, format="xml")

    for shape_path in settings.SHACL_SHAPES.values():
        conforms, results_graph, results_text = shacl_validate(
            graph,
            shacl_graph=shape_path,
            ont_graph=None,
            inference="rdfs",
            abort_on_error=False,
            meta_shacl=False,
            advanced=False,
            debug=False,
        )
        if (ignore_warnings is False and conforms is False) or (
            None,
            SH.severity,
            SH.Violation,
        ) in results_graph:
            return False
    return True


def get_pagination_dcat_ap_triples():
    pagination_ref = BNode("PagedCollection")
    triples = [
        (pagination_ref, ns.RDF.type, ns.HYDRA.PagedCollection),
        (pagination_ref, ns.HYDRA.totalItems, Literal(1)),
        (pagination_ref, ns.HYDRA.itemsPerPage, Literal(20)),
    ]
    return triples


def get_vcard_kind_dcat_ap_triples(vcard_kind_ref, config):
    triples = [
        (vcard_kind_ref, ns.RDF.type, ns.VCARD.Kind),
        (
            vcard_kind_ref,
            ns.VCARD.fn,
            Literal(config.DATASET__CONTACT_POINT__FN, datatype=XSD.string),
        ),
        (
            vcard_kind_ref,
            ns.VCARD.hasEmail,
            URIRef(config.DATASET__CONTACT_POINT__HAS_EMAIL),
        ),
    ]
    return triples


def get_spatial_triples(spatial_ref):
    triples = [
        (spatial_ref, ns.RDF.type, ns.DCT.Location),
        (spatial_ref, ns.DCT.identifier, URIRef("http://sws.geonames.org/798544/")),
    ]
    return triples


get_pagination_schemaorg_triples = get_pagination_dcat_ap_triples


def get_catalog_dcat_ap_triples(dataset, config):
    dataset_ref = URIRef(dataset.frontend_absolute_url)
    catalog_ref = URIRef(CATALOG_URL)
    resource = dataset.resources.first()
    vocab = DCAT_AP_VOCABULARIES

    pl_language_ref = URIRef(f'{vocab["language"]}POL')
    en_language_ref = URIRef(f'{vocab["language"]}ENG')
    spatial_ref = URIRef(f'{vocab["country"]}POL')
    spatial_scheme_ref = URIRef(vocab["country"].rstrip("/"))

    agent_ref = BNode("CatalogPublisher")
    agent_type_ref = URIRef(f'{vocab["publishertype-prefix"]}NationalAuthority')
    agent_type_scheme_ref = URIRef(vocab["publishertype"])

    theme_taxonomy_ref = URIRef(vocab["theme"].rstrip("/"))

    homepage_ref = URIRef(settings.BASE_URL)

    triples = [
        (catalog_ref, ns.RDF.type, ns.DCAT.Catalog),
        (catalog_ref, ns.DCT.title, Literal(config.CATALOG__TITLE_PL, lang="pl")),
        (catalog_ref, ns.DCT.title, Literal(config.CATALOG__TITLE_EN, lang="en")),
        (
            catalog_ref,
            ns.DCT.description,
            Literal(config.CATALOG__DESCRIPTION_PL, lang="pl"),
        ),
        (
            catalog_ref,
            ns.DCT.description,
            Literal(config.CATALOG__DESCRIPTION_EN, lang="en"),
        ),
        (
            catalog_ref,
            ns.DCT.modified,
            Literal(
                resource.modified.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                datatype=XSD.dateTime,
            ),
        ),
        (
            catalog_ref,
            ns.DCT.issued,
            Literal(config.CATALOG__ISSUED, datatype=XSD.date),
        ),
        (
            catalog_ref,
            ns.DCT.description,
            Literal(config.CATALOG__DESCRIPTION_EN, lang="en"),
        ),
        (catalog_ref, ns.DCAT.dataset, dataset_ref),
        (catalog_ref, ns.DCT.language, pl_language_ref),
        (pl_language_ref, ns.RDF.type, ns.DCT.LinguisticSystem),
        (pl_language_ref, ns.SKOS.inScheme, URIRef(vocab["language"].rstrip("/"))),
        (catalog_ref, ns.DCT.language, en_language_ref),
        (en_language_ref, ns.RDF.type, ns.DCT.LinguisticSystem),
        (en_language_ref, ns.SKOS.inScheme, URIRef(vocab["language"].rstrip("/"))),
        (catalog_ref, ns.DCT.spatial, spatial_ref),
        (spatial_ref, ns.RDF.type, ns.DCT.Location),
        (spatial_ref, ns.SKOS.inScheme, spatial_scheme_ref),
        (catalog_ref, ns.DCT.publisher, agent_ref),
        (agent_ref, ns.RDF.type, ns.FOAF.Agent),
        (
            agent_ref,
            ns.FOAF.name,
            Literal(config.CATALOG__PUBLISHER__NAME_PL, lang="pl"),
        ),
        (
            agent_ref,
            ns.FOAF.name,
            Literal(config.CATALOG__PUBLISHER__NAME_EN, lang="en"),
        ),
        (agent_ref, ns.FOAF.mbox, Literal(config.CATALOG__PUBLISHER__EMAIL)),
        (agent_ref, ns.FOAF.homepage, URIRef(config.CATALOG__PUBLISHER__HOMEPAGE)),
        (agent_ref, ns.DCT.type, agent_type_ref),
        (agent_type_ref, ns.RDF.type, ns.SKOS.Concept),
        (agent_type_ref, ns.SKOS.inScheme, agent_type_scheme_ref),
        (agent_type_ref, ns.SKOS.prefLabel, Literal("Organ krajowy", lang="pl")),
        (agent_type_ref, ns.SKOS.prefLabel, Literal("National authority", lang="en")),
        (agent_type_scheme_ref, ns.RDF.type, ns.SKOS.ConceptScheme),
        (agent_type_scheme_ref, ns.DCT.title, Literal("Publisher Type", lang="en")),
        (catalog_ref, ns.DCAT.themeTaxonomy, theme_taxonomy_ref),
        (theme_taxonomy_ref, ns.RDF.type, ns.SKOS.ConceptScheme),
        (theme_taxonomy_ref, ns.DCT.title, Literal("Kategoria danych", lang="pl")),
        (theme_taxonomy_ref, ns.DCT.title, Literal("Data theme", lang="en")),
        (catalog_ref, ns.FOAF.homepage, homepage_ref),
        (homepage_ref, ns.RDF.type, ns.FOAF.Document),
    ]
    return triples


def get_catalog_schemaorg_triples(dataset, config):
    dataset_ref = URIRef(dataset.frontend_absolute_url)
    catalog_ref = URIRef(CATALOG_URL)
    resource = dataset.resources.first()
    triples = [
        (catalog_ref, ns.SCHEMA.dataset, dataset_ref),
        (catalog_ref, ns.RDF.type, ns.SCHEMA.DataCatalog),
        (catalog_ref, ns.SCHEMA.inLanguage, Literal("pl")),
        (catalog_ref, ns.SCHEMA.inLanguage, Literal("en")),
        (catalog_ref, ns.SCHEMA.name, Literal(config.CATALOG__TITLE_PL, lang="pl")),
        (catalog_ref, ns.SCHEMA.name, Literal(config.CATALOG__TITLE_EN, lang="en")),
        (
            catalog_ref,
            ns.SCHEMA.description,
            Literal(config.CATALOG__DESCRIPTION_PL, lang="pl"),
        ),
        (
            catalog_ref,
            ns.SCHEMA.description,
            Literal(config.CATALOG__DESCRIPTION_EN, lang="en"),
        ),
        (
            catalog_ref,
            ns.SCHEMA.dateModified,
            Literal(resource.modified.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"),
        ),
        (catalog_ref, ns.SCHEMA.url, Literal(settings.BASE_URL)),
    ]
    return triples


def get_dataset_dcat_ap_triples(dataset, config):
    organization = dataset.organization
    organization_uri = organization.frontend_absolute_url
    organization_ref = URIRef(organization_uri)

    resource = dataset.resources.first()
    resource_uri = resource.frontend_absolute_url
    resource_ref = URIRef(resource_uri)

    dataset_uri = dataset.frontend_absolute_url
    dataset_ref = URIRef(dataset_uri)

    vocab = DCAT_AP_VOCABULARIES

    license_link = resource.dataset.license_link
    license_triple = (resource_ref, ns.DCAT.license, URIRef(license_link))

    vcard_kind_ref = BNode("VcardKind")
    vcard_kind_triples = get_vcard_kind_dcat_ap_triples(vcard_kind_ref, config)

    categories_triples = []
    for category in sorted(dataset.categories.all(), key=lambda c: c.code):
        category_uri = f'{vocab["theme"]}{category.code}'
        category_ref = URIRef(category_uri)
        theme_taxonomy_ref = URIRef(vocab["theme"].rstrip("/"))
        categories_triples.extend(
            [
                (dataset_ref, ns.DCAT.theme, category_ref),
                (category_ref, ns.RDF.type, ns.SKOS.Concept),
                (category_ref, ns.SKOS.inScheme, theme_taxonomy_ref),
                (category_ref, ns.SKOS.prefLabel, Literal(category.title, lang="pl")),
                (category_ref, ns.SKOS.prefLabel, Literal(category.title, lang="en")),
                (theme_taxonomy_ref, ns.RDF.type, ns.SKOS.ConceptScheme),
                (
                    theme_taxonomy_ref,
                    ns.DCT.title,
                    Literal("Kategoria danych", lang="pl"),
                ),
                (theme_taxonomy_ref, ns.DCT.title, Literal("Data theme", lang="en")),
            ]
        )

    dataset_supplements_triples = []
    for supplement in dataset.supplement_docs:
        if supplement.file_url is None:
            continue
        supplement_ref = URIRef(supplement.file_url)
        dataset_supplements_triples.extend(
            [
                (supplement_ref, ns.RDF.type, ns.FOAF.Document),
                (dataset_ref, ns.FOAF.page, supplement_ref),
            ]
        )

    resource_supplements_triples = []
    for supplement in resource.supplement_docs:
        if supplement.file_url is None:
            continue
        supplement_ref = URIRef(supplement.file_url)
        resource_supplements_triples.extend(
            [
                (supplement_ref, ns.RDF.type, ns.FOAF.Document),
                (resource_ref, ns.FOAF.page, supplement_ref),
            ]
        )

    accrual_periodicity = UPDATE_FREQUENCY_TO_DCAT.get(dataset.update_frequency)
    accrual_periodicity_triples = []
    if accrual_periodicity:
        accrual_periodicity_ref = URIRef(f'{vocab["frequency"]}{accrual_periodicity}')
        accrual_periodicity_triples = [
            (dataset_ref, ns.DCT.accrualPeriodicity, accrual_periodicity_ref),
            (accrual_periodicity_ref, ns.RDF.type, ns.DCT.Frequency),
            (
                accrual_periodicity_ref,
                ns.SKOS.inScheme,
                URIRef(vocab["frequency"].rstrip("/")),
            ),
        ]

    format_ref = URIRef(f'{vocab["file-type"]}{resource.format.upper()}')
    format_triples = [
        (resource_ref, ns.DCT["format"], format_ref),
        (format_ref, ns.RDF.type, ns.DCT.MediaTypeOrExtent),
        (format_ref, ns.SKOS.inScheme, URIRef(vocab["file-type"].rstrip("/"))),
    ]

    media_type_ref = URIRef(f'{vocab["media-type"]}{resource.main_file_mimetype}')
    media_type_triples = [
        (resource_ref, ns.DCAT.mediaType, media_type_ref),
        (media_type_ref, ns.RDF.type, ns.DCT.MediaType),
    ]

    pl_language_ref = URIRef(f'{vocab["language"]}POL')
    en_language_ref = URIRef(f'{vocab["language"]}ENG')
    geo_spatial_ref = BNode("DCTLocation" + hashlib.sha256("http://sws.geonames.org/798544/".encode("utf-8")).hexdigest())
    spatial_triples = get_spatial_triples(geo_spatial_ref)
    languages_metadata_triples = [
        (pl_language_ref, ns.RDF.type, ns.DCT.LinguisticSystem),
        (pl_language_ref, ns.SKOS.inScheme, URIRef(vocab["language"].rstrip("/"))),
        (en_language_ref, ns.RDF.type, ns.DCT.LinguisticSystem),
        (en_language_ref, ns.SKOS.inScheme, URIRef(vocab["language"].rstrip("/"))),
    ]

    status_ref = URIRef(f'{vocab["status-prefix"]}Completed')
    status_scheme_ref = URIRef(vocab["status"])
    status_triples = [
        (resource_ref, ns.ADMS.status, status_ref),
        (status_ref, ns.RDF.type, ns.SKOS.Concept),
        (status_ref, ns.SKOS.inScheme, status_scheme_ref),
        (status_ref, ns.SKOS.prefLabel, Literal("Completed", lang="en")),
        (status_scheme_ref, ns.RDF.type, ns.SKOS.ConceptScheme),
        (status_scheme_ref, ns.DCT.title, Literal("Status", lang="en")),
    ]

    triples = [
        # DATASET
        (dataset_ref, ns.DCAT.distribution, resource_ref),
        (dataset_ref, ns.DCT.publisher, organization_ref),
        (dataset_ref, ns.RDF.type, ns.DCAT.Dataset),
        (dataset_ref, ns.RDF.type, ns.FOAF.Document),
        (dataset_ref, ns.DCT.language, pl_language_ref),
        (dataset_ref, ns.DCT.language, en_language_ref),
        (dataset_ref, ns.DCT.identifier, Literal(dataset_uri)),
        (
            dataset_ref,
            ns.DCT.title,
            Literal(dataset.title_pl or dataset.title, lang="pl"),
        ),
        (
            dataset_ref,
            ns.DCT.title,
            Literal(dataset.title_en or dataset.title, lang="en"),
        ),
        (
            dataset_ref,
            ns.DCT.description,
            Literal(dataset.notes_pl or dataset.notes, lang="pl"),
        ),
        (
            dataset_ref,
            ns.DCT.description,
            Literal(dataset.notes_en or dataset.notes, lang="en"),
        ),
        (dataset_ref, ns.DCT.issued, Literal(str(dataset.created).replace(" ", "T"))),
        (
            dataset_ref,
            ns.DCT.modified,
            Literal(str(dataset.modified).replace(" ", "T")),
        ),
        (dataset_ref, ns.DCAT.landingPage, dataset_ref),
        (dataset_ref, ns.OWL.versionInfo, Literal(str(dataset.version))),
        *accrual_periodicity_triples,
        (dataset_ref, ns.DCAT.contactPoint, vcard_kind_ref),
        (dataset_ref, ns.DCT.spatial, geo_spatial_ref),
        *spatial_triples,
        *categories_triples,
        *dataset_supplements_triples,
        # RESOURCE
        (resource_ref, ns.RDF.type, ns.DCAT.Distribution),
        (resource_ref, ns.DCT.language, pl_language_ref),
        (resource_ref, ns.DCT.language, en_language_ref),
        (
            resource_ref,
            ns.DCT.title,
            Literal(resource.title_pl or resource.title, lang="pl"),
        ),
        (
            resource_ref,
            ns.DCT.title,
            Literal(resource.title_en or resource.title, lang="en"),
        ),
        (
            resource_ref,
            ns.DCT.description,
            Literal(resource.description_pl or resource.description, lang="pl"),
        ),
        (
            resource_ref,
            ns.DCT.description,
            Literal(resource.description_en or resource.description, lang="en"),
        ),
        *status_triples,
        (
            resource_ref,
            ns.DCT.issued,
            Literal(str(resource.created).replace(" ", "T"), datatype=XSD.dateTime),
        ),
        (
            resource_ref,
            ns.DCT.modified,
            Literal(str(resource.modified).replace(" ", "T"), datatype=XSD.dateTime),
        ),
        (resource_ref, ns.DCAT.accessURL, resource_ref),
        (resource_ref, ns.DCAT.downloadURL, URIRef(resource.download_url)),
        *format_triples,
        (
            resource_ref,
            ns.DCAT.byteSize,
            Literal(resource.file_size, datatype=XSD.decimal),
        ),
        *media_type_triples,
        license_triple,
        *resource_supplements_triples,
        # ORGANIZATION
        (organization_ref, ns.RDF.type, ns.FOAF.Agent),
        (organization_ref, ns.FOAF.mbox, Literal(organization.email)),
        (
            organization_ref,
            ns.FOAF.name,
            Literal(organization.title_pl or organization.title, lang="pl"),
        ),
        (
            organization_ref,
            ns.FOAF.name,
            Literal(organization.title_en or organization.title, lang="en"),
        ),
        *vcard_kind_triples,
        *languages_metadata_triples,
    ]

    return triples


def get_dataset_dcat_ap_pl_triples(dataset, config):
    organization = dataset.organization
    organization_uri = organization.frontend_absolute_url
    organization_ref = URIRef(organization_uri)

    resource = dataset.resources.first()
    resource_uri = resource.frontend_absolute_url
    resource_ref = URIRef(resource_uri)

    dataset_uri = dataset.frontend_absolute_url
    dataset_ref = URIRef(dataset_uri)

    vocabs = DCAT_AP_VOCABULARIES
    vocabs_pl = DCAT_AP_PL_VOCABULARIES

    license_link = resource.dataset.license_link
    license_triple = (resource_ref, ns.DCAT.license, URIRef(license_link))

    vcard_kind_ref = BNode("VcardKind")
    vcard_kind_triples = get_vcard_kind_dcat_ap_triples(vcard_kind_ref, config)

    categories_triples = []
    for category in sorted(dataset.categories.all(), key=lambda c: c.code):
        category_uri = f'{vocabs["theme"]}{category.code}'
        category_ref = URIRef(category_uri)
        theme_taxonomy_ref = URIRef(vocabs["theme"].rstrip("/"))
        categories_triples.extend(
            [
                (dataset_ref, ns.DCAT.theme, category_ref),
                (category_ref, ns.RDF.type, ns.SKOS.Concept),
                (category_ref, ns.SKOS.inScheme, theme_taxonomy_ref),
                (category_ref, ns.SKOS.prefLabel, Literal(category.title, lang="pl")),
                (category_ref, ns.SKOS.prefLabel, Literal(category.title, lang="en")),
                (theme_taxonomy_ref, ns.RDF.type, ns.SKOS.ConceptScheme),
                (
                    theme_taxonomy_ref,
                    ns.DCT.title,
                    Literal("Kategoria danych", lang="pl"),
                ),
                (theme_taxonomy_ref, ns.DCT.title, Literal("Data theme", lang="en")),
            ]
        )

    openness_score_triples = []
    if resource.openness_score:
        identifier = f"{resource.openness_score}-star" if resource.openness_score == 1 else f"{resource.openness_score}-stars"
        entry = OpennessScoreVocab().entries[identifier]
        openness_score_vocab_uri = vocabs_pl["openness-score"]
        openness_score_vocab_ref = URIRef(openness_score_vocab_uri)
        openness_score_uri = f"{openness_score_vocab_uri}/{identifier}"
        openness_score_ref = URIRef(openness_score_uri)
        openness_score_triples.extend(
            [
                (resource_ref, ns.DCATAPPL.opennessScore, openness_score_ref),
                (openness_score_ref, ns.RDF.type, ns.SKOS.Concept),
                (openness_score_ref, ns.SKOS.inScheme, openness_score_vocab_ref),
                (
                    openness_score_ref,
                    ns.SKOS.prefLabel,
                    Literal(entry.name_pl, lang="pl"),
                ),
                (
                    openness_score_ref,
                    ns.SKOS.prefLabel,
                    Literal(entry.name_en, lang="en"),
                ),
                (openness_score_vocab_ref, ns.RDF.type, ns.SKOS.ConceptScheme),
                (
                    openness_score_vocab_ref,
                    ns.DCT.title,
                    Literal("Poziom otwartości", lang="pl"),
                ),
                (
                    openness_score_vocab_ref,
                    ns.DCT.title,
                    Literal("Openness score", lang="en"),
                ),
            ]
        )

    special_sign_vocab_uri = vocabs_pl["special-sign"]
    special_sign_vocab_ref = URIRef(special_sign_vocab_uri)
    special_signs_triples = []
    for sign in resource.special_signs.filter(status="published"):
        special_sign_uri = f"{special_sign_vocab_uri}/{sign.id}"
        special_sign_ref = URIRef(special_sign_uri)
        special_signs_triples.extend(
            [
                (resource_ref, ns.DCATAPPL.specialSign, special_sign_ref),
                (special_sign_ref, ns.RDF.type, ns.SKOS.Concept),
                (special_sign_ref, ns.SKOS.inScheme, special_sign_vocab_ref),
                (special_sign_ref, ns.SKOS.prefLabel, Literal(sign.name_pl, lang="pl")),
                *(
                    [
                        (
                            special_sign_ref,
                            ns.SKOS.prefLabel,
                            Literal(sign.name_en, lang="en"),
                        )
                    ]
                    if sign.name_en
                    else []
                ),
                (special_sign_vocab_ref, ns.RDF.type, ns.SKOS.ConceptScheme),
                (
                    special_sign_vocab_ref,
                    ns.DCT.title,
                    Literal("Znak umowny", lang="pl"),
                ),
                (
                    special_sign_vocab_ref,
                    ns.DCT.title,
                    Literal("Special sign", lang="en"),
                ),
            ]
        )

    accrual_periodicity = UPDATE_FREQUENCY_TO_DCAT.get(dataset.update_frequency)
    accrual_periodicity_triples = []
    if accrual_periodicity:
        accrual_periodicity_ref = URIRef(f'{vocabs["frequency"]}{accrual_periodicity}')
        accrual_periodicity_triples = [
            (dataset_ref, ns.DCT.accrualPeriodicity, accrual_periodicity_ref),
            (accrual_periodicity_ref, ns.RDF.type, ns.DCT.Frequency),
            (
                accrual_periodicity_ref,
                ns.SKOS.inScheme,
                URIRef(vocabs["frequency"].rstrip("/")),
            ),
        ]

    format_ref = URIRef(f'{vocabs["file-type"]}{resource.format.upper()}')
    format_triples = [
        (resource_ref, ns.DCT["format"], format_ref),
        (format_ref, ns.RDF.type, ns.DCT.MediaTypeOrExtent),
        (format_ref, ns.SKOS.inScheme, URIRef(vocabs["file-type"].rstrip("/"))),
    ]

    media_type_ref = URIRef(f'{vocabs["media-type"]}{resource.main_file_mimetype}')
    media_type_triples = [
        (resource_ref, ns.DCAT.mediaType, media_type_ref),
        (media_type_ref, ns.RDF.type, ns.DCT.MediaType),
    ]

    pl_language_ref = URIRef(f'{vocabs["language"]}POL')
    en_language_ref = URIRef(f'{vocabs["language"]}ENG')
    geo_spatial_ref = BNode("DCTLocation" + hashlib.sha256("http://sws.geonames.org/798544/".encode("utf-8")).hexdigest())
    spatial_triples = get_spatial_triples(geo_spatial_ref)
    languages_metadata_triples = [
        (pl_language_ref, ns.RDF.type, ns.DCT.LinguisticSystem),
        (pl_language_ref, ns.SKOS.inScheme, URIRef(vocabs["language"].rstrip("/"))),
        (en_language_ref, ns.RDF.type, ns.DCT.LinguisticSystem),
        (en_language_ref, ns.SKOS.inScheme, URIRef(vocabs["language"].rstrip("/"))),
    ]

    status_ref = URIRef(f'{vocabs["status-prefix"]}Completed')
    status_scheme_ref = URIRef(vocabs["status"])
    status_triples = [
        (resource_ref, ns.ADMS.status, status_ref),
        (status_ref, ns.RDF.type, ns.SKOS.Concept),
        (status_ref, ns.SKOS.inScheme, status_scheme_ref),
        (status_ref, ns.SKOS.prefLabel, Literal("Completed", lang="en")),
        (status_scheme_ref, ns.RDF.type, ns.SKOS.ConceptScheme),
        (status_scheme_ref, ns.DCT.title, Literal("Status", lang="en")),
    ]

    triples = [
        # DATASET
        (dataset_ref, ns.DCAT.distribution, resource_ref),
        (dataset_ref, ns.DCT.publisher, organization_ref),
        (dataset_ref, ns.RDF.type, ns.DCAT.Dataset),
        (dataset_ref, ns.RDF.type, ns.FOAF.Document),
        (dataset_ref, ns.DCT.language, pl_language_ref),
        (dataset_ref, ns.DCT.language, en_language_ref),
        (dataset_ref, ns.DCT.identifier, Literal(dataset_uri)),
        (
            dataset_ref,
            ns.DCT.title,
            Literal(dataset.title_pl or dataset.title, lang="pl"),
        ),
        (
            dataset_ref,
            ns.DCT.title,
            Literal(dataset.title_en or dataset.title, lang="en"),
        ),
        (
            dataset_ref,
            ns.DCT.description,
            Literal(dataset.notes_pl or dataset.notes, lang="pl"),
        ),
        (
            dataset_ref,
            ns.DCT.description,
            Literal(dataset.notes_en or dataset.notes, lang="en"),
        ),
        (dataset_ref, ns.DCT.issued, Literal(str(dataset.created).replace(" ", "T"))),
        (
            dataset_ref,
            ns.DCT.modified,
            Literal(str(dataset.modified).replace(" ", "T")),
        ),
        (dataset_ref, ns.DCAT.landingPage, dataset_ref),
        (dataset_ref, ns.OWL.versionInfo, Literal(str(dataset.version))),
        *accrual_periodicity_triples,
        (dataset_ref, ns.DCAT.contactPoint, vcard_kind_ref),
        (dataset_ref, ns.DCT.spatial, geo_spatial_ref),
        (dataset_ref, ns.FOAF.logo, URIRef(dataset.image_absolute_url)),
        *spatial_triples,
        *categories_triples,
        # RESOURCE
        (resource_ref, ns.RDF.type, ns.DCAT.Distribution),
        (resource_ref, ns.DCT.language, pl_language_ref),
        (resource_ref, ns.DCT.language, en_language_ref),
        (
            resource_ref,
            ns.DCT.title,
            Literal(resource.title_pl or resource.title, lang="pl"),
        ),
        (
            resource_ref,
            ns.DCT.title,
            Literal(resource.title_en or resource.title, lang="en"),
        ),
        (
            resource_ref,
            ns.DCT.description,
            Literal(resource.description_pl or resource.description, lang="pl"),
        ),
        (
            resource_ref,
            ns.DCT.description,
            Literal(resource.description_en or resource.description, lang="en"),
        ),
        *status_triples,
        (
            resource_ref,
            ns.DCT.issued,
            Literal(str(resource.created).replace(" ", "T"), datatype=XSD.dateTime),
        ),
        (
            resource_ref,
            ns.DCT.modified,
            Literal(str(resource.modified).replace(" ", "T"), datatype=XSD.dateTime),
        ),
        (resource_ref, ns.DCAT.accessURL, resource_ref),
        (resource_ref, ns.DCAT.downloadURL, URIRef(resource.download_url)),
        *format_triples,
        (
            resource_ref,
            ns.DCAT.byteSize,
            Literal(resource.file_size, datatype=XSD.decimal),
        ),
        (resource_ref, ns.DCT.valid, Literal(resource.data_date, datatype=XSD.date)),
        *media_type_triples,
        *openness_score_triples,
        *special_signs_triples,
        license_triple,
        # ORGANIZATION
        (organization_ref, ns.RDF.type, ns.FOAF.Agent),
        (organization_ref, ns.FOAF.mbox, Literal(organization.email)),
        (
            organization_ref,
            ns.FOAF.name,
            Literal(organization.title_pl or organization.title, lang="pl"),
        ),
        (
            organization_ref,
            ns.FOAF.name,
            Literal(organization.title_en or organization.title, lang="en"),
        ),
        (organization_ref, ns.DCATAPPL.regon, Literal(organization.regon)),
        *vcard_kind_triples,
        *languages_metadata_triples,
    ]

    return triples


def get_dataset_schemaorg_triples(dataset):
    organization = dataset.organization
    organization_uri = organization.frontend_absolute_url
    organization_ref = URIRef(organization_uri)

    resource = dataset.resources.first()
    resource_uri = resource.frontend_absolute_url
    resource_ref = URIRef(resource_uri)

    dataset_uri = dataset.frontend_absolute_url
    dataset_ref = URIRef(dataset_uri)

    resource_license_triple = (
        resource_ref,
        ns.SCHEMA.license,
        Literal(resource.dataset.license_link),
    )
    dataset_license_triples = [(dataset_ref, ns.SCHEMA.license, Literal(dataset.license_link))]

    triples = [
        # DATASET
        (dataset_ref, ns.SCHEMA.distribution, resource_ref),
        (dataset_ref, ns.SCHEMA.creator, organization_ref),
        (dataset_ref, ns.RDF.type, ns.SCHEMA.Dataset),
        (dataset_ref, ns.SCHEMA.inLanguage, Literal("pl")),
        (dataset_ref, ns.SCHEMA.inLanguage, Literal("en")),
        (dataset_ref, ns.SCHEMA.url, Literal(dataset_uri)),
        (dataset_ref, ns.SCHEMA.identifier, Literal(str(dataset.id))),
        (
            dataset_ref,
            ns.SCHEMA.name,
            Literal(dataset.title_pl or dataset.title, lang="pl"),
        ),
        (
            dataset_ref,
            ns.SCHEMA.name,
            Literal(dataset.title_en or dataset.title, lang="en"),
        ),
        (
            dataset_ref,
            ns.SCHEMA.description,
            Literal(dataset.notes_pl or dataset.notes, lang="pl"),
        ),
        (
            dataset_ref,
            ns.SCHEMA.description,
            Literal(dataset.notes_en or dataset.notes, lang="en"),
        ),
        (dataset_ref, ns.SCHEMA.creativeWorkStatus, Literal(dataset.status)),
        (
            dataset_ref,
            ns.SCHEMA.dateCreated,
            Literal(str(dataset.created).replace(" ", "T")),
        ),
        (
            dataset_ref,
            ns.SCHEMA.dateModified,
            Literal(str(dataset.modified).replace(" ", "T")),
        ),
        (dataset_ref, ns.SCHEMA.version, Literal(str(dataset.version))),
        (dataset_ref, ns.SCHEMA.keywords, Literal("None")),
        *dataset_license_triples,
        # RESOURCE
        (resource_ref, ns.RDF.type, ns.SCHEMA.DataDownload),
        (resource_ref, ns.SCHEMA.inLanguage, Literal("pl")),
        (resource_ref, ns.SCHEMA.inLanguage, Literal("en")),
        (
            resource_ref,
            ns.SCHEMA.name,
            Literal(resource.title_pl or resource.title, lang="pl"),
        ),
        (
            resource_ref,
            ns.SCHEMA.name,
            Literal(resource.title_en or resource.title, lang="en"),
        ),
        (
            resource_ref,
            ns.SCHEMA.description,
            Literal(resource.description_pl or resource.description, lang="pl"),
        ),
        (
            resource_ref,
            ns.SCHEMA.description,
            Literal(resource.description_en or resource.description, lang="en"),
        ),
        (resource_ref, ns.SCHEMA.creativeWorkStatus, Literal(resource.status)),
        (
            resource_ref,
            ns.SCHEMA.dateCreated,
            Literal(str(resource.created).replace(" ", "T")),
        ),
        (
            resource_ref,
            ns.SCHEMA.dateModified,
            Literal(str(resource.modified).replace(" ", "T")),
        ),
        (resource_ref, ns.SCHEMA.url, Literal(resource_uri)),
        (resource_ref, ns.SCHEMA.contentUrl, Literal(resource.download_url)),
        (resource_ref, ns.SCHEMA.encodingFormat, Literal(resource.main_file_mimetype)),
        resource_license_triple,
        # ORGANIZATION
        (organization_ref, ns.RDF.type, ns.SCHEMA.Organization),
        (
            organization_ref,
            ns.SCHEMA.name,
            Literal(organization.title_pl or organization.title, lang="pl"),
        ),
        (
            organization_ref,
            ns.SCHEMA.name,
            Literal(organization.title_en or organization.title, lang="en"),
        ),
    ]

    return triples


def get_dataset_dcat_ap_expected_rdf(dataset, config, catalog=False):
    triples = get_dataset_dcat_ap_triples(dataset, config)
    graph = ExtendedGraph(ordered=True)
    for prefix, namespace in ns.NAMESPACES.items():
        graph.bind(prefix, namespace)

    if catalog:
        graph.bind("hydra", ns.HYDRA)
        triples.extend(get_catalog_dcat_ap_triples(dataset, config))
        triples.extend(get_pagination_dcat_ap_triples())

    for triple in triples:
        graph.add(triple)

    return graph.serialize(format="application/rdf+xml")


def get_dataset_dcat_ap_pl_expected_rdf(dataset, config, catalog=False):
    triples = get_dataset_dcat_ap_pl_triples(dataset, config)
    graph = ExtendedGraph(ordered=True)
    for prefix, namespace in ns.DCAT_AP_PL_NAMESPACES.items():
        graph.bind(prefix, namespace)

    if catalog:
        graph.bind("hydra", ns.HYDRA)
        triples.extend(get_catalog_dcat_ap_triples(dataset, config))
        triples.extend(get_pagination_dcat_ap_triples())

    for triple in triples:
        graph.add(triple)

    return graph.serialize(format="application/rdf+xml")


def get_dataset_schemaorg_expected_rdf(dataset, catalog=False, config=None):
    triples = get_dataset_schemaorg_triples(dataset)
    graph = ExtendedGraph(ordered=True)
    graph.bind("schema", ns.NAMESPACES["schema"])

    if catalog:
        graph.bind("hydra", ns.HYDRA)
        triples.extend(get_catalog_schemaorg_triples(dataset, config))
        triples.extend(get_pagination_dcat_ap_triples())

    for triple in triples:
        graph.add(triple)

    return graph.serialize(format="application/rdf+xml")
