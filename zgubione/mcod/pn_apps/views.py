import logging
import os
from time import time

from bokeh.embed import server_document
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseNotFound
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _

from mcod.pn_apps.utils import chart_thumb_path

extra_js = os.environ.get("BOKEH_EXTRA_JS")
profile_log = logging.getLogger("stats-profile")


def stats_dashboard(request: HttpRequest) -> HttpResponse:
    start = time()
    script = server_document(request.build_absolute_uri())
    if not request.user.is_authenticated:
        return HttpResponse(_("Unauthorized"), status=401)
    stats_event_settings = getattr(settings, "STATS_EVENTS", [])
    stats_log_level = getattr(settings, "STATS_LOG_LEVEL", "INFO")
    rendered_request = render(
        request,
        "pn_apps/stats.html",
        dict(
            script=script,
            extra_js=extra_js,
            user=request.user,
            stats_event_settings=stats_event_settings,
            stats_log_level=stats_log_level,
        ),
    )
    end = time()
    total = end - start
    profile_log.debug("VIEW TIME: %.4f" % total)
    return rendered_request


def chart_thumbnail(request: HttpRequest, slot: int) -> HttpRequest:
    if not request.user.is_authenticated:
        return HttpResponse(_("Unauthorized"), status=401)

    filename = chart_thumb_path(request.user, slot)

    try:
        with open(filename, "rb") as f:
            return HttpResponse(f.read(), content_type="image/png")
    except IOError:
        return HttpResponseNotFound()


def short_apps(request, notebook):
    script = server_document(request.build_absolute_uri())
    return render(request, "pn_apps/embed.html", dict(script=script))
