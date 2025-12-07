import re
from typing import List

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_eda(address: str) -> None:
    """
    Validates the format of an EDA (Electronic Delivery Address) address.
    For more information, see OTD-315.
    """

    # Regex to match the EDA address format
    # AE:PL-00000-00000-NNNNN-XX
    eda_pattern: str = r"^AE:PL-\d{5}-\d{5}-[A-Z]{5}-\d{2}$"

    # Validate the address
    if not re.match(eda_pattern, address):
        raise ValidationError(_("Given address does not match electronic delivery address pattern."))

    eda_parts: List[str] = address.split("-")
    digits_sum: int = int(eda_parts[1]) + int(eda_parts[2])
    letters_ascii_sum: int = sum(ord(char) for char in eda_parts[3])
    checksum: int = int(eda_parts[4])

    checksum_calculation_base: int = abs(letters_ascii_sum - digits_sum)
    checksum_calculation_base_digits_sum: int = sum(int(digit) for digit in str(checksum_calculation_base))
    if not checksum == checksum_calculation_base_digits_sum:
        raise ValidationError(_("Given address does not match electronic delivery address pattern."))
