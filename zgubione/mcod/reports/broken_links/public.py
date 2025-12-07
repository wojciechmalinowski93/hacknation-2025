import logging
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import sentry_sdk
from django.conf import settings
from django.utils.translation import gettext_lazy as _, override
from elasticsearch import ElasticsearchException

from mcod.reports.broken_links.common import SchemaValidationError, create_validated_dataframe
from mcod.reports.broken_links.constants import (
    BROKENLINKS_ES_INDEX_NAME,
    BrokenLinksReportField,
    ReportFormat,
    ReportLanguage,
    public_bl_report_elasticsearch_fields_types,
)
from mcod.reports.broken_links.elasticsearch import rebuild_brokenlinks_es_index
from mcod.reports.broken_links.serializers import PublicBrokenLinksSerializer

# This dictionary maps internal field names to their translated, human-readable column headers.
_HEADERS_MAP = OrderedDict(
    {
        BrokenLinksReportField.INSTITUTION: _("Publisher"),
        BrokenLinksReportField.DATASET: _("Dataset"),
        BrokenLinksReportField.TITLE: _("Data"),
        BrokenLinksReportField.PORTAL_DATA_LINK: _("Link to data on the portal"),
        BrokenLinksReportField.LINK: _("Broken link to provider data"),
    }
)
_REPORT_FILE_PREFIX = "public_brokenlinks_resources_"
SHARED_SUBPATH = ("resources", "public")
_ERRORS_TO_EXCLUDE = (
    "Weryfikacja certyfikatu SSL nie powiodła się.",
    "Lokalizacja zasobu została zmieniona.",
)

_LANGUAGES = ("pl", "en")


logger = logging.getLogger("mcod")


class ReportFolder:
    """
    A utility class to manage the report directory structure.

    This class provides a centralized interface for handling file paths, public URLs,
    and file system operations (creation, cleanup) within a predefined reports folder.
    It ensures that all operations are contained within a safe root directory.
    """

    # The common subdirectory structure within the media root for all reports.
    SHARED_SUBPATH = ("resources", "public")

    def __init__(self):
        # The absolute file system path to the root of the public reports' folder.
        self._root: Path = Path(settings.REPORTS_MEDIA_ROOT, *self.SHARED_SUBPATH)
        # The base URL corresponding to the root path.
        self._url: str = "/".join((settings.REPORTS_MEDIA, *self.SHARED_SUBPATH))

    def files(self, format_: Optional[str] = None, lang: Optional[str] = None) -> List[Path]:
        """
        Recursively searches for files, optionally filtering by format and language.

        If `lang` is provided, a specific language subdirectory is searched.
        Otherwise, the root directory is searched.
        If `format_` is not specified, all found files are returned.

        Args:
            format_ (Optional[str]): The file extension to filter the results by (e.g., 'csv').
            lang (Optional[str]): The language code that determines the directory to search.

        Returns:
            List[Path]: A list of file paths that match the criteria.
        """
        pattern = f"*.{format_}" if format_ else "*"
        path_to_search: Path = self._output_path(lang=lang) if lang else self._root
        return [file_path for file_path in path_to_search.rglob(pattern) if file_path.is_file()]

    def _output_path(self, lang: str) -> Path:
        """
        Constructs the full file system path for a language-specific subfolder.

        Args:
            lang (str): The language code (e.g., 'en', 'pl').

        Returns:
            Path: The complete Path object for the language directory.
        """
        return self._root / lang

    def output_folder(self, lang: str) -> Path:
        """
        Returns the path to a language-specific folder and ensures it exists.
        If the directory does not exist, it will be created.

        Args:
            lang (str): The language code for the subfolder.

        Returns:
            Path: The Path object for the existing output directory.
        """
        output_path = self._output_path(lang)
        output_path.mkdir(parents=True, exist_ok=True)
        return output_path

    def output_url_path(self, lang: str) -> str:
        """Constructs the public URL for a language-specific subfolder."""
        return f"{self._url}/{lang}"

    def output_root_path(self, lang: str) -> str:
        """Constructs the root path for a language-specific subfolder."""
        return f"{self._output_path(lang)}"

    def cleanup(self, reports: List[Path]) -> None:
        """
        Deletes a list of given report files after a security check.

        This method ensures that all files to be deleted are located within the
        managed `_root` directory to prevent accidental deletion of arbitrary files.

        Args:
            reports (List[Path]): A list of Path objects to be deleted.

        Raises:
            ValueError: If any of the provided paths are outside the managed `_root` directory.
        """
        outside_the_scope: List[Path] = [report for report in reports if self._root not in report.resolve().parents]
        if outside_the_scope:
            raise ValueError(f"Got paths outside the root folder: {outside_the_scope}.")
        for report_path in reports:
            report_path.unlink()


