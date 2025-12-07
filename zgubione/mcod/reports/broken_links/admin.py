import logging
import os
from collections import OrderedDict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, OrderedDict as OrderedDictType, Tuple

import pandas as pd
from django.conf import settings
from django.utils.functional import Promise
from django.utils.translation import gettext_lazy as _, override

from mcod.reports.broken_links.common import SchemaValidationError, create_validated_dataframe
from mcod.reports.broken_links.constants import BrokenLinksReportField
from mcod.reports.broken_links.serializers import AdminBrokenLinksSerializer

logger = logging.getLogger("mcod")


_APP = "resources"
_REPORT_FILE_FOLDER_URL: str = os.path.join(settings.REPORTS_MEDIA, _APP)
_REPORT_LANGUAGE = "pl"
_REPORT_DELIMITER = ";"

_REPORT_FILE_PREFIX = "brokenlinks_resources_"
_REPORT_FOLDER_PATH: str = os.path.join(settings.REPORTS_MEDIA_ROOT, _APP)

ValuesMapping = Dict[Any, Any]
_NULL_BOOLEAN_MAPPING: ValuesMapping = {
    True: _("YES"),
    False: _("NO"),
    None: _("not specified"),
}

# This dictionary maps internal field names to their translated, human-readable column headers and values mapping.
_REPORT_MAP: OrderedDictType[BrokenLinksReportField, Tuple[Promise, Optional[ValuesMapping]]] = OrderedDict(
    {
        BrokenLinksReportField.ID: (_("id"), None),
        BrokenLinksReportField.UUID: (_("uuid"), None),
        BrokenLinksReportField.TITLE: (_("title"), None),
        BrokenLinksReportField.PORTAL_DATA_LINK: (_("Link to data on the portal"), None),
        BrokenLinksReportField.DESCRIPTION: (_("description"), None),
        BrokenLinksReportField.LINK: (_("link"), None),
        BrokenLinksReportField.ERROR_REASON: (_("Cause"), None),
        BrokenLinksReportField.CONVERTED_FORMATS_STR: (_("formats after conversion"), None),
        BrokenLinksReportField.INSTITUTION_ID: (_("Id Institution"), None),
        BrokenLinksReportField.INSTITUTION: (_("Publisher"), None),
        BrokenLinksReportField.DATASET: (_("dataset"), None),
        BrokenLinksReportField.DATASET_ID: (_("Id dataset"), None),
        BrokenLinksReportField.CREATED_BY: (_("created_by"), None),
        BrokenLinksReportField.CREATED: (_("created"), None),
        BrokenLinksReportField.MODIFIED_BY: (_("modified_by"), None),
        BrokenLinksReportField.MODIFIED: (_("modified"), None),
        BrokenLinksReportField.RESOURCE_TYPE: (_("type"), None),
        BrokenLinksReportField.METHOD_OF_SHARING: (_("Method of sharing"), None),
        BrokenLinksReportField.HAS_HIGH_VALUE_DATA: (_("Resource has high value data"), _NULL_BOOLEAN_MAPPING),
        BrokenLinksReportField.HAS_HIGH_VALUE_DATA_FROM_EC_LIST: (
            _("Resource has high value data from the EC list"),
            _NULL_BOOLEAN_MAPPING,
        ),
        BrokenLinksReportField.HAS_DYNAMIC_DATA: (_("Resource has dynamic data"), _NULL_BOOLEAN_MAPPING),
        BrokenLinksReportField.HAS_RESEARCH_DATA: (_("Resource has research data"), _NULL_BOOLEAN_MAPPING),
        BrokenLinksReportField.CONTAINS_PROTECTED_DATA: (_("Contains protected data list"), _NULL_BOOLEAN_MAPPING),
    }
)


def _generate_base_file_name() -> str:
    prefix: str = _REPORT_FILE_PREFIX
    suffix: str = datetime.now().strftime("%Y%m%d%H%M%S.%s")
    return f"{prefix}{suffix}"


def _get_report_root_path() -> Path:
    return Path(_REPORT_FOLDER_PATH)


def _process_data(base_df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms a DataFrame for reporting by mapping values and renaming columns.

    This function prepares a raw data DataFrame for presentation. It performs
    two main operations based on the `_REPORT_MAP` configuration:
    1.  Maps cell values for columns with a defined value map (e.g., True -> "Yes").
    2.  Renames all columns to their human-readable headers.

    The function returns a new DataFrame with a consistent column structure and order.
    It efficiently handles empty input by returning a correctly structured empty DataFrame.

    Args:
        base_df: The input pandas DataFrame with raw data. Its column names
                 are guaranteed to match the keys in `_REPORT_MAP`.

    Returns:
        A new, processed pandas DataFrame ready for display or export.
    """
    # Define the final column headers and their order upfront from the report map.
    final_columns = [header for header, _ in _REPORT_MAP.values()]

    # Handle the edge case of an empty input DataFrame to avoid unnecessary processing.
    if base_df.empty:
        return pd.DataFrame(columns=final_columns)

    # Create a copy to prevent side effects on the original DataFrame.
    df = base_df.copy()

    # Apply value mappings where a mapping dictionary is provided in the report map.
    for column_key, (__, mapping) in _REPORT_MAP.items():
        if mapping:
            df[column_key] = df[column_key].map(mapping)

    # Sort the table by Institution title
    df.sort_values(by=BrokenLinksReportField.INSTITUTION.value, inplace=True)

    # Prepare a dictionary for renaming columns from internal keys to display headers.
    rename_map = {key: header for key, (header, _) in _REPORT_MAP.items()}
    df.rename(columns=rename_map, inplace=True)

    return df[final_columns]


def generate_admin_broken_links_report(data: List[Dict[str, Any]]) -> str:
    """
    Generates and saves the admin-facing broken links report as a CSV file.

    This function orchestrates the entire report generation process. It takes raw
    broken links data, validates it against a schema, processes it into a
    human-readable format (translating values and headers), and then exports
    the final result to a CSV file in a pre-configured directory.

    Args:
        data: A list of dictionaries containing the raw broken links data.

    Returns:
        The relative URL path to the newly created report file, suitable for API download link.

    Raises:
        ValidationError: If the input data does not match the expected schema.
    """

    # Step 1: Validate the raw input data and load it into a DataFrame.
    try:
        base_df: pd.DataFrame = create_validated_dataframe(data, AdminBrokenLinksSerializer)
    except SchemaValidationError as e:
        logger.error(f"Data validation error during Admin Broken Links report generation: {e}")
        raise e

    # Step 2: Process the data into a presentation-ready format.
    df: pd.DataFrame = _process_data(base_df)

    # Step 3: Ensure the directory for storing reports exists.
    report_path: Path = _get_report_root_path()
    os.makedirs(report_path, exist_ok=True)

    # Step 4: Generate a unique filename and save the report as a CSV file.
    base_file_name: str = _generate_base_file_name()
    csv_file_path: Path = report_path / f"{base_file_name}.csv"

    # The 'override' context ensures the report is generated in the correct language.
    with override(_REPORT_LANGUAGE):
        df.to_csv(csv_file_path, index=False, sep=_REPORT_DELIMITER)

    report_file_name: str = csv_file_path.name

    # Step 5: Construct and return the public-facing URL for the generated file.
    return f"{_REPORT_FILE_FOLDER_URL}/{report_file_name}"
