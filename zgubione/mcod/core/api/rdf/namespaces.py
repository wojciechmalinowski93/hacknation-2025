from rdflib.namespace import RDF, RDFS, SKOS, Namespace
from rdflib.term import bind

DCT = Namespace("http://purl.org/dc/terms/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
ADMS = Namespace("http://www.w3.org/ns/adms#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SCHEMA = Namespace("http://schema.org/")
TIME = Namespace("http://www.w3.org/2006/time")
LOCN = Namespace("http://www.w3.org/ns/locn#")
GSP = Namespace("http://www.opengis.net/ont/geosparql#")
OWL = Namespace("http://www.w3.org/2002/07/owl#")
SPDX = Namespace("http://spdx.org/rdf/terms#")
HYDRA = Namespace("http://www.w3.org/ns/hydra/core#")
DCATAPPL = Namespace("https://api.dane.gov.pl/ns/dcatappl#")

bind(datatype="http://www.opengis.net/ont/geosparql#asWKT", pythontype=str)


NAMESPACES = {
    "dct": DCT,
    "dcat": DCAT,
    "adms": ADMS,
    "vcard": VCARD,
    "foaf": FOAF,
    "schema": SCHEMA,
    "time": TIME,
    "skos": SKOS,
    "locn": LOCN,
    "gsp": GSP,
    "owl": OWL,
    "spdx": SPDX,
    "hydra": HYDRA,
    "rdf": RDF,
    "rdfs": RDFS,
}

DCAT_AP_PL_NAMESPACES = {
    **NAMESPACES,
    "dcatappl": DCATAPPL,
}
