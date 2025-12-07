import re

import dpath.util
import pytest
from django.apps import apps
from django.conf import settings
from pytest_bdd import parsers, then

from mcod.regions.api import PlaceholderApi


@pytest.fixture
def main_regions_response():
    return {
        "101752777": {
            "id": 101752777,
            "name": "Warszawa",
            "placetype": "locality",
            "rank": {"min": 9, "max": 10},
            "population": 1702139,
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 1477743805,
                    "localadmin_id": 1125365875,
                    "locality_id": 101752777,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.068027,
                "bbox": "20.851688,52.09785,21.271151,52.368154",
                "lat": 52.237695,
                "lon": 21.005427,
            },
            "names": {"eng": ["Warsaw"], "pol": ["Warszawa"]},
        },
        "1309742673": {
            "id": 1309742673,
            "name": "Wola Kosowska",
            "placetype": "locality",
            "rank": {"min": 9, "max": 10},
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 102079911,
                    "localadmin_id": 1125356333,
                    "locality_id": 1309742673,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "bbox": "20.82012,52.03683,20.86012,52.07683",
                "lat": 52.05683,
                "lon": 20.84012,
            },
            "names": {"pol": ["Wólka Kosowska"]},
        },
    }


@pytest.fixture
def main_region_response():
    return {
        "101752777": {
            "id": 101752777,
            "name": "Warszawa",
            "placetype": "locality",
            "rank": {"min": 9, "max": 10},
            "population": 1702139,
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 1477743805,
                    "localadmin_id": 1125365875,
                    "locality_id": 101752777,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.068027,
                "bbox": "20.851688,52.09785,21.271151,52.368154",
                "lat": 52.237695,
                "lon": 21.005427,
            },
            "names": {"eng": ["Warsaw"], "pol": ["Warszawa"]},
        }
    }


@pytest.fixture
def warsaw_additional_regions_response():
    return {
        "85687257": {
            "id": 85687257,
            "name": "Mazowieckie",
            "abbr": "MZ",
            "placetype": "region",
            "rank": {"min": 14, "max": 15},
            "population": 5268660,
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 4.689476,
                "bbox": "19.259214,51.013112,23.128409,53.481806",
                "lat": 52.512784,
                "lon": 21.125296,
            },
            "names": {"eng": ["Mazowieckie"], "pol": ["mazowieckie"]},
        },
        "1125365875": {
            "id": 1125365875,
            "name": "Gmina Warszawa",
            "placetype": "localadmin",
            "rank": {"min": 11, "max": 12},
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 1477743805,
                    "localadmin_id": 1125365875,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.068027,
                "bbox": "20.851688337,52.097849611,21.271151295,52.368153943",
                "lat": 52.2331,
                "lon": 21.0614,
            },
            "names": {
                "deu": ["Warschau"],
                "eng": ["Warsaw"],
                "fra": ["Varsovie"],
                "pol": ["Gmina Warszawa"],
            },
        },
        "1477743805": {
            "id": 1477743805,
            "name": "Warszawa",
            "placetype": "county",
            "rank": {"min": 12, "max": 13},
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 1477743805,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.068027,
                "bbox": "20.851688,52.09785,21.271151,52.368154",
                "lat": 52.245513,
                "lon": 21.001878,
            },
            "names": {"fra": ["Varsovie"], "pol": ["Warszawa"]},
        },
    }


