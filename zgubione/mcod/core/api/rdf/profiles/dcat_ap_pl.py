from functools import partial

from django.conf import settings
from rdflib import XSD, Literal, URIRef

import mcod.core.api.rdf.namespaces as ns
from mcod.core.api.rdf.profiles.common import RDFNestedField
from mcod.core.api.rdf.vocabs.openness_score import OpennessScoreVocab
from mcod.core.api.rdf.vocabs.special_sign import SpecialSignVocab
from mcod.lib.rdf.rdf_field import RDFField

from .dcat_ap import DCATCatalog, DCATDataset, DCATDistribution, FOAFAgent

VOCABULARIES = {
    "openness-score": f"{settings.API_URL}/vocab/openness-score",
    "special-sign": f"{settings.API_URL}/vocab/special-sign",
}


class ExtendedDCATCatalog(DCATCatalog):
    pass


class ExtendedDCATDataset(DCATDataset):
    resources = RDFNestedField("ExtendedDCATDistribution", predicate=ns.DCAT.distribution, many=True)
    organization = RDFNestedField("ExtendedFOAFAgent", predicate=ns.DCT.publisher)
    logo = RDFField(predicate=ns.FOAF.logo, object_type=URIRef, required=False)


class ExtendedDCATDistribution(DCATDistribution):
    validity_date = RDFField(
        predicate=ns.DCT.valid,
        object_type=partial(Literal, datatype=XSD.date),
        required=False,
    )
    openness_score = RDFNestedField("SKOSConcept", predicate=ns.DCATAPPL.opennessScore, required=False)
    special_signs = RDFNestedField("SKOSConcept", predicate=ns.DCATAPPL.specialSign, many=True)

    def get_openness_score_data(self, data):
        openness_score = data["openness_score"]
        if openness_score not in {1, 2, 3, 4, 5}:
            return None
        identifier = f"{openness_score}-star" if openness_score == 1 else f"{openness_score}-stars"
        vocab = OpennessScoreVocab()
        entry = vocab.entries[identifier]

        return {
            "subject": URIRef(f"{VOCABULARIES['openness-score']}/{identifier}"),
            "scheme": {
                "subject": URIRef(VOCABULARIES["openness-score"]),
                "title_pl": vocab.label_pl,
                "title_en": vocab.label_en,
            },
            "title_pl": entry.name_pl,
            "title_en": entry.name_en,
        }

    def get_special_signs_data(self, data):
        vocab = SpecialSignVocab()
        for sign in data["special_signs"]:
            sign.update(
                {
                    "subject": URIRef(f"{VOCABULARIES['special-sign']}/{sign['id']}"),
                    "scheme": {
                        "subject": URIRef(VOCABULARIES["special-sign"]),
                        "title_pl": vocab.label_pl,
                        "title_en": vocab.label_en,
                    },
                }
            )
        return data["special_signs"]


class ExtendedFOAFAgent(FOAFAgent):
    regon = RDFField(predicate=ns.DCATAPPL.regon)
