from enum import Enum
from pathlib import Path
from typing import List

import pandas as pd
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q, QuerySet

from mcod.organizations.models import Organization
from mcod.resources.dga_constants import DGA_COLUMNS, DGA_RESOURCE_EXTENSIONS
from mcod.resources.models import Resource

MIGRATION_REPORT_COLUMNS: List[str] = [
    "Organizacja",
    "Rodzaj organizacji",
    "Nazwa zbioru danych",
    "Id zasobu",
    "Nazwa zasobu",
    "Status zasobu",
    "Uwagi",
]

SEARCH_DGA_RESOURCE_NAME_OPTIONS: List[str] = [
    "chronionych danych",
    "danych chronionych",
]

DGA_RESOURCE_TITLE_MUST_CONTAIN: List[str] = [
    "Wykaz zasobów chronionych",
    "wykaz zasobów chronionych",
]

DGA_DATASET_NAME_WORD_INDICATOR = "DGA"


def string_contains_element_from_list(checked_string: str, list_elements: List[str]) -> bool:
    """Check if `checked_string` contains at least one element from `list_elements`."""
    return any(element in checked_string for element in list_elements)


def migrate_single_resource(resource: Resource):
    resource.contains_protected_data = True
    resource.save()


class DgaResourceValidationResult(Enum):
    CORRECT_VALIDATION = "walidacja poprawna"
    RESOURCE_FILE_FORMAT_ERROR = "nieprawidłowe rozszerzenie pliku"
    RESOURCE_NOT_TABLE = "zasób nie jest poprawną tabelą"
    OTHER_FLAG_ERROR = (
        "błąd ustawienia flagi `Zawiera dane dynamiczne` lub" " `Zawiera dane o wysokiej wartości` lub `Zawiera dane badawcze`"
    )
    COLUMN_NAMES_ERROR = "nieprawidłowe nazwy kolumn lub ich kolejność"


class DgaResourceValidator:
    def __init__(self, correct_extensions: List[str], correct_data_columns: List[str]):
        self.correct_extensions = correct_extensions
        self.correct_data_columns = correct_data_columns

    def _check_columns(self, resource: Resource) -> bool:
        """Checks if the `resource` columns are coincident with `correct_data_columns`."""
        resource_columns = [column["name"] for column in resource.tabular_data_schema["fields"]]
        if resource_columns == self.correct_data_columns:
            return True
        return False

    def validate(self, resource: Resource) -> DgaResourceValidationResult:
        """Validates the `resource` against the DGA resource conditions.
        @param resource: `resource` to validate.
        @return: `DgaResourceValidationResult` object with validation error.
        """
        if resource.format not in self.correct_extensions:
            return DgaResourceValidationResult.RESOURCE_FILE_FORMAT_ERROR
        if not resource.has_table:
            return DgaResourceValidationResult.RESOURCE_NOT_TABLE
        if not self._check_columns(resource):
            return DgaResourceValidationResult.COLUMN_NAMES_ERROR
        if (
            resource.has_dynamic_data
            or resource.has_high_value_data
            or resource.has_research_data
            or resource.has_high_value_data_from_ec_list
        ):
            return DgaResourceValidationResult.OTHER_FLAG_ERROR
        return DgaResourceValidationResult.CORRECT_VALIDATION


class ResourceNameFilterBasedOnList:
    """Class for filtering `Organization` resources using method based on list of sentences."""

    def __init__(self, name_options: List[str]):
        self.name_options = name_options

    def get_match_name_resources(self, organization: Organization) -> QuerySet:
        query = Q()
        for value in self.name_options:
            query |= Q(title__icontains=value)

        match_resources = Resource.objects.filter(dataset__organization=organization).filter(query)
        return match_resources


