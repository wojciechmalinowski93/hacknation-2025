import datetime
import json
import os
import re
import shutil
import smtplib
import zipfile
from io import BytesIO
from pydoc import locate
from typing import Any, Dict, List, Literal, Optional, Union
from unittest import mock

import dpath
import magic
import requests_mock
from bs4 import BeautifulSoup
from django.apps import apps
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import translation
from pytest_bdd import given, parsers, then, when

from mcod import settings
from mcod.core.api.rdf.namespaces import NAMESPACES
from mcod.core.registries import factories_registry
from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.datasets.factories import DatasetFactory
from mcod.datasets.models import Dataset
from mcod.organizations.factories import OrganizationFactory
from mcod.resources.factories import DGAResourceFactory


def copyfile(src, dst):
    shutil.copyfile(src, dst)
    return dst


def prepare_file(filename):
    dirs = filename.split(os.sep)
    filename = dirs.pop()
    src = str(os.path.join(settings.TEST_SAMPLES_PATH, *dirs, filename))
    dst_dir = os.path.join(settings.RESOURCES_MEDIA_ROOT, *dirs)
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)
    dst = str(os.path.join(dst_dir, filename))
    copyfile(src, dst)

    return dst


def prepare_dbf_file(filename):
    dbf_path = os.path.join(settings.DATA_DIR, "dbf_examples")
    return os.path.join(dbf_path, filename)


def create_object(obj_type, obj_id, is_removed=False, status="published", **kwargs):
    _factory = factories_registry.get_factory(obj_type)
    kwargs["pk"] = obj_id
    if obj_type not in ["alert", "tag", "task result", "log entry"]:
        kwargs["is_removed"] = is_removed
    if "user" not in obj_type and obj_type not in ["log entry"]:
        kwargs["status"] = status
    return _factory(**kwargs)


@given("list of sent emails is empty")
def email_file_path_is_empty():
    shutil.rmtree(settings.EMAIL_FILE_PATH, ignore_errors=True)


@given(parsers.parse("remove {object_type} with id {object_id:d}"))
def remove_object_with_id(object_type, object_id):
    _factory = factories_registry.get_factory(object_type)
    model = _factory._meta.model
    instance = model.objects.get(pk=object_id)
    instance.is_removed = True
    instance.save()


@when(parsers.parse("restore {object_type} with id {object_id:d}"))
@then(parsers.parse("restore {object_type} with id {object_id:d}"))
def restore_object_with_id(object_type, object_id):
    _factory = factories_registry.get_factory(object_type)
    model = _factory._meta.model
    instance = model.raw.get(pk=object_id)
    instance.is_removed = False
    instance.save()


@given(parsers.parse("set {attr_name} to {attr_value} on {object_type} with id {object_id:d}"))
@then(parsers.parse("set {attr_name} to {attr_value} on {object_type} with id {object_id:d}"))
def attr_to_object_with_id(attr_name, attr_value, object_type, object_id):
    _factory = factories_registry.get_factory(object_type)
    instance = _factory._meta.model.objects.get(pk=object_id)
    setattr(instance, attr_name, attr_value)
    instance.save()


@given(parsers.parse("{object_type} with id {object_id:d}"))
def object_with_id(object_type, object_id):
    return create_object(object_type, object_id)


def translated_object_type(object_type):
    params = {
        "showcase": {
            "id": 999,
            "title": "title_pl",
            "title_en": "title_en",
            "notes": "notes_pl",
            "notes_en": "notes_en",
            "slug": "slug_pl",
            "slug_en": "slug_en",
        },
        "article": {
            "id": 999,
            "title": "title_pl",
            "title_en": "title_en",
            "notes": "notes_pl",
            "notes_en": "notes_en",
            "slug": "slug_pl",
            "slug_en": "slug_en",
        },
        "dataset": {
            "id": 999,
            "title": "title_pl",
            "title_en": "title_en",
            "notes": "notes_pl",
            "notes_en": "notes_en",
            "slug": "slug_pl",
            "slug_en": "slug_en",
        },
        "institution": {
            "id": 999,
            "title": "title_pl",
            "title_en": "title_en",
            "description": "description_pl",
            "description_en": "description_en",
            "slug": "slug_pl",
            "slug_en": "slug_en",
        },
        "resource": {
            "id": 999,
            "title": "title_pl",
            "title_en": "title_en",
            "description": "description_pl",
            "description_en": "description_en",
        },
    }
    kwargs = params[object_type]
    object_id = kwargs.pop("id")
    obj = create_object(object_type, object_id, **kwargs)
    for field in kwargs:
        if field in ["title", "description", "notes", "slug"]:
            assert hasattr(obj, f"{field}_translated")
    return obj


def parse_and_create(context, object_type, params, mocker=None):
    params = json.loads(params)
    if object_type.endswith("report"):
        _factory = factories_registry.get_factory(object_type)
        return _factory.create(**params)
    object_id = params.pop("id")
    tags = params.pop("tags", [])
    tag_factory = factories_registry.get_factory("tag")
    _tags = []
    for name in tags:
        tag = tag_factory.create(name=name)
        _tags.append(tag)
    if _tags:
        params["tags"] = _tags
    if object_type == "chart":
        params["created_by"] = context.user
    file_size = params.pop("file_size", None)
    if file_size and mocker:
        mocker.patch("os.path.getsize", return_value=file_size)
    create_object(object_type, object_id, **params)


