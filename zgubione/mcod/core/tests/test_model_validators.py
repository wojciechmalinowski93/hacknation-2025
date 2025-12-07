import pytest
from django.core.exceptions import ValidationError

from mcod.core.model_validators import illegal_character_validator


@pytest.mark.parametrize(
    "char",
    [
        "&",
        "<",
        ">",
        '"',
        "'",
        "-",
        "*",
    ],
)
def test_illegal_character_validator_allows_chars(char):
    """Validator should NOT raise for allowed characters.

    Given the "no unescape" policy, numeric entities (e.g., '&#x26;', '&#x02;')
    are treated as literal text and should pass. Characters like '&', '<', '>'
    are allowed as input because downstream XML writers will escape them.
    """
    illegal_character_validator(f"ok{char}ok")


@pytest.mark.parametrize(
    "char",
    [
        # --- DISALLOWED in XML 1.0 (Fifth Edition) ---
        "\x00",  # null character (NUL)
        "\x01",
        "\x02",  # Start of Text — control character
        "\x03",
        "\x0B",  # vertical tab
        "\x0C",  # form feed (page break)
        "\uD800",  # lone high surrogate (disallowed)
        "\uDFFF",  # lone low surrogate (disallowed)
        "\uFFFE",  # non-character (disallowed in XML)
        "\uFFFF",  # non-character (disallowed in XML)
    ],
)
def test_illegal_character_validator_rejects_illegal_chars(char):
    """Validator MUST raise ValidationError for illegal XML 1.0 characters.

    This includes all disallowed C0 control characters (except TAB/LF/CR),
    surrogate code points, and non-characters like U+FFFE/U+FFFF.
    """
    with pytest.raises(ValidationError):
        illegal_character_validator(f"bad{char}bad")
