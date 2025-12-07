from mcod.lib.utils import is_django_ver_lt

if is_django_ver_lt(3, 2):
    default_app_config = "mcod.hacks.apps.HacksConfig"
