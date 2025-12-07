from urllib.request import Request

from django.http import HttpResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest


def prometheus_metrics_view(request: Request) -> HttpResponse:
    """Handle prometheus metrics endpoint."""
    return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
