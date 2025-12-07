import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from mcod.datasets.models import Dataset
from mcod.organizations.models import Organization
from mcod.resources.dga_constants import DGA_COLUMNS, DGA_RESOURCE_EXTENSIONS
from mcod.resources.management.commands.dga_migrate import (
    SEARCH_DGA_RESOURCE_NAME_OPTIONS,
    DgaMigrator,
    DgaReport,
    DgaResourceValidationResult,
    DgaResourceValidator,
    ResourceNameFilterBasedOnList,
    string_contains_element_from_list,
)
from mcod.resources.models import Resource


@pytest.fixture
def dga_resource(resource: Resource) -> Resource:
    dga_resource = resource
    dga_resource.title = "Sample resource of chronionych danych abc"
    dga_resource.format = "xlsx"
    dga_resource.has_table = True
    dga_resource.has_dynamic_data = False
    dga_resource.has_high_value_data = False
    dga_resource.has_high_value_data_from_ec_list = False
    dga_resource.has_research_data = False
    dga_resource.tabular_data_schema = {
        "fields": [
            {"name": "Lp.", "type": "integer", "format": "default"},
            {"name": "Zasób chronionych danych", "type": "string", "format": "default"},
            {"name": "Format danych", "type": "string", "format": "default"},
            {"name": "Rozmiar danych", "type": "string", "format": "default"},
            {
                "name": "Warunki ponownego wykorzystywania",
                "type": "string",
                "format": "default",
            },
        ],
        "missingValues": [],
    }

    return dga_resource


@pytest.mark.parametrize(
    "example_string, list_of_strings, result",
    [
        ("aaa_abc_bbb", ["abc", "def"], True),
        ("abc_def", ["aaa", "abc"], True),
        ("aaa_xyz_bbb", ["ddd", "ccc", "fff"], False),
    ],
)
def test_string_contains_element_from_list(example_string, list_of_strings, result):
    assert result == string_contains_element_from_list(checked_string=example_string, list_elements=list_of_strings)


def test_dga_resource_validation_result_positions():
    assert DgaResourceValidationResult.CORRECT_VALIDATION in DgaResourceValidationResult
    assert DgaResourceValidationResult.RESOURCE_FILE_FORMAT_ERROR in DgaResourceValidationResult
    assert DgaResourceValidationResult.RESOURCE_NOT_TABLE in DgaResourceValidationResult
    assert DgaResourceValidationResult.OTHER_FLAG_ERROR in DgaResourceValidationResult
    assert DgaResourceValidationResult.COLUMN_NAMES_ERROR in DgaResourceValidationResult


def test_dga_resource_validator(dga_resource: Resource):
    dga_resource_validator = DgaResourceValidator(correct_extensions=DGA_RESOURCE_EXTENSIONS, correct_data_columns=DGA_COLUMNS)
    assert dga_resource_validator.validate(dga_resource) == DgaResourceValidationResult.CORRECT_VALIDATION

    dga_resource.format = "doc"
    assert dga_resource_validator.validate(dga_resource) == DgaResourceValidationResult.RESOURCE_FILE_FORMAT_ERROR

    dga_resource.format = "xlsx"
    dga_resource.has_table = False
    assert dga_resource_validator.validate(dga_resource) == DgaResourceValidationResult.RESOURCE_NOT_TABLE

    dga_resource.has_table = True
    dga_resource.has_dynamic_data = True
    assert dga_resource_validator.validate(dga_resource) == DgaResourceValidationResult.OTHER_FLAG_ERROR

    dga_resource.has_dynamic_data = False
    dga_resource.has_high_value_data = True
    assert dga_resource_validator.validate(dga_resource) == DgaResourceValidationResult.OTHER_FLAG_ERROR

    dga_resource.has_high_value_data = False
    dga_resource.has_research_data = True
    assert dga_resource_validator.validate(dga_resource) == DgaResourceValidationResult.OTHER_FLAG_ERROR

    dga_resource.has_research_data = False
    dga_resource.has_high_value_data_from_ec_list = True
    assert dga_resource_validator.validate(dga_resource) == DgaResourceValidationResult.OTHER_FLAG_ERROR

    dga_resource.has_high_value_data_from_ec_list = False
    dga_resource.tabular_data_schema["fields"][0]["name"] = "bad column name"
    assert dga_resource_validator.validate(dga_resource) == DgaResourceValidationResult.COLUMN_NAMES_ERROR


def test_resource_name_filter(institution: Organization, dataset: Dataset, dga_resource: Resource):
    dga_resource.dataset = dataset
    dga_resource.save()
    dataset.organization = institution
    dataset.save()

    resource_name_filter = ResourceNameFilterBasedOnList(name_options=SEARCH_DGA_RESOURCE_NAME_OPTIONS)
    resources = resource_name_filter.get_match_name_resources(organization=institution).all()
    assert resources.count() == 1

    dga_resource.title = "no DGA resource title"
    dga_resource.save()
    resources = resource_name_filter.get_match_name_resources(organization=institution).all()
    assert resources.count() == 0


