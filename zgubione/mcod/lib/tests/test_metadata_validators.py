from typing import Dict, List, Tuple

import pytest
from django.core.exceptions import ValidationError

from mcod.lib.metadata_validators import (
    validate_conflicting_high_value_data_flags,
    validate_high_value_data_from_ec_list_organization,
)
from mcod.organizations.models import Organization
from mcod.resources.dga_utils import (
    get_dga_resources_info_from_xml_harvester_file,
    validate_contains_protected_data_with_other_metadata,
    validate_institution_type_for_contains_protected_data,
)


@pytest.mark.parametrize(
    ("has_high_value_data", "has_high_value_data_from_ec_list", "validation_exc_occurred"),
    [
        (True, True, False),
        (False, False, False),
        (True, False, False),
        (True, None, False),
        (False, None, False),
        (None, True, True),  # conflicting
        (None, False, False),
        (None, None, False),
        (False, True, True),  # conflicting
    ],
)
def test_validate_conflicting_high_value_data_flags(
    has_high_value_data: bool,
    has_high_value_data_from_ec_list: bool,
    validation_exc_occurred: bool,
):
    if validation_exc_occurred:
        with pytest.raises(ValidationError):
            validate_conflicting_high_value_data_flags(
                has_high_value_data,
                has_high_value_data_from_ec_list,
            )
    else:
        validate_conflicting_high_value_data_flags(
            has_high_value_data,
            has_high_value_data_from_ec_list,
        )


@pytest.mark.parametrize(
    ("has_high_value_data_from_ec_list", "organization_type", "should_raise"),
    [
        # Test cases where ValidationError should be raised
        (True, Organization.INSTITUTION_TYPE_PRIVATE, True),
        (True, Organization.INSTITUTION_TYPE_DEVELOPER, True),
        # Test cases where ValidationError should not be raised
        (True, Organization.INSTITUTION_TYPE_LOCAL, False),
        (True, Organization.INSTITUTION_TYPE_STATE, False),
        (True, Organization.INSTITUTION_TYPE_OTHER, False),
        (False, Organization.INSTITUTION_TYPE_PRIVATE, False),
        (False, Organization.INSTITUTION_TYPE_OTHER, False),
        (False, Organization.INSTITUTION_TYPE_LOCAL, False),
        (False, Organization.INSTITUTION_TYPE_STATE, False),
        (False, Organization.INSTITUTION_TYPE_DEVELOPER, False),
        (None, Organization.INSTITUTION_TYPE_PRIVATE, False),
        (None, Organization.INSTITUTION_TYPE_OTHER, False),
        (None, Organization.INSTITUTION_TYPE_LOCAL, False),
        (None, Organization.INSTITUTION_TYPE_STATE, False),
        (None, Organization.INSTITUTION_TYPE_DEVELOPER, False),
    ],
)
def test_validate_high_value_data_from_ec_list(
    has_high_value_data_from_ec_list: bool,
    organization_type: str,
    should_raise: bool,
):
    """
    Tests the validation of high-value data eligibility based on organization
    type. Validates that ValidationError is raised only for private and other
    types when high-value data from EC list is set to True.
    """
    if should_raise:
        with pytest.raises(ValidationError):
            validate_high_value_data_from_ec_list_organization(
                has_high_value_data_from_ec_list,
                organization_type,
            )
    else:
        validate_high_value_data_from_ec_list_organization(
            has_high_value_data_from_ec_list,
            organization_type,
        )


