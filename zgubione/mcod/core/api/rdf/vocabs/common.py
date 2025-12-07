from functools import partial

from rdflib import RDF, Literal, URIRef

import mcod.core.api.rdf.namespaces as ns
from mcod.core.api.rdf.profiles.common import RDFClass, RDFNestedField
from mcod.lib.rdf.rdf_field import RDFField


class VocabSKOSConcept(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.SKOS.Concept)
    name_pl = RDFField(
        predicate=ns.SKOS.prefLabel,
        object_type=partial(Literal, lang="pl"),
        required=False,
    )
    name_en = RDFField(
        predicate=ns.SKOS.prefLabel,
        object_type=partial(Literal, lang="en"),
        required=False,
    )
    description_pl = RDFField(
        predicate=ns.SKOS.definition,
        object_type=partial(Literal, lang="pl"),
        required=False,
    )
    description_en = RDFField(
        predicate=ns.SKOS.definition,
        object_type=partial(Literal, lang="en"),
        required=False,
    )
    notation = RDFField(predicate=ns.SKOS.notation, required=False)
    scheme = RDFField(predicate=ns.SKOS.inScheme, object_type=URIRef)
    top_concept_of = RDFField(predicate=ns.SKOS.topConceptOf, object_type=URIRef)

    def get_subject(self, data):
        return URIRef(data["url"])


class VocabSKOSConceptScheme(RDFClass):
    rdf_type = RDFField(predicate=RDF.type, object=ns.SKOS.ConceptScheme)
    concepts = RDFNestedField("VocabSKOSConcept", predicate=ns.SKOS.hasTopConcept, many=True)
    label_pl = RDFField(predicate=ns.RDFS.label, object_type=partial(Literal, lang="pl"), required=False)
    label_en = RDFField(predicate=ns.RDFS.label, object_type=partial(Literal, lang="en"), required=False)
    name_pl = RDFField(
        predicate=ns.SKOS.prefLabel,
        object_type=partial(Literal, lang="pl"),
        required=False,
    )
    name_en = RDFField(
        predicate=ns.SKOS.prefLabel,
        object_type=partial(Literal, lang="en"),
        required=False,
    )
    title_pl = RDFField(predicate=ns.DCT.title, object_type=partial(Literal, lang="pl"), required=False)
    title_en = RDFField(predicate=ns.DCT.title, object_type=partial(Literal, lang="en"), required=False)
    version = RDFField(predicate=ns.OWL.versionInfo, required=False)
    identifier = RDFField(predicate=ns.DCT.identifier, required=False)

    def get_subject(self, data):
        return URIRef(data["url"])

    def get_concepts_subject(self, data):
        return URIRef(data["url"])
