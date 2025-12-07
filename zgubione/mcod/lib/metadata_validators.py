from typing import Optional

from django.core.exceptions import ValidationError

from mcod.resources.dga_constants import ALLOWED_INSTITUTIONS_TO_USE_HIGH_VALUE_DATA_FROM_EC_LIST


def validate_conflicting_high_value_data_flags(
    has_high_value_data: Optional[bool],
    has_high_value_data_from_ec_list: Optional[bool],
) -> None:
    """
    Validates the consistency between the flags `has_high_value_data` and
    `has_high_value_data_from_ec_list`.

    Raises:
        ValidationError: If `has_high_value_data` is False and
        `has_high_value_data_from_ec_list` is True.

    See more: https://jira.coi.gov.pl/browse/OTD-720
    """
    if has_high_value_data is not True and has_high_value_data_from_ec_list is True:
        raise ValidationError("High value data flags conflict.")


def validate_high_value_data_from_ec_list_organization(
    has_high_value_data_from_ec_list: Optional[bool],
    organization_type: str,
) -> None:
    """
    Validates whether the high-value data from EC list can be used with the
    given organization type.

    Raises:
        ValidationError: If high-value data from the EC list is set for an
        ineligible organization type.

    See more: https://jira.coi.gov.pl/browse/OTD-720
    """
    if has_high_value_data_from_ec_list and organization_type not in ALLOWED_INSTITUTIONS_TO_USE_HIGH_VALUE_DATA_FROM_EC_LIST:
        raise ValidationError("Cannot use `high_value_data_from_ec_list` for this organization type.")
