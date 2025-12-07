import csv
import io
import json
import os
import xml.etree.ElementTree as ET
import zipfile
from datetime import date
from typing import Union

import pytest
import xmlschema
from dateutil import parser
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.test import override_settings
from pytest_bdd import given, parsers, then, when
from pytest_mock import MockerFixture

from mcod.categories.factories import CategoryFactory
from mcod.core.tests.fixtures.bdd.common import (
    copyfile,
    create_object,
    prepare_dbf_file,
    prepare_file,
)
from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.datasets.factories import DatasetFactory, SupplementFactory as DatasetSupplementFactory
from mcod.datasets.models import Dataset
from mcod.datasets.tasks import send_dataset_update_reminder
from mcod.harvester.factories import DataSourceFactory
from mcod.harvester.models import DataSource
from mcod.resources.factories import (
    ChartFactory,
    ResourceFactory,
    SupplementFactory as ResourceSupplementFactory,
)
from mcod.showcases.factories import ShowcaseFactory
from mcod.special_signs.factories import SpecialSignFactory
from mcod.tags.factories import TagFactory


@pytest.fixture
def dataset():
    _dataset = DatasetFactory.create()
    TagFactory.create_batch(2, datasets=(_dataset,))
    return _dataset


@pytest.fixture
def imported_ckan_dataset(ckan_data_source: DataSource) -> Dataset:
    _dataset = DatasetFactory.create(source=ckan_data_source)
    return _dataset


@pytest.fixture
def imported_xml_dataset(xml_data_source: DataSource) -> Dataset:
    _dataset = DatasetFactory.create(source=xml_data_source)
    return _dataset


@pytest.fixture
def dataset_with_run_events(dataset):
    """Returns a dataset after executing all pending on_commit hooks."""
    run_on_commit_events()
    return dataset


@given("dataset")
def create_dataset(dataset):
    return dataset


@given("removed dataset")
def removed_dataset():
    _dataset = DatasetFactory.create(is_removed=True, title="Removed dataset")
    return _dataset


@pytest.fixture
def dataset_with_resources():
    _dataset = DatasetFactory.create()
    ResourceFactory.create_batch(2, dataset=_dataset)
    run_on_commit_events()
    return _dataset


@pytest.fixture
def dataset_with_dga_resource() -> Dataset:
    _dataset = DatasetFactory.create()
    ResourceFactory.create(contains_protected_data=True, dataset=_dataset)
    run_on_commit_events()
    return _dataset


@pytest.fixture
def dataset_with_resources_with_mocked_path(mocker: MockerFixture, tmp_path: str) -> Dataset:
    """
    Fixture for generating a dataset with a resources. Overriding a media location
    property for dataset archives, ensuring it returns a temporary path provided by the
    'tmp_path' fixture. It is basically duplicated fixture dataset_with_resources,
    adding an extra mocker.
    """
    mocker_object = "mcod.core.storages.DatasetsArchivesStorage.location"
    mocker.patch(mocker_object, return_value=tmp_path, new_callable=mocker.PropertyMock)
    _dataset = DatasetFactory.create()
    ResourceFactory.create_batch(2, dataset=_dataset)
    run_on_commit_events()
    return _dataset


@given("dataset with resources")
def create_dataset_with_resources(dataset_with_resources):
    return dataset_with_resources


@given(parsers.parse("dataset with id {dataset_id:d} and institution {organization_id:d}"))
def dataset_with_organization(dataset_id, organization_id):
    organization = create_object("institution", organization_id)
    return create_object("dataset", dataset_id, organization=organization)


@given(parsers.parse("dataset with id {dataset_id:d} and title {dataset_title} and institution {organization_id:d}"))
def dataset_with_title_and_organization(dataset_id, dataset_title, organization_id):
    organization = create_object("institution", organization_id)
    return create_object("dataset", dataset_id, title=dataset_title, organization=organization)


