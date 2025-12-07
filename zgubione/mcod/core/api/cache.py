import functools

from django.conf import settings
from falcon_caching import Cache as BaseCache

from mcod.core.api import middlewares


class Cache(BaseCache):
    """Cache which uses custom version of middleware."""

    @property
    def middleware(self):
        return middlewares.FalconCacheMiddleware(self.cache, self.config)


app_cache = Cache(
    config={
        "CACHE_TYPE": "redis",
        "CACHE_EVICTION_STRATEGY": "time-based",
        "CACHE_KEY_PREFIX": "falcon-cache",
        "CACHE_REDIS_URL": settings.REDIS_URL,
    }
)


def documented_cache(*args, **kwargs):
    """
    Custom decorator for decorate API endpoints to cache them.

    IMPORTANT:
    Don't use app_cache.cached decorator directly, use it instead !!!
    app_cache.cached decorator causes the OpenAPI documentation errors for the decorated endpoint.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapped(*f_args, **f_kwargs):
            return app_cache.cached(*args, **kwargs)(func)(*f_args, **f_kwargs)

        return wrapped

    return decorator
