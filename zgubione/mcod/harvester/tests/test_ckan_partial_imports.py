from typing import Any, Dict, List
from unittest.mock import MagicMock, call, patch
from uuid import uuid4

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError

from mcod.datasets.factories import DatasetFactory
from mcod.harvester.ckan_utils import (
    CKANPartialImportError,
    format_dataset_hvd_conflict_error_details,
    format_dataset_in_trash_error_details,
    format_dataset_org_hvd_ec_conflict_error_details,
    format_invalid_license_error_details,
    format_organization_in_trash_error_details,
    format_res_dga_url_bad_columns_error_details,
    format_res_dga_url_no_field_error_details,
    format_res_dga_url_not_accessible_error_details,
    format_res_dga_url_remote_file_extension_error_details,
    format_res_hvd_conflict_error_details,
    format_res_org_hvd_ec_conflict_error_details,
)
from mcod.harvester.exceptions import CKANPartialValidationException
from mcod.harvester.factories import CKANDataSourceFactory
from mcod.harvester.models import DataSource
from mcod.organizations.factories import OrganizationFactory
from mcod.resources.dga_constants import (
    ALLOWED_INSTITUTIONS_TO_USE_HIGH_VALUE_DATA_FROM_EC_LIST,
    DGA_COLUMNS,
)
from mcod.resources.factories import DGAResourceFactory


