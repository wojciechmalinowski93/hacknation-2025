from django.conf import settings as _settings

from mcod.core.utils import route_to_name


def settings(request):
    return {"SETTINGS": _settings}


def apm(request):
    if request.resolver_match and hasattr(request.resolver_match, "route"):
        route = request.resolver_match.route
    else:
        route = request.path

    return {"admin_amp_transaction_name": route_to_name(route, method=request.method)}
