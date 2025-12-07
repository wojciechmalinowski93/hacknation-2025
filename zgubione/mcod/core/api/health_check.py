import logging
import threading
import time
from typing import Literal

import requests

from mcod import settings
from mcod.core.metrics import CMS_UP, DJANGO_ADMIN_UP

logger = logging.getLogger("mcod-api")
IS_UP = Literal[0, 1]


def check_service_health(url: str) -> IS_UP:
    """
    Checks the health of a service by sending a GET request to the provided URL.

    Returns:
    IS_UP: 1 if the service is healthy (HTTP 200), 0 otherwise.
    """
    try:
        resp = requests.get(url, timeout=2, verify=False)
        is_up: IS_UP = 1 if resp.status_code == 200 else 0
        logger.info(f"[HEALTH CHECK] {url} → {resp.status_code} → {is_up}")
    except Exception as e:
        logger.info(f"[HEALTH ERROR] {url} → {e}")
        is_up: IS_UP = 0
    return is_up


def _health_loop():
    """Continuously performs health checks for predefined services at regular intervals."""
    while True:
        # Check CMS status
        cms_url: str = settings.CMS_URL
        cms_up: Literal[1, 0] = check_service_health(cms_url + "/health/")
        CMS_UP.labels(url=cms_url).set(cms_up)

        # Check django admin status
        admin_url: str = settings.ADMIN_URL
        admin_up: Literal[1, 0] = check_service_health(admin_url + "/health/")
        DJANGO_ADMIN_UP.labels(url=admin_url).set(admin_up)
        time.sleep(settings.HEALTH_STATUS_SLEEP_TIME)


def start_health_monitoring():
    """
    Starts the background thread that monitors the health of services.

    Behavior:
        - Launches `_health_loop` in a daemon thread, allowing it to run continuously in the background.
        - The thread terminates automatically when the main program exits.
    """
    if settings.HEALTH_CHECK:
        threading.Thread(target=_health_loop, daemon=True, name="HealthMonitor").start()