@pytest.fixture
def wof_ids_regions_response():
    return {
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [21.005427, 52.237695]},
                "properties": {
                    "id": "101752777",
                    "gid": "whosonfirst:locality:101752777",
                    "layer": "locality",
                    "source": "whosonfirst",
                    "source_id": "101752777",
                    "country_code": "PL",
                    "name": "Warszawa",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Warszawa",
                    "county_gid": "whosonfirst:county:1477743805",
                    "localadmin": "Gmina Warszawa",
                    "localadmin_gid": "whosonfirst:localadmin:1125365875",
                    "locality": "Warszawa",
                    "locality_gid": "whosonfirst:locality:101752777",
                    "label": "Warszawa, MZ, Polska",
                    "addendum": {
                        "concordances": {
                            "dbp:id": "Warsaw",
                            "fb:id": "en.warsaw",
                            "fct:id": "024ce880-8f76-11e1-848f-cfd5bf3ef515",
                            "gn:id": 756135,
                            "gp:id": 523920,
                            "loc:id": "n79018894",
                            "ne:id": 1159151299,
                            "nyt:id": "N38439611599745838241",
                            "qs_pg:id": 900428,
                            "wd:id": "Q270",
                            "wk:page": "Warsaw",
                        }
                    },
                },
                "bbox": [20.851688, 52.09785, 21.271151, 52.368154],
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [21.0614, 52.2331]},
                "properties": {
                    "id": "1125365875",
                    "gid": "whosonfirst:localadmin:1125365875",
                    "layer": "localadmin",
                    "source": "whosonfirst",
                    "source_id": "1125365875",
                    "country_code": "PL",
                    "name": "Gmina Warszawa",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Warszawa",
                    "county_gid": "whosonfirst:county:1477743805",
                    "localadmin": "Gmina Warszawa",
                    "localadmin_gid": "whosonfirst:localadmin:1125365875",
                    "label": "Gmina Warszawa, MZ, Polska",
                    "addendum": {
                        "concordances": {
                            "gn:id": 7531926,
                            "gp:id": 24548810,
                            "qs_pg:id": 1175844,
                            "qs:id": 1175844,
                        }
                    },
                },
                "bbox": [20.851688337, 52.097849611, 21.271151295, 52.368153943],
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [21.125296, 52.512784]},
                "properties": {
                    "id": "85687257",
                    "gid": "whosonfirst:region:85687257",
                    "layer": "region",
                    "source": "whosonfirst",
                    "source_id": "85687257",
                    "country_code": "PL",
                    "name": "mazowieckie",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "label": "mazowieckie, Polska",
                    "addendum": {
                        "concordances": {
                            "digitalenvoy:region_code": 14344,
                            "fips:code": "PL78",
                            "hasc:id": "PL.MZ",
                            "iso:id": "PL-MZ",
                            "pl-gugik": "14",
                            "unlc:id": "PL-MZ",
                            "wd:id": "Q54169",
                        }
                    },
                },
                "bbox": [19.259214, 51.013112, 23.128409, 53.481806],
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [21.001878, 52.245513]},
                "properties": {
                    "id": "1477743805",
                    "gid": "whosonfirst:county:1477743805",
                    "layer": "county",
                    "source": "whosonfirst",
                    "source_id": "1477743805",
                    "country_code": "PL",
                    "name": "Warszawa",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Warszawa",
                    "county_gid": "whosonfirst:county:1477743805",
                    "label": "Warszawa, MZ, Polska",
                    "addendum": {"concordances": {"pl-gugik": "1465"}},
                },
                "bbox": [20.851688, 52.09785, 21.271151, 52.368154],
            },
        ]
    }


@pytest.fixture
def additional_regions_response():
    return {
        "85687257": {
            "id": 85687257,
            "name": "Mazowieckie",
            "abbr": "MZ",
            "placetype": "region",
            "rank": {"min": 14, "max": 15},
            "population": 5268660,
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 4.689476,
                "bbox": "19.259214,51.013112,23.128409,53.481806",
                "lat": 52.512784,
                "lon": 21.125296,
            },
            "names": {"eng": ["Mazowieckie"], "pol": ["mazowieckie"]},
        },
        "102079911": {
            "id": 102079911,
            "name": "Piaseczyński",
            "placetype": "county",
            "rank": {"min": 12, "max": 13},
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 102079911,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.081285,
                "bbox": "20.685116,51.887954,21.281262,52.144728",
                "lat": 52.020263,
                "lon": 21.044128,
            },
            "names": {"fra": ["Piaseczno"], "pol": ["Piaseczyński"]},
        },
        "1125356333": {
            "id": 1125356333,
            "name": "Lesznowola",
            "placetype": "localadmin",
            "rank": {"min": 11, "max": 12},
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 102079911,
                    "localadmin_id": 1125356333,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.009084,
                "bbox": "20.809666165,52.021535516,21.035504392,52.120636077",
                "lat": 52.090032,
                "lon": 20.941123,
            },
            "names": {"pol": ["Lesznowola"]},
        },
        "1125365875": {
            "id": 1125365875,
            "name": "Gmina Warszawa",
            "placetype": "localadmin",
            "rank": {"min": 11, "max": 12},
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 1477743805,
                    "localadmin_id": 1125365875,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.068027,
                "bbox": "20.851688337,52.097849611,21.271151295,52.368153943",
                "lat": 52.2331,
                "lon": 21.0614,
            },
            "names": {
                "deu": ["Warschau"],
                "eng": ["Warsaw"],
                "fra": ["Varsovie"],
                "pol": ["Gmina Warszawa"],
            },
        },
        "1477743805": {
            "id": 1477743805,
            "name": "Warszawa",
            "placetype": "county",
            "rank": {"min": 12, "max": 13},
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 1477743805,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.068027,
                "bbox": "20.851688,52.09785,21.271151,52.368154",
                "lat": 52.245513,
                "lon": 21.001878,
            },
            "names": {"fra": ["Varsovie"], "pol": ["Warszawa"]},
        },
    }