@pytest.mark.parametrize(
    (
        "contains_protected_data",
        "has_dynamic_data",
        "has_research_data",
        "has_high_value_data",
        "has_high_value_data_from_ec_list",
        "validation_result",
    ),
    [
        # Test cases where validation result is not OK (False)
        (True, True, False, False, False, False),
        (True, False, True, False, False, False),
        (True, False, False, True, False, False),
        (True, False, None, False, True, False),
        # Test cases where validation result is OK (True)
        (False, False, False, False, False, True),
        (True, False, False, False, False, True),
        (True, None, None, False, False, True),
        (True, None, None, None, None, True),
    ],
)
def test_validate_contains_protected_data_with_other_metadata(
    contains_protected_data,
    has_dynamic_data,
    has_research_data,
    has_high_value_data,
    has_high_value_data_from_ec_list,
    validation_result,
):
    """
    Tests the validation of `contains_protected_data` with other `Resource` metadata.
    `contains_protected_data` can be set to True only if any `has_dynamic_data`, `has_research_data`,
    `has_high_value_data`, `has_high_value_data_from_ec_list` is not set to True.
    """

    assert validation_result == validate_contains_protected_data_with_other_metadata(
        contains_protected_data, has_dynamic_data, has_research_data, has_high_value_data, has_high_value_data_from_ec_list
    )


@pytest.mark.parametrize(
    ("contains_protected_data", "institution_type", "validation_result"),
    [
        # Test cases where validation result is not OK (False)
        (True, "private", False),
        (True, "other", False),
        (True, "developer", False),
        # Test cases where validation result is OK (True)
        (True, "state", True),
        (True, "local", True),
        # Test cases where contains_protected_data is False
        (False, "state", True),
        (False, "local", True),
        (False, "private", True),
        (False, "other", True),
        (False, "developer", True),
        # Test cases where contains_protected_data is not set
        (None, "state", True),
        (None, "local", True),
        (None, "private", True),
        (None, "other", True),
        (None, "developer", True),
    ],
)
def test_validate_contains_protected_data_with_institution_type(contains_protected_data, institution_type, validation_result):
    """
    Tests the validation of `contains_protected_data` eligibility based on organization
    type. Only `state` and `local` institutions are permitted to use `contains_protected_data`=True.
    """

    assert validation_result == validate_institution_type_for_contains_protected_data(contains_protected_data, institution_type)


@pytest.mark.parametrize(
    ("loaded_data", "expected_result"),
    [
        # 2 resources have `containsProtectedData` set True. Resources in different datasets
        (
            [
                {
                    "resources": [
                        {"containsProtectedData": True, "extIdent": 1, "title": {"polish": "First title"}},
                        {"containsProtectedData": False, "extIdent": 2, "title": {"polish": "Second title"}},
                    ]
                },
                {
                    "resources": [
                        {"containsProtectedData": False, "extIdent": 3, "title": {"polish": "Third title"}},
                        {"containsProtectedData": True, "extIdent": 4, "title": {"polish": "Fourth title"}},
                    ]
                },
            ],
            [(1, "First title"), (4, "Fourth title")],
        ),
        # 2 resources have `containsProtectedData` set True. Resources in the same dataset
        (
            [
                {
                    "resources": [
                        {"containsProtectedData": True, "extIdent": 1, "title": {"polish": "First title"}},
                        {"containsProtectedData": True, "extIdent": 2, "title": {"polish": "Second title"}},
                    ]
                },
                {
                    "resources": [
                        {"containsProtectedData": False, "extIdent": 3, "title": {"polish": "Third title"}},
                        {"containsProtectedData": False, "extIdent": 4, "title": {"polish": "Fourth  title"}},
                    ]
                },
            ],
            [(1, "First title"), (2, "Second title")],
        ),
        # no resources have `containsProtectedData` set True
        (
            [
                {
                    "resources": [
                        {"containsProtectedData": False, "extIdent": 1, "title": {"polish": "First title"}},
                        {"containsProtectedData": False, "extIdent": 2, "title": {"polish": "Second title"}},
                    ]
                },
                {
                    "resources": [
                        {"containsProtectedData": False, "extIdent": 3, "title": {"polish": "Third title"}},
                    ]
                },
            ],
            [],
        ),
    ],
)
def test_get_dga_resources_info_from_xml_harvester_file(loaded_data: List[Dict], expected_result: List[Tuple]):
    """
    Tests getting info about all resources having containsProtectedData set True in XML harvester file.
    """
    assert expected_result == get_dga_resources_info_from_xml_harvester_file(loaded_data)
