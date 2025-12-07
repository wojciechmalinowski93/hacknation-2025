import json
import os
import re
import typing
import uuid
from calendar import monthrange
from datetime import date
from io import BytesIO

import factory
import pytest
import pytz
import requests
import requests_mock
from dateutil import parser
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.core.files import File
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils.timezone import datetime, now
from django_celery_beat.models import IntervalSchedule, PeriodicTask
from pytest_bdd import given, parsers, then, when

from mcod import settings
from mcod.core.tests.fixtures.bdd.common import copyfile, prepare_file
from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.counters.factories import ResourceDownloadCounterFactory, ResourceViewCounterFactory
from mcod.counters.lib import Counter
from mcod.counters.tasks import save_counters
from mcod.datasets.models import Dataset
from mcod.harvester.factories import CKANDataSourceFactory, XMLDataSourceFactory
from mcod.regions.documents import RegionDocument
from mcod.resources.archives import PasswordProtectedArchiveError, UnsupportedArchiveError
from mcod.resources.documents import ResourceDocument
from mcod.resources.factories import (
    ChartFactory,
    DGACompliantResourceFactory,
    DGAResourceFactory,
    ResourceFactory,
    ResourceFileFactory,
    SupplementFactory,
    TaskResultFactory,
)
from mcod.resources.file_validation import analyze_file, check_support
from mcod.resources.link_validation import DangerousContentError, _get_resource_type, download_file
from mcod.resources.tasks import update_data_date

if typing.TYPE_CHECKING:
    from mcod.resources.models import Resource


@pytest.fixture
def httpsserver_custom(request):
    """Custom version of pytest_localserver's httpsserver.
    See: https://github.com/diazona/pytest-localserver/issues/2#issuecomment-919358939
    Stronger cert was generated with command:
        $ openssl req -new -x509 -sha256 -keyout server.pem -out server.pem -nodes
    """
    from pytest_localserver import https

    certificate = os.path.join(settings.TEST_CERTS_PATH, "server.pem")
    server = https.SecureContentServer(cert=certificate, key=certificate)
    server.start()
    request.addfinalizer(server.stop)
    return server


def create_res(ds, editor, **kwargs):
    from mcod.resources.models import Resource, ResourceFile

    _fname = kwargs.pop("filename")
    copyfile(
        os.path.join(settings.TEST_SAMPLES_PATH, _fname),
        os.path.join(settings.RESOURCES_MEDIA_ROOT, _fname),
    )
    _kwargs = {
        "title": "Analysis of fake news sites and viral posts",
        "description": "Over the past four years, BuzzFeed News has maintained lists of sites that "
        "publish completely fabricated stories. As we encounter new ones and debunk "
        "their content, we add them to the list.",
        "file": _fname,
        "link": f"https://falconframework.org/media/resources/{_fname}",
        "format": "csv",
        "openness_score": 3,
        "views_count": 10,
        "downloads_count": 20,
        "dataset": ds,
        "created_by": editor,
        "modified_by": editor,
        "data_date": datetime.today(),
        "has_dynamic_data": False,
        "has_high_value_data": False,
        "has_research_data": False,
        "contains_protected_data": False,
        "has_high_value_data_from_ec_list": False,
    }
    _kwargs.update(**kwargs)

    with open(os.path.join(settings.RESOURCES_MEDIA_ROOT, _fname), "rb") as f:
        from mcod.resources.link_validation import session

        adapter = requests_mock.Adapter()
        adapter.register_uri(
            "GET",
            _kwargs["link"],
            content=f.read(),
            headers={"Content-Type": "application/csv"},
        )
        session.mount("https://falconframework.org", adapter)
    _kwargs.pop("file")
    res = Resource.objects.create(**_kwargs)
    ResourceFile.objects.create(
        is_main=True,
        resource=res,
        file=os.path.join(settings.RESOURCES_MEDIA_ROOT, _fname),
        format="csv",
    )
    res = Resource.objects.get(pk=res.pk)
    return res


def create_geo_res(ds, editor, **kwargs):
    data = {
        "filename": "geo.csv",
        "title": "Geo tab test",
        "description": "more than 20 characters",
    }
    data.update(kwargs)
    return create_res(ds, editor, **data)


def create_res_with_regions(res_id, dataset_id, main_region, additional_regions, **kwargs):
    doc = RegionDocument()
    resource = ResourceFactory.create(id=res_id, dataset_id=dataset_id, type="file", **kwargs)
    resource.regions.set([main_region])
    resource.regions.add(*additional_regions, through_defaults={"is_additional": True})
    resource.save()
    if kwargs.get("status", "published") == "published":
        doc.update(resource.all_regions)


@pytest.fixture
def buzzfeed_fakenews_resource(buzzfeed_dataset, buzzfeed_editor):
    res = create_res(
        buzzfeed_dataset,
        buzzfeed_editor,
        filename="buzzfeed-2018-fake-news-1000-lines.csv",
    )
    run_on_commit_events()
    return res


@pytest.fixture
def resource_with_date_and_datetime(buzzfeed_dataset, buzzfeed_editor, mocker):
    return create_res(buzzfeed_dataset, buzzfeed_editor, filename="date_and_datetime.csv")


@pytest.fixture
def geo_tabular_data_resource(buzzfeed_dataset, buzzfeed_editor, mocker):
    res = create_geo_res(buzzfeed_dataset, buzzfeed_editor)
    run_on_commit_events()
    return res