@pytest.fixture
def main_region():
    region = apps.get_model("regions", "Region")
    return region.objects.create(
        name="Warszawa",
        region_id=101752777,
        region_type="locality",
        lat=52.237695,
        lng=21.005427,
        bbox=[20.851688, 52.09785, 21.271151, 52.368154],
        geonames_id=756135,
        hierarchy_label="Warszawa, Gmina Warszawa, pow. Warszawa, woj. mazowieckie",
    )


@pytest.fixture
def wroclaw_main_region():
    region = apps.get_model("regions", "Region")
    return region.objects.create(
        name="Wrocław",
        region_id=101752181,
        region_type="locality",
        lat=51.097349,
        lng=17.023978,
        bbox=[16.807339, 51.21006, 17.176219, 51.042669],
        geonames_id=None,
        hierarchy_label="Wrocław, Gmina Wrocław, pow. Wrocław, woj. dolnośląskie",
    )


@pytest.fixture
def teryt_regions_response():
    return {
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [21.047816, 52.229286]},
                "properties": {
                    "id": "0918123",
                    "gid": "teryt:locality:0918123",
                    "layer": "locality",
                    "source": "teryt",
                    "source_id": "0918123",
                    "country_code": "PL",
                    "name": "Warszawa",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Warszawa",
                    "county_gid": "whosonfirst:county:1477743805",
                    "localadmin": "Gmina Warszawa",
                    "localadmin_gid": "whosonfirst:localadmin:1125365875",
                    "locality": "Warszawa",
                    "locality_gid": "whosonfirst:locality:101752777",
                    "label": "Warszawa, MZ, Polska",
                },
            }
        ],
    }


@pytest.fixture
def main_teryt_region_response():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [20.849725, 52.058357]},
                "properties": {
                    "id": "0005084",
                    "gid": "teryt:locality:0005084",
                    "layer": "locality",
                    "source": "teryt",
                    "source_id": "0005084",
                    "country_code": "PL",
                    "name": "Wólka Kosowska",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Piaseczyński",
                    "county_gid": "whosonfirst:county:102079911",
                    "localadmin": "Lesznowola",
                    "localadmin_gid": "whosonfirst:localadmin:1125356333",
                    "label": "Wólka Kosowska, Lesznowola, MZ, Polska",
                    "addendum": {
                        "terytdata": {
                            "teryt_name": "Wólka Kosowska",
                            "teryt_admin_area_id": "1418032",
                        }
                    },
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [21.047816, 52.229286]},
                "properties": {
                    "id": "0918123",
                    "gid": "teryt:locality:0918123",
                    "layer": "locality",
                    "source": "teryt",
                    "source_id": "0918123",
                    "country_code": "PL",
                    "name": "Warszawa",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Warszawa",
                    "county_gid": "whosonfirst:county:1477743805",
                    "localadmin": "Gmina Warszawa",
                    "localadmin_gid": "whosonfirst:localadmin:1125365875",
                    "locality": "Warszawa",
                    "locality_gid": "whosonfirst:locality:101752777",
                    "label": "Warszawa, MZ, Polska",
                    "addendum": {
                        "terytdata": {
                            "teryt_name": "Warszawa",
                            "teryt_admin_area_id": "1465011",
                        }
                    },
                },
            },
        ],
        "bbox": [20.849725, 52.058357, 21.047816, 52.229286],
    }