def _generate_base_file_name() -> str:
    """
    Creates a unique base filename for a report, without the file extension.

    The name is composed of a fixed prefix and a precise timestamp to ensure
    uniqueness and prevent naming collisions.
    """
    prefix: str = _REPORT_FILE_PREFIX
    suffix: str = datetime.now().strftime("%Y%m%d%H%M%S.%s")
    return f"{prefix}{suffix}"


def _process_data(base_df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters and formats the report DataFrame for the final output.

    This function performs two main actions:
    1. Filters out rows containing specific technical errors that should not
       be included in the public-facing report.
    2. Renames a subset of columns and selects them for the final report structure.

    Note: Headers are not translated during this process, only assigned.
    """

    # Define the final, user-facing column headers and their intended order.
    final_columns: List[str] = list(_HEADERS_MAP.values())

    # Early exit for empty input: return an empty DataFrame with correct final headers.
    if base_df.empty:
        return pd.DataFrame(columns=final_columns)

    # Filter out rows with errors configured to be excluded.
    df: pd.DataFrame = base_df[~base_df[BrokenLinksReportField.ERROR_REASON.value].isin(_ERRORS_TO_EXCLUDE)]

    # Sort the table by Institution title
    df.sort_values(by=BrokenLinksReportField.INSTITUTION.value, inplace=True)

    # Rename columns from internal names to their final, human-readable headers.
    df.rename(columns=_HEADERS_MAP, inplace=True)

    # Return a new DataFrame containing only the specified final columns in the correct order.
    return df[final_columns]


def generate_public_broken_links_reports(data: List[Dict[str, Any]]) -> None:
    """
    Generates public-facing broken links reports in multiple languages and formats.

    This function orchestrates the entire process: data validation, processing,
    multi-format export, and cleanup of old reports. It ensures atomicity by
    cleaning up partially generated files if an error occurs during the process.
    """

    report_folder = ReportFolder()

    # Step 1: Get a list of all existing report files for deletion after a successful run
    # This is done first so that if generation fails, the old reports are kept
    old_reports: List[Path] = report_folder.files()

    # Step 2: Validate the raw input data and prepare the base DataFrame.
    # Headers are not translated yet; the 'override' context manager handles that later.
    try:
        base_df: pd.DataFrame = create_validated_dataframe(data, PublicBrokenLinksSerializer)
    except SchemaValidationError as e:
        logger.error(f"Data validation error during Public Broken Links reports generation: {e}")
        raise e

    processed_df: pd.DataFrame = _process_data(base_df)

    # Step 3: Generate a new report for each configured language and file format
    generated_reports: List[Path] = []
    try:
        logger.info("Generating Public Broken Links reports.")
        base_file_name: str = _generate_base_file_name()
        for lang in _LANGUAGES:
            # Determine the output directory and a unique base name for the files
            output_path: Path = report_folder.output_folder(lang)

            # Use a context manager to set the correct translation language
            with override(lang):
                # Generate CSV report
                csv_file_path: Path = output_path / f"{base_file_name}.csv"
                processed_df.to_csv(csv_file_path, index=False, sep=";")
                generated_reports.append(csv_file_path)

                # Generate XLSX report
                xlsx_file_path: Path = output_path / f"{base_file_name}.xlsx"
                with pd.ExcelWriter(xlsx_file_path, engine="xlsxwriter") as writer:
                    sheet_name = "Arkusz 1"
                    processed_df.to_excel(writer, index=False, sheet_name=sheet_name, header=False, startrow=1)

                    # Get the xlsxwriter workbook and worksheet objects
                    workbook = writer.book
                    worksheet = writer.sheets[sheet_name]

                    # Format Excel file headers
                    # https://xlsxwriter.readthedocs.io/working_with_pandas.html#formatting-of-the-dataframe-headers
                    header_format = workbook.add_format(
                        {
                            "bold": True,
                            "align": "left",
                        }
                    )
                    # Write the column headers with the defined format
                    for col_num, value in enumerate(processed_df.columns.values):
                        worksheet.write(0, col_num, str(value), header_format)

                    # Freeze the first row
                    worksheet.freeze_panes(1, 0)

                    # Set the width for the first 5 columns
                    worksheet.set_column(0, 4, 40, None)

                generated_reports.append(xlsx_file_path)

    except Exception as exc:
        logger.error(f"Unexpected exception during reports creation: {exc}")
        # If any part of the generation fails, clean up the files created during this run
        # to prevent a partial or inconsistent state
        for file in generated_reports:
            file.unlink()
        raise exc

    logger.info("SUCCESS: All Public Broken Links reports generated!")

    # Step 4: After all new reports have been successfully created, delete the old ones
    logger.info(f"Deleting old Public Broken Links reports files {old_reports}.")
    report_folder.cleanup(old_reports)

    # Step 5: Rebuild Elasticsearch index for public brokenlinks report
    try:
        change_cols_name_data = {str(v): str(k.value) for k, v in _HEADERS_MAP.items()}

        documents_created, documents_failed = rebuild_brokenlinks_es_index(
            BROKENLINKS_ES_INDEX_NAME,
            public_bl_report_elasticsearch_fields_types,
            processed_df,
            change_cols_name_data,
        )
        logger.info(
            f"ES index for public broken links report {BROKENLINKS_ES_INDEX_NAME} rebuild."
            f" Created {documents_created} documents. Failed {documents_failed} documents."
        )
    except ElasticsearchException as exc:
        sentry_sdk.api.capture_exception(exc)
        logger.error(f"Rebuilding ES index for broken links report failed: {exc}")


def get_public_broken_links_root_path(lang: ReportLanguage, format_: ReportFormat) -> Optional[str]:
    """
    Searches a folder for the latest report file and returns its root path.

    Args:
        lang: The language code used to determine the folder.
        format_: The expected file format (e.g., "xlsx", "csv") without a dot.

    Returns:
        The root path to the latest report file, or None if no file is found.
    """
    report_folder = ReportFolder()
    try:
        # Find all matching files and select the latest one
        latest_file = max(report_folder.files(lang=lang.value, format_=format_.value), key=lambda p: p.stat().st_mtime)
        return f"{report_folder.output_root_path(lang.value)}/{latest_file.name}"

    except (FileNotFoundError, ValueError):
        # FileNotFoundError - if the folder does not exist
        # ValueError - if `max` receives an empty sequence (no files found)
        return None


def get_public_broken_links_location(lang: ReportLanguage, format_: ReportFormat) -> Optional[str]:
    """
    Searches a folder for the latest report file and returns its public api url path.

    Args:
        lang: The language code used to determine the folder.
        format_: The expected file format (e.g., "xlsx", "csv") without a dot.

    Returns:
        The public api url path to the latest report file, or None if no file is found.
    """
    report_folder = ReportFolder()
    try:
        # Find all matching files and select the latest one
        latest_file = max(report_folder.files(lang=lang.value, format_=format_.value), key=lambda p: p.stat().st_mtime)
        return f"{report_folder.output_url_path(lang.value)}/{latest_file.name}"

    except (FileNotFoundError, ValueError):
        # FileNotFoundError - if the folder does not exist
        # ValueError - if `max` receives an empty sequence (no files found)
        return None
