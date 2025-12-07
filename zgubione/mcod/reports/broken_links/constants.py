from enum import Enum
from typing import Dict


class ReportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"


class ReportLanguage(str, Enum):
    PL = "pl"
    EN = "en"


class BrokenLinksReportField(str, Enum):
    """
    Defines a single source of truth for all field names used in broken links reports.
    These names are used as `data_key` in serializers and as keys for header maps
    to ensure consistency across the data processing pipeline.
    """

    # --- Fields for both, Admin and Public Reports ---
    INSTITUTION = "institution"
    DATASET = "dataset"
    TITLE = "title"
    PORTAL_DATA_LINK = "portal_data_link"
    LINK = "link"
    ERROR_REASON = "error_reason"

    # --- Fields for Admin/Internal Use ---
    ID = "id"
    UUID = "uuid"
    DESCRIPTION = "description"
    CONVERTED_FORMATS_STR = "converted_formats_str"
    INSTITUTION_ID = "institution_id"
    DATASET_ID = "dataset_id"
    CREATED_BY = "created_by"
    CREATED = "created"
    MODIFIED_BY = "modified_by"
    MODIFIED = "modified"
    RESOURCE_TYPE = "resource_type"
    METHOD_OF_SHARING = "method_of_sharing"
    HAS_HIGH_VALUE_DATA = "has_high_value_data"
    HAS_HIGH_VALUE_DATA_FROM_EC_LIST = "has_high_value_data_from_ec_list"
    HAS_DYNAMIC_DATA = "has_dynamic_data"
    HAS_RESEARCH_DATA = "has_research_data"
    CONTAINS_PROTECTED_DATA = "contains_protected_data"


public_bl_report_elasticsearch_fields_types: Dict[str, str] = {
    "institution": "text",
    "dataset": "text",
    "title": "text",
    "portal_data_link": "text",
    "link": "text",
}

BROKENLINKS_ES_INDEX_NAME = "broken-links"