@given(parsers.parse("{object_type} created with params {params}"))
def object_type_created_with_params(context, object_type, params, mocker):
    parse_and_create(context, object_type, params, mocker)


@given("translated objects")
def translated_objects():
    for object_type in ["showcase", "dataset", "institution", "resource"]:
        translated_object_type(object_type)


@given(parsers.parse("{object_type} with id {object_id:d} and {field_name1} is {value1} and {field_name2} is {value2}"))
def object_with_id_and_2_params(object_type, object_id, field_name1, value1, field_name2, value2):
    return create_object(object_type, object_id, **{field_name1: value1, field_name2: value2})


@given(parsers.parse("{param_object_type} with id {param_object_id} and {param_field_name} is {param_value}"))
def object_with_id_and_param(param_object_type, param_object_id, param_field_name, param_value):
    return create_object(param_object_type, param_object_id, **{param_field_name: param_value})


@given(parsers.parse("{objects_count:d} random instances of {object_type}"))
def random_instances(objects_count, object_type):
    _factory = factories_registry.get_factory(object_type)
    return _factory.create_batch(objects_count)


@when(parsers.parse("admin request body field {field} is {value}"))
def admin_request_body_field(context, field, value):
    dpath.new(context.obj, field, value)


@when(parsers.parse("admin's request method is {request_method}"))
@then(parsers.parse("admin's request method is {request_method}"))
def admin_request_method(admin_context, request_method):
    admin_context.admin.method = request_method


@given(parsers.parse("form class is {form_class}"))
def form_class_is(admin_context, form_class):
    admin_context.form_class = locate(form_class)
    assert admin_context.form_class


@given("form has image to upload")
def form_has_image_to_upload(admin_context, small_image):
    admin_context.form_files = {"image": small_image}


def get_data(resource):
    resource.revalidate()
    run_on_commit_events()
    resource.refresh_from_db()
    assert resource.tabular_data_schema
    data = resource.__dict__
    data["dataset"] = resource.dataset_id
    data["has_dynamic_data"] = False
    data["has_high_value_data"] = False
    data["has_high_value_data_from_ec_list"] = False
    data["has_research_data"] = False
    return data


@given(parsers.parse("form {object_type} data is {form_data}"))
def form_data_is(
    admin_context,
    institution,
    tag_pl,
    tag_en,
    categories,
    buzzfeed_fakenews_resource,
    geo_tabular_data_resource,
    object_type,
    form_data,
):
    data_map = {
        "dataset": {
            "categories": [x.id for x in categories],
            "customfields": None,
            "has_dynamic_data": False,
            "has_high_value_data": False,
            "has_high_value_data_from_ec_list": False,
            "has_research_data": False,
            "license_condition_db_or_copyrighted": None,
            "license_condition_modification": None,
            "license_condition_original": None,
            "license_condition_personal_data": None,
            "license_condition_responsibilities": None,
            "license_condition_cc40_responsibilities": None,
            "license_condition_source": None,
            "license_id": "other-pd",
            "notes": "more than 20 characters",
            "organization": institution.id,
            "slug": "test",
            "status": "published",
            "tags_en": [],
            "tags_pl": [tag_pl],
            "title": "Test",
            "update_frequency": "weekly",
            "url": "http://cos.tam.pl",
        }
    }
    if object_type == "tabular":
        data = get_data(buzzfeed_fakenews_resource)
    elif object_type == "geo":
        data = get_data(geo_tabular_data_resource)
    else:
        data = data_map.get(object_type, {})
    data.update(json.loads(form_data))
    admin_context.form_data = data


@given(parsers.parse("form instance is {form_instance}"))
def form_instance_is(admin_context, geo_tabular_data_resource, tabular_resource, form_instance):
    if form_instance == "geo_tabular_data_resource":
        admin_context.form_instance = geo_tabular_data_resource
    elif form_instance == "tabular_resource":
        admin_context.form_instance = tabular_resource


@given(parsers.parse("admin's request logged user is {user_type}"))
def admin_request_logged_user_is(admin_context, user_type):
    _factory = factories_registry.get_factory(user_type)
    assert _factory is not None
    admin_context.admin.user = _factory.create(
        email="{}@dane.gov.pl".format(user_type.replace(" ", "_")),
        password="12345.Abcde",
        phone="0048123456789",
    )


@given(parsers.parse("admin's request logged {user_type} created with params {user_params}"))
def admin_request_logged_user_with_id(admin_context, user_type, user_params):
    _factory = factories_registry.get_factory(user_type)
    assert _factory is not None
    data = json.loads(user_params)
    admin_context.admin.user = _factory(**data)


@given("admin's request user is unauthenticated")
def admin_request_user_unauthenticated(admin_context):
    admin_context.admin.user = None