@pytest.mark.ckan_partial_import
class TestCKANErrorDescriptionFormatters:
    def test_format_invalid_license_error_details(self):
        error_data = [
            {
                "item_id": "dataset-id-1",
                "license_id": "some-license-id-1",
            },
            {
                "item_id": "dataset-id-2",
                "license_id": "some-license-id-2",
            },
        ]
        result = format_invalid_license_error_details(error_data)
        expected_result = (
            'Wartość w polu license_id spoza słownika CC<div class="expandable">'
            "<p><strong>id zbioru danych:</strong> dataset-id-1</p>"
            "<p><strong>license_id:</strong> some-license-id-1</p><br>"
            "<p><strong>id zbioru danych:</strong> dataset-id-2</p>"
            "<p><strong>license_id:</strong> some-license-id-2</p></div>"
        )
        assert result == expected_result

    def test_format_organization_in_trash_error_details(self):
        error_data = [
            {
                "item_id": "dataset-id-1",
                "organization_title": "Org Title 1",
            },
            {
                "item_id": "dataset-id-2",
                "organization_title": "Org Title 2",
            },
        ]
        result = format_organization_in_trash_error_details(error_data)
        expected_result = (
            '<p>Instytucja znajduje się w koszu</p><div class="expandable">'
            "<p><strong>id zbioru danych:</strong> dataset-id-1</p>"
            "<p><strong>organization.title:</strong> Org Title 1</p><br>"
            "<p><strong>id zbioru danych:</strong> dataset-id-2</p>"
            "<p><strong>organization.title:</strong> Org Title 2</p></div>"
        )
        assert result == expected_result

    def test_format_dataset_in_trash_error_details(self):
        error_data = [{"item_id": "dataset-id-1"}, {"item_id": "dataset-id-2"}]
        result = format_dataset_in_trash_error_details(error_data)
        expected_result = (
            '<p>Zbiór danych znajduje się w koszu</p><div class="expandable">'
            "<p><strong>id zbioru danych:</strong> dataset-id-1</p><br>"
            "<p><strong>id zbioru danych:</strong> dataset-id-2</p></div>"
        )
        assert result == expected_result

    def test_format_dataset_org_hvd_ec_conflict_error_details(self):
        error_data = [{"item_id": "dataset-id-1"}, {"item_id": "dataset-id-2"}]
        result = format_dataset_org_hvd_ec_conflict_error_details(error_data)
        expected_result = (
            "<p>Instytucja typu 'prywatna' lub 'deweloper' nie może wybrać wartości true w polu "
            "'has_high_value_data_from_european_commission_list' zbioru danych.</p>"
            '<div class="expandable">'
            "<p><strong>id zbioru danych:</strong> dataset-id-1</p><br>"
            "<p><strong>id zbioru danych:</strong> dataset-id-2</p></div>"
        )
        assert result == expected_result

    def test_format_dataset_hvd_conflict_error_details(self):
        error_data = [{"item_id": "dataset-id-1"}, {"item_id": "dataset-id-2"}]
        result = format_dataset_hvd_conflict_error_details(error_data)
        expected_result = (
            "<p>Pole zbioru danych 'has_high_value_data' musi mieć wartość równą true, "
            "jeżeli pole 'has_high_value_data_from_european_commission_list' ma wartość true.</p>"
            '<div class="expandable">'
            "<p><strong>id zbioru danych:</strong> dataset-id-1</p><br>"
            "<p><strong>id zbioru danych:</strong> dataset-id-2</p></div>"
        )
        assert result == expected_result

    def test_format_res_org_hvd_ec_conflict_error_details(self):
        error_data = [
            {"item_id": "dataset-id-1", "resources_ids": ["resource-id-1", "resource-id-2"]},
            {"item_id": "dataset-id-2", "resources_ids": ["resource-id-3"]},
        ]
        result = format_res_org_hvd_ec_conflict_error_details(error_data)
        expected_result = (
            "<p>Instytucja typu 'prywatna' lub 'deweloper' nie może wybrać wartości true w polu "
            "'has_high_value_data_from_european_commission_list' zasobu.</p>"
            '<div class="expandable">'
            "<p><strong>id zbioru danych:</strong> dataset-id-1</p>"
            "<p><strong>id zasobu:</strong> resource-id-1</p>"
            "<br>"
            "<p><strong>id zasobu:</strong> resource-id-2</p>"
            "<br>"
            "<p><strong>id zbioru danych:</strong> dataset-id-2</p>"
            "<p><strong>id zasobu:</strong> resource-id-3</p>"
            "</div>"
        )
        assert result == expected_result

    def test_format_res_hvd_conflict_error_details(self):
        error_data = [
            {"item_id": "dataset-id-1", "resources_ids": ["resource-id-1", "resource-id-2"]},
            {"item_id": "dataset-id-2", "resources_ids": ["resource-id-3"]},
        ]
        result = format_res_hvd_conflict_error_details(error_data)
        expected_result = (
            "<p>Pole zasobu 'has_high_value_data' musi mieć wartość równą true, jeżeli pole "
            "'has_high_value_data_from_european_commission_list' ma wartość true.</p>"
            '<div class="expandable">'
            "<p><strong>id zbioru danych:</strong> dataset-id-1</p>"
            "<p><strong>id zasobu:</strong> resource-id-1</p>"
            "<br>"
            "<p><strong>id zasobu:</strong> resource-id-2</p>"
            "<br>"
            "<p><strong>id zbioru danych:</strong> dataset-id-2</p>"
            "<p><strong>id zasobu:</strong> resource-id-3</p>"
            "</div>"
        )
        assert result == expected_result

    def test_format_res_dga_url_no_field_error_details(self):
        error_data = [
            {"item_id": "dataset-id-1", "resources_ids": ["resource-id-1", "resource-id-2"]},
            {"item_id": "dataset-id-2", "resources_ids": ["resource-id-3"]},
        ]
        result = format_res_dga_url_no_field_error_details(error_data)
        expected_result = (
            "<p>Jeśli zasób ma wartość pola 'contains_protected_data' równą true, "
            "to pole 'url' musi mieć ustawioną wartość.</p>"
            '<div class="expandable">'
            "<p><strong>id zbioru danych:</strong> dataset-id-1</p>"
            "<p><strong>id zasobu:</strong> resource-id-1</p>"
            "<br>"
            "<p><strong>id zasobu:</strong> resource-id-2</p>"
            "<br>"
            "<p><strong>id zbioru danych:</strong> dataset-id-2</p>"
            "<p><strong>id zasobu:</strong> resource-id-3</p>"
            "</div>"
        )
        assert result == expected_result

    def test_format_res_dga_url_not_accessible_error_details(self):
        error_data = [
            {"item_id": "dataset-id-1", "resources_ids": ["resource-id-1", "resource-id-2"]},
            {"item_id": "dataset-id-2", "resources_ids": ["resource-id-3"]},
        ]
        result = format_res_dga_url_not_accessible_error_details(error_data)
        expected_result = (
            "<p>Adres w polu 'url' zasobu, który zawiera pole 'contains_protected_data' z wartością równą true,"
            " nie odpowiada.</p>"
            '<div class="expandable">'
            "<p><strong>id zbioru danych:</strong> dataset-id-1</p>"
            "<p><strong>id zasobu:</strong> resource-id-1</p>"
            "<br>"
            "<p><strong>id zasobu:</strong> resource-id-2</p>"
            "<br>"
            "<p><strong>id zbioru danych:</strong> dataset-id-2</p>"
            "<p><strong>id zasobu:</strong> resource-id-3</p>"
            "</div>"
        )
        assert result == expected_result

    def test_format_res_dga_url_remote_file_extension_error_details(self):
        error_data = [
            {"item_id": "dataset-id-1", "resources_ids": ["resource-id-1", "resource-id-2"]},
            {"item_id": "dataset-id-2", "resources_ids": ["resource-id-3"]},
        ]
        result = format_res_dga_url_remote_file_extension_error_details(error_data)
        expected_result = (
            "<p>Jeśli zasób ma wartość pola 'contains_protected_data' równą true, to musi wskazywać "
            "w polu 'url' na plik w formacie xls, xlsx lub csv.</p>"
            '<div class="expandable">'
            "<p><strong>id zbioru danych:</strong> dataset-id-1</p>"
            "<p><strong>id zasobu:</strong> resource-id-1</p>"
            "<br>"
            "<p><strong>id zasobu:</strong> resource-id-2</p>"
            "<br>"
            "<p><strong>id zbioru danych:</strong> dataset-id-2</p>"
            "<p><strong>id zasobu:</strong> resource-id-3</p>"
            "</div>"
        )
        assert result == expected_result

    def test_format_res_dga_url_bad_columns_error_details(self):
        error_data = [
            {"item_id": "dataset-id-1", "resources_ids": ["resource-id-1", "resource-id-2"]},
            {"item_id": "dataset-id-2", "resources_ids": ["resource-id-3"]},
        ]
        result = format_res_dga_url_bad_columns_error_details(error_data)
        dga_columns_names: str = ", ".join(DGA_COLUMNS)
        error_comment: str = (
            f"<p>Jeśli zasób ma wartość pola 'contains_protected_data' równą true, to plik zasobu musi "
            f"zawierać dokładnie {len(DGA_COLUMNS)} kolumn ułożonych następująco "
            f"i nazwanych dokładnie: {dga_columns_names}.</p>"
        )

        expected_result = error_comment + (
            '<div class="expandable">'
            "<p><strong>id zbioru danych:</strong> dataset-id-1</p>"
            "<p><strong>id zasobu:</strong> resource-id-1</p>"
            "<br>"
            "<p><strong>id zasobu:</strong> resource-id-2</p>"
            "<br>"
            "<p><strong>id zbioru danych:</strong> dataset-id-2</p>"
            "<p><strong>id zasobu:</strong> resource-id-3</p>"
            "</div>"
        )
        assert result == expected_result


