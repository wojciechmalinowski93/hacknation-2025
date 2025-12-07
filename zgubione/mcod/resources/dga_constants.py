from typing import List

from mcod.organizations.models import Organization

DGA_RESOURCE_EXTENSIONS: List[str] = ["xlsx", "xls", "csv"]
DGA_COLUMNS: List[str] = [
    "Lp.",
    "Zasób chronionych danych",
    "Format danych",
    "Rozmiar danych",
    "Warunki ponownego wykorzystywania",
]
ALLOWED_DGA_INSTITUTIONS: List[str] = [
    Organization.INSTITUTION_TYPE_LOCAL,
    Organization.INSTITUTION_TYPE_STATE,
]
ALLOWED_INSTITUTIONS_TO_USE_HIGH_VALUE_DATA_FROM_EC_LIST: List[str] = [
    Organization.INSTITUTION_TYPE_LOCAL,
    Organization.INSTITUTION_TYPE_STATE,
    Organization.INSTITUTION_TYPE_OTHER,
]
SAVE_CONFIRMATION_FIELD: str = "confirm_save"