@when(parsers.parse("admin's request posted {data_type} data is {req_post_data}"))
def api_request_post_data(admin_context, data_type, req_post_data):
    post_data = json.loads(req_post_data)
    default_post_data = {
        "action": {
            "action": "export_to_csv",
        },
        "alert": {
            "title_pl": "Alert title",
            "description_pl": "alert description",
            "title_en": "",
            "description_en": "",
            "status": "published",
        },
        "application": {
            "title": "Application title",
            "slug": "application-title",
            "notes": "opis",
            "url": "http://test.pl",
            "status": "published",
        },
        "article": {
            "title": "Test with article title",
            "slug": "",
            "notes": "Tresc",
            "status": "published",
            "category": None,
        },
        "course": {
            "modules-TOTAL_FORMS": "1",
            "modules-INITIAL_FORMS": "0",
            "modules-MIN_NUM_FORMS": "1",
            "modules-MAX_NUM_FORMS": "1000",
            "modules-0-id": "",
            "modules-0-course": "",
            "modules-0-start": "",
            "modules-0-number_of_days": "",
            "modules-0-type": "",
            "modules-__prefix__-id": "",
            "modules-__prefix__-course": "",
            "modules-__prefix__-start": "",
            "modules-__prefix__-number_of_days": "",
            "modules-__prefix__-type": "",
            "_save": "",
            "title": "",
            "participants_number": "",
            "venue": "",
            "notes": "",
            "file": "",
            "materials_file": "",
            "status": "published",
        },
        "dataset": {
            "title": "Test with dataset title",
            "notes": "more than 20 characters",
            "status": "published",
            "update_frequency": "weekly",
            "url": "http://www.test.pl",
            "organization": [],
            "tags": [],
            "has_high_value_data": False,
            "has_high_value_data_from_ec_list": False,
            "has_dynamic_data": False,
            "has_research_data": False,
            "resources-TOTAL_FORMS": "0",
            "resources-INITIAL_FORMS": "0",
            "resources-MIN_NUM_FORMS": "0",
            "resources-MAX_NUM_FORMS": "1000",
            "supplements-INITIAL_FORMS": "0",
            "supplements-MAX_NUM_FORMS": "10",
            "supplements-MIN_NUM_FORMS": "0",
            "supplements-TOTAL_FORMS": "0",
            "resources-2-TOTAL_FORMS": "0",
            "resources-2-INITIAL_FORMS": "0",
            "resources-2-MIN_NUM_FORMS": "0",
            "resources-2-MAX_NUM_FORMS": "1000",
            "resources-2-0-has_high_value_data": False,
            "resources-2-0-has_high_value_data_from_ec_list": False,
            "resources-2-0-has_dynamic_data": False,
            "resources-2-0-language": "pl",
            "resources-2-0-has_research_data": False,
            "resources-2-0-contains_protected_data": False,
            # nested admin required fields.
            "resources-2-0-supplements-TOTAL_FORMS": "0",
            "resources-2-0-supplements-INITIAL_FORMS": "0",
            "resources-2-0-supplements-MIN_NUM_FORMS": "0",
            "resources-2-0-supplements-MAX_NUM_FORMS": "1000",
            "resources-2-empty-supplements-TOTAL_FORMS": "0",
            "resources-2-empty-supplements-INITIAL_FORMS": "0",
            "resources-2-empty-supplements-MIN_NUM_FORMS": "0",
            "resources-2-empty-supplements-MAX_NUM_FORMS": "1000",
        },
        "datasource": {
            "_save": [""],
            "name": [""],
            "description": [""],
            "source_type": [""],
            "source_hash": [""],
            "xml_url": [""],
            "portal_url": ["http://example.com"],
            "api_url": [""],
            "organization": [],
            "frequency_in_days": [],
            "status": [""],
            "license_condition_db_or_copyrighted": [""],
            "categories": [],
            "institution_type": ["local"],
            "imports-TOTAL_FORMS": ["0"],
            "imports-INITIAL_FORMS": ["0"],
            "imports-MIN_NUM_FORMS": ["0"],
            "imports-MAX_NUM_FORMS": ["0"],
            "datasource_datasets-TOTAL_FORMS": ["0"],
            "datasource_datasets-INITIAL_FORMS": ["0"],
            "datasource_datasets-MIN_NUM_FORMS": ["0"],
            "datasource_datasets-MAX_NUM_FORMS": ["0"],
        },
        "datasetsubmission": {},
        "guide": {
            "title": "test",
            "status": "published",
            "items-TOTAL_FORMS": 1,
            "items-INITIAL_FORMS": 0,
            "items-MIN_NUM_FORMS": 1,
            "items-MAX_NUM_FORMS": 1000,
            "items-0-title": "test",
            "items-0-content": "test",
            "items-0-route": "/",
            "items-0-css_selector": "test",
            "items-0-position": "top",
            "items-0-order": 0,
        },
        "institution": {
            "_save": "",
            "institution_type": "local",
            "title": "Instytucja testowa X",
            "slug": "",
            "abbreviation": "TEST",
            "status": "published",
            "description": "",
            "image": "",
            "postal_code": "00-060",
            "city": "Warszawa",
            "street_type": "ul",
            "street": "Królewska",
            "street_number": "27",
            "flat_number": "",
            "email": "test@dane.gov.pl",
            "tel": "222500110",
            "tel_internal": "",
            "fax": "",
            "fax_internal": "",
            "epuap": "123",
            "regon": "145881488",
            "website": "https://mc.gov.pl",
            "title_en": "",
            "description_en": "",
            "slug_en": "",
            "datasets-TOTAL_FORMS": "0",
            "datasets-INITIAL_FORMS": "0",
            "datasets-MIN_NUM_FORMS": "0",
            "datasets-MAX_NUM_FORMS": "0",
            "datasets-2-TOTAL_FORMS": "0",
            "datasets-2-INITIAL_FORMS": "0",
            "datasets-2-MIN_NUM_FORMS": "0",
            "datasets-2-MAX_NUM_FORMS": "1000",
            "datasets-__prefix__-id": "",
            "datasets-__prefix__-organization": "",
            "datasets-2-__prefix__-title": "",
            "datasets-2-__prefix__-notes": "",
            "datasets-2-__prefix__-url": "",
            "datasets-2-__prefix__-update_frequency": "weekly",
            "datasets-2-__prefix__-category": "",
            "datasets-2-__prefix__-status": "published",
            "datasets-2-__prefix__-license_condition_responsibilities": "",
            "datasets-2-__prefix__-license_condition_cc40_responsibilities": "",
            "datasets-2-__prefix__-license_condition_db_or_copyrighted": "",
            "datasets-2-__prefix__-license_condition_personal_data": "",
            "datasets-2-__prefix__-id": "",
            "datasets-2-__prefix__-organization": "",
            "json_key[datasets-2-__prefix__-customfields]": "key",
            "json_value[datasets-2-__prefix__-customfields]": "value",
            # default dataset formset data if: "datasets-2-TOTAL_FORMS": > 0.
            "datasets-2-0-title": "test",
            "datasets-2-0-notes": "<p>123</p>",
            "datasets-2-0-url": "",
            "json_key[datasets-2-0-customfields]": "key",
            "json_value[datasets-2-0-customfields]": "value",
            "datasets-2-0-update_frequency": "weekly",
            "datasets-2-0-category": "",
            "datasets-2-0-status": "published",
            "datasets-2-0-license_condition_responsibilities": "",
            "datasets-2-0-license_condition_cc40_responsibilities": "",
            "datasets-2-0-license_condition_db_or_copyrighted": "",
            "datasets-2-0-license_condition_personal_data": "",
            "datasets-2-0-id": "",
            "datasets-2-0-organization": "",
            "datasets-2-0-has_high_value_data": False,
            "datasets-2-0-has_high_value_data_from_ec_list": False,
            "datasets-2-0-has_dynamic_data": False,
            "datasets-2-0-has_research_data": False,
            "datasets-2-0-supplements-TOTAL_FORMS": "0",
            "datasets-2-0-supplements-INITIAL_FORMS": "0",
            "datasets-2-0=supplements-MIN_NUM_FORMS": "0",
            "datasets-2-0-supplements-MAX_NUM_FORMS": "10",
        },
        "lab_event": {
            "reports-TOTAL_FORMS": "1",
            "reports-INITIAL_FORMS": "0",
            "reports-MIN_NUM_FORMS": "1",
            "reports-MAX_NUM_FORMS": "2",
            "reports-0-id": "",
            "reports-0-lab_event": "",
            "reports-0-link": "",
            "reports-0-file": "",
            "reports-__prefix__-id": "",
            "reports-__prefix__-lab_event": "",
            "reports-__prefix__-link": "",
            "reports-__prefix__-file": "",
            "_save": "",
            "title": "",
            "notes": "",
            "event_type": "",
            "execution_date": "",
        },
        "resource": {
            "Resource_file_tasks-INITIAL_FORMS": "0",
            "Resource_file_tasks-MAX_NUM_FORMS": "1000",
            "Resource_file_tasks-MIN_NUM_FORMS": "0",
            "Resource_file_tasks-TOTAL_FORMS": "3",
            "Resource_data_tasks-INITIAL_FORMS": "0",
            "Resource_data_tasks-MAX_NUM_FORMS": "1000",
            "Resource_data_tasks-MIN_NUM_FORMS": "0",
            "Resource_data_tasks-TOTAL_FORMS": "3",
            "Resource_link_tasks-INITIAL_FORMS": "0",
            "Resource_link_tasks-MAX_NUM_FORMS": "1000",
            "Resource_link_tasks-MIN_NUM_FORMS": "0",
            "Resource_link_tasks-TOTAL_FORMS": "3",
            "supplements-INITIAL_FORMS": "0",
            "supplements-MAX_NUM_FORMS": "10",
            "supplements-MIN_NUM_FORMS": "0",
            "supplements-TOTAL_FORMS": "0",
            "_save": "",
            "from_resource": "",
            "related_resource": "",
            "title_en": "",
            "description_en": "",
            "slug_en": "",
            "has_high_value_data": False,
            "has_high_value_data_from_ec_list": False,
            "has_dynamic_data": False,
            "has_research_data": False,
            "contains_protected_data": False,
            "language": "pl",
        },
        "showcase": {
            "category": "app",
            "license_type": "free",
            "title": "Showcase title",
            "slug": "showcase-title",
            "notes": "opis",
            "url": "http://test.pl",
            "status": "published",
        },
        "showcaseproposal": {
            "category": "app",
            "license_type": "free",
            "title": "Showcase title",
            "slug": "showcase-title",
            "notes": "opis",
            "url": "https://test.pl",
            "external_datasets": [{"title": "example.com", "url": "https://example.com"}],
            "keywords": ["test"],
        },
        "user": {
            "email": "",
            "fullname": "",
            "phone": "",
            "phone_internal": "",
            "is_staff": False,
            "is_superuser": False,
            "state": "active",
            "organizations": [],
        },
    }

    assert data_type in default_post_data.keys()
    default_post_data["datasets-2-0-tags_pl"] = []
    default_post_data["datasets-2-0-tags_en"] = []
    data = default_post_data.get(data_type, {}).copy()
    data.update(post_data)
    admin_context.obj = data


