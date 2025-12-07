from cache_memoize import cache_memoize
from django.utils import timezone, translation

from mcod.alerts.models import Alert
from mcod.lib.utils import escape_braces_and_format_html


@cache_memoize(60)
def get_active_alerts(language_code):
    now = timezone.now()
    with translation.override(language_code):
        alerts = Alert.objects.filter(status="published", start_date__lt=now, finish_date__gt=now)

        return [
            {"title": alert.title_i18n, "description": escape_braces_and_format_html(alert.description_i18n)} for alert in alerts
        ]