def create_remote_file_resource_with_params(params, httpserver, admin_context=None):
    simple_csv_path = os.path.join(settings.TEST_SAMPLES_PATH, "simple.csv")
    httpserver.serve_content(
        content=open(simple_csv_path).read(),
        headers={"content-type": "application/csv"},
    )
    with open(simple_csv_path, "rb") as f:
        from mcod.resources.link_validation import session

        adapter = requests_mock.Adapter()
        adapter.register_uri(
            "GET",
            httpserver.url,
            content=f.read(),
            headers={"Content-Type": "application/csv"},
        )
        session.mount(httpserver.url, adapter)
    params_ = {
        "type": "file",
        "format": "csv",
        "link": httpserver.url,
    }
    if admin_context:
        admin_context.link = httpserver.url

    params_.update(params)
    res = ResourceFactory(**params_)
    return res


@pytest.fixture
def remote_file_resource(buzzfeed_dataset, buzzfeed_editor, httpserver):
    from mcod.resources.models import Resource

    simple_csv_path = os.path.join(settings.TEST_SAMPLES_PATH, "simple.csv")
    httpserver.serve_content(
        content=open(simple_csv_path).read(),
        headers={"content-type": "application/csv"},
    )

    res = Resource(
        title="Remote file resource",
        description="Remote file resource",
        link=httpserver.url,
        format="csv",
        openness_score=3,
        views_count=10,
        downloads_count=20,
        dataset=buzzfeed_dataset,
        created_by=buzzfeed_editor,
        modified_by=buzzfeed_editor,
        data_date=datetime.today(),
    )
    res.save()
    run_on_commit_events()
    return res


@pytest.fixture
def other_remote_file_resource(buzzfeed_dataset, buzzfeed_editor, mocker, httpserver):
    from mcod.resources.models import Resource

    simple_csv_path = os.path.join(settings.TEST_SAMPLES_PATH, "simple.csv")
    httpserver.serve_content(
        content=open(simple_csv_path).read(),
        headers={"content-type": "application/csv"},
    )

    res = Resource(
        title="Other remote file resource",
        description="Other remote file resource",
        link=httpserver.url,
        format="csv",
        openness_score=3,
        views_count=10,
        downloads_count=20,
        dataset=buzzfeed_dataset,
        created_by=buzzfeed_editor,
        modified_by=buzzfeed_editor,
        data_date=datetime.today(),
    )
    res.save()
    return res


@pytest.fixture
def remote_file_resource_of_api_type(buzzfeed_dataset, buzzfeed_editor, httpserver):
    from mcod.resources.models import Resource

    httpserver.serve_content(
        content=get_json_file().read(),
        headers={"content-type": "application/json"},
    )
    res = Resource(
        title="Remote file resource",
        description="Remote file resource",
        link=httpserver.url,
        format="json",
        openness_score=3,
        views_count=10,
        downloads_count=20,
        dataset=buzzfeed_dataset,
        created_by=buzzfeed_editor,
        modified_by=buzzfeed_editor,
        data_date=datetime.today(),
        type="api",
    )
    res.save()
    return res


@pytest.fixture
def remote_file_resource_with_forced_file_type(remote_file_resource):
    remote_file_resource.type = "file"
    remote_file_resource.forced_file_type = True
    remote_file_resource.save()
    return remote_file_resource


@pytest.fixture
def local_file_resource(buzzfeed_dataset, buzzfeed_editor) -> "Resource":
    kwargs = {
        "filename": "geo.csv",
        "title": "Local file resource",
        "description": "Local file resource",
    }
    res = create_res(buzzfeed_dataset, buzzfeed_editor, **kwargs)
    ChartFactory.create(resource=res, is_default=True)
    run_on_commit_events()
    return res


@pytest.fixture
def resource_with_xls_file(example_xls_file):
    from mcod.resources.models import Resource

    res = ResourceFactory.create(
        type="file",
        format="xls",
        link=None,
        main_file__file=example_xls_file,
    )
    res = Resource.objects.get(pk=res.pk)
    res.increase_openness_score()
    return res


@pytest.fixture
def onlyheaderscsv_resource(onlyheaders_csv_file):
    from mcod.resources.models import Resource

    resource = ResourceFactory.create(
        type="file",
        format="csv",
        link=None,
        main_file__file=onlyheaders_csv_file,
    )
    resource = Resource.objects.get(pk=resource.pk)
    return resource


@pytest.fixture
def resource_with_success_tasks_statuses(remote_file_resource):
    tasks = TaskResultFactory.create_batch(size=3, status="SUCCESS")
    remote_file_resource.link_tasks.add(tasks[0])
    remote_file_resource.file_tasks.add(tasks[1])
    remote_file_resource.data_tasks.add(tasks[2])
    remote_file_resource.link_tasks_last_status = tasks[0].status
    remote_file_resource.save()
    return remote_file_resource


@pytest.fixture
def resource_with_failure_tasks_statuses(other_remote_file_resource):
    tasks = TaskResultFactory.create_batch(size=3, status="FAILURE")
    other_remote_file_resource.link_tasks.add(tasks[0])
    other_remote_file_resource.file_tasks.add(tasks[1])
    other_remote_file_resource.data_tasks.add(tasks[2])
    other_remote_file_resource.link_tasks_last_status = tasks[0].status
    other_remote_file_resource.save()
    return other_remote_file_resource