class DgaReport:
    """Class used to generate report from DGA migration process. Based on Pandas DataFrame."""

    def __init__(self, columns: List[str]) -> None:
        self.columns = columns
        self.df = pd.DataFrame(columns=columns)

    def add_row_to_report(self, row: dict) -> None:
        """Add `row` as a record to report."""
        if sorted(list(row.keys())) == sorted(self.columns):
            self.df = self.df.append(row, ignore_index=True)
        else:
            raise CommandError("Building report error - logged information inconsistent with report pattern")

    def save_report(self, file_name: Path) -> None:
        """Save report `file_name` file."""
        if len(self.df) > 0:
            self.df.index += 1
            self.df.to_csv(file_name, sep=";")
            print(f"Report - {file_name} created")
        else:
            print(f"No data to create report - {file_name}")


class DgaMigrator:
    """Class to manage DGA migration process."""

    def __init__(
        self,
        resource_name_filter: ResourceNameFilterBasedOnList,
        report_columns: List[str],
    ):
        self.resource_name_filter = resource_name_filter
        self.reports = {
            "public_institutions": DgaReport(report_columns),
            "no_public_institutions": DgaReport(report_columns),
            "migrations": DgaReport(report_columns),
        }

    @staticmethod
    def get_public_organizations() -> QuerySet:
        qs = Organization.objects.filter(
            Q(institution_type=Organization.INSTITUTION_TYPE_LOCAL) | Q(institution_type=Organization.INSTITUTION_TYPE_STATE)
        )
        return qs

    @staticmethod
    def get_not_public_organizations() -> QuerySet:
        qs = Organization.objects.exclude(
            Q(institution_type=Organization.INSTITUTION_TYPE_LOCAL) | Q(institution_type=Organization.INSTITUTION_TYPE_STATE)
        )
        return qs

    def get_dga_resources_for_organization(self, organization: Organization) -> List[Resource]:
        """Get all `resources` which belong to `organization` and are not removed from system and match name condition.
        @param organization: organization for whose DGA resources are being queried.
        """
        resources_data_protected = []

        for rs in self.resource_name_filter.get_match_name_resources(organization):
            if rs.is_removed is False and rs.is_permanently_removed is False:
                if rs.is_published:
                    resources_data_protected.append(rs)

        return resources_data_protected

    @staticmethod
    def get_organization_dga_datasources_for_organization(
        organization: Organization,
    ) -> QuerySet:
        qs = organization.datasets.filter(title__contains=DGA_DATASET_NAME_WORD_INDICATOR)
        return qs


