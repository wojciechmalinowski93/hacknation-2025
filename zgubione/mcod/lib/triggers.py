from importlib import import_module

from mcod import settings

session_store = import_module(settings.SESSION_ENGINE).SessionStore