@pytest.fixture
def additional_teryt_regions_response():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [21.096447, 52.345756]},
                "properties": {
                    "id": "14",
                    "gid": "teryt:region:14",
                    "layer": "region",
                    "source": "teryt",
                    "source_id": "14",
                    "country_code": "PL",
                    "name": "mazowieckie",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "label": "mazowieckie, Polska",
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [21.019279, 52.011262]},
                "properties": {
                    "id": "1418",
                    "gid": "teryt:county:1418",
                    "layer": "county",
                    "source": "teryt",
                    "source_id": "1418",
                    "country_code": "PL",
                    "name": "Piaseczyński",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Piaseczyński",
                    "county_gid": "whosonfirst:county:102079911",
                    "label": "Piaseczyński, MZ, Polska",
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [20.914684, 52.074476]},
                "properties": {
                    "id": "1418032",
                    "gid": "teryt:localadmin:1418032",
                    "layer": "localadmin",
                    "source": "teryt",
                    "source_id": "1418032",
                    "country_code": "PL",
                    "name": "Lesznowola",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Piaseczyński",
                    "county_gid": "whosonfirst:county:102079911",
                    "localadmin": "Lesznowola",
                    "localadmin_gid": "whosonfirst:localadmin:1125356333",
                    "label": "Lesznowola, MZ, Polska",
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [21.047739, 52.229334]},
                "properties": {
                    "id": "1465",
                    "gid": "teryt:county:1465",
                    "layer": "county",
                    "source": "teryt",
                    "source_id": "1465",
                    "country_code": "PL",
                    "name": "Warszawa",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Warszawa",
                    "county_gid": "whosonfirst:county:1477743805",
                    "label": "Warszawa, MZ, Polska",
                },
            },
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [21.047739, 52.229334]},
                "properties": {
                    "id": "1465011",
                    "gid": "teryt:localadmin:1465011",
                    "layer": "localadmin",
                    "source": "teryt",
                    "source_id": "1465011",
                    "country_code": "PL",
                    "name": "Gmina Warszawa",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Warszawa",
                    "county_gid": "whosonfirst:county:1477743805",
                    "localadmin": "Gmina Warszawa",
                    "localadmin_gid": "whosonfirst:localadmin:1125365875",
                    "label": "Gmina Warszawa, MZ, Polska",
                },
            },
        ],
        "bbox": [20.914684, 52.011262, 21.096447, 52.345756],
    }


@pytest.fixture
def placeholder_wof_response():
    return {
        "85687257": {
            "id": 85687257,
            "name": "Mazowieckie",
            "abbr": "MZ",
            "placetype": "region",
            "rank": {"min": 14, "max": 15},
            "population": 5268660,
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 4.689476,
                "bbox": "19.259214,51.013112,23.128409,53.481806",
                "lat": 52.512784,
                "lon": 21.125296,
            },
            "names": {"eng": ["Warsaw"], "pol": ["Warszawa"]},
        },
        "101752777": {
            "id": 101752777,
            "name": "Warszawa",
            "placetype": "locality",
            "rank": {"min": 9, "max": 10},
            "population": 1702139,
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 1477743805,
                    "localadmin_id": 1125365875,
                    "locality_id": 101752777,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.068027,
                "bbox": "20.851688,52.09785,21.271151,52.368154",
                "lat": 52.237695,
                "lon": 21.005427,
            },
            "names": {"eng": ["Warsaw"], "pol": ["Warszawa"]},
        },
        "102079911": {
            "id": 102079911,
            "name": "Piaseczyński",
            "placetype": "county",
            "rank": {"min": 12, "max": 13},
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 102079911,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.081285,
                "bbox": "20.685116,51.887954,21.281262,52.144728",
                "lat": 52.020263,
                "lon": 21.044128,
            },
            "names": {"fra": ["Piaseczno"], "pol": ["Piaseczyński"]},
        },
        "1125356333": {
            "id": 1125356333,
            "name": "Lesznowola",
            "placetype": "localadmin",
            "rank": {"min": 11, "max": 12},
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 102079911,
                    "localadmin_id": 1125356333,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.009084,
                "bbox": "20.809666165,52.021535516,21.035504392,52.120636077",
                "lat": 52.090032,
                "lon": 20.941123,
            },
            "names": {"pol": ["Lesznowola"]},
        },
        "1125365875": {
            "id": 1125365875,
            "name": "Gmina Warszawa",
            "placetype": "localadmin",
            "rank": {"min": 11, "max": 12},
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 1477743805,
                    "localadmin_id": 1125365875,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.068027,
                "bbox": "20.851688337,52.097849611,21.271151295,52.368153943",
                "lat": 52.2331,
                "lon": 21.0614,
            },
            "names": {
                "deu": ["Warschau"],
                "eng": ["Warsaw"],
                "fra": ["Varsovie"],
                "pol": ["Gmina Warszawa"],
            },
        },
        "1477743805": {
            "id": 1477743805,
            "name": "Warszawa",
            "placetype": "county",
            "rank": {"min": 12, "max": 13},
            "lineage": [
                {
                    "continent_id": 102191581,
                    "country_id": 85633723,
                    "county_id": 1477743805,
                    "region_id": 85687257,
                }
            ],
            "geom": {
                "area": 0.068027,
                "bbox": "20.851688,52.09785,21.271151,52.368154",
                "lat": 52.245513,
                "lon": 21.001878,
            },
            "names": {"fra": ["Varsovie"], "pol": ["Warszawa"]},
        },
    }


