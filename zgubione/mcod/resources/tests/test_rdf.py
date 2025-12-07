import pytest
from falcon import HTTP_NOT_FOUND, HTTP_OK
from pytest_bdd import scenarios
from rdflib import Literal, URIRef

import mcod.core.api.rdf.namespaces as ns
from mcod.core.api.rdf.profiles.dcat_ap_pl import VOCABULARIES as DCAT_AP_PL_VOCABULARIES
from mcod.core.api.rdf.vocabs.openness_score import OpennessScoreVocab
from mcod.core.api.rdf.vocabs.special_sign import SpecialSignVocab
from mcod.lib.extended_graph import ExtendedGraph

scenarios("features/resource_rdf.feature")
scenarios("features/resource_sparql.feature")

vocabs_pl = DCAT_AP_PL_VOCABULARIES


def test_openness_score_vocab(client14):
    response = client14.simulate_get("/vocab/openness-score")
    vocab = OpennessScoreVocab()
    identifiers = ["1-star", "2-stars", "3-stars", "4-stars", "5-stars"]
    triples = get_vocab_triples(vocab, identifiers)
    expected_rdf = triples_to_rdf(triples)
    assert expected_rdf == response.text
    assert HTTP_OK == response.status


def test_openness_score_vocab_nonexisting_entry(client14):
    response = client14.simulate_get("/vocab/openness-score/NONEXISTING")
    assert '''"Openness Score Vocabulary doesn't have 'NONEXISTING' entry."''' == response.text
    assert HTTP_NOT_FOUND == response.status


@pytest.mark.parametrize("score", [1, 2, 3, 4, 5])
def test_openness_score_vocab_entry(client14, score):
    identifier = f"{score}-star" if score == 1 else f"{score}-stars"
    response = client14.simulate_get(f"/vocab/openness-score/{identifier}")
    vocab = OpennessScoreVocab()
    entry = vocab.entries[identifier]
    expected_rdf = triples_to_rdf(get_vocab_entry_triples(entry, vocab.url))
    assert expected_rdf == response.text
    assert HTTP_OK == response.status


def test_special_sign_vocab(client14, special_signs):
    response = client14.simulate_get("/vocab/special-sign")
    vocab = SpecialSignVocab()
    identifiers = [str(sign.id) for sign in special_signs]
    triples = get_vocab_triples(vocab, identifiers)
    expected_rdf = triples_to_rdf(triples)
    assert expected_rdf == response.text
    assert HTTP_OK == response.status


def test_special_sign_vocab_nonexisting_entry(client14):
    response = client14.simulate_get("/vocab/special-sign/NONEXISTING")
    assert '''"Special Sign Vocabulary doesn't have 'NONEXISTING' entry."''' == response.text
    assert HTTP_NOT_FOUND == response.status


def test_special_sign_vocab_entry(client14, special_sign):
    sign = special_sign
    response = client14.simulate_get(f"/vocab/special-sign/{sign.id}")
    vocab = SpecialSignVocab()
    entry = vocab.entries[str(sign.id)]
    expected_rdf = triples_to_rdf(get_vocab_entry_triples(entry, vocab.url))
    assert expected_rdf == response.text
    assert HTTP_OK == response.status


def triples_to_rdf(triples):
    graph = ExtendedGraph(ordered=True)
    for prefix, namespace in ns.DCAT_AP_PL_NAMESPACES.items():
        graph.bind(prefix, namespace)

    for triple in triples:
        graph.add(triple)

    return graph.serialize(format="application/rdf+xml")


def get_vocab_entry_triples(entry, vocab_uri):
    vocab_ref = URIRef(vocab_uri)
    entry_uri = entry.url
    entry_ref = URIRef(entry_uri)
    triples = [
        (entry_ref, ns.RDF.type, ns.SKOS.Concept),
        (entry_ref, ns.SKOS.inScheme, vocab_ref),
        (entry_ref, ns.SKOS.topConceptOf, vocab_ref),
    ]
    if entry.notation:
        triples.append((entry_ref, ns.SKOS.notation, Literal(entry.notation)))
    if entry.name_pl:
        triples.append((entry_ref, ns.SKOS.prefLabel, Literal(entry.name_pl, lang="pl")))
    if entry.name_en:
        triples.append((entry_ref, ns.SKOS.prefLabel, Literal(entry.name_en, lang="en")))
    if entry.description_pl:
        triples.append((entry_ref, ns.SKOS.definition, Literal(entry.description_pl, lang="pl")))
    if entry.description_en:
        triples.append((entry_ref, ns.SKOS.definition, Literal(entry.description_en, lang="en")))
    return triples


def get_vocab_triples(vocab, identifiers):
    vocab_uri = vocab.url
    vocab_ref = URIRef(vocab_uri)
    triples = [
        (vocab_ref, ns.RDF.type, ns.SKOS.ConceptScheme),
        (vocab_ref, ns.DCT.title, Literal(vocab.label_pl, lang="pl")),
        (vocab_ref, ns.DCT.title, Literal(vocab.label_en, lang="en")),
        (vocab_ref, ns.RDFS.label, Literal(vocab.label_pl, lang="pl")),
        (vocab_ref, ns.RDFS.label, Literal(vocab.label_en, lang="en")),
        (vocab_ref, ns.SKOS.prefLabel, Literal(vocab.label_pl, lang="pl")),
        (vocab_ref, ns.SKOS.prefLabel, Literal(vocab.label_en, lang="en")),
        (vocab_ref, ns.DCT.identifier, Literal(vocab_uri)),
        (vocab_ref, ns.OWL.versionInfo, Literal(vocab.version)),
    ]
    for identifier in identifiers:
        entry = vocab.entries[identifier]
        entry_ref = URIRef(entry.url)
        triples.append((vocab_ref, ns.SKOS.hasTopConcept, entry_ref))
        triples.extend(get_vocab_entry_triples(entry, vocab_uri))

    return triples
