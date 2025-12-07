import decorator
from django.core.cache import caches

from mcod import settings

marker = object()


def _memoize(func, *args, **kw):
    cache = getattr(func, "_cache", marker)
    if cache is marker:
        func._cache = func(*args, **kw)
        return func._cache
    else:
        return cache


def memoize(f):
    return decorator.decorator(_memoize, f)


def flush_sessions():
    """
    Clear session cache for the current pytest worker or all sessions if no
    worker ID. Used in tests to isolate cache between test runs.
    """
    _session_cache = caches[settings.SESSION_CACHE_ALIAS]
    session_cache_prefix = _session_cache.key_prefix
    if session_cache_prefix:
        _session_cache.delete_pattern(f"{session_cache_prefix}*")
    else:
        _session_cache.delete_pattern("*")
