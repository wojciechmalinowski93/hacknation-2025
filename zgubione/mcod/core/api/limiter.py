from django.conf import settings
from falcon_limiter import Limiter

from mcod.core.utils import get_limiter_key

limiter = Limiter(
    key_func=get_limiter_key,
    default_limits=settings.FALCON_LIMITER_DEFAULT_LIMITS,
    config={
        "RATELIMIT_KEY_PREFIX": "falcon-limiter",
        "RATELIMIT_STORAGE_URL": settings.REDIS_URL,
    },
)
