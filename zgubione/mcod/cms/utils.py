from urllib.parse import urlsplit, urlunsplit

from django.contrib.contenttypes.models import ContentType
from wagtail.core import hooks
from wagtail.core.models import UserPagePermissionsProxy

from mcod.cms.models import FormPage


def get_forms_for_user(user):
    editable_forms = UserPagePermissionsProxy(user).editable_pages()
    ct = ContentType.objects.get_for_model(FormPage)
    editable_forms = editable_forms.filter(content_type=ct)

    # Apply hooks
    for fn in hooks.get_hooks("filter_form_submissions_for_user"):
        editable_forms = fn(user, editable_forms)

    return editable_forms


def to_i18n_url(url, lang_code):
    scheme, netloc, path, query, fragment = urlsplit(url)
    return urlunsplit((scheme, netloc, f"/{lang_code}{path}", query, fragment))


def filter_page_type(queryset, page_models):
    qs = queryset.none()

    for model in page_models:
        qs |= queryset.type(model)

    return qs