@pytest.fixture
def resource():
    res = ResourceFactory.create()
    run_on_commit_events()
    return res


@pytest.fixture
def another_resource():
    return ResourceFactory.create()


@pytest.fixture
def resource_with_file():
    res = ResourceFactory.create(
        type="file",
        format="csv",
        main_file__file=factory.django.FileField(
            from_path=os.path.join(settings.TEST_SAMPLES_PATH, "simple.csv"),
            filename="simple.csv",
        ),
    )
    return res


@pytest.fixture
def resource_with_counters():
    res = ResourceFactory.create()
    ResourceViewCounterFactory.create_batch(size=2, resource=res)
    ResourceDownloadCounterFactory.create_batch(size=2, resource=res)
    return res


@pytest.fixture
def imported_ckan_resource(imported_ckan_dataset: Dataset) -> "Resource":
    _resource = ResourceFactory.create(dataset=imported_ckan_dataset)
    return _resource


@pytest.fixture
def imported_xml_resource(imported_xml_dataset: Dataset) -> "Resource":
    _resource = ResourceFactory.create(dataset=imported_xml_dataset)
    return _resource


@pytest.fixture
def ckan_data_source():
    return CKANDataSourceFactory.create()


@pytest.fixture
def xml_data_source():
    return XMLDataSourceFactory.create()


def get_html_file():
    return BytesIO(
        b"""
        <html>
        </html>
        """
    )


def get_json_file():
    return BytesIO(
        b"""
        {}
        """
    )


@pytest.fixture
def geo_tabular_data_response():
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
                    "name": "Warsaw",
                    "confidence": 0.6,
                    "match_type": "fallback",
                    "distance": 104.639,
                    "accuracy": "centroid",
                    "country": "Poland",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "Mazowieckie",
                    "region_gid": "whosonfirst:region:85687257",
                    "region_a": "MZ",
                    "county": "Warszawa County",
                    "county_gid": "whosonfirst:county:1477743805",
                    "localadmin": "Warsaw",
                    "localadmin_gid": "whosonfirst:localadmin:1125365875",
                    "locality": "Warsaw",
                    "locality_gid": "whosonfirst:locality:101752777",
                    "label": "Warsaw, MZ, Poland",
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
                "geometry": {"type": "Point", "coordinates": [19.3406, 50.76855]},
                "properties": {
                    "id": "1309831997",
                    "gid": "whosonfirst:locality:1309831997",
                    "layer": "locality",
                    "source": "whosonfirst",
                    "source_id": "1309831997",
                    "country_code": "PL",
                    "name": "Bukowno Warszawa",
                    "confidence": 0.6,
                    "match_type": "fallback",
                    "distance": 130.189,
                    "accuracy": "centroid",
                    "country": "Poland",
                    "country_gid": "whosonfirst:country:85633723",
                    "country_a": "POL",
                    "region": "Silesian Voivodeship",
                    "region_gid": "whosonfirst:region:85687277",
                    "region_a": "SL",
                    "county": "Częstochowski County",
                    "county_gid": "whosonfirst:county:102079663",
                    "localadmin": "Olsztyn",
                    "localadmin_gid": "whosonfirst:localadmin:1125304413",
                    "locality": "Bukowno Warszawa",
                    "locality_gid": "whosonfirst:locality:1309831997",
                    "label": "Bukowno Warszawa, SL, Poland",
                    "addendum": {"concordances": {"gn:id": 3102072}},
                },
                "bbox": [19.3206, 50.74855, 19.3606, 50.78855],
            },
        ]
    }


def create_website_resource(**kwargs) -> "Resource":
    obj_kwargs = {
        "type": "website",
        "format": "html",
        "link": "https://google.com",
        "main_file": None,
    }
    obj_kwargs.update(kwargs)
    return ResourceFactory.create(**obj_kwargs)


@pytest.fixture
def resource_of_type_website():
    return create_website_resource()


@given("resource of type website")
def create_resource_of_type_website(resource_of_type_website):
    return resource_of_type_website


@given(parsers.parse("resource of type website with id {res_id}"))
def website_resource_with_id(res_id):
    return create_website_resource(id=res_id)


@pytest.fixture
def resource_of_type_api():
    return ResourceFactory.create(
        type="api",
        format=None,
        main_file__file=factory.django.FileField(from_func=get_json_file, filename="{}.json".format(str(uuid.uuid4()))),
        main_file__content_type="application/json",
    )


@given("resource of type api")
def create_resource_of_type_api(resource_of_type_api):
    return resource_of_type_api


@given("resource with buzzfeed file")
def resource_with_buzzfeed_file(buzzfeed_fakenews_resource):
    return buzzfeed_fakenews_resource


@given(parsers.parse("resource with regular zip file and id {res_id}"))
def resource_with_zip_file(res_id):
    return ResourceFactory.create(
        id=res_id,
        type="file",
        format="csv",
        main_file__file=factory.django.FileField(
            from_path=os.path.join(settings.TEST_SAMPLES_PATH, "regular.zip"),
            filename="regular.zip",
        ),
    )