@pytest.fixture
def wof_gn_response():
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [21.005427, 52.237695]},
                "properties": {
                    "id": "101752777",
                    "gid": "whosonfirst:locality:101752777",
                    "layer": "locality",
                    "source": "whosonfirst",
                    "source_id": "101752777",
                    "country_code": "PL",
                    "name": "Warszawa",
                    "accuracy": "centroid",
                    "country": "Polska",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Warszawa",
                    "county_gid": "whosonfirst:county:1477743805",
                    "localadmin": "Gmina Warszawa",
                    "localadmin_gid": "whosonfirst:localadmin:1125365875",
                    "locality": "Warszawa",
                    "locality_gid": "whosonfirst:locality:101752777",
                    "label": "Warszawa, MZ, Polska",
                    "addendum": {
                        "concordances": {
                            "dbp:id": "Warsaw",
                            "fb:id": "en.warsaw",
                            "fct:id": "024ce880-8f76-11e1-848f-cfd5bf3ef515",
                            "gn:id": 756135,
                            "gp:id": 523920,
                            "loc:id": "n79018894",
                            "ne:id": 1159151299,
                            "nyt:id": "N38439611599745838241",
                            "qs_pg:id": 900428,
                            "wd:id": "Q270",
                            "wk:page": "Warsaw",
                        }
                    },
                },
                "bbox": [20.851688, 52.09785, 21.271151, 52.368154],
            }
        ],
        "bbox": [20.851688, 52.09785, 21.271151, 52.368154],
    }


@pytest.fixture
def additional_regions(additional_regions_response):
    to_create_regions = ["1477743805", "1125365875", "85687257"]
    region = apps.get_model("regions", "Region")
    api = PlaceholderApi()
    api.add_hierarchy_labels(additional_regions_response)
    created_regions = region.objects.bulk_create(
        [
            region(
                region_id=reg_id,
                region_type=additional_regions_response[reg_id]["placetype"],
                name_pl=(
                    additional_regions_response[reg_id]["names"]["pol"][0]
                    if additional_regions_response[reg_id]["names"].get("pol")
                    else additional_regions_response[reg_id]["name"]
                ),
                name_en=(
                    additional_regions_response[reg_id]["names"]["eng"][0]
                    if additional_regions_response[reg_id]["names"].get("eng")
                    else additional_regions_response[reg_id]["name"]
                ),
                bbox=additional_regions_response[reg_id]["geom"]["bbox"].split(","),
                lat=additional_regions_response[reg_id]["geom"]["lat"],
                lng=additional_regions_response[reg_id]["geom"]["lon"],
                hierarchy_label_pl=additional_regions_response[reg_id]["hierarchy_label_pl"],
                hierarchy_label_en=additional_regions_response[reg_id]["hierarchy_label_en"],
            )
            for reg_id in to_create_regions
        ]
    )
    return created_regions


