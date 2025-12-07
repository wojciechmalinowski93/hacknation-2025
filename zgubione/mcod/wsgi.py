"""
WSGI config for mcod project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mcod.settings,base")
os.environ.setdefault("COMPONENT", "admin")
application = get_wsgi_application()
