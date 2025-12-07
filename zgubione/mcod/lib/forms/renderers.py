import os

from django.conf import settings
from django.forms import renderers
from django.template.backends.django import DjangoTemplates
from django.utils.functional import cached_property

TEMPLATES_DIR = str(settings.APPS_DIR.path("templates"))


class EngineMixin(renderers.EngineMixin):
    @cached_property
    def engine(self):
        return self.backend(
            {
                "APP_DIRS": True,
                "DIRS": [
                    TEMPLATES_DIR,
                    os.path.join(renderers.ROOT, self.backend.app_dirname),
                ],
                "NAME": "djangoforms",
                "OPTIONS": {},
            }
        )


class TemplatesRenderer(EngineMixin, renderers.BaseRenderer):
    backend = DjangoTemplates
