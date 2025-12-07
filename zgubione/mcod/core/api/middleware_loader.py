import logging
from inspect import isclass
from typing import List

from django.conf import settings
from django.utils.module_loading import import_string

from mcod.core.api.cache import app_cache
from mcod.core.api.limiter import limiter
from mcod.core.api.types import FalconMiddlewareProtocol

logger = logging.getLogger("mcod-api")
FALCON_CSRF_MIDDLEWARE = "mcod.core.api.middlewares.ContentTypeMiddleware"


def middleware_loader() -> List[FalconMiddlewareProtocol]:
    """
    Loads and returns Falcon middleware instances based on the current runtime configuration.

    Middleware can be provided in two forms:
    - As fully-qualified strings, which will be dynamically imported
    - As already-initialized objects or classes defined directly in code

    Loaded from:
    - `FALCON_MIDDLEWARES` (always included)
    - `FALCON_CSRF_MIDDLEWARE` (included if `ENABLE_CSRF` is True)
    - `limiter.middleware` (included if `FALCON_LIMITER_ENABLED` is True)
    - `app_cache.middleware` (included if `FALCON_CACHING_ENABLED` is True)

    Each item is either directly used or imported and instantiated if it's a string referring to a class.

    Returns:
        A list of middleware instances conforming to FalconMiddlewareProtocol.
        Returns an empty list if no middleware is configured or enabled.
    """
    middleware_instances = []

    base_middlewares = [el for el in settings.FALCON_MIDDLEWARES]

    if settings.ENABLE_CSRF:
        base_middlewares.append(FALCON_CSRF_MIDDLEWARE)
    if settings.FALCON_LIMITER_ENABLED:
        base_middlewares.append(limiter.middleware)
    if settings.FALCON_CACHING_ENABLED:
        base_middlewares.append(app_cache.middleware)

    for middleware_object_or_string in base_middlewares:
        if isinstance(middleware_object_or_string, str):
            instance = _middleware_from_string(middleware_object_or_string)
        else:
            instance = middleware_object_or_string

        middleware_instances.append(instance)

    return middleware_instances


def _middleware_from_string(middleware_fqcn: str) -> FalconMiddlewareProtocol:
    """
    Imports and returns a Falcon middleware instance from a fully-qualified class or object path.

    If the resolved object is a class, it is instantiated.
    If it's already an object (not a class), it is returned as-is.

    Args:
        middleware_fqcn: Fully-qualified string path to the middleware class or object.

    Returns:
        An instance conforming to FalconMiddlewareProtocol.
    """
    class_or_object = import_string(middleware_fqcn)
    if isclass(class_or_object):
        instance = class_or_object()
    else:
        instance = class_or_object
    return instance
