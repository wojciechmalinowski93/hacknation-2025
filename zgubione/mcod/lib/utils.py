import logging
import os
import os.path
from pathlib import Path
from typing import List, Optional

from django import VERSION
from django.conf import settings
from django.utils.html import format_html

logger = logging.getLogger("mcod")


def is_django_ver_lt(major=2, minor=2):
    return VERSION[0] < major or (VERSION[0] == major and VERSION[1] < minor)


def escape_braces_and_format_html(text: str) -> str:
    """
    Escapes curly braces in the given text and formats it for safe HTML
    display.

    This function ensures that any literal curly braces in the `text` are not
    treated as placeholders in string formatting operations, which could
    otherwise lead to errors if `format_html` tries to insert values where
    none are intended.

    Parameters:
    - text (str): The text to be formatted.

    Returns:
    - str: The HTML-safe formatted text with escaped braces.
    """
    return format_html(text.replace("{", "{{").replace("}", "}}"))


def capitalize_first_character(text: str) -> str:
    """
    Capitalize the first character of the provided text and return the
    modified text.
    """
    return text[:1].upper() + text[1:]


def get_file_extensions_no_dot(filenames: List[str]) -> List[str]:
    extensions = []
    for filename in filenames:
        _, ext = os.path.splitext(filename)
        if ext and len(ext) > 1:
            ext = ext[1:]  # remove leading dot
            extensions.append(ext)
    return extensions


def get_file_content(filename: Optional[str]) -> bytes:
    """Load binary content from a sample file stored locally."""
    if not filename:
        return b""
    file_path = Path(settings.TEST_SAMPLES_PATH) / filename
    with open(file_path, "rb") as f:
        return f.read()