@given("dataset with chart as visualization type")
def dataset_with_chart_as_visualization_type():
    _dataset = DatasetFactory.create()
    _resource = ResourceFactory(
        dataset=_dataset,
        link="https://github.com/frictionlessdata/goodtables-py/blob/master/data/valid.csv",
    )
    ChartFactory.create(resource=_resource, is_default=True)
    _dataset.save()
    return _dataset


@given("dataset with map as visualization type")
def dataset_with_map_as_visualization_type(geo_tabular_data_resource):
    return geo_tabular_data_resource.dataset


@given(parsers.parse("dataset for data {dataset_data} imported from {source_type} named {name} with url {portal_url}"))
def imported_dataset(dataset_data, source_type, name, portal_url):
    dataset_data = json.loads(dataset_data)
    _source = DataSourceFactory.create(source_type=source_type, name=name, portal_url=portal_url)
    _dataset = DatasetFactory.create(source=_source, **dataset_data)
    ResourceFactory.create(dataset=_dataset)
    return _dataset


@given(parsers.parse("resource with id {resource_id} imported from {source_type} named {name} with url {portal_url}"))
def imported_resource(resource_id, source_type, name, portal_url):
    _source = DataSourceFactory.create(source_type=source_type, name=name, portal_url=portal_url)
    _dataset = DatasetFactory.create(source=_source)
    _resource = ResourceFactory.create(id=resource_id, dataset=_dataset)
    return _resource


@given(
    parsers.parse(
        "resource with id {resource_id} imported from {source_type} named {name} with url {portal_url}" " and type {res_type}"
    )
)
def imported_resource_of_type(resource_id, source_type, name, portal_url, res_type):
    _source = DataSourceFactory.create(source_type=source_type, name=name, portal_url=portal_url)
    _dataset = DatasetFactory.create(source=_source)
    _resource = ResourceFactory.create(id=resource_id, dataset=_dataset, type=res_type)
    return _resource


@pytest.fixture
def dataset_with_resource():
    _dataset = DatasetFactory.create()
    ResourceFactory.create(dataset=_dataset)
    CategoryFactory.create_batch(2, datasets=(_dataset,))
    run_on_commit_events()
    return _dataset


@given("dataset with resource")
def create_dataset_with_resource(dataset_with_resource):
    return dataset_with_resource


@pytest.fixture
def dataset_with_resource_with_special_signs():
    _dataset = DatasetFactory.create()
    _resource = ResourceFactory.create(dataset=_dataset)
    CategoryFactory.create_batch(2, datasets=(_dataset,))
    SpecialSignFactory.create_batch(2, special_signs_resources=(_resource,))
    run_on_commit_events()
    return _dataset


@given("dataset with resource with special signs")
def create_dataset_with_resource_with_special_signs(
    dataset_with_resource_with_special_signs,
):
    return dataset_with_resource_with_special_signs


@pytest.fixture
def dataset_with_supplements_plus_resource_with_supplements():
    _dataset = DatasetFactory.create()
    _resource = ResourceFactory.create(dataset=_dataset)
    CategoryFactory.create_batch(2, datasets=(_dataset,))
    ResourceSupplementFactory.create_batch(2, resource=_resource)
    DatasetSupplementFactory.create_batch(2, dataset=_dataset)
    run_on_commit_events()
    return _dataset


@given(parsers.parse("dataset with id {dataset_id:d} and {num:d} resources"))
def dataset_with_id_and_datasets(dataset_id, num):
    _dataset = DatasetFactory.create(id=dataset_id, title="dataset {} with resources".format(dataset_id))
    ResourceFactory.create_batch(num, dataset=_dataset)
    return _dataset


@given(parsers.parse("dataset with id {dataset_id:d} and {num:d} showcases"))
def dataset_with_id_and_showcases(dataset_id, num):
    _dataset = DatasetFactory.create(id=dataset_id, title="dataset {} with showcases".format(dataset_id))
    for x in range(num):
        ShowcaseFactory.create(title=f"Ponowne wykorzystanie {x + 1}", datasets=[_dataset])
    return _dataset