@pytest.fixture
def data_source() -> DataSource:
    return CKANDataSourceFactory.create(institution_type="other")


@pytest.fixture
def base_item_data() -> Dict[str, Any]:
    return {
        "ext_ident": "dataset-id-1",
        "organization": {
            "title": "Organization 1",
        },
    }


def base_item_resource_data_factory(**kwargs) -> Dict[str, Any]:
    base_resource_data = {
        # required fields
        "ext_ident": str(uuid4()),
        "title": "Resource Title",
        # metadata fields
        "has_high_value_data_from_ec_list": False,
        "has_high_value_data": False,
        "has_dynamic_data": False,
        "has_research_data": False,
        "contains_protected_data": False,
    }

    base_resource_data.update(kwargs)
    return base_resource_data


@pytest.fixture
def base_item_with_resources_data() -> Dict[str, Any]:
    return {
        "ext_ident": "dataset-id-1",
        "resources": [
            {
                "ext_ident": "resource-id-1",
                "title": "resource-1-title",
                "has_high_value_data_from_ec_list": True,
                "has_high_value_data": True,
                "has_dynamic_data": False,
                "has_research_data": False,
                "contains_protected_data": False,
            },
            {
                "ext_ident": "resource-id-2",
                "title": "resource-2-title",
                "has_high_value_data_from_ec_list": False,
                "has_high_value_data": False,
                "has_dynamic_data": False,
                "has_research_data": False,
                "contains_protected_data": False,
            },
        ],
    }


@pytest.fixture
def base_item_with_dga_resources_data() -> Dict[str, Any]:
    return {
        "ext_ident": "dataset-id-1",
        "resources": [
            {
                "ext_ident": "resource-id-1",
                "title": "resource-1-title",
                "has_high_value_data_from_ec_list": False,
                "has_high_value_data": False,
                "contains_protected_data": True,
                "has_dynamic_data": False,
                "has_research_data": False,
            },
            {
                "ext_ident": "resource-id-2",
                "title": "resource-2-title",
                "has_high_value_data_from_ec_list": True,
                "has_high_value_data": True,
                "contains_protected_data": False,
                "has_dynamic_data": False,
                "has_research_data": False,
            },
            {
                "ext_ident": "resource-id-3",
                "title": "resource-3-title",
                "has_high_value_data_from_ec_list": False,
                "has_high_value_data": False,
                "contains_protected_data": False,
                "has_dynamic_data": False,
                "has_research_data": False,
            },
        ],
    }


