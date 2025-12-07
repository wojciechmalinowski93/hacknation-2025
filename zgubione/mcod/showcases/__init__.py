from mcod.lib.utils import is_django_ver_lt

if is_django_ver_lt(3, 2):  # pragma: no cover
    default_app_config = "mcod.showcases.apps.ShowcasesConfig"
