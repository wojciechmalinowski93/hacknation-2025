from typing import Dict, List, Union

import bleach
from bleach.css_sanitizer import CSSSanitizer
from ckeditor_uploader.fields import RichTextUploadingField as BaseRichTextUploadingField
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.fields.jsonb import JsonAdapter
from django.db import models
from modeltrans.fields import TranslationField


def sanitize_html(html_content: str, strip_comments=False) -> str:
    """
    Sanitizes the provided HTML content by removing or escaping disallowed tags, attributes, and styles.

    This function uses the `bleach` library to clean the HTML content based on a predefined set of allowed tags,
    attributes, and styles. It ensures that only the specified HTML elements and attributes are retained, and it
    strips any unwanted content to prevent potential security risks, such as Cross-Site Scripting (XSS) attacks.

    Args:
        html_content (str): The HTML content to be sanitized.
        strip_comments (bool): Removes comments if `strip_comments` is set to `True`.

    Returns:
        str: The sanitized HTML content, where disallowed tags, attributes, and styles have been removed or escaped.

    Allowed Tags:
        - a, abbr, acronym, address, b, br, blockquote, code, div, em, h1, h2, h3, h4, h5, h6, hr, i, img, li, ol, p,
          pre, span, strong, table, caption, tbody, tr, td, ul.

    Allowed Attributes:
        - Global attributes (applies to all tags): style.
        - img: src, alt, title, width, height, rel.
        - a: href, title, target.
        - table: align, border, caption, cellpadding, cellspacing, dir, width, height, id, summary.
        - Plus any attributes specified in `bleach.sanitizer.ALLOWED_ATTRIBUTES`.

    Allowed Styles:
        - color, background-color, font-family, font-weight, font-size, width, height, text-align, border, border-width,
          border-style, border-color, border-radius, padding, padding-top, padding-right, padding-bottom, padding-left,
          margin, margin-top, margin-right, margin-bottom, margin-left, text-decoration, line-height, font-style,
          font-variant, letter-spacing, word-spacing, text-transform, white-space, vertical-align, list-style-type,
          list-style-position, list-style-image.

    Notes:
        - The function strips any HTML tags that are not in the allowed list and removes comments if `strip_comments` is
          set to `True`.
        - It also ensures that only the allowed CSS properties are retained within the style attributes.

    Example:
        sanitized_content = sanitize_html('<div style="color:red; font-size:20px;">Hello <script>alert("XSS")</script></div>')
        # Output: '<div style="color:red; font-size:20px;">Hello alert("XSS")</div>'
    """
    allowed_tags = [
        "a",
        "abbr",
        "acronym",
        "address",
        "b",
        "br",
        "blockquote",
        "code",
        "div",
        "em",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "hr",
        "i",
        "img",
        "li",
        "ol",
        "p",
        "pre",
        "span",
        "strong",
        "table",
        "caption",
        "tbody",
        "tr",
        "td",
        "ul",
    ]
    allowed_attributes = {
        **bleach.sanitizer.ALLOWED_ATTRIBUTES,
        "*": ["style"],
        "img": ["src", "alt", "title", "width", "height", "rel"],
        "a": ["href", "title", "target"],
        "table": ["align", "border", "caption", "cellpadding", "cellspacing", "dir", "width", "height", "id", "summary"],
    }
    allowed_styles = [
        "color",
        "background-color",
        "font-family",
        "font-weight",
        "font-size",
        "width",
        "height",
        "text-align",
        "border",
        "border-width",
        "border-style",
        "border-color",
        "border-radius",
        "padding",
        "padding-top",
        "padding-right",
        "padding-bottom",
        "padding-left",
        "margin",
        "margin-top",
        "margin-right",
        "margin-bottom",
        "margin-left",
        "text-decoration",
        "line-height",
        "font-style",
        "font-variant",
        "letter-spacing",
        "word-spacing",
        "text-transform",
        "white-space",
        "vertical-align",
        "list-style-type",
        "list-style-position",
        "list-style-image",
    ]

    css_sanitizer = CSSSanitizer(allowed_css_properties=allowed_styles)

    sanitized_html = bleach.clean(
        html_content,
        tags=allowed_tags,
        attributes=allowed_attributes,
        css_sanitizer=css_sanitizer,
        strip=True,
        strip_comments=strip_comments,
    )
    return sanitized_html


class SanitizedCharField(models.CharField):
    def get_prep_value(self, value: str):
        value = super().get_prep_value(value)
        if isinstance(value, str):
            return sanitize_html(value)
        return value


class SanitizedRichTextUploadingField(BaseRichTextUploadingField):
    def get_prep_value(self, value: str):
        value = super().get_prep_value(value)
        if isinstance(value, str):
            return sanitize_html(value)
        return value


class SanitizedTextField(models.TextField):
    def get_prep_value(self, value: str):
        value = super().get_prep_value(value)
        if isinstance(value, str):
            return sanitize_html(value)
        return value


class SanitizedJSONField(JSONField):
    """
    Overloads the `get_prep_value` method of the `JSONField` class to sanitize JSON fields specific to
    this project's forms. Depending on the instance type after unpacking (dictionary or list), sanitizes a specific
    field value. The class is not for general use and its use must be tested.
    """

    def get_prep_value(self, value: Union[Dict[str, str], List[Dict[str, str]]]):
        value = super().get_prep_value(value)
        if isinstance(value, JsonAdapter):
            value = value.adapted

        if isinstance(value, dict):
            return self._sanitize_dict(value)
        elif isinstance(value, list):
            return self._sanitize_list(value)
        return value

    def _sanitize_dict(self, value: Dict[str, str]) -> JsonAdapter:
        """
        Sanitizes a dictionary by sanitizing both keys and values.
        """
        sanitized_value = {sanitize_html(key): sanitize_html(val) for key, val in value.items()}
        return JsonAdapter(sanitized_value, encoder=self.encoder)

    def _sanitize_list(self, value: List[Union[str, Dict[str, str]]]) -> JsonAdapter:
        """
        Sanitizes a list by sanitizing each item. If an item is a dictionary, it sanitizes the key-value pairs.
        """
        sanitized_list = []
        for item in value:
            if isinstance(item, dict):
                sanitized_item = {key: sanitize_html(val) if val is not None else None for key, val in item.items()}
                sanitized_list.append(sanitized_item)
            else:
                sanitized_list.append(sanitize_html(item))
        return JsonAdapter(sanitized_list, encoder=self.encoder)


class SanitizedTranslationField(TranslationField):
    def get_prep_value(self, value: Dict[str, str]):
        value = super().get_prep_value(value)
        if isinstance(value, JsonAdapter):
            value = value.adapted

        if isinstance(value, dict):
            return self._sanitize_dict(value)
        return value

    def _sanitize_dict(self, value: Dict[str, str]) -> JsonAdapter:
        """
        Sanitizes a dictionary by sanitizing the values of the key-value pairs.
        If a value is `None`, it is preserved as `None`. The keys are left unchanged.
        """
        sanitized_value = {key: sanitize_html(val) if val is not None else None for key, val in value.items()}
        return JsonAdapter(sanitized_value, encoder=self.encoder)