@pytest.mark.ckan_partial_import
class TestDataSourceCKANPartialImports:
    ckan_licenses_whitelist = settings.CKAN_LICENSES_WHITELIST.keys()
    allowed_hvd_institution_types = ALLOWED_INSTITUTIONS_TO_USE_HIGH_VALUE_DATA_FROM_EC_LIST

    def test_get_error_description_formatters_for_all_error_codes(self):
        formatters = DataSource._get_error_description_formatters()

        all_error_codes = set(error for error in CKANPartialImportError)
        formatters_codes = set(formatters.keys())

        assert formatters_codes == all_error_codes

    @pytest.mark.parametrize(
        "resources,expected_ids",
        (
            # 5 resources (2 DGA)
            (
                [
                    {
                        "ext_ident": "resource-id-1",
                        "contains_protected_data": True,
                    },
                    {
                        "ext_ident": "resource-id-2",
                        "contains_protected_data": True,
                    },
                    {
                        "ext_ident": "resource-id-3",
                        "contains_protected_data": False,
                    },
                    {
                        "ext_ident": "resource-id-4",
                        "contains_protected_data": True,
                    },
                    {
                        "ext_ident": "resource-id-5",
                        "contains_protected_data": False,
                    },
                ],
                ["resource-id-1", "resource-id-2", "resource-id-4"],
            ),
            # Empty list of resources
            ([], []),
        ),
    )
    def test_get_ids_of_dga_resources_for_item(
        self,
        resources: List[Dict[str, Any]],
        expected_ids: List[str],
    ):
        # GIVEN
        item = {
            "ext_ident": "item-id-1",
            "resources": resources,
        }

        # WHEN
        dga_ids: List[str] = DataSource._get_ids_of_dga_resources_for_item(item)

        # THEN
        assert dga_ids == expected_ids

    def test_get_number_of_dga_resources_per_organization(self, data_source: DataSource):
        # GIVEN
        items = [
            {"organization": {"title": "organization-1"}},
            {"organization": {"title": "organization-2"}},
            {"organization": {"title": "organization-3"}},
            {"organization": {"title": "organization-1"}},
        ]

        # mock dga resources retriever for each item from items list
        mock_get_item_dga_resources_ids = MagicMock()
        mock_get_item_dga_resources_ids.side_effect = [
            ["dga-1", "dga-2", "dga-3"],  # items[0]
            ["dga-4", "dga-5"],  # items[1]
            [],  # items[2]
            ["dga-6"],  # items[3]
        ]

        data_source._get_ids_of_dga_resources_for_item = mock_get_item_dga_resources_ids

        # WHEN
        result = data_source._get_number_of_dga_resources_per_organization(items)

        # THEN
        assert result == {
            "organization-1": 4,
            "organization-2": 2,
            "organization-3": 0,
        }

    @pytest.mark.parametrize("license_id", ckan_licenses_whitelist)
    def test_validate_item_license_id_valid(self, data_source: DataSource, base_item_data: Dict[str, Any], license_id: str):
        base_item_data.update({"license_id": license_id})
        data_source._ckan_validate_item_license_id(base_item_data)

    @pytest.mark.parametrize("license_id", ["", None, "not-existing-license"])
    def test_validate_item_license_id_invalid(self, data_source: DataSource, base_item_data: Dict[str, Any], license_id: str):
        base_item_data.update({"license_id": license_id})
        with pytest.raises(CKANPartialValidationException) as exc:
            data_source._ckan_validate_item_license_id(base_item_data)

        validation_exc = exc.value
        assert validation_exc.error_code == CKANPartialImportError.INVALID_LICENSE_ID
        assert validation_exc.error_data["item_id"] == base_item_data["ext_ident"]
        assert validation_exc.error_data["license_id"] == license_id

    @pytest.mark.parametrize("org_exists", (True, False))
    def test_validate_item_organization_not_in_trash_valid(
        self,
        data_source: DataSource,
        base_item_data: Dict[str, Any],
        org_exists: bool,
    ):
        organization_title = "Organization Title"
        if org_exists:
            OrganizationFactory.create(title=organization_title)

        base_item_data.update({"organization": {"title": organization_title}})

        data_source._ckan_validate_item_organization_not_in_trash(base_item_data)

    def test_validate_item_organization_not_in_trash_invalid(
        self,
        data_source: DataSource,
        base_item_data: Dict[str, Any],
    ):
        organization_title = "Organization Title"
        OrganizationFactory.create(title=organization_title, is_removed=True)

        base_item_data.update({"organization": {"title": organization_title}})

        with pytest.raises(CKANPartialValidationException) as exc:
            data_source._ckan_validate_item_organization_not_in_trash(base_item_data)

        validation_exc = exc.value
        assert validation_exc.error_code == CKANPartialImportError.ORGANIZATION_IN_TRASH
        assert validation_exc.error_data["item_id"] == base_item_data["ext_ident"]
        assert validation_exc.error_data["organization_title"] == organization_title

    @pytest.mark.parametrize("dataset_exists", (True, False))
    def test_validate_item_dataset_not_in_trash_valid(
        self,
        data_source: DataSource,
        base_item_data: Dict[str, Any],
        dataset_exists: bool,
    ):
        if dataset_exists:
            DatasetFactory.create(
                ext_ident=base_item_data["ext_ident"],
                source=data_source,
            )

        data_source._ckan_validate_item_dataset_not_in_trash(base_item_data)

    def test_validate_item_dataset_not_in_trash_invalid(
        self,
        data_source: DataSource,
        base_item_data: Dict[str, Any],
    ):
        DatasetFactory.create(
            ext_ident=base_item_data["ext_ident"],
            source=data_source,
            is_removed=True,
        )

        with pytest.raises(CKANPartialValidationException) as exc:
            data_source._ckan_validate_item_dataset_not_in_trash(base_item_data)

        validation_exc = exc.value
        assert validation_exc.error_code == CKANPartialImportError.DATASET_IN_TRASH
        assert validation_exc.error_data["item_id"] == base_item_data["ext_ident"]

    @pytest.mark.parametrize("is_conflict", (True, False))
    def test_validate_item_dataset_org_ec_conflict(
        self,
        data_source: DataSource,
        base_item_data: Dict[str, Any],
        is_conflict: bool,
    ):
        # GIVEN
        hvd_ec = True
        institution_type = "some institution type"  # no exact check in this test

        base_item_data.update({"has_high_value_data_from_ec_list": hvd_ec})
        base_item_data.update({"organization": {"title": institution_type}})

        # Mock item institution type retriever
        data_source._get_item_institution_type = MagicMock(return_value=institution_type)

        # WHEN
        # Use patch because of no need to test validate_high_value_data_from_ec_list_organization again
        with patch("mcod.harvester.models.validate_high_value_data_from_ec_list_organization") as hvd_ec_org_validator:
            if is_conflict:
                hvd_ec_org_validator.side_effect = ValidationError(
                    "Cannot use `high_value_data_from_ec_list` for this organization type."
                )
                with pytest.raises(CKANPartialValidationException) as exc:
                    data_source._ckan_validate_item_dataset_org_ec_conflict(base_item_data)
            else:
                data_source._ckan_validate_item_dataset_org_ec_conflict(base_item_data)

        # THEN
        data_source._get_item_institution_type.assert_called_once_with(base_item_data)
        hvd_ec_org_validator.assert_called_once_with(hvd_ec, institution_type)
        if is_conflict:
            validation_exc = exc.value
            assert validation_exc.error_code == CKANPartialImportError.DATASET_ORG_EC_CONFLICT
            assert validation_exc.error_data["item_id"] == base_item_data["ext_ident"]

    @pytest.mark.parametrize("is_conflict", (True, False))
    def test_validate_item_dataset_hvd_conflict(
        self,
        data_source: DataSource,
        base_item_data: Dict[str, Any],
        is_conflict: bool,
    ):
        # GIVEN
        hvd_ec = True
        hvd = True

        base_item_data.update({"has_high_value_data_from_ec_list": hvd_ec})
        base_item_data.update({"has_high_value_data": hvd})

        # WHEN
        # Use patch because of no need to test validate_conflicting_high_value_data_flags again
        with patch("mcod.harvester.models.validate_conflicting_high_value_data_flags") as hvd_validator:
            if is_conflict:
                hvd_validator.side_effect = ValidationError("High value data flags conflict.")
                with pytest.raises(CKANPartialValidationException) as exc:
                    data_source._ckan_validate_item_dataset_hvd_conflict(base_item_data)
            else:
                data_source._ckan_validate_item_dataset_hvd_conflict(base_item_data)

        # THEN
        hvd_validator.assert_called_once_with(hvd, hvd_ec)
        if is_conflict:
            validation_exc = exc.value
            assert validation_exc.error_code == CKANPartialImportError.DATASET_HVD_CONFLICT
            assert validation_exc.error_data["item_id"] == base_item_data["ext_ident"]

    def test_validate_item_resource_org_ec_conflict(
        self,
        data_source: DataSource,
        base_item_with_resources_data: Dict[str, Any],
    ):
        # GIVEN
        # Set only to check whether the corresponding function has been called with this parameter.
        institution_type = "some institution type"

        resources: List[Dict[str, Any]] = base_item_with_resources_data["resources"]
        base_item_with_resources_data.update({"organization": {"title": institution_type}})

        # Mock item institution type retriever
        data_source._get_item_institution_type = MagicMock(return_value=institution_type)

        # Use patch because of no need to test validate_high_value_data_from_ec_list_organization again.
        with patch("mcod.harvester.models.validate_high_value_data_from_ec_list_organization") as hvd_ec_org_validator:

            # Assume that the first resource is invalid and the second one is valid.
            # Validation function will raise exception for the first resource
            # and return None for the second one.

            # It is worth noting that the submitted metadata is not validated,
            # and only the call to the function validating it is tested.
            hvd_ec_org_validator.side_effect = [
                ValidationError("Cannot use `high_value_data_from_ec_list` for this organization type."),
                None,
            ]

            # WHEN
            with pytest.raises(CKANPartialValidationException) as exc:
                data_source._ckan_validate_item_resources_org_ec_conflict(base_item_with_resources_data)

        # THEN
        # Validator should be run for all (2) resources.
        expected_calls = [
            call(
                resources[0]["has_high_value_data_from_ec_list"],
                institution_type,
            ),
            call(
                resources[1]["has_high_value_data_from_ec_list"],
                institution_type,
            ),
        ]
        hvd_ec_org_validator.assert_has_calls(expected_calls, any_order=False)

        # Check error contains invalid resource data only.
        validation_exc = exc.value
        assert validation_exc.error_code == CKANPartialImportError.RES_ORG_EC_CONFLICT
        assert validation_exc.error_data["item_id"] == base_item_with_resources_data["ext_ident"]
        assert validation_exc.error_data["resources_ids"] == [resources[0]["ext_ident"]]

    def test_validate_item_resource_hvd_conflict(
        self,
        data_source: DataSource,
        base_item_with_resources_data: Dict[str, Any],
    ):
        # GIVEN
        resources: List[Dict[str, Any]] = base_item_with_resources_data["resources"]

        # Use patch because of no need to test validate_conflicting_high_value_data_flags again
        with patch("mcod.harvester.models.validate_conflicting_high_value_data_flags") as hvd_validator:

            # Assume that the first resource is invalid and the second one is valid.
            # Validation function will raise exception for the first resource
            # and return None for the second one.

            # It is worth noting that the submitted metadata is not validated,
            # and only the call to the function validating it is tested.
            hvd_validator.side_effect = [
                ValidationError("High value data flags conflict."),
                None,
            ]

            # WHEN
            with pytest.raises(CKANPartialValidationException) as exc:
                data_source._ckan_validate_item_resources_hvd_conflict(base_item_with_resources_data)

        # THEN
        # Validator should be run for all (2) resources.
        expected_calls = [
            call(
                resources[0]["has_high_value_data"],
                resources[0]["has_high_value_data_from_ec_list"],
            ),
            call(
                resources[1]["has_high_value_data"],
                resources[1]["has_high_value_data_from_ec_list"],
            ),
        ]
        hvd_validator.assert_has_calls(expected_calls, any_order=False)

        # Check error contains invalid resource data only.
        validation_exc = exc.value
        assert validation_exc.error_code == CKANPartialImportError.RES_HVD_CONFLICT
        assert validation_exc.error_data["item_id"] == base_item_with_resources_data["ext_ident"]
        assert validation_exc.error_data["resources_ids"] == [resources[0]["ext_ident"]]

    def test_get_item_institution_type_default_type(
        self,
        data_source: DataSource,
        base_item_data: Dict[str, Any],
    ):
        # GIVEN
        default_institution_type = "other"  # explicit set
        data_source.institution_type = default_institution_type
        base_item_data.update({"organization": {"title": "Not existing Organization"}})

        # WHEN
        item_institution_type = data_source._get_item_institution_type(base_item_data)

        # THEN
        assert item_institution_type == default_institution_type

    def test_get_item_institution_type_existing(
        self,
        data_source: DataSource,
        base_item_data: Dict[str, Any],
    ):
        # GIVEN
        default_institution_type = "other"  # explicit set
        data_source.institution_type = default_institution_type

        organization_title = "Organization Title"
        organization_type = "private"
        OrganizationFactory.create(title=organization_title, institution_type=organization_type)

        base_item_data.update({"organization": {"title": organization_title}})

        # WHEN
        item_institution_type = data_source._get_item_institution_type(base_item_data)

        # THEN
        assert item_institution_type == organization_type

    def test_ckan_validate_item_resources_dga_other_metadata_conflict(
        self,
        data_source: DataSource,
        base_item_with_resources_data: Dict[str, Any],
    ):
        """
        GIVEN list resources with example data obout two resources
        WHEN call datasource method `_ckan_validate_item_resources_dga_other_metadata_conflict` method
        THEN `_ckan_validate_item_resources_dga_other_metadata_conflict` will throw `CKANPartialValidationException`
        AND `CKANPartialValidationException` will point to correct import error
        AND `CKANPartialValidationException` will consist correct info only about conflicting artifacts
        AND validation function will be called for every resource
        """

        # GIVEN
        resources: List[Dict[str, Any]] = base_item_with_resources_data["resources"]
        with patch("mcod.harvester.models.validate_contains_protected_data_with_other_metadata") as dga_other_metadata_validator:
            dga_other_metadata_validator.side_effect = [
                True,
                False,
            ]

            # WHEN
            with pytest.raises(CKANPartialValidationException) as exc:
                data_source._ckan_validate_item_resources_dga_other_metadata_conflict(base_item_with_resources_data)

        # THEN
        validation_exc = exc.value
        assert validation_exc.error_code == CKANPartialImportError.RES_DGA_OTHER_METADATA_CONFLICT
        assert validation_exc.error_data["item_id"] == base_item_with_resources_data["ext_ident"]
        assert resources[0]["ext_ident"] not in validation_exc.error_data["resources_ids"]
        assert resources[1]["ext_ident"] in validation_exc.error_data["resources_ids"]
        assert dga_other_metadata_validator.call_count == 2

    @pytest.mark.parametrize("dga_resources_in_data", [True, False])
    def test_validate_item_dga_resources_institution_type(
        self,
        data_source: DataSource,
        base_item_with_resources_data: Dict[str, Any],
        base_item_with_dga_resources_data: Dict[str, Any],
        dga_resources_in_data: bool,
    ):
        # GIVEN
        data = base_item_with_dga_resources_data if dga_resources_in_data else base_item_with_resources_data
        institution_type = MagicMock()  # this variable is only for called once assertion
        # Mock item institution type retriever
        data_source._get_item_institution_type = MagicMock(return_value=institution_type)

        with patch("mcod.harvester.models.validate_institution_type_for_contains_protected_data") as mock_is_allowed_institution:
            mock_is_allowed_institution.return_value = True
            # WHEN
            data_source._ckan_validate_item_resources_dga_institution_type(data)

        # THEN
        if dga_resources_in_data:
            # this function is expected to be called because some resources were marked as dga
            mock_is_allowed_institution.assert_called_once_with(True, institution_type)
        else:
            mock_is_allowed_institution.assert_not_called()

    def test_validate_item_dga_resources_institution_type_raise_exc(
        self,
        data_source: DataSource,
        base_item_with_dga_resources_data: Dict[str, Any],
    ):
        # GIVEN
        # Mock item institution type retriever
        data_source._get_item_institution_type = MagicMock()
        with patch("mcod.harvester.models.validate_institution_type_for_contains_protected_data") as mock_is_allowed_institution:
            mock_is_allowed_institution.return_value = False

            # WHEN
            with pytest.raises(CKANPartialValidationException) as exc:
                data_source._ckan_validate_item_resources_dga_institution_type(base_item_with_dga_resources_data)

        # THEN
        # Check error contains invalid resource data only.
        dga_resources_ids = [
            resource["ext_ident"]
            for resource in base_item_with_dga_resources_data["resources"]
            if resource.get("contains_protected_data")
        ]
        validation_exc = exc.value
        assert validation_exc.error_code == CKANPartialImportError.NOT_DGA_INSTITUTION_TYPE
        assert validation_exc.error_data["item_id"] == base_item_with_dga_resources_data["ext_ident"]
        assert validation_exc.error_data["resources_ids"] == dga_resources_ids

    @pytest.mark.parametrize(
        "contains_protected_data_value, url_field_present, should_throw_exception",
        [
            (True, True, False),
            (True, False, True),
            (False, True, False),
            (False, False, False),
        ],
    )
    def test_ckan_validate_item_resources_dga_no_url_field(
        self, data_source: DataSource, contains_protected_data_value: bool, url_field_present: bool, should_throw_exception: bool
    ):
        """
        Tests the required presence of `url` field depending on the value of the `contains_protected_data` field.
        """

        # GIVEN
        item = {
            "ext_ident": "item123",
            "resources": [{"ext_ident": "resource123", "contains_protected_data": contains_protected_data_value}],
        }

        if url_field_present:
            item["resources"][0].update({"link": "https://some.url"})

        with patch("mcod.harvester.models.request_remote_dga") as mocked_request_remote_dga:
            mocked_request_remote_dga.return_value = MagicMock(
                status_code=200, headers={"Content-Type": "text/csv"}, content=b"some content"
            )
            with patch("mcod.harvester.models.validate_dga_file_columns") as mocked_validate_dga_file_columns:
                mocked_validate_dga_file_columns.return_value = True
                if should_throw_exception:
                    with pytest.raises(CKANPartialValidationException) as exc_info:
                        # WHEN
                        data_source._ckan_validate_item_resources_dga_url(item)
                        # THEN
                        exception = exc_info.value
                        assert exception.error_code == CKANPartialImportError.RES_DGA_URL_NO_FIELD
                        assert exception.error_data["item_id"] == "item123"
                        assert "resource123" in exception.error_data["resources_ids"]
                else:
                    # WHEN - call _ckan_validate_item_resources_dga_url
                    # THEN - no exception
                    data_source._ckan_validate_item_resources_dga_url(item)

    @pytest.mark.parametrize(
        "url_response_status_code,  content_type, dga_column_validation_result, expected_exception",
        [
            # url not accessible
            (404, "text/csv", True, CKANPartialImportError.RES_DGA_URL_NOT_ACCESSIBLE),
            # bad extension
            (200, "application/msword", False, CKANPartialImportError.RES_DGA_URL_BAD_REMOTE_FILE_EXTENSION),
            # bad DGA columns
            (200, "text/csv", False, CKANPartialImportError.RES_DGA_URL_BAD_COLUMNS),
            (200, "application/vnd.ms-excel", False, CKANPartialImportError.RES_DGA_URL_BAD_COLUMNS),
            (
                200,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                False,
                CKANPartialImportError.RES_DGA_URL_BAD_COLUMNS,
            ),
            # all OK
            (200, "text/csv", True, None),
            (200, "application/vnd.ms-excel", True, None),
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", True, None),
        ],
    )
    def test_ckan_validate_item_resources_dga_url(
        self,
        data_source: DataSource,
        url_response_status_code: int,
        content_type: str,
        dga_column_validation_result: bool,
        expected_exception: CKANPartialImportError,
    ):
        """
        Tests the `url` field validation. Tests includes `url` response validations i.e. - status code,
        content-type and DGA column validation.
        """
        # GIVEN
        item = {
            "ext_ident": "item123",
            "resources": [{"ext_ident": "resource123", "contains_protected_data": True, "link": "http://some.url"}],
        }
        with patch("mcod.harvester.models.request_remote_dga") as mocked_request_remote_dga:
            mocked_request_remote_dga.return_value = MagicMock(
                status_code=url_response_status_code, headers={"Content-Type": content_type}, content=b"some content"
            )

            with patch("mcod.harvester.models.validate_dga_file_columns") as mocked_validate_dga_file_columns:
                mocked_validate_dga_file_columns.return_value = dga_column_validation_result
                if expected_exception is not None:
                    with pytest.raises(CKANPartialValidationException) as exc_info:
                        # WHEN
                        data_source._ckan_validate_item_resources_dga_url(item)
                        # THEN
                        exception = exc_info.value
                        assert exception.error_code == expected_exception
                        assert exception.error_data["item_id"] == "item123"
                        assert "resource123" in exception.error_data["resources_ids"]
                else:
                    # WHEN call _ckan_validate_item_resources_dga_url(item)
                    # THEN - run without raising extension
                    data_source._ckan_validate_item_resources_dga_url(item)

    @pytest.mark.parametrize(
        (
            "number_of_dga_resources_for_organization",
            "number_of_item_dga_resources",
            "is_valid",
        ),
        [
            (0, 0, True),
            (1, 0, True),
            (1, 1, True),
            (2, 0, True),
            (2, 1, False),
            (2, 2, False),
        ],
    )
    def test_validate_item_org_single_dga_json(
        self,
        data_source: DataSource,
        number_of_dga_resources_for_organization: int,
        number_of_item_dga_resources: int,
        is_valid: bool,
    ):
        # GIVEN
        institution_title = "Organization 1"
        item = {
            "ext_ident": "item-id-1",
            "organization": {"title": institution_title},
        }

        # Create ITEM 3 non-dga resources
        resources = [base_item_resource_data_factory() for _ in range(3)]

        # Create ITEM dga resources according to test scenario
        dga_resources = []
        for idx in range(number_of_item_dga_resources):
            dga_resources.append(
                {
                    "ext_ident": f"dga-resource-id-{idx}",
                    "title": f"dga-resource-title-{idx}",
                    "contains_protected_data": True,
                }
            )

        # Add all created resources to item data
        item["resources"] = [*resources, *dga_resources]

        # Prepare dict with number of dga resources for item organization
        dga_resources_per_organization = {
            institution_title: number_of_dga_resources_for_organization,
        }

        if is_valid:
            # WHEN validations runs, THEN no exception should be raised
            data_source._ckan_validate_item_org_single_dga_json(item, dga_resources_per_organization)

        else:
            # WHEN
            with pytest.raises(CKANPartialValidationException) as exc:
                data_source._ckan_validate_item_org_single_dga_json(item, dga_resources_per_organization)

            # THEN
            validation_exc = exc.value
            assert validation_exc.error_code == CKANPartialImportError.TOO_MANY_DGA_RESOURCES_FOR_ORGANIZATION
            assert validation_exc.error_data["item_id"] == item["ext_ident"]

            resources_error_data = validation_exc.error_data["resources"]
            expected_resources_in_error_data = [
                {
                    "title": resource["title"],
                    "ext_ident": resource["ext_ident"],
                }
                for resource in dga_resources
            ]
            assert resources_error_data == expected_resources_in_error_data

    def test_validate_item_org_does_not_have_dga_resource_raise_exc(
        self,
        data_source: DataSource,
        base_item_data: Dict[str, Any],
    ):
        """
        Tests validation function raises an exception when there is a Resource marked as DGA
        in DB owned by the same Organization which was not created by the same DataSource.
        """
        # GIVEN
        base_item_data["resources"] = [{"ext_ident": "dga-resource-id-1", "contains_protected_data": True}]

        organization_title = base_item_data["organization"]["title"]
        # Organization with DGA Resource which was not created by the same DataSource
        organization = OrganizationFactory(title=organization_title)
        dataset = DatasetFactory(organization=organization)
        dga_resource = DGAResourceFactory.create(dataset=dataset)

        # WHEN
        with pytest.raises(CKANPartialValidationException) as exc:
            data_source._ckan_validate_item_org_does_not_have_dga_resource(base_item_data)

        # THEN
        validation_exc = exc.value
        assert validation_exc.error_code == CKANPartialImportError.ORGANIZATION_ALREADY_HAS_DGA_RESOURCE
        assert validation_exc.error_data["item_id"] == base_item_data["ext_ident"]
        assert validation_exc.error_data["item_dga_resources_ids"] == ["dga-resource-id-1"]
        assert validation_exc.error_data["existing_dga_resource_id"] == dga_resource.pk
        assert validation_exc.error_data["existing_dga_resource_title"] == dga_resource.title

    @pytest.mark.parametrize("organization_exists", [True, False])
    def test_validate_item_org_does_not_have_dga_resource(
        self,
        data_source: DataSource,
        base_item_data: Dict[str, Any],
        organization_exists: bool,
    ):
        """
        Tests the ability to mark a Resource as a DGA while there is no
        DGA Resource for the Organization in DB.
        """
        # GIVEN
        organization_title = base_item_data["organization"]["title"]
        if organization_exists:
            # Organization without any DGA Resource
            OrganizationFactory(title=organization_title)

        # WHEN validation runs, THEN no exception occurred
        data_source._ckan_validate_item_org_does_not_have_dga_resource(base_item_data)

    def test_validate_item_org_does_not_have_dga_resource_same_datasource(
        self,
        data_source: DataSource,
        base_item_data: Dict[str, Any],
    ):
        """
        Tests the ability to mark a resource as a DGA while there is a DGA Resource
        for the Organization that was created by the same DataSource.
        """
        # GIVEN
        organization_title = base_item_data["organization"]["title"]
        # Organization with DGA Resource created by the same DataSource
        organization = OrganizationFactory(title=organization_title)
        dataset = DatasetFactory(
            organization=organization,
            source=data_source,
        )
        DGAResourceFactory.create(dataset=dataset)

        # WHEN validation runs, THEN no exception occurred
        data_source._ckan_validate_item_org_does_not_have_dga_resource(base_item_data)
