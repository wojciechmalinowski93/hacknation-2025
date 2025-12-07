import os
from pathlib import Path
from typing import List, Union

import pytest
import requests_mock
import shapefile
from django.conf import settings

from mcod.core.tests.fixtures.bdd.common import prepare_file
from mcod.resources.archives import ArchiveReader
from mcod.resources.geo import (
    ExtractUAddressError,
    ShapeTransformer,
    _has_geotiff_with_world_file,
    analyze_shapefile,
    are_shapefiles,
    clean_house_number,
    extract_coords_from_uaddress,
    geocode,
    is_geotiff,
    median_point,
)


@pytest.fixture
def shapefile_world() -> List[Union[Path, str]]:
    return [prepare_file("TM_WORLD_BORDERS-0.3.%s" % ext) for ext in ("shp", "shx", "prj", "dbf")]


@pytest.mark.parametrize(
    "shapefiles_candidate, expected_are_shapefiles",
    (
        (["minimal.shp", "minimal.dbf", "minimal.shx"], True),
        (["minimal.shx", "minimal.dbf", "minimal.shp"], True),
        (["extra_files.shx", "extra_files.dbf", "extra_files.shp", "test.xd", "test.xe"], True),
        (["test.shp", "test.dbf", "test.prj", "test.shx", "test.cst"], True),
        (["test.shp", "test.dbf", "test.txt", "other_test.csv"], False),
        (["a.shp", "b.dbf", "c.shx"], False),
        (["test.shp", "test.dbf", "test.txt", "other_test.csv", "other.shp"], False),
    ),
)
def test_are_shapefiles(shapefiles_candidate: List[str], expected_are_shapefiles: bool):
    assert are_shapefiles(shapefiles_candidate) is expected_are_shapefiles


@pytest.mark.parametrize(
    "geotiff_candidate, expected_has_tif, expected_has_geotiff_with_world_file",
    (
        (["minimal.tif", "minimal.tfw"], True, True),
        (["minimal.tiff", "minimal.tfw"], True, True),
        (["minimal.tif", "other_name.tfw"], True, True),
        (["minimal.tiff", "other_name.tfw"], True, True),
        (["just_not_tif.csv"], False, False),
        (["just_not_tif.csv", "other_name.tfw"], False, False),
        (["minimal.tif", "not-a-world-file.csv"], True, False),
        (["minimal.tiff", "not-a-world-file.csv"], True, False),
    ),
)
def test_has_geotiff_files(geotiff_candidate: List[str], expected_has_tif: bool, expected_has_geotiff_with_world_file: bool):
    assert _has_geotiff_with_world_file(geotiff_candidate) is expected_has_geotiff_with_world_file


def test_has_geotiff_files_with_real_file():
    # Special case - the .tif file needs to exist here
    expected_has_geotiff_files = True
    tiff_sample = os.path.join(settings.TEST_SAMPLES_PATH, "cea.tif")
    assert is_geotiff(tiff_sample) is expected_has_geotiff_files


def test_analyze_files():
    shp_file = prepare_file("TM_WORLD_BORDERS-0.3.shp")
    shp, options = analyze_shapefile(shp_file)
    assert shp == "POLYGON"
    assert options == {"charset": "utf-8"}


class TestTransformShpFiles:
    def test_transform_shp_files_wgs_1984_to_geojson(self, shapefile_world: List[str]):
        shp_path = next(iter(f for f in shapefile_world if f.endswith(".shp")))
        prj_path = next(iter(f for f in shapefile_world if f.endswith(".prj")))
        source = shapefile.Reader(shp_path)
        transformer = ShapeTransformer(prj_path)
        geojson_data = []
        for row_no, sr in enumerate(source.shapeRecords(), 1):
            geojson = transformer.transform(sr.shape)
            geojson_data.append(geojson)
        geo_types = set([geodata["type"] for geodata in geojson_data])
        assert len(geojson_data) == 246
        assert "coordinates" in geojson_data[0]
        assert {"Polygon", "MultiPolygon"} == geo_types

    def test_transform_shp_files_no_prj_file(self, shapefile_world: List[str]):
        new_file_list = [f for f in shapefile_world if not f.endswith(".prj")]
        shp_path = next(iter(f for f in new_file_list if f.endswith(".shp")))
        prj_path = next(iter(f for f in shapefile_world if f.endswith(".prj")))
        source = shapefile.Reader(shp_path)
        transformer = ShapeTransformer(prj_path)
        geojson_data = []
        for row_no, sr in enumerate(source.shapeRecords(), 1):
            geojson = transformer.transform(sr.shape)
            geojson_data.append(geojson)
        geo_types = set([geodata["type"] for geodata in geojson_data])
        assert len(geojson_data) == 246
        assert "coordinates" in geojson_data[0]
        assert {"Polygon", "MultiPolygon"} == geo_types

    def test_transform_shp_files_non_wgs_1984_to_geojson(self):
        media = Path(__file__).parent / "media" / "test_geo"
        shp_path = media / "iglaste.shp"
        shx_path = media / "iglaste.shx"
        dbf_path = media / "iglaste.dbf"
        other = (media / "iglaste_other.tar.xz").as_posix()
        with ArchiveReader(other) as archive_other:
            prj_path = next(archive_other.get_by_extension("prj"))
            with open(dbf_path, "rb") as dbf, open(shp_path, "rb") as shp, open(shx_path, "rb") as shx:
                source = shapefile.Reader(dbf=dbf, shp=shp, shx=shx)
                transformer = ShapeTransformer(prj_path)
                geojson_data = []
                for row_no, sr in enumerate(source.shapeRecords(), 1):
                    geojson = transformer.transform(sr.shape)
                    geojson_data.append(geojson)
                geo_types = set([geodata["type"] for geodata in geojson_data])
                assert len(geojson_data) == 48378
                assert "coordinates" in geojson_data[0]
                assert {"Point"} == geo_types


