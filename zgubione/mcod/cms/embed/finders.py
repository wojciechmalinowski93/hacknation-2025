import re

from wagtail.embeds.exceptions import EmbedNotFoundException
from wagtail.embeds.finders.base import EmbedFinder
from wagtailvideos import get_video_model


class ODEmbedFinder(EmbedFinder):

    _urls = None

    def __init__(self, **options):
        _urls = []
        for provider in options["providers"]:
            _urls.extend(provider.get("urls", []))
        self._urls = _urls

    def accept(self, url):
        for pattern in self._urls:
            if re.match(pattern, url):
                return True
        return False

    def find_embed(self, url, max_width=None):
        video_model = get_video_model()
        match = re.search(r"/(\d+)/?", url)
        video_pk = match.group(1)
        try:
            obj = video_model.objects.get(pk=video_pk)
        except video_model.DoesNotExist:
            raise EmbedNotFoundException
        return {
            "title": obj.title,
            "author_name": "",
            "provider_name": "dane.gov.pl",
            "type": "video",
            "thumbnail_url": obj.thumbnail_url,
            "width": None,
            "height": None,
            "html": obj.embed_html,
        }


embed_finder_class = ODEmbedFinder
