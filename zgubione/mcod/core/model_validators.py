from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from mcod.core.utils import XmlTextInvalid, validate_xml10_text


def illegal_character_validator(value: str) -> None:
    """
    Validate whether the input contains illegal characters within a specific format.
    Basically it's a validator for xml creation files. When illegal characters
    occurs, then task create_xml_metadata_files will fail.

    Args:
    - value (str): The string to be validated for illegal characters.

    Raises:
    - ValidationError: If the input contains illegal characters.

    Note:
    This function wraps the input string in a specified format
    (for example "<description>...</description>") and checks if it can be parsed without
    raising an exception due to illegal characters. If you want to make a tests on website, use this
    value: 
    """
    try:
        validate_xml10_text(value)
    except XmlTextInvalid as e:
        raise ValidationError(_("Given text contains illegal character. Please revalidate provided data.")) from e
