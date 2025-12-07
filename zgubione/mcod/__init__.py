import logging

__all__ = []
logger = logging.getLogger("mcod")

try:
    from mcod.celeryapp import app as celery_app  # noqa F401

    __all__ += "celery_app"
except ImportError as exc:
    logger.debug(exc)