class Command(BaseCommand):
    """Django command to migrate DGA resources. When flag `-m` or `--migrate` is used then DGA resources will be
    migrated and reports from migration will be created.
    If `-m` or `--migrate` is not used only reports from migration will be created without migration process.
    """

    def add_arguments(self, parser):
        parser.add_argument(
            "-m",
            "--migrate",
            action="store_true",
            help="set flag -m or --migrate to migrate DGA resource."
            " Without flag only simulation of migration process will be performed.",
        )

        parser.add_argument(
            "--report-dir",
            type=str,
            default=".",
            help="default report folder name",
        )

    def handle(self, *args, **options):  # noqa: C901

        migrate_operation = options["migrate"]
        report_dir = Path(options["report_dir"])

        if migrate_operation:
            self.stdout.write("Start real migration and reports creating ...")
        else:
            self.stdout.write("Starting migration dry-run ...")

        resource_name_filter_based_on_list = ResourceNameFilterBasedOnList(name_options=SEARCH_DGA_RESOURCE_NAME_OPTIONS)
        dga_migrator = DgaMigrator(
            resource_name_filter=resource_name_filter_based_on_list,
            report_columns=MIGRATION_REPORT_COLUMNS,
        )

        resource_validator = DgaResourceValidator(correct_extensions=DGA_RESOURCE_EXTENSIONS, correct_data_columns=DGA_COLUMNS)

        # Public organizations (Local government and Public government) processing

        for public_org in dga_migrator.get_public_organizations():
            message = {
                "Organizacja": public_org.title,
                "Rodzaj organizacji": public_org.get_institution_type_display(),
            }

            resources: List[Resource] = dga_migrator.get_dga_resources_for_organization(public_org)
            if len(resources) == 1:
                resource = resources[0]

                validation_result = resource_validator.validate(resource)
                message.update(
                    {
                        "Nazwa zbioru danych": resource.dataset.title,
                        "Id zasobu": resource.id,
                        "Nazwa zasobu": resource.title,
                        "Status zasobu": Resource.STATUS[resource.status],
                    }
                )

                if validation_result == DgaResourceValidationResult.CORRECT_VALIDATION:
                    if migrate_operation:  # Make migration
                        migrate_single_resource(resource)
                        message["Uwagi"] = "zasób DGA zmigrowany"
                        self.stdout.write(f"Organization `{public_org.title}` - migration of DGA resource: {resource.title}")

                    else:  # Don't make migrations, only reports
                        message["Uwagi"] = "zasób DGA kwalifikuje się do migracji"
                        self.stdout.write(
                            f"Organization `{public_org.title}` - resource: {resource.title}" f" is qualified to DGA migration"
                        )

                    if not string_contains_element_from_list(resource.title, DGA_RESOURCE_TITLE_MUST_CONTAIN):
                        warning = " - uwaga: tytuł zasobu nie zawiera żadnej z fraz: " + " | ".join(
                            DGA_RESOURCE_TITLE_MUST_CONTAIN
                        )
                        message["Uwagi"] = message["Uwagi"] + warning

                    dga_migrator.reports["migrations"].add_row_to_report(row=message)
                else:
                    message["Uwagi"] = validation_result.value
                    dga_migrator.reports["public_institutions"].add_row_to_report(row=message)

            elif len(resources) > 1:
                for resource in resources:
                    message.update(
                        {
                            "Nazwa zbioru danych": resource.dataset.title,
                            "Id zasobu": resource.id,
                            "Nazwa zasobu": resource.title,
                            "Status zasobu": Resource.STATUS[resource.status],
                            "Uwagi": "Organizacja publiczna posiada więcej niż jeden opublikowany zasób podejrzany"
                            " o bycie wykazem zasobów chronionych",
                        }
                    )
                    dga_migrator.reports["public_institutions"].add_row_to_report(row=message)

            else:
                datasets = dga_migrator.get_organization_dga_datasources_for_organization(public_org)
                if datasets:  # Public organization have DGA dataset but without DGA resource
                    for dataset in datasets:
                        message.update(
                            {
                                "Nazwa zbioru danych": dataset.title,
                                "Id zasobu": "",
                                "Nazwa zasobu": "",
                                "Status zasobu": "",
                                "Uwagi": "Organizacja publiczna posiada zbiór danych o nazwie zawierającej ciąg DGA"
                                " pomimo że nie posiada opublikowanego zasobu zawierającego"
                                " wykaz chronionych danych",
                            }
                        )
                        dga_migrator.reports["public_institutions"].add_row_to_report(row=message)

        # Not public (Private entities and Others) organizations processing

        for no_public_org in dga_migrator.get_not_public_organizations():

            resources = dga_migrator.get_dga_resources_for_organization(no_public_org)

            if len(resources) > 0:
                for resource in resources:
                    message = {
                        "Organizacja": no_public_org.title,
                        "Rodzaj organizacji": no_public_org.get_institution_type_display(),
                        "Nazwa zbioru danych": resource.dataset.title,
                        "Id zasobu": resource.id,
                        "Nazwa zasobu": resource.title,
                        "Status zasobu": Resource.STATUS[resource.status],
                        "Uwagi": "Organizacja niepubliczna posiada zasób podejrzany o bycie listą zasobów chronionych",
                    }
                    dga_migrator.reports["no_public_institutions"].add_row_to_report(row=message)

        report_dir.mkdir(parents=True, exist_ok=True)
        dga_migrator.reports["public_institutions"].save_report(report_dir / "RAPORT_Inst_PUBLICZNE_nieprawidłowości.csv")
        dga_migrator.reports["no_public_institutions"].save_report(report_dir / "RAPORT_Inst_NIEPUBLICZNE_nieprawidłowości.csv")
        dga_migrator.reports["migrations"].save_report(report_dir / "RAPORT_migracja_realizacja.csv")