@given(parsers.parse("geo_tabular_data_resource with params {params}"))
def geo_tabular_data_resource_with_params(buzzfeed_dataset, buzzfeed_editor, params):
    data = json.loads(params)
    return create_geo_res(buzzfeed_dataset, buzzfeed_editor, **data)


@given(parsers.parse("three resources with created dates in {dates}"))
def three_resources_with_different_created_at(dates):
    dates_ = dates.split("|")
    resources = []
    for d in dates_:
        date = parser.parse(d)
        res = ResourceFactory.create(created=date)
        resources.append(res)
    return resources


@given(parsers.parse("default charts for resource with id {resource_id:d} with ids {charts_ids_str}"))
def default_charts_for_resource_id(context, resource_id, charts_ids_str):
    resource = ResourceFactory.create(id=resource_id)
    for chart_id in charts_ids_str.split(","):
        ChartFactory.create(
            id=chart_id,
            resource=resource,
            created_by=context.user,
            is_default=True,
            chart={},
        )


@given(parsers.parse("private chart for resource with id {resource_id:d} with id {chart_id}"))
def private_chart_for_resource_id_with_id(context, resource_id, chart_id):
    resource = ResourceFactory.create(id=resource_id)
    ChartFactory.create(
        id=chart_id,
        resource=resource,
        created_by=context.user,
        is_default=False,
        chart={},
    )


@given(parsers.parse("two charts for resource with {data_str}"))
def two_charts_for_resource_id(context, data_str):
    data = json.loads(data_str)
    resource = ResourceFactory.create(**data)
    ChartFactory.create(resource=resource, created_by=context.user, is_default=True)
    ChartFactory.create(resource=resource, created_by=context.user, is_default=False)


@given("resource with date and datetime")
def _resource_with_date_and_datetime(csv_with_date_and_datetime):
    res = ResourceFactory.create(type="file", format="csv", main_file__file=File(csv_with_date_and_datetime))
    return res


@given(
    parsers.parse("resource with id {res_id} and xls file converted to csv"),
    target_fixture="resource_with_xls_file_converted_to_csv",
)
def resource_with_xls_file_converted_to_csv(res_id, example_xls_file, buzzfeed_dataset, buzzfeed_editor) -> "Resource":
    from mcod.resources.models import Resource

    params = {
        "id": res_id,
        "type": "file",
        "format": "xls",
        "link": None,
        "filename": "example_xls_file.xls",
        "openness_score": 1,
    }
    res = create_res(buzzfeed_dataset, buzzfeed_editor, **params)
    res.revalidate()
    run_on_commit_events()
    res = Resource.objects.get(pk=res.pk)
    resource_score, _ = res.get_openness_score()
    Resource.objects.filter(pk=res.pk).update(openness_score=resource_score)
    res = Resource.objects.get(pk=res.pk)
    return res


@given(
    parsers.parse("resource with id {res_id} and xls file with conversion to jsonld"),
    target_fixture="resource_xls_converted_to_jsonld",
)
@requests_mock.Mocker(kw="mock_request")
def resource_xls_converted_to_jsonld(res_id, example_xls_file, buzzfeed_dataset, buzzfeed_editor, **kwargs):
    mock_request = kwargs["mock_request"]
    url_regex = re.compile(settings.API_URL_INTERNAL + r"/media/resources/\d{8}/example_xls_file\.csv$")
    url_short_meta_regex = re.compile(settings.API_URL_INTERNAL + r"/.*csv-metadata\.json$")
    mock_request.get("http://localhost/.well-known/csvm", status_code=404)
    with open(os.path.join(settings.TEST_SAMPLES_PATH, "simple.csv"), "rb") as f:
        f_data = f.read()
        mock_request.get(url_short_meta_regex, status_code=404)
        mock_request.head(url_regex, content=f_data, headers={"Content-Type": "application/csv"})
        mock_request.get(url_regex, content=f_data, headers={"Content-Type": "application/csv"})
        res = resource_with_xls_file_converted_to_csv(res_id, example_xls_file, buzzfeed_dataset, buzzfeed_editor)
        return res


@given(parsers.parse("resource with csv file converted to jsonld with params {params_str}"))
def resource_with_csv_file_converted_to_jsonld(csv2jsonld_csv_file, csv2jsonld_jsonld_file, params_str):
    from mcod.resources.models import Resource

    params = json.loads(params_str)
    obj_id = params.pop("id")
    res = ResourceFactory(
        main_file__file=csv2jsonld_csv_file,
        id=obj_id,
        type="file",
        format="csv",
        link=None,
        **params,
    )
    ResourceFileFactory.create(file=csv2jsonld_jsonld_file, format="jsonld", resource=res, is_main=False)
    resource_score, files_score = res.get_openness_score()
    Resource.objects.filter(pk=res.pk).update(openness_score=resource_score)
    res = Resource.objects.get(pk=res.pk)
    res.revalidate()
    run_on_commit_events()
    return res


@given(parsers.parse("resource with id {res_id} and simple csv file"))
def resource_with_simple_csv(res_id, simple_csv_file):
    res = ResourceFactory(
        id=res_id,
        type="file",
        format="csv",
        link=None,
        main_file__file=simple_csv_file,
    )
    run_on_commit_events()
    res.data_tasks_last_status = res.data_tasks.all().last().status
    res.file_tasks_last_status = res.file_tasks.all().last().status
    res.save()
    return res