@when(parsers.parse("admin's request posted data with {update_frequency}"))
def api_request_post_data_with_update_frequency_param(admin_context, request, update_frequency):
    post_data: Dict[str, Any] = request.getfixturevalue("post_data_to_create_dataset")

    post_data["title"] = "Dataset for update_frequency test"
    post_data["update_frequency"] = update_frequency
    post_data["organization"] = 999
    post_data["categories"] = [999]
    post_data["tags"] = [999]
    post_data["tags_pl"] = [999]
    admin_context.obj = post_data


@when(parsers.parse("admin requests to delete selected resources with ids {obj_ids}"))
@when(parsers.parse("admin requests to delete selected datasets with ids {obj_ids}"))
def api_delete_selected_request(admin_context: Dict[str, Any], obj_ids: str):
    req_post_data = {
        "action": "delete_selected",
        "_selected_action": obj_ids.split(", "),
    }
    admin_context.obj = req_post_data


@when(parsers.parse("admin's request posted files {req_post_files}"))
def api_request_post_files(admin_context, req_post_files):
    post_file_names = json.loads(req_post_files)
    posted_files = {}
    content_type_for_extension: Dict[str, str] = {
        "xls": "application/vnd.ms-excel",
        "xlsx": "application/vnd.ms-excel",
        "csv": "text/csv",
    }
    for field_name, file_name in post_file_names.items():
        with open(os.path.join(settings.TEST_SAMPLES_PATH, file_name), "rb") as f:
            simple_uploaded_file_params = {
                "name": file_name,
                "content": f.read(),
            }
            extension: str = file_name.split(".")[-1].lower()
            content_type: str = content_type_for_extension.get(extension)
            if content_type:
                simple_uploaded_file_params.update({"content_type": content_type})

            posted_files[field_name] = SimpleUploadedFile(**simple_uploaded_file_params)
    admin_context.obj.update(posted_files)


