from functools import partial

import falcon

from mcod.core.api.cache import app_cache as cache
from mcod.core.api.handlers import (
    IncludeMixin,
    RetrieveManyHdlr as BaseRetrieveManyHdlr,
    RetrieveOneHdlr,
)
from mcod.core.api.views import JsonAPIView
from mcod.core.versioning import versioned
from mcod.guides.deserializers import GuideApiRequest, GuidesApiRequest
from mcod.guides.models import Guide
from mcod.guides.serializers import GuideApiResponse


class RetrieveManyHdlr(IncludeMixin, BaseRetrieveManyHdlr):
    pass


class GuidesView(JsonAPIView):

    @cache.cached(timeout=60)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveManyHdlr):
        database_model = Guide
        deserializer_schema = GuidesApiRequest
        serializer_schema = partial(GuideApiResponse, many=True)
        _includes = {
            "item": "guides.GuideItem",
        }
        _include_map = {
            "item": "items_included",
        }

        def _get_queryset(self, cleaned, *args, **kwargs):
            return self.database_model.objects.published().get_paginated_results(**cleaned)


class GuideView(JsonAPIView):

    @cache.cached(timeout=60)
    @versioned
    def on_get(self, request, response, *args, **kwargs):
        # TODO: omit cached version if url param changed, i.e ?lang=en
        # https://falcon-caching.readthedocs.io/en/stable/#query-string
        self.handle(request, response, self.GET, *args, **kwargs)

    class GET(RetrieveOneHdlr):
        deserializer_schema = GuideApiRequest
        serializer_schema = GuideApiResponse
        database_model = Guide
        _includes = {
            "item": "guides.GuideItem",
        }
        _include_map = {
            "item": "items_included",
        }

        def clean(self, *args, **kwargs):
            self._get_instance(*args, **kwargs)
            return {}

        def _get_data(self, cleaned, *args, **kwargs):
            return self._get_instance(*args, **kwargs)

        def _get_instance(self, *args, **kwargs):
            instance = getattr(self, "_cached_instance", None)
            if not instance:
                try:
                    self._cached_instance = self.database_model.objects.published().get(id=kwargs["id"])
                except self.database_model.DoesNotExist:
                    raise falcon.HTTPNotFound
            return self._cached_instance