@given(parsers.parse("dataset with title {title} and {num:d} resources"))
def dataset_with_title_and_x_resources(title, num):
    _dataset = DatasetFactory.create(title=title)
    ResourceFactory.create_batch(num, dataset=_dataset)
    return _dataset


@given(parsers.parse("{number_of_datasets:d} datasets with {num:d} resources"))
def number_of_datasets_with_resources(number_of_datasets, num):
    for x in range(number_of_datasets):
        _dataset = DatasetFactory.create()
        ResourceFactory.create_batch(num, dataset=_dataset)


@pytest.fixture
def datasets():
    datasets = DatasetFactory.create_batch(2)
    run_on_commit_events()
    return datasets


@given(parsers.parse("{num:d} datasets"))
def x_datasets(num):
    return DatasetFactory.create_batch(num)


@given(parsers.parse("{num:d} promoted datasets"))
def x_promoted_datasets(num):
    return DatasetFactory.create_batch(num, is_promoted=True)


@when(parsers.parse("remove dataset with id {dataset_id}"))
@then(parsers.parse("remove dataset with id {dataset_id}"))
def remove_dataset(dataset_id):
    model = apps.get_model("datasets", "dataset")
    inst = model.objects.get(pk=dataset_id)
    inst.is_removed = True
    inst.save()


@when(parsers.parse("restore dataset with id {dataset_id}"))
@then(parsers.parse("restore dataset with id {dataset_id}"))
def restore_dataset(dataset_id):
    model = apps.get_model("datasets", "dataset")
    inst = model.raw.get(pk=dataset_id)
    inst.is_removed = False
    inst.save()


@when(parsers.parse("change status to {status} for dataset with id {dataset_id}"))
@then(parsers.parse("change status to {status} for dataset with id {dataset_id}"))
def change_dataset_status(status, dataset_id):
    model = apps.get_model("datasets", "dataset")
    inst = model.objects.get(pk=dataset_id)
    inst.status = status
    inst.save()


@then("api's response datasets contain valid links to related resources")
def api_response_datasets_contain_valid_links_to_related_resources(context):
    dataset_model = apps.get_model("datasets.Dataset")
    for x in context.response.json["data"]:
        obj = dataset_model.objects.get(id=x["id"])
        assert obj.ident in x["relationships"]["resources"]["links"]["related"]


@then("api's response data is None")
def api_response_data_is_none(context):
    data = context.response.json["data"]
    assert data is None


@given(parsers.parse("three datasets with created dates in {dates}"))
def three_datasets_with_different_created_at(dates):
    dates_ = dates.split("|")
    datasets = []
    for d in dates_:
        d = parser.parse(d)
        ds = DatasetFactory.create(created=d)
        datasets.append(ds)
    return datasets


@pytest.fixture
def buzzfeed_editor(buzzfeed_organization):
    from mcod.users.models import User

    usr = User.objects.create_user("buzzfeed@test-dane.gov.pl", "12345.Abcde")
    usr.fullname = "Buzzfeed Editor"
    usr.state = "active"
    usr.is_staff = True
    usr.is_superuser = False
    usr.save()
    usr.organizations.add(buzzfeed_organization)
    return usr


@pytest.fixture
def buzzfeed_dataset(
    journalism_category,
    cc_4_license,
    buzzfeed_organization,
    buzzfeed_editor,
    fakenews_tag,
    top50_tag,
):
    from mcod.datasets.models import Dataset

    ds = Dataset.objects.create(
        title="Analizy, dane i statystki stworzone przez Buzzfeed.com",
        slug="analizy-buzzfeed",
        notes="Open - source data, analysis, libraries, tools, and guides from BuzzFeed's newsroom.",
        url="https://github.com/BuzzFeedNews/",
        views_count=242,
        license=cc_4_license,
        organization=buzzfeed_organization,
        update_frequency="yearly",
        category=journalism_category,
        created_by=buzzfeed_editor,
        modified_by=buzzfeed_editor,
    )
    ds.tags.add(fakenews_tag, top50_tag)
    run_on_commit_events()
    return ds


