import pytest

from mcod.resources.score_computation.calculators import (
    calculate_score_for_json,
    calculate_score_for_rdf,
    calculate_score_for_xml,
    get_calculator_for_extension,
)
from mcod.resources.score_computation.common import OpennessScoreCalculator, OpennessScoreValue
from mcod.resources.score_computation.score_calculation import (
    get_default_openness_score_for_extension,
)


@pytest.mark.parametrize(
    "extension, expected_default_openness_score",
    (
        [
            ("abw", 1),
            ("bat", 1),
            ("bmp", 1),
            ("doc", 1),
            ("docx", 1),
            ("dot", 1),
            ("epub", 1),
            ("jpe", 1),
            ("jpeg", 1),
            ("jpg", 1),
            ("md", 1),
            ("odc", 1),
            ("odp", 1),
            ("odt", 1),
            ("pdf", 1),
            ("png", 1),
            ("pot", 1),
            ("ppa", 1),
            ("pps", 1),
            ("ppt", 1),
            ("pptx", 1),
            ("ps", 1),
            ("pwz", 1),
            ("rd", 1),
            ("rtf", 1),
            ("tif", 1),
            ("tiff", 1),
            ("txt", 1),
            ("vsd", 1),
            ("wiz", 1),
            ("gif", 2),
            ("grib", 2),
            ("grib2", 2),
            ("nc", 2),
            ("odi", 2),
            ("ppm", 2),
            ("webp", 2),
            ("xbm", 2),
            ("xlb", 2),
            ("xls", 2),
            ("xlsx", 2),
            ("csv", 3),
            ("dbf", 3),
            ("geojson", 3),
            ("geotiff", 3),
            ("gpx", 3),
            ("htm", 3),
            ("html", 3),
            ("json", 3),
            ("kml", 3),
            ("kmz", 3),
            ("odf", 3),
            ("odg", 3),
            ("ods", 3),
            ("shp", 3),
            ("svg", 3),
            ("tex", 3),
            ("texi", 3),
            ("texinfo", 3),
            ("tsv", 3),
            ("wsdl", 3),
            ("xml", 3),
            ("xpdl", 3),
            ("xsl", 3),
            ("jsonld", 4),
            ("n3", 4),
            ("nq", 4),
            ("nquads", 4),
            ("nt", 4),
            ("nt11", 4),
            ("ntriples", 4),
            ("rdf", 4),
            ("rdfa", 4),
            ("trig", 4),
            ("trix", 4),
            ("ttl", 4),
            ("turtle", 4),
            ("UNKNOWN_EXTENSION", 1),  # openness score for other extension should be 1
            ("", 1),
        ]
    ),
)
def test_default_openness_score_for_extension(extension: str, expected_default_openness_score: OpennessScoreValue):
    default_openness_score = get_default_openness_score_for_extension(extension)
    assert default_openness_score == expected_default_openness_score


@pytest.mark.parametrize(
    "extension, expected_calculator",
    (
        [
            ("json", calculate_score_for_json),
            ("xml", calculate_score_for_xml),
            ("jsonld", calculate_score_for_rdf),
            ("rdf", calculate_score_for_rdf),
            ("rdfa", calculate_score_for_rdf),
            ("ttl", calculate_score_for_rdf),
            ("turtle", calculate_score_for_rdf),
            ("n3", calculate_score_for_rdf),
            ("nt", calculate_score_for_rdf),
            ("nt11", calculate_score_for_rdf),
            ("ntriples", calculate_score_for_rdf),
            ("nq", calculate_score_for_rdf),
            ("nquads", calculate_score_for_rdf),
            ("trix", calculate_score_for_rdf),
            ("trig", calculate_score_for_rdf),
        ]
    ),
)
def test_get_calculator_for_extension(extension: str, expected_calculator: OpennessScoreCalculator):
    calculator = get_calculator_for_extension(extension)
    assert calculator == expected_calculator
