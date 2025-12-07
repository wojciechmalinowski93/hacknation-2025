import logging
import os

import django
import environ
from channels.routing import get_default_application

log = logging.getLogger(__name__)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mcod.settings")
os.environ.setdefault("COMPONENT", "admin")

env = environ.Env()
ROOT_DIR = environ.Path(__file__) - 1

try:
    env.read_env(ROOT_DIR.file(".env"))
except FileNotFoundError:
    pass

DEBUG = True if env("DEBUG", default="no") in ("yes", 1, "true") else False
DEBUGGER = env("DEBUGGER", default=None)

django.setup()

if DEBUG and DEBUGGER == "debugpy":
    import debugpy

    try:
        debugpy.listen(("0.0.0.0", 5678))
        log.info("Debugger attached.")
    except Exception:
        log.info("Debugger is already running.")

application = get_default_application()

log.info("App started successfully.")