@pytest.fixture
def onlyheaders_csv_file():
    return prepare_file("onlyheaders.csv")


@pytest.fixture
def csv2jsonld_csv_file():
    return prepare_file("csv2jsonld.csv")


@pytest.fixture
def csv2jsonld_jsonld_file():
    return prepare_file("csv2jsonld.jsonld")


@pytest.fixture
def example_docx_file():
    return prepare_file("doc_img.docx")


@pytest.fixture
def example_geojson_file():
    return prepare_file("example_geojson.geojson")


@pytest.fixture
def example_geojson_file_without_extension():
    return prepare_file("example_geojson_without_extension")


@pytest.fixture
def example_gpx_file():
    return prepare_file("run.gpx")


@pytest.fixture
def example_jsonld_file():
    return prepare_file("rdf/example_jsonld.jsonld")


@pytest.fixture
def example_jsonstat_file():
    # https://json-stat.org/samples/order.json
    return prepare_file("example_jsonstat.json")


@pytest.fixture
def example_json_file_with_geojson_content():
    return prepare_file("example_geojson.json")


@pytest.fixture
def example_kml_file():
    return prepare_file("example_kml.kml")


@pytest.fixture
def example_n3_file():
    # https://w3c.github.io/N3/spec/#simpletriples
    return prepare_file("rdf/example_n3.n3")


@pytest.fixture
def example_n_triples_file():
    # https://www.w3.org/TR/2014/REC-n-triples-20140225/Overview.html
    return prepare_file("rdf/example_n_triples.nt")


@pytest.fixture
def example_n_quads_file():
    # https://www.w3.org/TR/2014/REC-n-quads-20140225/
    return prepare_file("rdf/example_n_quads.nq")


@pytest.fixture
def example_xls_file():
    return prepare_file("example_xls_file.xls")


@pytest.fixture
def example_xlsx_file():
    return prepare_file("sheet_img.xlsx")


@pytest.fixture
def simple_csv_file():
    return prepare_file("simple.csv")


@pytest.fixture
def single_file_pack():
    return prepare_file("single_file.tar.gz")


@pytest.fixture
def single_csv_zip():
    return prepare_file("single_csv.zip")


@pytest.fixture
def multi_file_pack():
    return prepare_file("multi_file.rar")


@pytest.fixture
def multi_file_zip_pack():
    return prepare_file("multi_pdf_xlsx.zip")


@pytest.fixture
def multi_file_zip_pack_no_extension():
    return prepare_file("multi_pdf_xlsx")


@pytest.fixture
def shapefile_arch():
    return prepare_file("Mexico_and_US_Border.zip")


@pytest.fixture
def empty_zip_file():
    return prepare_file("empty_file.zip")


@pytest.fixture
def empty_rar_file():
    return prepare_file("empty_file.rar")


@pytest.fixture
def empty_docx_packed_rar_file():
    return prepare_file("empty_docx_packed.rar")


@pytest.fixture
def empty_7z_file():
    return prepare_file("empty_file.7z")


@pytest.fixture
def empty_tar_gz_file():
    return prepare_file("empty_file.tar.gz")


@pytest.fixture
def empty_tar_bz2_file():
    return prepare_file("empty_file.tar.bz2")


@pytest.fixture
def example_ods_file():
    return prepare_file("example_ods_file.ods")


@pytest.fixture
def example_rdf_file():
    # https://www.w3.org/TR/REC-rdf-syntax/#example7
    return prepare_file("rdf/example_rdf.rdf")


@pytest.fixture
def example_trig_file():
    # https://www.w3.org/TR/2014/REC-trig-20140225/
    return prepare_file("rdf/example_trig.trig")


@pytest.fixture
def example_trix_file():
    # https://www.w3.org/2004/03/trix/
    return prepare_file("rdf/example_trix.trix")


@pytest.fixture
def example_turtle_file():
    # https://www.w3.org/TR/2014/REC-turtle-20140225/examples/example1.ttl
    return prepare_file("rdf/example_turtle.ttl")