def test_add_row_to_dga_report_and_save_report(tmp_path):
    example_column_names = ["abc", "def", "ghi"]
    dga_report = DgaReport(columns=example_column_names)

    incorrect_data_row = {
        "bad_column_name": "value_1",
        "def": "value_2",
        "ghi": "value_3",
    }
    with pytest.raises(CommandError) as command_error:
        dga_report.add_row_to_report(row=incorrect_data_row)
    assert str(command_error.value) == "Building report error - logged information inconsistent with report pattern"

    correct_data_row = {"abc": "value_1", "def": "value_2", "ghi": "value_3"}
    dga_report.add_row_to_report(row=correct_data_row)
    assert dga_report.df.shape == (1, 3)

    file = tmp_path / "example_dga_report.csv"
    dga_report.save_report(file)
    assert file.exists()


@pytest.mark.parametrize(
    "institution_type, public_count, not_public_count",
    [("local", 1, 0), ("state", 1, 0), ("private", 0, 1), ("other", 0, 1), ("developer", 0, 1)],
)
def test_dga_migrator_get_public_and_not_public_organizations(
    institution: Organization, institution_type, public_count, not_public_count
):
    test_institution = institution
    test_institution.institution_type = institution_type
    test_institution.save()

    assert DgaMigrator.get_public_organizations().count() == public_count
    assert DgaMigrator.get_not_public_organizations().count() == not_public_count


def test_migration_command_parameters(tmpdir):
    result_1 = call_command("dga_migrate", "--report-dir", tmpdir)
    result_2 = call_command("dga_migrate", "-m", "--report-dir", tmpdir)
    result_3 = call_command("dga_migrate", "--migrate", "--report-dir", tmpdir)

    assert result_1 is None
    assert result_2 is None
    assert result_3 is None

    with pytest.raises(CommandError) as command_error:
        call_command("dga_migrate", "--report-dir", tmpdir, "--bad-flag")
    assert str(command_error.value) == "Error: unrecognized arguments: --bad-flag"


def test_public_institution_migration_correct(tmpdir, institution: Organization, dataset: Dataset, dga_resource: Resource):
    institution.institution_type = "state"
    institution.save()
    dataset.organization = institution
    dataset.save()
    dga_resource.dataset = dataset
    dga_resource.save()

    assert dga_resource.contains_protected_data is False

    call_command("dga_migrate", "--report-dir", tmpdir)  # call command without -m parameter
    dga_resource.refresh_from_db()
    assert dga_resource.contains_protected_data is False

    call_command("dga_migrate", "-m", "--report-dir", tmpdir)  # call command with -m parameter
    dga_resource.refresh_from_db()
    assert dga_resource.contains_protected_data is True


def test_public_institution_migration_resource_validation_fail(
    tmpdir, capsys, institution: Organization, dataset: Dataset, dga_resource: Resource
):
    institution.institution_type = "state"
    institution.save()
    dataset.organization = institution
    dataset.save()
    dga_resource.dataset = dataset
    dga_resource.has_dynamic_data = True  # will cause validation error during command execution
    dga_resource.save()

    call_command("dga_migrate", "-m", "--report-dir", tmpdir)  # call command with -m parameter
    out, _ = capsys.readouterr()
    expected_message = "RAPORT_Inst_PUBLICZNE_nieprawidłowości.csv created"

    assert expected_message in out


def test_public_institution_has_dga_datasource_and_no_dga_resource(tmpdir, capsys, institution: Organization, dataset: Dataset):
    institution.institution_type = "state"
    institution.save()
    dataset.organization = institution
    dataset.title = "some title with DGA in content"
    dataset.save()

    call_command("dga_migrate", "-m", "--report-dir", tmpdir)  # call command with -m parameter
    out, _ = capsys.readouterr()
    expected_message = "RAPORT_Inst_PUBLICZNE_nieprawidłowości.csv created"

    assert expected_message in out


def test_no_public_institution_migration(tmpdir, capsys, institution: Organization, dataset: Dataset, dga_resource: Resource):
    """Private or Other institution should not have any resource which name indicates dga_resource."""
    institution.institution_type = "private"
    institution.save()
    dataset.organization = institution
    dataset.save()
    dga_resource.dataset = dataset
    dga_resource.save()  # will cause validation error during command execution (private institution with dga_resource)

    call_command("dga_migrate", "-m", "--report-dir", tmpdir)  # call command with -m parameter
    out, _ = capsys.readouterr()
    expected_message = "RAPORT_Inst_NIEPUBLICZNE_nieprawidłowości.csv created"

    assert expected_message in out
