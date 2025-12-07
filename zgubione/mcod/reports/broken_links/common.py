import logging
from typing import Any, Dict, List, Type, cast

import pandas as pd
from marshmallow import ValidationError
from marshmallow.schema import BaseSchema

from mcod.reports.broken_links.constants import BrokenLinksReportField

logger = logging.getLogger("mcod")


class SchemaValidationError(ValidationError):
    """Exception raised when a validation error concerns the entire data structure, not individual records."""

    pass


def create_validated_dataframe(
    raw_data: List[Dict[str, Any]],
    schema_class: Type[BaseSchema],
) -> pd.DataFrame:
    """
    Validates data against a serializer schema and creates a DataFrame from valid records.

    This function performs two levels of validation:
    1.  **Schema-level**: Checks if the overall data structure is correct (e.g., a list of objects).
        If not, it raises a `SchemaValidationError`.
    2.  **Record-level**: Validates each dictionary in the list. Invalid records are
        filtered out and logged, while valid records are used to create the DataFrame.

    The resulting DataFrame's columns and their order are determined by the fields
    defined in the schema class, ensuring a consistent and expected structure.

    Args:
        raw_data: A list of dictionaries to validate and load.
        schema_class: The serializer schema class used for validation.

    Returns:
        A pandas DataFrame containing only the valid data, with columns matching the schema.
        Returns an empty DataFrame with correct columns if no valid data is found.

    Raises:
        SchemaValidationError: If a schema-level error occurs.
    """
    serializer: BaseSchema = schema_class(many=True)
    errors: Dict = serializer.validate(raw_data)

    if not errors:
        clean_data = raw_data
    else:
        # Check if all error keys are integers, indicating record-level errors
        is_record_level_error = all(isinstance(key, int) for key in errors)

        if is_record_level_error:
            logger.warning(f"Found {len(errors)} invalid records. They will be skipped. " f"Details: {errors}")
            invalid_indices = set(errors.keys())
            clean_data: List[Dict[str, Any]] = [record for i, record in enumerate(raw_data) if i not in invalid_indices]
        else:
            # A schema-level error occurred (e.g., wrong input type for the payload)
            raise SchemaValidationError(f"Schema-level validation failed: {errors}")

    # Dynamically extract column names and order from the schema's fields
    # Use field.data_key if available (for fields like 'load_from'), otherwise the field name
    cols_to_keep = cast(
        List[BrokenLinksReportField],
        [field.data_key or name for name, field in serializer.fields.items()],
    )

    # Create the DataFrame, ensuring column order and filtering extraneous fields
    df = pd.DataFrame(clean_data, columns=cols_to_keep)
    return df
