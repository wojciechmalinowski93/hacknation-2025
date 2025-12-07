from functools import partial

from constance import config
from rdflib import RDF, Literal, URIRef

import mcod.core.api.rdf.namespaces as ns
from mcod import settings
from mcod.core.api.rdf.profiles.common import CATALOG_URL, RDFClass, RDFNestedField
from mcod.lib.rdf.rdf_field import RDFField


class SCHEMACatalog(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.SCHEMA.DataCatalog)

    language_pl = RDFField(predicate=ns.SCHEMA.inLanguage, object_value="pl")
    language_en = RDFField(predicate=ns.SCHEMA.inLanguage, object_value="en")
    title_pl = RDFField(predicate=ns.SCHEMA.name, object_type=partial(Literal, lang="pl"))
    title_en = RDFField(
        predicate=ns.SCHEMA.name,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    description_pl = RDFField(
        predicate=ns.SCHEMA.description,
        object_type=partial(Literal, lang="pl"),
        allow_null=False,
    )
    description_en = RDFField(
        predicate=ns.SCHEMA.description,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    modified = RDFField(predicate=ns.SCHEMA.dateModified)
    homepage = RDFField(predicate=ns.SCHEMA.url)

    dataset = RDFField(predicate=ns.SCHEMA.dataset, object_type=URIRef, many=True)

    def get_subject(self, data):
        return URIRef(CATALOG_URL)

    def get_data(self, data):
        return {
            "title_pl": config.CATALOG__TITLE_PL,
            "title_en": config.CATALOG__TITLE_EN,
            "description_pl": config.CATALOG__DESCRIPTION_PL,
            "description_en": config.CATALOG__DESCRIPTION_EN,
            "modified": data.get("catalog_modified"),
            "homepage": settings.BASE_URL,
            "dataset": data.get("dataset_refs"),
        }


class SCHEMADataset(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.SCHEMA.Dataset)

    resources = RDFNestedField("SCHEMADistribution", predicate=ns.SCHEMA.distribution, many=True)
    organization = RDFNestedField("SCHEMAOrganization", predicate=ns.SCHEMA.creator)

    language_pl = RDFField(predicate=ns.SCHEMA.inLanguage, object_value="pl")
    language_en = RDFField(predicate=ns.SCHEMA.inLanguage, object_value="en")
    identifier = RDFField(predicate=ns.SCHEMA.url)
    id = RDFField(predicate=ns.SCHEMA.identifier)
    title_pl = RDFField(predicate=ns.SCHEMA.name, object_type=partial(Literal, lang="pl"))
    title_en = RDFField(
        predicate=ns.SCHEMA.name,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    notes_pl = RDFField(
        predicate=ns.SCHEMA.description,
        object_type=partial(Literal, lang="pl"),
        allow_null=False,
    )
    notes_en = RDFField(
        predicate=ns.SCHEMA.description,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    status = RDFField(predicate=ns.SCHEMA.creativeWorkStatus)
    created = RDFField(predicate=ns.SCHEMA.dateCreated)
    modified = RDFField(predicate=ns.SCHEMA.dateModified)
    version = RDFField(predicate=ns.SCHEMA.version)
    tags = RDFField(predicate=ns.SCHEMA.keywords)
    license = RDFField(predicate=ns.SCHEMA.license, required=False)

    def get_subject(self, data):
        return URIRef(data["frontend_absolute_url"])

    def get_data(self, data):
        data["tags"] = ", ".join(data["tags"])
        data["catalog"] = CATALOG_URL
        return data

    def get_organization_subject(self, data):
        return URIRef(data["access_url"])

    def get_resources_subject(self, data):
        return URIRef(data["access_url"])


class SCHEMAOrganization(RDFClass):
    type = RDFField(predicate=RDF.type, object=ns.SCHEMA.Organization)
    title_pl = RDFField(predicate=ns.SCHEMA.name, object_type=partial(Literal, lang="pl"))
    title_en = RDFField(
        predicate=ns.SCHEMA.name,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )


class SCHEMADistribution(RDFClass):
    type = RDFField(predicate=RDF.type, object=ns.SCHEMA.DataDownload)
    language_pl = RDFField(predicate=ns.SCHEMA.inLanguage, object_value="pl")
    language_en = RDFField(predicate=ns.SCHEMA.inLanguage, object_value="en")
    title_pl = RDFField(predicate=ns.SCHEMA.name, object_type=partial(Literal, lang="pl"))
    title_en = RDFField(
        predicate=ns.SCHEMA.name,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    description_pl = RDFField(
        predicate=ns.SCHEMA.description,
        object_type=partial(Literal, lang="pl"),
        allow_null=False,
    )
    description_en = RDFField(
        predicate=ns.SCHEMA.description,
        object_type=partial(Literal, lang="en"),
        allow_null=False,
    )
    status = RDFField(predicate=ns.SCHEMA.creativeWorkStatus)
    created = RDFField(predicate=ns.SCHEMA.dateCreated)
    modified = RDFField(predicate=ns.SCHEMA.dateModified)
    access_url = RDFField(predicate=ns.SCHEMA.url)
    download_url = RDFField(predicate=ns.SCHEMA.contentUrl)
    file_mimetype = RDFField(predicate=ns.SCHEMA.encodingFormat)
    license = RDFField(predicate=ns.SCHEMA.license)

    def get_subject(self, data):
        return URIRef(data["access_url"])
