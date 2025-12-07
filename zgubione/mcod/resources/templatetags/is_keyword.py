from django import template

register = template.Library()


@register.filter("is_keyword")
def is_keyword(text):
    if isinstance(text, str):
        return text.endswith(".keyword")
    return False