@when(parsers.parse("admin's request posted links {req_post_links}"))
@when("admin's request posted links <req_post_links>")
def api_request_post_links(admin_context, httpsserver_custom, req_post_links):
    _magic = magic.Magic(mime=True, mime_encoding=True)
    data = json.loads(req_post_links)
    posted_links = {}
    for field_name, file_name in data.items():
        file_path = os.path.join(settings.TEST_SAMPLES_PATH, file_name)
        with open(file_path, "rb") as file:
            content = file.read()
        httpsserver_custom.serve_content(
            content=content,
            headers={
                "Content-Disposition": f'attachment; filename="{file_name}"',
                "Content-Type": _magic.from_buffer(content),
            },
        )
        posted_links[field_name] = httpsserver_custom.url

    admin_context.obj.update(posted_links)


@when("admin's request save and continue will be chosen")
def admin_request_save_and_continue(admin_context):
    admin_context.obj.pop("_save", None)
    admin_context.obj["_continue"] = ""


def form_is_validated(admin_context):
    assert admin_context.form_class
    kwargs = {"data": admin_context.form_data}
    if admin_context.form_instance:
        kwargs["instance"] = admin_context.form_instance
    if admin_context.form_files:
        kwargs["files"] = admin_context.form_files
    admin_context.form = admin_context.form_class(**kwargs)


@then("form is valid")
def form_is_valid(admin_context):
    form_is_validated(admin_context)
    form = admin_context.form
    assert form.is_valid(), 'Form "%s" should be valid, but has errors: %s"' % (
        form.__class__,
        form.errors,
    )


@then("form is not valid")
def form_is_not_valid(admin_context):
    form_is_validated(admin_context)
    form = admin_context.form
    assert not form.is_valid()


@then("form is saved")
def form_is_saved(admin_context):
    assert admin_context.form
    admin_context.form.save()


@then(parsers.parse("form field {field_name} error is {error_msg}"))
def form_field_error_is(admin_context, field_name, error_msg):
    form_is_validated(admin_context)
    form = admin_context.form
    assert not form.is_valid()
    assert field_name in form.errors, f"Field {field_name} was not found in form.errors"
    errors = form.errors[field_name]
    assert any([error_msg in x for x in errors]), f'"{error_msg}" not found in {errors}'


@then(parsers.parse("admin's response status code is {status_code:d}"))
def admin_response_status_code(admin_context, status_code):
    assert status_code == admin_context.response.status_code, 'Response status should be "%s", is "%s"' % (
        status_code,
        admin_context.response.status_code,
    )


@then(parsers.parse("admin's response page is not editable"))
def admin_response_page_not_editable(admin_context):
    assert admin_context.response.status_code == 200
    cnt = admin_context.response.content.decode()
    assert '<button type="submit" class="btn btn-high  btn-info" name="_save" >Zapisz</button>' not in cnt
    assert '<button type="submit" name="_continue" class="btn btn-high">Zapisz i kontynuuj edycję</button>' not in cnt
    assert '<button type="submit" name="_addanother" class="btn">Zapisz i dodaj kolejny</button>' not in cnt
    assert 'id="duplicate_button"' not in cnt
    assert 'id="revalidate_button"' not in cnt