@pytest.fixture
def example_grib():
    return prepare_file("example_grib.grib")


@pytest.fixture
def example_hdf_netcdf():
    return prepare_file("darwin_2012.nc")


@pytest.fixture
def example_binary_netcdf():
    return prepare_file("madis-maritime.nc")


@pytest.fixture
def example_regular_zip():
    return prepare_file("regular.zip")


@pytest.fixture
def json_in_zip_zip():
    return prepare_file("json_in_zip.zip")


@pytest.fixture
def example_encrypted_content_zip():
    return prepare_file("encrypted_content.zip")


@pytest.fixture
def example_regular_7z():
    return prepare_file("regular.7z")


@pytest.fixture
def example_encrypted_content_7z():
    return prepare_file("encrypted_content.7z")


@pytest.fixture
def example_encrypted_content_and_headers_7z():
    return prepare_file("encrypted_content_and_headers.7z")


@pytest.fixture
def example_regular_rar():
    return prepare_file("regular.rar")


@pytest.fixture
def example_encrypted_content_rar():
    return prepare_file("encrypted_content.rar")


@pytest.fixture
def example_encrypted_content_and_headers_rar():
    return prepare_file("encrypted_content_and_headers.rar")


@given(parsers.parse("I have file {file_type}"), target_fixture="validated_file")
def validated_file(
    empty_zip_file,
    empty_rar_file,
    empty_docx_packed_rar_file,
    empty_7z_file,
    empty_tar_gz_file,
    empty_tar_bz2_file,
    example_docx_file,
    example_geojson_file,
    example_geojson_file_without_extension,
    example_gpx_file,
    example_jsonld_file,
    example_jsonstat_file,
    example_json_file_with_geojson_content,
    example_kml_file,
    example_n3_file,
    example_n_triples_file,
    example_n_quads_file,
    example_ods_file,
    example_trig_file,
    example_trix_file,
    example_turtle_file,
    example_xlsx_file,
    example_rdf_file,
    multi_file_pack,
    single_csv_zip,
    multi_file_zip_pack,
    multi_file_zip_pack_no_extension,
    single_file_pack,
    shapefile_arch,
    example_grib,
    example_hdf_netcdf,
    example_binary_netcdf,
    file_type,
    example_regular_zip,
    json_in_zip_zip,
    example_encrypted_content_zip,
    example_regular_7z,
    example_encrypted_content_7z,
    example_encrypted_content_and_headers_7z,
    example_regular_rar,
    example_encrypted_content_rar,
    example_encrypted_content_and_headers_rar,
):
    file_types = {
        "docx": example_docx_file,
        "empty_file.zip": empty_zip_file,
        "empty_file.rar": empty_rar_file,
        "empty_docx_packed.rar": empty_docx_packed_rar_file,
        "empty_file.7z": empty_7z_file,
        "empty_file.tar.gz": empty_tar_gz_file,
        "empty_file.tar.bz2": empty_tar_bz2_file,
        "geojson": example_geojson_file,
        "geojson without extension": example_geojson_file_without_extension,
        "json with geojson content": example_json_file_with_geojson_content,
        "jsonld": example_jsonld_file,
        "jsonstat": example_jsonstat_file,
        "kml": example_kml_file,
        "n3": example_n3_file,
        "n_triples": example_n_triples_file,
        "n_quads": example_n_quads_file,
        "ods": example_ods_file,
        "xlsx": example_xlsx_file,
        "rar with many files": multi_file_pack,
        "rdf": example_rdf_file,
        "zip with one csv": single_csv_zip,
        "zip with many files": multi_file_zip_pack,
        "zip with many files no extension": multi_file_zip_pack_no_extension,
        "tar.gz with one csv": single_file_pack,
        "trig": example_trig_file,
        "trix": example_trix_file,
        "turtle": example_turtle_file,
        "shapefile arch": shapefile_arch,
        "gpx": example_gpx_file,
        "grib": example_grib,
        "hdf_netcdf": example_hdf_netcdf,
        "binary_netcdf": example_binary_netcdf,
        "regular.zip": example_regular_zip,
        "json_in_zip.zip": json_in_zip_zip,
        "encrypted_content.zip": example_encrypted_content_zip,
        "regular.7z": example_regular_7z,
        "encrypted_content.7z": example_encrypted_content_7z,
        "encrypted_content_and_headers.7z": example_encrypted_content_and_headers_7z,
        "regular.rar": example_regular_rar,
        "encrypted_content.rar": example_encrypted_content_rar,
        "encrypted_content_and_headers.rar": example_encrypted_content_and_headers_rar,
    }
    if file_type.endswith(".dbf"):
        return prepare_dbf_file(file_type)
    else:
        return file_types.get(file_type)


