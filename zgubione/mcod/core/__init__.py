from django.utils.module_loading import autodiscover_modules

from mcod.lib.utils import is_django_ver_lt


def autodiscover():
    autodiscover_modules("sparql_graphs")


if is_django_ver_lt(3, 2):
    default_app_config = "mcod.core.apps.CoreConfig"