@given("draft resource")
def draft_resource():
    res = ResourceFactory.create(status="draft", title="Draft resource")
    return res


@pytest.fixture
def removed_resource():
    res = ResourceFactory.create(is_removed=True, title="Removed resource")
    return res


@given("removed resource")
def create_removed_resource(removed_resource):
    return removed_resource


@given(parsers.parse("draft resource with id {resource_id:d}"))
def draft_resource_with_id(resource_id):
    res = ResourceFactory.create(id=resource_id, title="Draft resource {}".format(resource_id), status="draft")
    return res


@given(parsers.parse("removed resource with id {resource_id:d}"))
def removed_resource_with_id(resource_id):
    res = ResourceFactory.create(id=resource_id, title="Removed resource {}".format(resource_id), is_removed=True)
    return res


@pytest.fixture
def resources():
    return ResourceFactory.create_batch(2)


@given(parsers.parse("{num:d} resources"))
def x_resources(num):
    return ResourceFactory.create_batch(num)


@given(parsers.parse("resource with id {res_id} and status {status} and data date update periodic task with interval schedule"))
def resource_with_periodic_task(res_id, status):
    res = ResourceFactory(
        status=status,
        id=res_id,
        type="api",
        format=None,
        main_file__file=factory.django.FileField(from_func=get_json_file, filename="{}.json".format(str(uuid.uuid4()))),
        main_file__content_type="application/json",
        is_auto_data_date=True,
        automatic_data_date_start=datetime(2022, 5, 20).date(),
        endless_data_date_update=True,
    )
    schedule, _ = IntervalSchedule.objects.get_or_create(every=1, period=IntervalSchedule.DAYS)
    PeriodicTask.objects.create(
        name=res.data_date_task_name,
        task="mcod.resources.tasks.update_data_date",
        args=json.dumps([res_id]),
        queue="periodic",
        interval=schedule,
    )


@given(parsers.parse("resource with status {status} and data date update periodic task with interval schedule"))
def resource_with_status_and_periodic_task(admin_context, status):
    res = ResourceFactory(
        status=status,
        type="api",
        format=None,
        main_file__file=factory.django.FileField(from_func=get_json_file, filename="{}.json".format(str(uuid.uuid4()))),
        main_file__content_type="application/json",
        is_auto_data_date=True,
        automatic_data_date_start=datetime(2022, 5, 20).date(),
        endless_data_date_update=True,
        data_date_update_period="daily",
    )
    admin_context.object_id = res.id


@when(parsers.parse("resource document with id {resource_id:d} is reindexed using regular queryset"))
def resource_document_is_updated_using_regular_queryset(resource_id, ctx):
    doc = ResourceDocument()
    qs = doc.get_queryset().filter(id=resource_id)
    doc.update(qs)
    ctx["regular_queryset_document"] = ResourceDocument.get(id=resource_id)


@when(parsers.parse("resource document with id {resource_id:d} is reindexed using queryset iterator"))
def resource_document_is_updated_using_queryset_iterator(resource_id, ctx):
    doc = ResourceDocument()
    qs = doc.get_queryset().filter(id=resource_id).iterator()
    doc.update(qs)
    ctx["queryset_iterator_document"] = ResourceDocument.get(id=resource_id)


@then("compare resource documents reindexed using different approaches")
def compare_resource_documents_reindexed_using_different_approaches(ctx):
    assert ctx["regular_queryset_document"]._d_ == ctx["queryset_iterator_document"]._d_


@then(parsers.parse("resource document with id {resource_id:d} field {field_name} equals {field_value}"))
def resource_document_specified_field_equals_specified_value(resource_id, field_name, field_value):
    assert str(getattr(ResourceDocument.get(id=resource_id), field_name)) == field_value


@when(parsers.parse("remove resource with id {resource_id}"))
@then(parsers.parse("remove resource with id {resource_id}"))
def remove_resource(resource_id):
    model = apps.get_model("resources", "resource")
    inst = model.objects.get(pk=resource_id)
    inst.is_removed = True
    inst.save()


@then(parsers.parse("resource with id {resource_id:d} {counter_type} is {val:d}"))
def resource_views_count_is(resource_id, counter_type, val):
    model = apps.get_model("resources", "resource")
    obj = model.objects.get(pk=resource_id)
    current_count = getattr(obj, f"computed_{counter_type}")
    assert current_count == val


@given(parsers.parse("resource with id {resource_id:d} and {counter_type} is {val:d}"))
def given_resource_views_count_is(resource_id, counter_type, val):
    kwargs = {"id": resource_id, counter_type: val, "type": "file"}
    return ResourceFactory.create(**kwargs)


@given(parsers.parse("unpublished resource with id {resource_id:d} and {counter_type} is {val:d}"))
def given_unpublished_resource_views_count_is(resource_id, counter_type, val):
    kwargs = {"id": resource_id, counter_type: val, "status": "draft", "type": "file"}
    return ResourceFactory.create(**kwargs)


@then(parsers.parse("resource csv file has {columns} as headers"))
def resource_csv_file_has_headers(resource_with_xls_file_converted_to_csv: "Resource", columns: str):
    res = resource_with_xls_file_converted_to_csv
    with open(res.csv_converted_file.path, "r") as outfile:
        first_line = outfile.readline().rstrip("\n")
        assert columns == first_line