@then(parsers.parse("admin's response page contains {contained_value}"))
def admin_response_page_contains(admin_context, contained_value):
    content = admin_context.response.content.decode()
    assert contained_value in content, f'Page content should contain phrase: "{contained_value}". Actual content is: {content}'


@then(parsers.parse("admin's response body field {field} is {value}"))
def admin_response_body_field(admin_context, field, value):
    data = admin_context.response.json()
    values = [str(value) for value in dpath.util.values(data, field)]
    assert set(values) == {value}, "value should be {}, but is {}. Full response: {}".format({value}, set(values), data)


@then(parsers.parse("admin's response page form contains {contained_value} and {another_value}"))
def admin_response_page_contains_values(admin_context, contained_value, another_value):
    content = admin_context.response.content.decode()
    assert (
        contained_value in content and another_value in content
    ), f'Page content should contain phrases: "{contained_value}" and "{another_value}"'


@then(parsers.parse("admin's response page not contains {value}"))
def admin_response_page_not_contains(admin_context, value):
    content = admin_context.response.content.decode()
    assert value not in content, f'Page content should not contain phrase: "{value}". Actual content is: {content}'


@then(parsers.parse("admin's response page {condition} element {tag_name} with {text}"))
def admin_response_page_contains_element(admin_context, condition: Literal["has", "has no"], tag_name: str, text: str):
    content: str = admin_context.response.content.decode()
    soup = BeautifulSoup(content, "html.parser")
    elements = list(soup.find_all(tag_name))
    expects_elements_to_exist: bool = True if condition == "has" else False
    found = False
    for field in elements:
        if text in field.text:
            found = True
            break
    if expects_elements_to_exist:
        assert elements, f"Page does not contain any {tag_name}. Actual content is: {content}"
        assert found, f"No {tag_name} contains {text}. Actual content is: {content}"
    else:
        assert not found, f"Found {tag_name} with {text}. Actual content is: {content}"


@then(parsers.parse("admin's response resolved url name is {url_name}"))
def admin_response_resolved_url_name_is(admin_context, url_name):
    resolved_url_name = admin_context.response.resolver_match.url_name
    assert url_name == resolved_url_name, f"Resolved name is: {resolved_url_name}"


def get_response(admin_context):
    client = Client()
    if admin_context.admin.user:
        client.force_login(admin_context.admin.user)
    translation.activate("pl")
    if admin_context.admin.method == "POST":
        response = client.post(
            admin_context.admin.path,
            data=getattr(admin_context, "obj", None),
            follow=True,
        )
    else:
        response = client.get(admin_context.admin.path, follow=True)
    return response


@when("admin's page is requested")
@then("admin's page is requested")
def admin_path_is_requested(admin_context):
    admin_context.response = get_response(admin_context)


@when(parsers.parse("admin's page {page_url} is requested"))
@then(parsers.parse("admin's page {page_url} is requested"))
def admin_page_is_requested(admin_context, page_url):
    admin_context.admin.path = page_url
    admin_context.response = get_response(admin_context)


def create_dataset_for_given_institution_type(institution_type: str, obj_id: int, title: Optional[str] = None) -> Dataset:
    organization = OrganizationFactory.create(
        institution_type=institution_type,
    )
    create_params = {
        "pk": obj_id,
        "organization": organization,
    }
    if title:
        create_params.update({"title": title})
    return DatasetFactory.create(**create_params)


def create_dataset_with_dga_resource(
    dataset_id: int,
    resource_id: Optional[int] = None,
    resource_title: Optional[str] = None,
    dataset_title: Optional[str] = None,
) -> Dataset:
    _dataset = create_dataset_for_given_institution_type(institution_type="state", obj_id=dataset_id, title=dataset_title)
    resource_create_params = {"dataset": _dataset}
    if resource_id:
        resource_create_params.update({"pk": resource_id})
    if resource_title:
        resource_create_params.update({"title": resource_title})

    DGAResourceFactory.create(**resource_create_params)
    return _dataset


@given(parsers.parse("dataset with pk {object_id:d} for {institution_type} institution"))
def dataset_for_given_institution_type(object_id, institution_type):
    create_dataset_for_given_institution_type(institution_type, object_id)


@given(parsers.parse("dataset with pk {dataset_id:d} containing dga resource"))
def dataset_with_dga_resource(dataset_id):
    create_dataset_with_dga_resource(dataset_id)


@given(parsers.parse("dataset with pk {dataset_id:d} containing dga resource with pk {resource_id:d}"))
def dataset_with_dga_resource_with_given_id(dataset_id, resource_id):
    create_dataset_with_dga_resource(dataset_id, resource_id=resource_id)


@given(parsers.parse("dataset with pk {dataset_id:d} and title {dataset_title} containing dga resource"))
def named_dataset_with_dga_resource(dataset_id, dataset_title):
    create_dataset_with_dga_resource(dataset_id, dataset_title=dataset_title)


@given(parsers.parse("dataset with pk {dataset_id:d} containing dga resource with pk {resource_id:d} and title {resource_title}"))
def dataset_with_named_dga_resource_with_given_id(dataset_id, resource_id, resource_title):
    create_dataset_with_dga_resource(dataset_id, resource_id=resource_id, resource_title=resource_title)


