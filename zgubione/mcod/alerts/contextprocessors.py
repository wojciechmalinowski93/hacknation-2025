from django.utils.translation import get_language

from mcod.alerts.utils import get_active_alerts


def active_alerts(request):
    return {"active_alerts": get_active_alerts(get_language())}