def get_mock_response(mock_request, content_filename, headers):
    with open(content_filename, "rb") as f:
        mock_request.get("http://mocker-test.com", headers=headers, content=f.read())
    return requests.get("http://mocker-test.com")


@pytest.fixture
@requests_mock.Mocker(kw="mock_request")
def xml_resource_api_response(file_xml, **kwargs):
    headers = {"Content-Type": "text/xml"}
    return get_mock_response(kwargs["mock_request"], file_xml.name, headers)


@pytest.fixture
@requests_mock.Mocker(kw="mock_request")
def xml_resource_file_response(file_xml, **kwargs):
    headers = {
        "Content-Disposition": 'attachment; filename="example.xml"',
        "Content-Type": "text/xml",
    }
    return get_mock_response(kwargs["mock_request"], file_xml.name, headers)


@pytest.fixture
@requests_mock.Mocker(kw="mock_request")
def html_resource_response(file_html, **kwargs):
    headers = {"Content-Type": "text/html"}
    return get_mock_response(kwargs["mock_request"], file_html.name, headers)


@pytest.fixture
@requests_mock.Mocker(kw="mock_request")
def json_resource_response(file_json, **kwargs):
    headers = {"Content-Type": "application/json"}
    return get_mock_response(kwargs["mock_request"], file_json.name, headers)


@pytest.fixture
@requests_mock.Mocker(kw="mock_request")
def jsonstat_resource_response(file_jsonstat, **kwargs):
    headers = {"Content-Type": "application/json"}
    return get_mock_response(kwargs["mock_request"], file_jsonstat.name, headers)


@given(parsers.parse("resource with {filename} file and id {obj_id}"))
def resource_with_id_and_filename(filename, dataset, obj_id):
    from mcod.resources.models import Resource

    full_filename = prepare_file(filename)
    with open(full_filename, "rb") as outfile:
        res = Resource.objects.create(
            id=obj_id,
            title="Local file resource",
            description="Resource with file",
            dataset=dataset,
            data_date=datetime.today(),
            status="published",
        )
        ResourceFileFactory.create(
            resource_id=res.pk,
            file=File(outfile),
        )


@given(parsers.parse("resource with {filename} file, dataset_id {dataset_id} and id {obj_id}"))
def resource_with_id_and_filename_and_dataset_id(filename, dataset_id, obj_id):
    from mcod.resources.models import Resource

    full_filename = prepare_file(filename)
    with open(full_filename, "rb") as outfile:
        res = Resource.objects.create(
            id=obj_id,
            title="Local file resource",
            description="Resource with file",
            dataset_id=dataset_id,
            data_date=datetime.today(),
            status="published",
        )
        ResourceFileFactory.create(
            resource_id=res.pk,
            file=File(outfile),
        )


@given(parsers.parse("draft remote file resource of api type with id {obj_id}"))
def draft_remote_file_resource(obj_id, httpsserver_custom):
    httpsserver_custom.serve_content(
        content=get_json_file().read(),
        headers={"content-type": "application/json"},
    )
    kwargs = {
        "id": obj_id,
        "link": httpsserver_custom.url,
        "status": "draft",
        "main_file": None,
        "type": "api",
    }
    res = ResourceFactory.create(**kwargs)
    return res


@then(parsers.parse("resource with id {obj_id} attributes are equal {expected_attr_vals}"))
def resource_with_id_attr_is_equal(obj_id, expected_attr_vals):
    expected_vals = json.loads(expected_attr_vals)
    model = apps.get_model("resources", "resource")
    obj = model.objects.get(pk=obj_id)
    actual_vals = {expected_attr: getattr(obj, expected_attr) for expected_attr in expected_vals.keys()}
    assert actual_vals == expected_vals, "Expected values: {}, Actual values: {}".format(expected_vals, actual_vals)


@then(parsers.parse("resource field {r_field} is {r_value}"))
def resource_field_value_is(context, r_field, r_value):
    model = apps.get_model("resources", "resource")
    resource = model.objects.latest("id")
    assert getattr(resource, r_field) == r_value


@then(parsers.parse("file is validated and result is {file_format}"))
def file_format(validated_file, file_format):
    ext, *other = analyze_file(validated_file)
    assert ext == file_format, f'Analyzed {validated_file} file format is not: "{file_format}", but: "{ext}"'


@then(parsers.parse("extracted file is validated and result is {file_format}"))
def extracted_file_format(validated_file, file_format):
    ext, _, _, _, _, _, extracted_ext, *other = analyze_file(validated_file)
    assert extracted_ext == file_format, f'Analyzed {validated_file} file format is not: "{file_format}", but: "{extracted_ext}"'


@then(parsers.parse("file is validated and result mimetype is {mimetypes}"))
def file_mimetype(validated_file, mimetypes):
    _, _, _, _, file_mimetype, *other = analyze_file(validated_file)
    assert file_mimetype in json.loads(mimetypes)


@then("file is validated and UnsupportedArchiveError is raised")
def file_validation_exception(validated_file):
    with pytest.raises(UnsupportedArchiveError) as e:
        extension, _, _, _, file_mimetype, *other = analyze_file(validated_file)
        check_support(extension, file_mimetype)
        assert str(e.value) == "archives-are-not-supported"


