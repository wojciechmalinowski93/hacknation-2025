import re

from django.apps import apps
from django.utils.deprecation import MiddlewareMixin
from wagtail.core.models import Site

from mcod.counters.lib import Counter

NewsPage = apps.get_model("cms", "NewsPage")


class SiteMiddleware(MiddlewareMixin):
    def process_request(self, request):
        try:
            request.site = Site.find_for_request(request)
        except Site.DoesNotExist:
            request.site = None


class CounterMiddleware(MiddlewareMixin):
    NEWS_API_URL_PATTERN = re.compile(r"/news/([-a-zA-Z0-9_]+)/")

    def process_response(self, request, response):
        if response.status_code == 200:
            match = self.NEWS_API_URL_PATTERN.match(request.path)
            if match:
                slug = match.group(1)
                try:
                    obj_id = NewsPage.objects.get(slug=slug).id
                    Counter().incr_view_count(NewsPage._meta.label, obj_id)
                except NewsPage.DoesNotExist:
                    pass
        return response