@given(parsers.parse("dataset with id {dataset_id}, slug {slug} and resources"))
def dataset_with_id_and_resources(dataset_id, slug):
    _dataset = DatasetFactory.create(id=dataset_id, slug=slug)
    ResourceFactory.create_batch(2, dataset=_dataset)
    return _dataset


@then(parsers.parse("api response is csv file with {record_count:d} records"))
def api_response_is_csv_file_with_records(context, record_count):
    csv_reader = csv.reader(io.StringIO(context.response.content.decode("utf-8")), delimiter=";")
    csv_record_count = -1
    for row in csv_reader:
        csv_record_count += 1
    assert record_count == csv_record_count


@then(parsers.parse("api response is xml file with {datasets_count:d} datasets and {resources_count:d} resources"))
def api_response_is_xml_file_with_datasets_and_resources(context, datasets_count, resources_count):
    root = ET.fromstring(context.response.content.decode("utf-8"))
    assert root.tag == "catalog"
    assert len(root.findall("dataset")) == datasets_count
    assert len(root.findall("dataset/resources/resource")) == resources_count


@then(parsers.parse("api's response body conforms to {lang_code} xsd schema"))
def api_response_body_conforms_to_xsd_schema(context, lang_code):
    content = context.response.content.decode("utf-8")
    xsd_path = f"{settings.SCHEMAS_DIR}/{lang_code}/katalog.xsd"
    xml_schema = xmlschema.XMLSchema(xsd_path)
    xml_schema.validate(content)


@given("created catalog csv file")
def create_catalog_csv_file():
    src = str(os.path.join(settings.TEST_SAMPLES_PATH, "datasets", "pl", "katalog.csv"))
    dest = str(os.path.join(settings.METADATA_MEDIA_ROOT, "pl", "katalog.csv"))
    if not os.path.exists(os.path.dirname(dest)):
        os.makedirs(os.path.dirname(dest))
    copyfile(src, dest)


@given("created catalog xml file")
def create_catalog_xml_file():
    for lang_code in ("pl", "en"):
        src = str(os.path.join(settings.TEST_SAMPLES_PATH, "datasets", lang_code, "katalog.xml"))
        dest = str(os.path.join(settings.METADATA_MEDIA_ROOT, lang_code, "katalog.xml"))
        if not os.path.exists(os.path.dirname(dest)):
            os.makedirs(os.path.dirname(dest))
        copyfile(src, dest)


@then(parsers.parse("Dataset with id {dataset_id} has archive containing {files_count:d} files"))
def archive_contains_files(dataset_id, files_count):
    model = apps.get_model("datasets", "dataset")
    inst = model.objects.get(pk=dataset_id)
    zipped_files = inst.archived_resources_files
    with zipfile.ZipFile(zipped_files.path) as zip_f:
        assert len(zip_f.namelist()) == files_count