@then(parsers.parse("file is validated and PasswordProtectedArchiveError is raised"))
def archive_file_validation_exception(validated_file):
    (
        format,
        file_info,
        file_encoding,
        p,
        file_mimetype,
        analyze_exc,
        extracted_format,
        extracted_mimetype,
        extracted_encoding,
    ) = analyze_file(validated_file)
    assert isinstance(analyze_exc, PasswordProtectedArchiveError)


@given(parsers.parse("resource with id {res_id} is viewed and counter incrementing task is executed"))
def resourced_is_visited_and_counter_incremented(res_id):
    import time

    counter = Counter()
    counter.incr_view_count("resources.Resource", res_id)
    counter.save_counters()
    time.sleep(1)  # time for indexing in ES


@given(parsers.parse("resource with id {res_id} dataset id {dataset_id} and single main region"))
def resource_with_region(res_id, dataset_id, main_region, additional_regions):
    create_res_with_regions(res_id, dataset_id, main_region, additional_regions)


@given(parsers.parse("resource with id {res_id} dataset id {dataset_id} and wroclaw main region"))
def resource_with_wroclaw_region(res_id, dataset_id, wroclaw_main_region, additional_regions):
    create_res_with_regions(res_id, dataset_id, wroclaw_main_region, additional_regions)


@given(parsers.parse("draft resource with id {res_id} dataset id {dataset_id} and single main region"))
def draft_resource_with_region(res_id, dataset_id, main_region, additional_regions):
    create_res_with_regions(res_id, dataset_id, main_region, additional_regions, status="draft")


@given(parsers.parse("resource with id {res_id} dataset id {dataset_id} and supplement with id {supplement_id}"))
def resource_with_supplement(res_id, dataset_id, supplement_id):
    resource = ResourceFactory.create(id=res_id, dataset_id=dataset_id)
    SupplementFactory.create(id=supplement_id, resource_id=resource.id)


@when(parsers.parse("resource with id {obj_id} is revalidated"))
def resource_is_validated(obj_id):
    from mcod.resources.link_validation import session
    from mcod.resources.models import Resource

    res = Resource.objects.get(pk=obj_id)
    if res.link and res.main_file:
        adapter = requests_mock.Adapter()
        adapter.register_uri(
            "GET",
            res.link,
            content=res.main_file.read(),
            headers={"Content-Type": res.main_file_mimetype},
        )
        session.mount(res.link, adapter)
    res.revalidate()


@when("request resource posted data contains simple file")
def posted_data_with_file(admin_context):
    _file = SimpleUploadedFile("test.html", get_html_file().read(), content_type="text/html")
    admin_context.obj["file"] = _file


@then("resource has assigned file")
def resource_created_with_file():
    from mcod.resources.models import Resource

    res = Resource.objects.all().latest("id")
    assert res.file.name == ""
    assert res.main_file.name != ""


@then("counter incrementing task is executed")
def counter_incrementing_task_is_executed(context):
    save_counters()


@then(parsers.parse("Resource with title {title} has assigned file {filename}"))
def resource_file_name_id(title, filename):
    model = apps.get_model("resources", "resource")
    obj = model.objects.get(title=title)
    assert obj.main_file.name.endswith(filename)


@when(parsers.parse("response is {resp_name} type is {resp_type}"))
def response_mocked(
    resp_name,
    resp_type,
    html_resource_response,
    json_resource_response,
    jsonstat_resource_response,
    xml_resource_api_response,
    xml_resource_file_response,
):
    responses = {
        "html_resource_response": html_resource_response,
        "json_resource_response": json_resource_response,
        "jsonstat_resource_response": jsonstat_resource_response,
        "xml_resource_api_response": xml_resource_api_response,
        "xml_resource_file_response": xml_resource_file_response,
    }
    assert _get_resource_type(responses.get(resp_name)) == resp_type


@when("response is malicious php DangerousContentError is raised")
@requests_mock.Mocker(kw="mock_request")
def response_raises_dangerous_content_error(**kwargs):
    mock_request = kwargs["mock_request"]
    url = "https://mock-resource.com.pl/malicious.php"
    mock_request.get(
        url,
        headers={"content-type": "text/plain", "Content-Disposition": "attachment"},
        content=b"<?php system($_GET['cmd']); ?>",
    )
    with pytest.raises(DangerousContentError):
        download_file(url)


@then(parsers.parse("resource with id {res_id} has periodic task with {schedule_type} schedule"))
def resource_has_periodic_task_with_schedule_type(res_id, schedule_type):
    from mcod.resources.models import Resource

    res = Resource.objects.get(pk=res_id)
    task = PeriodicTask.objects.get(name=res.data_date_task_name)
    assert getattr(task, schedule_type) is not None


@then(parsers.parse("created resource has periodic task with {schedule_type} schedule"))
def created_resource_has_periodic_task_with_schedule_type(admin_context, schedule_type):
    from mcod.resources.models import Resource

    res = Resource.objects.get(pk=admin_context.object_id)
    task = PeriodicTask.objects.get(name=res.data_date_task_name)
    assert getattr(task, schedule_type) is not None


@then(parsers.parse("resource with id {res_id} has no data date periodic task"))
def resource_has_no_periodic_task(res_id):
    assert not PeriodicTask.objects.filter(name__contains=res_id).exists()