@pytest.mark.parametrize(
    "house_num, expected_num",
    [
        ("25", "25"),
        ("25A", "25"),
        ("25/12", "25"),
        ("25/1", "25/1"),
        ("55A/12", "55"),
        ("55AN", "55"),
        (25, 25),
        ("4A/292", "4"),
    ],
)
def test_clean_house_number(house_num, expected_num):
    assert clean_house_number(house_num) == expected_num


@pytest.mark.parametrize(
    "geo_coordinates, expected_point",
    [
        ({"type": "Point", "coordinates": [30.0, 10.0]}, [30.0, 10.0]),
        (
            {
                "type": "LineString",
                "coordinates": [[30.0, 12.0], [15.0, 30.0], [45.0, 33.0]],
            },
            (30.0, 25.0),
        ),
        (
            {
                "type": "MultiLineString",
                "coordinates": [
                    [[30.0, 12.0], [15.0, 30.0], [45.0, 33.0]],
                    [[40.0, 40.0], [30.0, 30.0], [40.0, 20.0], [30.0, 10.0]],
                ],
            },
            (32.5, 25.0),
        ),
        (
            {
                "type": "GeometryCollection",
                "geometries": [
                    {"type": "Point", "coordinates": [16.0, 8.0]},
                    {
                        "type": "LineString",
                        "coordinates": [[30.0, 12.0], [15.0, 30.0], [45.0, 33.0]],
                    },
                ],
            },
            (23.0, 16.5),
        ),
        (
            {
                "type": "MultiPolygon",
                "coordinates": [
                    [[[36.0, 12.0], [15.0, 30.0], [45.0, 33.0]]],
                    [
                        [
                            [20.0, 35.0],
                            [28.0, 30.0],
                            [12.0, 10.0],
                            [30.0, 5.0],
                            [45.0, 20.0],
                            [42.0, 35.0],
                        ],
                        [[30.0, 20.0], [60.0, 15.0], [15.0, 25.0], [30.0, 20.0]],
                    ],
                ],
            },
            (28.25, 20.5),
        ),
    ],
)
def test_median_point(geo_coordinates, expected_point):
    assert median_point(geo_coordinates) == expected_point


class TestGeocode:

    geocoder_url = f"{settings.GEOCODER_URL}/v1/search/structured"
    geocoder_text_url = f"{settings.GEOCODER_URL}/v1/search?text="

    @requests_mock.Mocker(kw="mock_request")
    def test_geocode_get_coordinates_from_address(self, **kwargs):
        mock_request = kwargs["mock_request"]
        mock_request.get(
            self.geocoder_url,
            json={
                "features": [
                    {
                        "geometry": {
                            "type": "Point",
                            "coordinates": [21.008889, 52.238506],
                        }
                    }
                ]
            },
        )
        geocoding_kwargs = {"address": "Królewska 27", "locality": "Warszawa"}
        result = geocode(**geocoding_kwargs)
        assert result == {"type": "Point", "coordinates": [21.008889, 52.238506]}

    @requests_mock.Mocker(kw="mock_request")
    def test_geocode_wrong_response_code(self, **kwargs):
        mock_request = kwargs["mock_request"]
        mock_request.get(self.geocoder_url, json={}, status_code=404)
        mock_request.get(self.geocoder_text_url + "Królewska 27 Warszawa", json={}, status_code=404)
        geocoding_kwargs = {"address": "Królewska 27", "locality": "Warszawa"}
        result = geocode(**geocoding_kwargs)
        assert result is None

    @requests_mock.Mocker(kw="mock_request")
    def test_geocode_no_feature_data(self, **kwargs):
        mock_request = kwargs["mock_request"]
        mock_request.get(self.geocoder_text_url + "Warszawa", json={"features": []})
        geocoding_kwargs = {"text": "Warszawa"}
        result = geocode(**geocoding_kwargs)
        assert result is None


def test_extract_coords_from_uaddress():
    coords = extract_coords_from_uaddress("00060|146501|0918123|0918123|09987|487729|637113|27|")
    assert coords == (21.008654028022857, 52.23850135904742)


def test_extract_coords_from_uaddress_raise_error():
    try:
        extract_coords_from_uaddress("05075|146501|0918123|0918123|00432|115|")
        raise pytest.fail("No exception occurred. Expected: ExtractUAddressError")
    except ExtractUAddressError as err:
        assert err.args[0] == "05075|146501|0918123|0918123|00432|115|"