def extract_hidden_fields_from_response(
    response_content: str,
) -> Dict[str, Union[str, List[str]]]:
    soup = BeautifulSoup(response_content, "html.parser")
    hidden_fields = soup.find_all("input", type="hidden")
    extracted_data = {}
    for field in hidden_fields:
        name = field.get("name")
        value = field.get("value")
        if name:
            if name in extracted_data:
                if not isinstance(extracted_data[name], list):
                    extracted_data[name] = [extracted_data[name]]
                extracted_data[name].append(value)
            else:
                extracted_data[name] = value

    return extracted_data


@when("admin confirms saving the resource with posted data")
@when("admin confirms deleting selected datasets")
@when("admin confirms deleting selected resources")
@when("admin confirms deleting dataset")
@when("admin confirms deleting resource")
def admin_confirms_resource_creation(admin_context):
    posted_data = extract_hidden_fields_from_response(admin_context.response.content)
    admin_context.obj = posted_data
    admin_context.response = get_response(admin_context)


@when(parsers.parse("'{admin_class_path}' creation page is requested"))
@then(parsers.parse("'{admin_class_path}' creation page is requested"))
def creation_page_is_requested(admin_context, admin_class_path):
    admin_class_path_to_model = {
        f"{admin_class.__class__.__module__}.{admin_class.__class__.__name__}": (
            model,
            admin_class,
        )
        for model, admin_class in admin.site._registry.items()
    }
    model, admin_class_instance = admin_class_path_to_model[admin_class_path]
    admin_class = type(admin_class_instance)
    admin_context.admin.path = getattr(model, "get_admin_add_url")()

    admin_context.object_id = None
    admin_context.object_model = model

    def save_model(self, request, obj, form, change):
        original_save_model(self, request, obj, form, change)
        admin_context.object_id = obj.id

    original_save_model = getattr(admin_class, "save_model")
    with mock.patch(f"{admin_class_path}.save_model", save_model):
        admin_context.response = get_response(admin_context)


@when(parsers.parse("'{admin_class_path}' edition page is requested for created object"))
@then(parsers.parse("'{admin_class_path}' edition page is requested for created object"))
def edition_page_is_requested(admin_context, admin_class_path):
    admin_class_path_to_model = {
        f"{admin_class.__class__.__module__}.{admin_class.__class__.__name__}": (
            model,
            admin_class,
        )
        for model, admin_class in admin.site._registry.items()
    }
    model, admin_class_instance = admin_class_path_to_model[admin_class_path]
    admin_context.admin.path = getattr(model, "get_admin_change_url")(admin_context.object_id)
    admin_context.response = get_response(admin_context)


@when(parsers.parse("'{field_name}' field of created object is '{params}'"))
@then(parsers.parse("'{field_name}' field of created object is '{params}'"))
def field_of_created_object_is(admin_context, field_name, params):
    params = json.loads(params)
    model = admin_context.object_model.objects.get(id=admin_context.object_id)
    assert getattr(model, field_name) == params


@when(parsers.parse("set language to '{language}'"))
@then(parsers.parse("set language to '{language}'"))
def set_language_to(admin_context, language):
    admin_context.language = language


@when(parsers.parse("check if queryset.values match '{params}'"))
@then(parsers.parse("check if queryset.values match '{params}'"))
def check_if_queryset_values_match(admin_context, params):
    language = getattr(admin_context, "language", settings.LANGUAGE_CODE)
    params = json.loads(params)
    with translation.override(language):
        values = admin_context.object_model.objects.filter(id=admin_context.object_id).values(*params).first()
    for key, value in params.items():
        assert values[key] == value


@when(parsers.parse("admin's page with mocked geo api {page_url} is requested"))
@then(parsers.parse("admin's page with mocked geo api {page_url} is requested"))
def admin_page_with_mocked_geo_api_is_requested(admin_context, page_url, mocked_geocoder_responses):
    client = Client()
    client.force_login(admin_context.admin.user)
    translation.activate("pl")
    if admin_context.admin.method == "POST":
        with requests_mock.Mocker(real_http=True) as mock_request:
            for resp in mocked_geocoder_responses:
                mock_request.get(resp[0], json=resp[1])
            response = client.post(page_url, data=getattr(admin_context, "obj", None), follow=True)
    else:
        response = client.get(page_url, follow=True)
    admin_context.response = response


@when(parsers.parse("admin's page with geocoder mocked api for tabular data {page_url} is requested"))
@then(parsers.parse("admin's page with geocoder mocked api for tabular data {page_url} is requested"))
def admin_page_with_geo_mocked_api_for_tabular_data_is_requested(admin_context, page_url, geo_tabular_data_response):
    client = Client()
    api_expr = re.compile(settings.GEOCODER_URL + r"/v1/search/structured\?postalcode=\d{2}-\d{3}&locality=\w+")
    client.force_login(admin_context.admin.user)
    translation.activate("pl")
    if admin_context.admin.method == "POST":
        with requests_mock.Mocker(real_http=True) as mock_request:
            mock_request.get(api_expr, json=geo_tabular_data_response)
            response = client.post(page_url, data=getattr(admin_context, "obj", None), follow=True)
            run_on_commit_events()
    else:
        response = client.get(page_url, follow=True)
    admin_context.response = response


