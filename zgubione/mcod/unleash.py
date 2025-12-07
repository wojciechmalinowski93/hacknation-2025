import logging

from mcod import settings
from mcod.core.unleash.strategies import EnvironmentName

logger = logging.getLogger("mcod")

unleash_client = None

try:
    from UnleashClient import UnleashClient

    unleash_client = UnleashClient(
        url=settings.UNLEASH_URL,
        app_name=settings.COMPONENT,
        environment=settings.ENVIRONMENT,
        custom_strategies={"environmentName": EnvironmentName},
    )
    unleash_client.initialize_client()

except ImportError as exc:
    logger.debug(exc)


def is_enabled(feature_name: str, env_name: dict = settings.ENVIRONMENT) -> bool:
    if not unleash_client or not unleash_client.is_initialized:
        logger.debug("UnleashClient was not initialized!")
        return False
    return unleash_client.is_enabled(feature_name, context={"envName": env_name})


def if_is_enabled(*unleash_args, **unleash_kwargs):
    """
    Decorator version of is_enabled function.
    Features are checked on init.
    """

    def decorator(f):
        if is_enabled(*unleash_args, **unleash_kwargs):
            return f
        else:  # do nothing
            return lambda *f_args, **f_kwargs: None

    return decorator


__all__ = ["is_enabled", "if_is_enabled"]