@pytest.fixture
def mocked_geocoder_responses(
    main_regions_response,
    additional_regions_response,
    main_teryt_region_response,
    additional_teryt_regions_response,
    placeholder_wof_response,
    wof_gn_response,
):
    main_reg_expr = re.compile(settings.GEOCODER_URL + r"/v1/place\?ids=teryt%3Alocality%3A\d{7}%2Cteryt%3Alocality%3A\d{7}")
    additional_reg_expr = re.compile(
        settings.GEOCODER_URL + r"/v1/place\?ids=teryt%3A\w+%3A\d{2,7}%2Cteryt%3A\w+%3A\d{2,7}%2Cteryt%3A\w+%3A\d{2,7}%2C"
        r"teryt%3A\w+%3A\d{2,7}%2Cteryt%3A\w+%3A\d{2,7}"
    )
    placeholder_resp_expr = re.compile(
        settings.PLACEHOLDER_URL + r"/parser/findbyid\?ids=\d{8,10}%2C\d{8,10}%2C\d{8,10}%2C\d{8,10}%2C\d{8,10}%2C\d{8,10}"
    )
    gn_reg_expr = re.compile(settings.GEOCODER_URL + r"/v1/place\?ids=whosonfirst%3A\w+%3A\d{8,10}")
    mocked_responses = [
        (main_reg_expr, main_teryt_region_response),
        (additional_reg_expr, additional_teryt_regions_response),
        (placeholder_resp_expr, placeholder_wof_response),
        (gn_reg_expr, wof_gn_response),
    ]
    return mocked_responses


@pytest.fixture
def mocked_geocoder_responses_for_xml_import(
    main_regions_response,
    additional_regions_response,
    teryt_regions_response,
    wof_ids_regions_response,
    main_teryt_region_response,
    additional_teryt_regions_response,
    placeholder_wof_response,
    wof_gn_response,
):
    main_reg_expr = re.compile(settings.GEOCODER_URL + r"/v1/place\?ids=teryt%3Alocality%3A\d{7}")
    additional_reg_expr = re.compile(
        settings.GEOCODER_URL + r"/v1/place\?ids=teryt%3A\w+%3A\d{2,7}%2Cteryt%3A\w+%3A\d{2,7}%2Cteryt%3A\w+%3A\d{2,7}"
    )
    placeholder_resp_expr = re.compile(
        settings.PLACEHOLDER_URL + r"/parser/findbyid\?ids=\d{8,10}%2C\d{8,10}%2C\d{8,10}%2C\d{8,10}"
    )
    gn_reg_expr = re.compile(settings.GEOCODER_URL + r"/v1/place\?ids=whosonfirst%3A\w+%3A\d{8,10}")
    main_teryt_region_response["features"].pop(0)
    additional_teryt_regions_response["features"] = [
        f for f in additional_teryt_regions_response["features"] if f["properties"]["id"] not in ["1418032", "1418"]
    ]
    placeholder_wof_response.pop("102079911")
    placeholder_wof_response.pop("1125356333")
    mocked_responses = [
        (main_reg_expr, main_teryt_region_response),
        (additional_reg_expr, additional_teryt_regions_response),
        (placeholder_resp_expr, placeholder_wof_response),
        (gn_reg_expr, wof_gn_response),
    ]
    return mocked_responses


@then("resource has assigned main and additional regions")
def resource_has_assigned_regions():
    model = apps.get_model("resources", "resource")
    res = model.objects.all().last()
    expected_main = ["0005084", "0918123"]
    expected_additional = ["14", "1418", "1418032", "1465", "1465011"]
    main_regions = list(res.regions.filter(resourceregion__is_additional=False).values_list("region_id", flat=True))
    additional_regions = list(res.regions.filter(resourceregion__is_additional=True).values_list("region_id", flat=True))
    assert sorted(main_regions) == sorted(expected_main)
    assert sorted(additional_regions) == sorted(expected_additional)


@then(parsers.parse("has assigned {field_values} as {field_name} for regions"))
def has_regions_names_assigned(field_values, field_name, context):
    values = [x.strip() for x in field_values.split(",")]
    items = dpath.util.values(context.response.json, "data/[0]/attributes/regions")
    current_values = [str(item[field_name]) for item in items[0]]
    assert set(values).issubset(set(current_values))