@then(parsers.parse("api's response data has length {number:d}"))
def api_response_data_has_length(context, number):
    data = context.response.json["data"]
    v_len = len(data) if data else 0
    assert v_len == int(number), "data length should be {}, but is {}".format(number, v_len)


@when("send_mail will raise SMTPException")
def api_request_csrf_token(context, mocker):
    mocker.patch("mcod.core.db.models.send_mail", side_effect=smtplib.SMTPException)


@then(parsers.parse("sparql store contains {item_type} {item_value}"))
def sparql_store_contains_subject(sparql_registry, item_type, item_value):
    items = {"subject": "s", "predicate": "p", "object": "o"}
    store_query = (
        f"SELECT ?{items[item_type]} WHERE {{ GRAPH {sparql_registry.graph_name}"
        f" {{ ?s ?p ?o . FILTER (?{items[item_type]} = {item_value}) }} }}"
    )
    response = sparql_registry.sparql_store.query(store_query, initNs=NAMESPACES)
    store_values = set([resp[0].n3() for resp in response])
    assert item_value in store_values


@then(parsers.parse("sparql store does not contain subject {subject}"))
def sparql_store_does_not_contain_subject(sparql_registry, subject):
    store_query = f"SELECT ?s WHERE {{ GRAPH {sparql_registry.graph_name} {{ ?s ?p ?o . FILTER (?s = {subject}) }} }}"
    response = sparql_registry.sparql_store.query(store_query)
    store_subjects = set([resp[0].n3() for resp in response])
    assert subject not in store_subjects


@then(parsers.parse("sparql store contains triple with attributes {attributes}"))
def sparql_store_contains_triple(sparql_registry, attributes):
    parsed_attrs = json.loads(attributes)
    subject = parsed_attrs.get("subject") or "?s"
    predicate = parsed_attrs.get("predicate") or "?p"
    object = parsed_attrs.get("object") or "?o"
    store_query = f"ASK WHERE {{ GRAPH {sparql_registry.graph_name} {{ {subject} {predicate} {object} }} }}"
    response = sparql_registry.sparql_store.query(store_query, initNs=NAMESPACES)
    assert response.askAnswer


@then(parsers.parse("latest {obj_type} attribute {attr} is {value}"))
def latest_object_attribute_is(obj_type, attr, value):
    _factory = factories_registry.get_factory(obj_type)
    model = _factory._meta.model
    obj = model.raw.latest("id")
    attr_val = getattr(obj, attr)
    attr_val = str(attr_val) if not isinstance(attr_val, str) else attr_val
    if value == "not None":
        assert attr_val is not None, f"{obj} attribute {attr} should not be None, but is {attr_val}"
    else:
        assert attr_val == value, f"{obj} attribute {attr} should be {value}, but is {attr_val}"


@given(parsers.parse('removed {object_type} objects with ids "{object_ids}"'))
def removed_objects_with_ids_2(object_type, object_ids):
    _factory = factories_registry.get_factory(object_type)
    split_ids = object_ids.split(",")
    for obj_id in split_ids:
        instance = _factory(pk=int(obj_id))
        instance.is_removed = True
        instance.save()


@given(
    parsers.parse(
        "removed {object_type} objects with ids {object_with_related_removed_ids} and removed related "
        "{related_object_type} through {relation_name}"
    )
)
def removed_objects_with_ids_and_removed_related_object(
    object_type, object_with_related_removed_ids, related_object_type, relation_name
):
    _factory = factories_registry.get_factory(object_type)
    _related_factory = factories_registry.get_factory(related_object_type)
    split_ids = object_with_related_removed_ids.split(",")
    related_object = _related_factory.create(is_removed=True)
    factory_kwargs = {"is_removed": True, relation_name: related_object}
    for obj_id in split_ids:
        factory_kwargs["pk"] = int(obj_id)
        _factory.create(**factory_kwargs)


@then(parsers.parse("{object_type} with title {title} contains data {data_str}"))
def obj_with_title_attribute_is(object_type, title, data_str):
    model = apps.get_model(object_type)
    obj = model.objects.get(title=title)
    data = json.loads(data_str)
    for attr_name, attr_value in data.items():
        obj_attr = getattr(obj, attr_name)
        if isinstance(obj_attr, datetime.date):
            obj_attr = str(obj_attr)
        assert obj_attr == attr_value, f"{object_type} attribute {attr_name} should be {attr_value}, but is {obj_attr}"


@then(parsers.parse("{object_type} with id {obj_id} contains data {data_str}"))
def obj_with_id_attribute_is(object_type, obj_id, data_str):
    model = apps.get_model(object_type)
    obj = model.raw.get(id=obj_id) if hasattr(model, "raw") else model.objects.get(id=obj_id)
    data = json.loads(data_str)
    for attr_name, attr_value in data.items():
        obj_attr = getattr(obj, attr_name)
        if isinstance(obj_attr, datetime.date):
            obj_attr = str(obj_attr)
        assert obj_attr == attr_value, f"{object_type} attribute {attr_name} should be {attr_value}, but is {obj_attr}"


@then(parsers.parse("api's response data has zipped {files_count:d} files"))
def api_response_data_has_zipped_files(context, files_count):
    with zipfile.ZipFile(BytesIO(context.response.content)) as z:
        assert len(z.filelist) == files_count
