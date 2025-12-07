import hashlib
from functools import partial

from constance import config
from rdflib import RDF, XSD, BNode, Literal, URIRef
from rdflib.term import _is_valid_uri

import mcod.core.api.rdf.namespaces as ns
from mcod import settings
from mcod.core.api.rdf.profiles.common import CATALOG_URL, RDFClass, RDFNestedField
from mcod.lib.rdf.rdf_field import RDFField

VOCABULARIES = {
    "theme": "http://publications.europa.eu/resource/authority/data-theme/",
    "language": "http://publications.europa.eu/resource/authority/language/",
    "file-type": "http://publications.europa.eu/resource/authority/file-type/",
    "media-type": "https://www.iana.org/assignments/media-types/",
    "frequency": "http://publications.europa.eu/resource/authority/frequency/",
    "country": "http://publications.europa.eu/resource/authority/country/",
    "publishertype-prefix": "http://purl.org/adms/publishertype/",
    "publishertype": "http://purl.org/adms/publishertype/1.0",
    "status-prefix": "http://purl.org/adms/status/",
    "status": "http://purl.org/adms/status/1.0",
    "license": "http://publications.europa.eu/resource/authority/licence/",
}


class DCTMediaType(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.DCT.MediaType)


class DCTMediaTypeOrExtent(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.DCT.MediaTypeOrExtent)
    scheme = RDFField(predicate=ns.SKOS.inScheme, object_type=URIRef)


class FOAFDocument(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.FOAF.Document)


class DCTLinguisticSystem(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.DCT.LinguisticSystem)
    scheme = RDFField(predicate=ns.SKOS.inScheme, object_type=URIRef)


class DCTLocation(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.DCT.Location)
    scheme = RDFField(predicate=ns.SKOS.inScheme, object_type=URIRef)


class GeonamesDCTLocation(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.DCT.Location)
    geonames_url = RDFField(predicate=ns.DCT.identifier, object_type=URIRef, required=False)
    centroid = RDFField(
        predicate=ns.DCAT.centroid,
        object_type=partial(Literal, datatype=ns.GSP.asWKT),
        required=False,
    )


class DCTFrequency(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.DCT.Frequency)
    scheme = RDFField(predicate=ns.SKOS.inScheme, object_type=URIRef)


class SKOSConcept(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.SKOS.Concept)
    title_pl = RDFField(
        predicate=ns.SKOS.prefLabel,
        object_type=partial(Literal, lang="pl"),
        required=False,
    )
    title_en = RDFField(
        predicate=ns.SKOS.prefLabel,
        object_type=partial(Literal, lang="en"),
        required=False,
    )
    scheme = RDFNestedField("SKOSConceptScheme", predicate=ns.SKOS.inScheme)


class SKOSConceptScheme(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.SKOS.ConceptScheme)
    title_pl = RDFField(predicate=ns.DCT.title, object_type=partial(Literal, lang="pl"), required=False)
    title_en = RDFField(predicate=ns.DCT.title, object_type=partial(Literal, lang="en"), required=False)


class VCARDKind(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.VCARD.Kind)
    type = RDFField(predicate=RDF.type, object=ns.VCARD.Kind)
    name = RDFField(
        predicate=ns.VCARD.fn,
        object_type=partial(Literal, datatype=XSD.string),
        allow_null=False,
    )
    email = RDFField(predicate=ns.VCARD.hasEmail, object_type=URIRef, required=False)


class FOAFAgent(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.FOAF.Agent)

    title_pl = RDFField(
        predicate=ns.FOAF.name,
        object_type=partial(Literal, lang="pl"),
        allow_null=False,
    )
    title_en = RDFField(
        predicate=ns.FOAF.name,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )

    email = RDFField(predicate=ns.FOAF.mbox, object_type=Literal, required=False)
    homepage = RDFField(predicate=ns.FOAF.homepage, object_type=URIRef, required=False)
    agent_type = RDFNestedField("SKOSConcept", predicate=ns.DCT.type, required=False)