@then(parsers.parse("created resource has no data date periodic task"))
def created_resource_has_no_periodic_task(admin_context):
    assert not PeriodicTask.objects.filter(name__contains=admin_context.object_id).exists()


@then(parsers.parse("Periodic task for resource with id {res_id:d} has last_run_at attr set"))
def resource_periodic_task_has_last_run_at_set(res_id):
    assert PeriodicTask.objects.get(name__contains=res_id).last_run_at is not None


@given(parsers.parse("remote file resource with id {res_id}"))
def remote_file_resource_with_id(res_id, httpsserver_custom, admin_context):
    return create_remote_file_resource_with_params({"id": res_id}, httpsserver_custom, admin_context=admin_context)


@given(parsers.parse("update link of remote file resource with id '{res_id}'"))
def update_link_of_remote_file_resource_with_id(res_id, admin_context):
    from mcod.resources.models import Resource

    Resource.objects.filter(id=res_id).update(link=admin_context.link)


@given(parsers.parse("remote file resource with enabled auto data date update and id {res_id}"))
def remote_file_resource_with_id_and_auto_data_date_enabled(res_id, httpsserver_custom):
    params_ = {
        "id": res_id,
        "is_auto_data_date": True,
        "automatic_data_date_start": datetime(2022, 5, 20).date(),
        "endless_data_date_update": True,
        "data_date_update_period": "daily",
        "openness_score": 0,
    }
    res = create_remote_file_resource_with_params(params_, httpsserver_custom)
    update_data_date.s(res_id).apply_async()
    return res


@when(parsers.parse("update data date task for resource with id {res_id} is executed"))
def run_auto_data_date_update_task(res_id):
    update_data_date.s(res_id).apply_async()


@then(parsers.parse("resource with id {res_id} has {result_count:d} {validation_type} validation results"))
def resource_has_file_validation_results(res_id, result_count, validation_type):
    model = apps.get_model("resources", "resource")
    res = model.objects.get(pk=res_id)
    validation_tasks = getattr(res, f"{validation_type}_tasks")
    assert validation_tasks.all().count() == result_count


@then(parsers.parse("resource with title {res_title} has zipped xlsx converted to csv"))
def zipped_xlsx_has_converted_csv(res_title):
    from mcod.resources.models import ResourceFile

    res_file = ResourceFile.objects.filter(resource__title=res_title, is_main=False, format="csv")
    assert res_file.exists()


@then(parsers.parse("crontab schedule for resource with id {res_id} has current month last day set up as run date"))
def crontab_with_current_month_last_day(res_id):
    from mcod.resources.models import Resource

    res = Resource.objects.get(pk=res_id)
    warsaw_tz = pytz.timezone(settings.TIME_ZONE)
    localized_today = now().astimezone(warsaw_tz).date()
    m_range = monthrange(localized_today.year, localized_today.month)
    month_last_day = date(localized_today.year, localized_today.month, m_range[1])
    schedule_date = res.automatic_data_date_start
    while schedule_date < month_last_day:
        schedule_date += relativedelta(months=1)
        schedule_date = res.correct_last_moth_day(schedule_date)
    task_schedule = PeriodicTask.objects.get(name=res.data_date_task_name).crontab
    assert task_schedule.day_of_month == str(schedule_date.day)
    assert task_schedule.month_of_year == str(schedule_date.month)


@given(parsers.parse("DGA compliant resource with pk {resource_id} in dataset with pk {dataset_id}"))
def dga_compliant_resource_in_dataset(resource_id, dataset_id):
    DGACompliantResourceFactory.create(pk=resource_id, dataset_id=dataset_id)


@given(parsers.parse("DGA resource with pk {resource_id} in dataset with pk {dataset_id}"))
def dga_resource_in_dataset(resource_id, dataset_id):
    DGAResourceFactory.create(pk=resource_id, dataset_id=dataset_id)


@given(parsers.parse("DGA resource with pk {resource_id} and title {resource_title} in " "dataset with pk {dataset_id}"))
def named_dga_resource_in_dataset(resource_id, resource_title, dataset_id):
    DGAResourceFactory.create(pk=resource_id, title=resource_title, dataset_id=dataset_id)


@then(parsers.parse("resource with id {res_id} does not contain protected data"))
def resource_does_not_contain_protected_data(res_id: typing.Union[int, str]):
    from mcod.resources.models import Resource

    res = Resource.objects.get(pk=res_id)
    assert res.contains_protected_data is False


@then(parsers.parse("resource with id {res_id} is draft"))
def resource_is_draft(res_id: typing.Union[int, str]):
    from mcod.resources.models import Resource

    res = Resource.objects.get(pk=res_id)
    assert res.status == "draft"


@then(parsers.parse("resource with id {res_id} is DGA"))
def resource_is_dga(res_id: typing.Union[int, str]):
    from mcod.resources.models import Resource

    res = Resource.objects.get(pk=res_id)
    assert res.is_dga


@then(parsers.parse("resource with id {res_id} is not DGA"))
def resource_is_not_dga(res_id: typing.Union[int, str]):
    from mcod.resources.models import Resource

    res = Resource.objects.get(pk=res_id)
    assert not res.is_dga


@then(parsers.parse("resource with id {res_id} is removed"))
def resource_is_removed(res_id: typing.Union[str, int]):
    from mcod.resources.models import Resource

    res = Resource.raw.get(pk=res_id)
    assert res.is_removed
