import falcon

from mcod.core.api.cache import documented_cache
from mcod.core.api.views import JsonAPIView
from mcod.core.versioning import versioned


class ApiTestView(JsonAPIView):

    call_counter = {"1.0": 0, "1.4": 0}

    @versioned
    @documented_cache(timeout=1)
    def on_get(self, request, response, *args, **kwargs):
        self.call_counter["1.4"] += 1
        response.media = {"message": "OK from API version 1.4"}
        response.status = falcon.HTTP_200

    @on_get.version("1.0")
    @documented_cache(timeout=1)
    def on_get(self, request, response, *args, **kwargs):
        self.call_counter["1.0"] += 1
        response.media = {"message": "OK from API version 1.0"}
        response.status = falcon.HTTP_200