class DCATDistribution(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.DCAT.Distribution)

    format = RDFNestedField("DCTMediaTypeOrExtent", predicate=ns.DCT["format"], required=False)
    file_mimetype = RDFNestedField("DCTMediaType", predicate=ns.DCAT.mediaType)
    language_pl = RDFNestedField("DCTLinguisticSystem", predicate=ns.DCT.language)
    language_en = RDFNestedField("DCTLinguisticSystem", predicate=ns.DCT.language)
    status = RDFNestedField("SKOSConcept", predicate=ns.ADMS.status)
    supplements = RDFNestedField("FOAFDocument", predicate=ns.FOAF.page, many=True)

    title_pl = RDFField(predicate=ns.DCT.title, object_type=partial(Literal, lang="pl"))
    title_en = RDFField(
        predicate=ns.DCT.title,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    description_pl = RDFField(
        predicate=ns.DCT.description,
        object_type=partial(Literal, lang="pl"),
        allow_null=False,
    )
    description_en = RDFField(
        predicate=ns.DCT.description,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    created = RDFField(predicate=ns.DCT.issued, object_type=partial(Literal, datatype=XSD.dateTime))
    modified = RDFField(predicate=ns.DCT.modified, object_type=partial(Literal, datatype=XSD.dateTime))
    access_url = RDFField(predicate=ns.DCAT.accessURL, object_type=URIRef)
    download_url = RDFField(predicate=ns.DCAT.downloadURL, object_type=URIRef, allow_null=False)
    file_size = RDFField(
        predicate=ns.DCAT.byteSize,
        object_type=partial(Literal, datatype=XSD.decimal),
        value_on_null=0,
    )
    license = RDFField(predicate=ns.DCAT.license, object_type=URIRef)

    def get_subject(self, data):
        return URIRef(data["access_url"])

    def get_format_data(self, data):
        if data["format"] is not None:
            return {
                "subject": URIRef(VOCABULARIES["file-type"] + data["format"].upper()),
                "scheme": URIRef(VOCABULARIES["file-type"].rstrip("/")),
            }

    def get_file_mimetype_subject(self, data):
        if data is not None:
            return URIRef(VOCABULARIES["media-type"] + data)

    def get_status_data(self, data):
        return {
            "subject": URIRef(VOCABULARIES["status-prefix"] + "Completed"),
            "scheme": {
                "subject": URIRef(VOCABULARIES["status"]),
                "title_en": "Status",
            },
            "title_en": "Completed",
        }

    def get_supplements_subject(self, data):
        return URIRef(data["file_url"])

    def get_language_pl_data(self, data):
        return {
            "subject": URIRef(VOCABULARIES["language"] + "POL"),
            "scheme": URIRef(VOCABULARIES["language"].rstrip("/")),
        }

    def get_language_en_data(self, data):
        return {
            "subject": URIRef(VOCABULARIES["language"] + "ENG"),
            "scheme": URIRef(VOCABULARIES["language"].rstrip("/")),
        }


class DCATDataset(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.DCAT.Dataset)

    resources = RDFNestedField("DCATDistribution", predicate=ns.DCAT.distribution, many=True)
    organization = RDFNestedField("FOAFAgent", predicate=ns.DCT.publisher)
    contact_point = RDFNestedField("VCARDKind", predicate=ns.DCAT.contactPoint)
    categories = RDFNestedField("SKOSConcept", predicate=ns.DCAT.theme, many=True)
    landing_page = RDFNestedField("FOAFDocument", predicate=ns.DCAT.landingPage)
    supplements = RDFNestedField("FOAFDocument", predicate=ns.FOAF.page, many=True)
    update_frequency = RDFNestedField("DCTFrequency", predicate=ns.DCT.accrualPeriodicity)
    language_pl = RDFNestedField("DCTLinguisticSystem", predicate=ns.DCT.language)
    language_en = RDFNestedField("DCTLinguisticSystem", predicate=ns.DCT.language)
    spatial = RDFNestedField("GeonamesDCTLocation", predicate=ns.DCT.spatial, many=True)

    identifier = RDFField(predicate=ns.DCT.identifier)
    title_pl = RDFField(predicate=ns.DCT.title, object_type=partial(Literal, lang="pl"))
    title_en = RDFField(
        predicate=ns.DCT.title,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    notes_pl = RDFField(
        predicate=ns.DCT.description,
        object_type=partial(Literal, lang="pl"),
        allow_null=False,
    )
    notes_en = RDFField(
        predicate=ns.DCT.description,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    created = RDFField(predicate=ns.DCT.issued)
    modified = RDFField(predicate=ns.DCT.modified)
    version = RDFField(predicate=ns.OWL.versionInfo)
    tags = RDFField(predicate=ns.DCAT.keyword, many=True)

    def get_subject(self, data):
        return URIRef(data["frontend_absolute_url"])

    def get_organization_subject(self, data):
        return URIRef(data["access_url"])

    def get_resources_subject(self, data):
        return URIRef(data["access_url"])

    def get_landing_page_subject(self, data):
        return URIRef(data)

    def get_update_frequency_data(self, data):
        update_frequency = data["update_frequency"]
        if update_frequency is None:
            update_frequency = f"{VOCABULARIES['frequency']}UNKNOWN"
        return {
            "subject": URIRef(update_frequency),
            "scheme": URIRef(VOCABULARIES["frequency"].rstrip("/")),
        }

    def get_language_pl_data(self, data):
        return {
            "subject": URIRef(VOCABULARIES["language"] + "POL"),
            "scheme": URIRef(VOCABULARIES["language"].rstrip("/")),
        }

    def get_language_en_data(self, data):
        return {
            "subject": URIRef(VOCABULARIES["language"] + "ENG"),
            "scheme": URIRef(VOCABULARIES["language"].rstrip("/")),
        }

    def get_supplements_subject(self, data):
        return URIRef(data["file_url"])

    def get_categories_subject(self, data):
        return URIRef(VOCABULARIES["theme"] + data["code"])

    def get_categories_data(self, data):
        for category in data["categories"]:
            category["scheme"] = {
                "subject": URIRef(VOCABULARIES["theme"].rstrip("/")),
                "title_pl": "Kategoria danych",
                "title_en": "Data theme",
            }
        return data["categories"]

    def get_contact_point_subject(self, data):
        return BNode("VcardKind")

    def get_contact_point_data(self, data):
        result = {
            "name": config.DATASET__CONTACT_POINT__FN,
        }
        if config.DATASET__CONTACT_POINT__HAS_EMAIL:
            result["email"] = config.DATASET__CONTACT_POINT__HAS_EMAIL
        return result

    def get_spatial_data(self, data):
        spatial_details = [
            ({"centroid": d["centroid"]} if d["geonames_url"] is None else {"geonames_url": d["geonames_url"]})
            for d in data["spatial"]
        ]
        return spatial_details

    def get_spatial_subject(self, data):
        data_str = data.get("geonames_url", data.get("centroid", ""))
        return BNode("DCTLocation" + hashlib.sha256(data_str.encode("utf-8")).hexdigest())


class DCATCatalog(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.DCAT.Catalog)

    publisher = RDFNestedField("FOAFAgent", predicate=ns.DCT.publisher)
    language_pl = RDFNestedField("DCTLinguisticSystem", predicate=ns.DCT.language)
    language_en = RDFNestedField("DCTLinguisticSystem", predicate=ns.DCT.language)
    homepage = RDFNestedField("FOAFDocument", predicate=ns.FOAF.homepage)
    spatial = RDFNestedField("DCTLocation", predicate=ns.DCT.spatial)
    theme_taxonomy = RDFNestedField("SKOSConceptScheme", predicate=ns.DCAT.themeTaxonomy)

    dataset = RDFField(predicate=ns.DCAT.dataset, object_type=URIRef, many=True)
    title_pl = RDFField(
        predicate=ns.DCT.title,
        object_type=partial(Literal, lang="pl"),
        allow_null=False,
    )
    title_en = RDFField(
        predicate=ns.DCT.title,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    description_pl = RDFField(
        predicate=ns.DCT.description,
        object_type=partial(Literal, lang="pl"),
        allow_null=False,
    )
    description_en = RDFField(
        predicate=ns.DCT.description,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    issued = RDFField(predicate=ns.DCT.issued, object_type=partial(Literal, datatype=XSD.date))
    modified = RDFField(predicate=ns.DCT.modified, object_type=partial(Literal, datatype=XSD.dateTime))

    def get_subject(self, data):
        return URIRef(CATALOG_URL)

    def get_publisher_subject(self, data):
        return BNode("CatalogPublisher")

    def get_data(self, data):
        result = {
            "title_pl": config.CATALOG__TITLE_PL,
            "title_en": config.CATALOG__TITLE_EN,
            "description_pl": config.CATALOG__DESCRIPTION_PL,
            "description_en": config.CATALOG__DESCRIPTION_EN,
            "issued": config.CATALOG__ISSUED,
            "spatial": {
                "subject": URIRef(VOCABULARIES["country"] + "POL"),
                "scheme": URIRef(VOCABULARIES["country"].rstrip("/")),
            },
            "language_pl": {
                "subject": URIRef(VOCABULARIES["language"] + "POL"),
                "scheme": URIRef(VOCABULARIES["language"].rstrip("/")),
            },
            "language_en": {
                "subject": URIRef(VOCABULARIES["language"] + "ENG"),
                "scheme": URIRef(VOCABULARIES["language"].rstrip("/")),
            },
            "modified": data.get("catalog_modified"),
            "homepage": settings.BASE_URL,
            "publisher": {
                "title_pl": config.CATALOG__PUBLISHER__NAME_PL,
                "title_en": config.CATALOG__PUBLISHER__NAME_EN,
                "agent_type": {
                    "subject": URIRef(VOCABULARIES["publishertype-prefix"] + "NationalAuthority"),
                    "scheme": {
                        "subject": URIRef(VOCABULARIES["publishertype"].rstrip("/")),
                        "title_en": "Publisher Type",
                    },
                    "title_pl": "Organ krajowy",
                    "title_en": "National authority",
                },
            },
            "theme_taxonomy": {
                "subject": URIRef(VOCABULARIES["theme"].rstrip("/")),
                "title_pl": "Kategoria danych",
                "title_en": "Data theme",
            },
            "dataset": data.get("dataset_refs"),
        }
        if config.CATALOG__PUBLISHER__EMAIL:
            result["publisher"]["email"] = config.CATALOG__PUBLISHER__EMAIL

        if config.CATALOG__PUBLISHER__HOMEPAGE:
            result["publisher"]["homepage"] = config.CATALOG__PUBLISHER__HOMEPAGE

        return result

    def get_homepage_subject(self, data):
        return URIRef(data)


class DCATVocabularyField(RDFField):
    def __init__(self, vocabulary_name, object_type=URIRef, *args, **kwargs):
        self.vocabulary_name = vocabulary_name
        super().__init__(object_type=object_type, *args, **kwargs)

    def parse_value(self, value):
        vocab_uri = VOCABULARIES[self.vocabulary_name]
        val = value.lstrip(vocab_uri)
        return val


class LicenseDCATVocabularyField(DCATVocabularyField):
    def __init__(self, predicate=ns.DCT.license, vocabulary_name="license", *args, **kwargs):
        super().__init__(predicate=predicate, vocabulary_name=vocabulary_name, *args, **kwargs)

    def parse_value(self, value):
        parsed_value = super().parse_value(value)
        license_names = {
            license_name.replace(" ", "_").replace("-", "_").replace(".", "_"): license_name
            for license_name in settings.LICENSES_LINKS.keys()
        }
        val = license_names.get(parsed_value, parsed_value)
        return val


class BaseDCATDeserializer(RDFClass):
    ext_ident = RDFField(predicate=ns.DCT.identifier)
    title_pl = RDFField(
        predicate=ns.DCT.title,
        object_type=partial(Literal, lang="pl"),
        try_non_lang=True,
    )
    title_en = RDFField(predicate=ns.DCT.title, object_type=partial(Literal, lang="en"))
    description_pl = RDFField(
        predicate=ns.DCT.description,
        object_type=partial(Literal, lang="pl"),
        try_non_lang=True,
    )
    description_en = RDFField(predicate=ns.DCT.description, object_type=partial(Literal, lang="en"))
    created = RDFField(predicate=ns.DCT.issued, object_type=partial(Literal, datatype=XSD.dateTime))
    modified = RDFField(predicate=ns.DCT.modified, object_type=partial(Literal, datatype=XSD.dateTime))

    def get_ext_ident_object(self, triple_store, subject, field):
        ident = [
            value.split("/")[-1] if _is_valid_uri(value) else value
            for value in triple_store.objects(subject=subject, predicate=field.predicate)
        ]
        if not ident and _is_valid_uri(subject):
            ident = [subject.split("/")[-1]]
        return ident


class DCATDistributionDeserializer(BaseDCATDeserializer):
    rdf_type = RDFField(predicate=RDF.type, object=ns.DCAT.Distribution)

    format = DCATVocabularyField(predicate=ns.DCT["format"], vocabulary_name="file-type")
    file_mimetype = DCATVocabularyField(predicate=ns.DCAT.mediaType, vocabulary_name="media-type")
    link = RDFField(predicate=ns.DCAT.accessURL, object_type=URIRef)
    license = LicenseDCATVocabularyField()


class DCATDatasetDeserializer(BaseDCATDeserializer):
    rdf_type = RDFField(predicate=RDF.type, object=ns.DCAT.Dataset)

    categories = DCATVocabularyField(predicate=ns.DCAT.theme, vocabulary_name="theme", many=True)
    resources = RDFNestedField("DCATDistributionDeserializer")
    update_frequency = DCATVocabularyField(predicate=ns.DCT.AccrualPeriodicity, vocabulary_name="frequency")
    tags = RDFField(predicate=ns.DCAT.keyword, many=True)

    def get_tags_object(self, triple_store, subject, field):
        return [
            (
                {"name": value.value, "lang": value.language}
                if value.language in ("pl", "en")
                else {"name": value.value} if not value.language else {}
            )
            for value in triple_store.objects(subject=subject, predicate=field.predicate)
        ]
