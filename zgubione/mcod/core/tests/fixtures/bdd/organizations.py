import json
import os

import pytest
from django.apps import apps
from pytest_bdd import given, parsers, then, when

from mcod import settings
from mcod.core.tests.fixtures.bdd.common import copyfile
from mcod.core.tests.helpers.tasks import run_on_commit_events
from mcod.datasets.factories import DatasetFactory
from mcod.organizations.factories import OrganizationFactory


@pytest.fixture
def institution():
    org = OrganizationFactory.create()
    run_on_commit_events()
    return org


@pytest.fixture
def institutions():
    organizations = OrganizationFactory.create_batch(3)
    run_on_commit_events()
    return organizations


@given("institution")
def _institution():
    return OrganizationFactory.create()


@given("removed institution")
def removed_institution():
    org = OrganizationFactory.create(is_removed=True, title="Removed institution")
    return org


@pytest.fixture
def institution_with_datasets():
    org = OrganizationFactory.create()
    DatasetFactory.create_batch(2, organization=org)
    run_on_commit_events()
    return org


@given("institution with datasets")
def create_institution_with_datasets(institution_with_datasets):
    return institution_with_datasets


@given(parsers.parse("institution with id {institution_id:d} and {num:d} datasets"))
def institution_with_id_and_datasets(institution_id, num):
    org = OrganizationFactory.create(id=institution_id, title="Institution {} with datasets".format(institution_id))
    DatasetFactory.create_batch(num, organization=org)
    return org


@given(parsers.parse("institution with id {institution_id:d} and {num:d} datasets and {rm_num:d} removed datasets"))
def institution_with_id_and_datasets_and_removed_datasets(institution_id, num, rm_num):
    org = OrganizationFactory.create(id=institution_id, title="Institution {} with datasets.".format(institution_id))
    DatasetFactory.create_batch(num, organization=org)
    DatasetFactory.create_batch(rm_num, organization=org, is_removed=True)
    return org


@given(parsers.parse("{num:d} institutions"))
def x_institutions(num):
    return OrganizationFactory.create_batch(num)


@given(parsers.parse("institutions of type {institution_types}"))
def x_institutions_of_type(institution_types):
    institution_types = json.loads(institution_types)
    for institution_type, count in institution_types.items():
        OrganizationFactory.create_batch(count, institution_type=institution_type)


@when(parsers.parse("remove institution with id {organization_id}"))
@then(parsers.parse("remove institution with id {organization_id}"))
def remove_organization(organization_id):
    model = apps.get_model("organizations", "organization")
    inst = model.objects.get(pk=organization_id)
    inst.is_removed = True
    inst.save()


@when(parsers.parse("restore institution with id {organization_id}"))
@then(parsers.parse("restore institution with id {organization_id}"))
def restore_organization(organization_id):
    model = apps.get_model("organizations", "organization")
    inst = model.raw.get(pk=organization_id)
    inst.is_removed = False
    inst.save()


@when(parsers.parse("change status to {status} for institution with id {organization_id}"))
@then(parsers.parse("change status to {status} for institution with id {organization_id}"))
def change_organization_status(status, organization_id):
    model = apps.get_model("organizations", "organization")
    inst = model.objects.get(pk=organization_id)
    inst.status = status
    inst.save()


@pytest.fixture
def buzzfeed_organization(admin):
    from mcod.organizations.models import Organization

    _name = "buzzfeed-logo.jpg"
    copyfile(
        os.path.join(settings.TEST_SAMPLES_PATH, _name),
        os.path.join(settings.IMAGES_MEDIA_ROOT, _name),
    )

    return Organization.objects.create(
        title="Buzzfeed",
        description="BuzzFeed has breaking news, vital journalism, quizzes, videos",
        image="buzzfeed-logo.jpg",
        email="buzzfeed@test-buzzfeed.com",
        institution_type="state",
        website="https://www.buzzfeed.com",
        slug="buzzfeed",
        created_by=admin,
        modified_by=admin,
    )
