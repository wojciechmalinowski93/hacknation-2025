from typing import Any, Dict

from mcod.harvester.ckan_utils import CKANPartialImportError


class CKANPartialValidationException(Exception):
    """
    Custom exception for CKAN partial validation errors.
    Stores both the error code and associated error data.
    This data is later used to generate detailed error descriptions.
    """

    def __init__(self, error_code: CKANPartialImportError, error_data: Dict[str, Any]):
        self.error_code = error_code
        self.error_data = error_data
        super().__init__(f"CKAN Partial Validation error: {error_code}.")
