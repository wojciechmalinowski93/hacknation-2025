from typing import List

import pytest
from django.core.management import call_command
from pytest_mock import MockerFixture

from mcod.datasets.factories import DatasetFactory
from mcod.organizations.factories import OrganizationFactory
from mcod.organizations.models import Organization
from mcod.resources.factories import ResourceFactory
from mcod.resources.tasks import delete_es_resource_tabular_data_indexes_for_organization
from mcod.resources.tasks.tasks import _get_resources_ids_for_organization


def test_get_resources_ids_for_organization():
    """
    Checks if function `_get_resources_ids_for_organization`
    gets for the organization only resources ids which are not permanently removed.
    """
    # GIVEN
    organization = OrganizationFactory()
    dataset = DatasetFactory(organization=organization)
    resources_published_1 = ResourceFactory(dataset=dataset, status="published")
    resources_published_2 = ResourceFactory(dataset=dataset, status="published")
    resources_draft = ResourceFactory(dataset=dataset, status="draft")
    resources_in_recycle = ResourceFactory(dataset=dataset, is_removed=True)
    resources_permanently_removed = ResourceFactory(dataset=dataset, is_permanently_removed=True)
    resources_permanently_removed_2 = ResourceFactory(dataset=dataset, is_permanently_removed=True)

    # other organization resources
    ResourceFactory.build_batch(10)

    # WHEN
    resources_ids: List[int] = _get_resources_ids_for_organization(organization_id=organization.id)
    # THEN
    assert len(resources_ids) == 4
    assert resources_published_1.id in resources_ids
    assert resources_published_2.id in resources_ids
    assert resources_draft.id in resources_ids
    assert resources_in_recycle.id in resources_ids
    assert resources_permanently_removed.id not in resources_ids
    assert resources_permanently_removed_2 not in resources_ids


@pytest.fixture
def organizations_developers_and_others() -> List[Organization]:
    organizations = [
        *OrganizationFactory.create_batch(4, institution_type=Organization.INSTITUTION_TYPE_DEVELOPER),
        OrganizationFactory(institution_type=Organization.INSTITUTION_TYPE_STATE),
        OrganizationFactory(institution_type=Organization.INSTITUTION_TYPE_LOCAL),
        OrganizationFactory(institution_type=Organization.INSTITUTION_TYPE_PRIVATE),
        OrganizationFactory(institution_type=Organization.INSTITUTION_TYPE_OTHER),
    ]

    # add developer organization which is in bin (was deleted)
    deleted_developer = OrganizationFactory(institution_type=Organization.INSTITUTION_TYPE_DEVELOPER)
    deleted_developer.delete()
    organizations.append(deleted_developer)

    # add developer organization which is permanently deleted
    permanently_deleted_developer = OrganizationFactory(institution_type=Organization.INSTITUTION_TYPE_DEVELOPER)
    permanently_deleted_developer.delete()
    permanently_deleted_developer.delete()  # second delete -> permanent delete
    organizations.append(permanently_deleted_developer)

    return organizations


@pytest.mark.parametrize("dry_run", [True, False])
def test_command_delete_indexes_for_developers(
    mocker: MockerFixture, organizations_developers_and_others: List[Organization], dry_run: bool
):
    """
    Checks if command `delete_indexes_for_developers` delete resource indexes only for developer organizations
    (which are not permanently removed)
    and only when command is called without parameter `dry_run`
    """

    # GIVEN
    developers_ids: List[int] = [
        organization.id
        for organization in organizations_developers_and_others
        if organization.institution_type == Organization.INSTITUTION_TYPE_DEVELOPER and not organization.is_permanently_removed
    ]

    mocked_task = mocker.patch(
        "mcod.resources.management.commands.delete_indexes_for_developers."
        "delete_es_resource_tabular_data_indexes_for_organization",
        mocker.MagicMock(),
    )

    # WHEN
    call_command("delete_indexes_for_developers", dry_run=dry_run)

    # THEN
    if dry_run:
        mocked_task.delay.assert_not_called()
    else:
        assert mocked_task.delay.call_count == 5
        task_args: List[int] = [x[0][0] for x in mocked_task.delay.call_args_list]
        assert task_args == developers_ids


def test_first_org_pk_last_org_pk_parameters(mocker: MockerFixture, organizations_developers_and_others: List[Organization]):
    mocked_task = mocker.patch(
        "mcod.resources.management.commands.delete_indexes_for_developers."
        "delete_es_resource_tabular_data_indexes_for_organization",
        mocker.MagicMock(),
    )

    developers_ids: List[int] = sorted(
        [
            organization.id
            for organization in organizations_developers_and_others
            if organization.institution_type == Organization.INSTITUTION_TYPE_DEVELOPER
            and not organization.is_permanently_removed
        ]
    )

    # call without first_org_pk and last_org_pk
    call_command("delete_indexes_for_developers")
    assert mocked_task.delay.call_count == 5, "call without parameters --first-org-pk and --last-org-pk"

    # call given first_org_pk, last_org_pk not given
    mocked_task.reset_mock()
    call_command("delete_indexes_for_developers", first_org_pk=developers_ids[1])
    assert mocked_task.delay.call_count == 4, "call with only parameter --first-org-pk which excludes one developer id"

    # call not given first_org_pk, last_org_pk given
    mocked_task.reset_mock()
    call_command("delete_indexes_for_developers", last_org_pk=developers_ids[1])
    assert mocked_task.delay.call_count == 2, "call with only parameter --last-org-pk which excludes three developer ids"

    # call first_org_pk and last_org_pk include developers ids range
    mocked_task.reset_mock()
    call_command("delete_indexes_for_developers", first_org_pk=0, last_org_pk=max(developers_ids) + 1)
    assert (
        mocked_task.delay.call_count == 5
    ), "call with both parameters --first-org-pk and --last-org-pk which includes all developers ids"

    # call first_org_pk and last_org_pk outside of developers ids range
    mocked_task.reset_mock()
    call_command("delete_indexes_for_developers", first_org_pk=max(developers_ids) + 1, last_org_pk=max(developers_ids) + 100)
    assert (
        mocked_task.delay.call_count == 0
    ), "call with both parameters --first-org-pk and --last-org-pk which excludes all developers ids"


def test_task_delete_es_resource_tabular_data_indexes_for_organization(mocker: MockerFixture):
    # GIVEN
    organization: Organization = OrganizationFactory()
    dataset = DatasetFactory(organization=organization)
    resources_published = ResourceFactory(dataset=dataset, status="published")
    resources_draft = ResourceFactory(dataset=dataset, status="draft")
    resources_in_recycle = ResourceFactory(dataset=dataset, is_removed=True)
    ResourceFactory(dataset=dataset, is_permanently_removed=True)

    indexes_which_should_be_deleted: List[str] = [
        f"resource-{resources_published.id}",
        f"resource-{resources_draft.id}",
        f"resource-{resources_in_recycle.id}",
    ]

    mocked_task = mocker.patch("mcod.resources.tasks.tasks.delete_index")

    # WHEN
    delete_es_resource_tabular_data_indexes_for_organization(organization.id)
    task_args: List[str] = [x[0][0] for x in mocked_task.call_args_list]

    # THEN
    assert mocked_task.call_count == len(indexes_which_should_be_deleted)
    for deleted_index in task_args:
        assert deleted_index in indexes_which_should_be_deleted