@then(parsers.parse("Dataset with id {dataset_id} has zip with trimmed file names and no special characters"))
def archive_files_trimmed_filename_and_no_special_chars(dataset_id):
    model = apps.get_model("datasets", "dataset")
    special_chars = '<>:"/\\|?*~#%&+{}-^ęóąśćłńźżĘÓĄŚŁŻŹĆŃ'
    inst = model.objects.get(pk=dataset_id)
    zipped_files = inst.archived_resources_files
    zip_name = os.path.basename(zipped_files.path)
    found_ds_chars = [ch for ch in special_chars if ch in zip_name]
    assert len(zip_name) == 223
    assert len(found_ds_chars) == 0
    with zipfile.ZipFile(zipped_files.path) as zip_f:
        dirs_list = [os.path.dirname(fname) for fname in zip_f.namelist()]
        for d_name in dirs_list:
            found_res_chars = [ch for ch in special_chars if ch in d_name]
            assert len(d_name) <= 255
            assert len(found_res_chars) == 0


@then(parsers.parse("Dataset with id {dataset_id} has no archive assigned"))
def no_archive_created(dataset_id):
    model = apps.get_model("datasets", "dataset")
    inst = model.objects.get(pk=dataset_id)
    zipped_files = inst.archived_resources_files
    assert zipped_files.name is None


@then(parsers.parse("latest dataset has categories with ids {categories_ids}"))
def dataset_has_categories_with_ids(categories_ids):
    dataset = DatasetFactory._meta.model.raw.latest("id")
    categories_ids = [int(x) for x in categories_ids.split(",")]
    dataset_categories_ids = [x.id for x in dataset.categories.all()]
    assert all(x in dataset_categories_ids for x in categories_ids)


@when(
    parsers.parse(
        "Dataset with id {param_value} resource's data_date delay equals {first_delay:d} and"
        " dataset with id {another_param_value} resource's data_date delay equals {second_delay:d}"
    )
)
def dataset_resources_has_set_data_date(param_value, another_param_value, first_delay, second_delay, admin):
    freq_updates_with_delays = {
        "yearly": {"default_delay": 7, "relative_delta": relativedelta(years=1)},
        "everyHalfYear": {
            "default_delay": 7,
            "relative_delta": relativedelta(months=6),
        },
        "quarterly": {"default_delay": 7, "relative_delta": relativedelta(months=3)},
        "monthly": {"default_delay": 3, "relative_delta": relativedelta(months=1)},
        "weekly": {"default_delay": 1, "relative_delta": relativedelta(days=7)},
    }
    dataset_model = apps.get_model("datasets", "dataset")
    first_ds = dataset_model.objects.get(pk=param_value)
    second_ds = dataset_model.objects.get(pk=another_param_value)
    first_ds.modified_by = admin
    second_ds.modified_by = admin
    first_ds.save()
    second_ds.save()
    first_resource = first_ds.resources.latest("created")
    second_resource = second_ds.resources.latest("created")
    first_reldelta = freq_updates_with_delays[first_ds.update_frequency]["relative_delta"]
    second_reldelta = freq_updates_with_delays[second_ds.update_frequency]["relative_delta"]
    first_data_date = date.today() + relativedelta(days=int(second_delay)) - first_reldelta
    first_resource.data_date = first_data_date
    first_resource.update_notification_frequency = first_delay
    second_data_date = date.today() + relativedelta(days=int(second_delay)) - second_reldelta
    second_resource.data_date = second_data_date
    second_resource.type = "file"
    first_resource.type = "file"
    second_resource.update_notification_frequency = second_delay
    first_resource.save()
    second_resource.save()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
@when("Dataset update reminders are sent")
def dataset_reminders_are_sent():
    send_dataset_update_reminder()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
@then(parsers.parse("There is 1 sent reminder for dataset with title {dataset_title}"))
def single_sent_reminder(dataset_title):
    from django.core import mail

    assert len(mail.outbox) == 1
    assert mail.outbox[0].subject == dataset_title
    assert "Przypomnienie o aktualizacji Zbioru danych" in mail.outbox[0].body


@then(parsers.parse("dataset with id {dataset_id} is removed"))
def dataset_is_removed(dataset_id: Union[str, int]) -> None:
    _dataset = Dataset.raw.get(pk=dataset_id)
    assert _dataset.is_removed
