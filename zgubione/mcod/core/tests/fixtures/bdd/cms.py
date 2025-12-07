import json
import os

from django.apps import apps
from django.test import Client
from pytest_bdd import given, parsers, then, when
from wagtail.core.models import Page, Site

from mcod import settings


@given(parsers.parse("cms structure from file {file_name} is loaded"))
def cms_structure_from_file(context, active_user, file_name):
    file_path = os.path.join(settings.TEST_SAMPLES_PATH, file_name)
    Site.objects.filter(hostname="localhost", port=80).delete()
    Page.objects.filter(pk=1).update(numchild=1)

    with open(file_path, "r") as file:
        data = json.loads(file.read())

    for row in data:
        model = apps.get_model(row["model"])
        fields = row["fields"]
        fields["pk"] = row.pop("pk")
        if issubclass(model, Page):
            fields["owner"] = active_user
            page = model.objects.create(**fields)
            revision = page.save_revision()
            page.live_revision = revision
            page.save()
            revision.publish()
        else:
            model.objects.create(**fields)


@when(parsers.parse("every CMS API endpoint is requested"))
def all_apis_endpoints_are_requested(context):
    context.responses = []
    api_prefix = "/api/"
    urls = [f"{api_prefix}pages{page.url_path}" for page in Page.objects.exclude(live_revision__isnull=True)]
    urls.extend(
        [
            f"{api_prefix}images/",
            f"{api_prefix}documents/",
        ]
    )
    client = Client()
    for url in urls:
        context.responses.append(client.get(url))


@then(parsers.parse("every CMS API response status code is {status_code:d}"))
def every_response_status_code_is(context, status_code):
    for response in context.responses:
        assert status_code == response.status_code, 'Response for url "%s" should be "%s", is "%s"' % (
            getattr(response, "url", None),
            status_code,
            response.status_code,
        )


@then(parsers.parse("CMS live page count is {page_count:d}"))
def cms_page_count_is(page_count):
    actual_page_count = Page.objects.exclude(live_revision__isnull=True).count()
    assert page_count == actual_page_count, (
        f"Actual page count is {actual_page_count} and isn't equal" f" to expected page count {page_count}"
    )
