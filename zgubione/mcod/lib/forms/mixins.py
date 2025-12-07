from typing import Optional

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from mcod.core.widgets import UnescapeTextInput
from mcod.lib.metadata_validators import validate_conflicting_high_value_data_flags


class HighValueDataFormValidatorMixin:
    def validate_high_value_data_flags_conflict(self, data: dict) -> None:
        """
        This function checks if `has_high_value_data` is set to False while
        `has_high_value_data_from_ec_list` is set to True, which is a
        conflicting state. If such a conflict is detected, it adds validation
        errors to both form fields.
        """
        has_high_value_data: Optional[bool] = data.get("has_high_value_data") == "True" if "has_high_value_data" in data else None
        has_high_value_data_from_ec_list: Optional[bool] = (
            data.get("has_high_value_data_from_ec_list") == "True" if "has_high_value_data_from_ec_list" in data else None
        )

        try:
            validate_conflicting_high_value_data_flags(has_high_value_data, has_high_value_data_from_ec_list)
        except ValidationError:
            self.add_error(
                "has_high_value_data",
                _("Check YES, because high-value data from the EC list is a special subcategory of high-value data."),
            )


class UnEscapeWidgetMixin:
    def _add_unescape_widget_for_fields_or_not(self):
        """
        Manually unescape fields. CKEditorWidget doing it automatically for fields like `description`.
        """
        if "title" in self.fields:
            self.fields["title"].widget = UnescapeTextInput()
