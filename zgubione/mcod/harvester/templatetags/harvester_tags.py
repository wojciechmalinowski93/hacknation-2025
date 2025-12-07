from django import template
from django.contrib.admin.views.main import PAGE_VAR
from django.utils.html import escape
from django.utils.safestring import mark_safe

from mcod.lib.utils import is_django_ver_lt

register = template.Library()

DOT = "."


@register.simple_tag
def paginator_number(cl, i):
    """
    Generates an individual page index link in a paginated list.
    Overriden suit.templatetags.suit_list.paginator_number with custom page_param added.
    """
    page_arg_num = i
    if not is_django_ver_lt(3, 2):
        page_arg_num = i + 1
    if i == DOT:
        return mark_safe(
            '<li class="disabled"><a href="#" onclick="return false;">..' ".</a></li>"
        )
    elif i == cl.page_num:
        return mark_safe('<li class="active"><a href="">%d</a></li> ' % (i + 1))
    else:
        return mark_safe(
            '<li><a href="%s"%s>%d</a></li> '
            % (
                escape(
                    cl.get_query_string(
                        {getattr(cl, "page_param", PAGE_VAR): page_arg_num}
                    )
                ),
                (i == cl.paginator.num_pages - 1 and ' class="end"' or ""),
                i + 1,
            )
        )
