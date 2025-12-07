import importlib
import sys
from importlib.machinery import ModuleSpec, PathFinder, SourceFileLoader

from django.apps import AppConfig
from django.core.exceptions import ImproperlyConfigured
from modeltrans.fields import TranslatedVirtualField

from mcod.hacks import search_index as search_index_hacked
from mcod.hacks.goodtables_spec import spec as gt_spec


class CustomLoader(SourceFileLoader):
    def exec_module(self, module):
        module.Command = search_index_hacked.Command
        return module


class Finder(PathFinder):
    def __init__(self, module_name):
        self.module_name = module_name

    def find_spec(self, fullname, path=None, target=None):
        if fullname == self.module_name:
            spec = super().find_spec(fullname, path, target)
            return ModuleSpec(fullname, CustomLoader(fullname, spec.origin))


def translated_field_factory_hacked(original_field, language=None, *args, **kwargs):
    if not original_field.get_internal_type() in (
        "CharField",
        "TextField",
        "SlugField",
    ):
        raise ImproperlyConfigured("{} is not supported by django-modeltrans.".format(original_field.__class__.__name__))

    class Specific(TranslatedVirtualField, original_field.__class__):
        pass

    Specific.__name__ = "Translated{}".format(original_field.__class__.__name__)

    return Specific(original_field, language, *args, **kwargs)


def goodtables_spec_hacked():
    return gt_spec


class HacksConfig(AppConfig):
    name = "mcod.hacks"

    @staticmethod
    def hack_modeltrans():
        import modeltrans.translator

        _module = importlib.import_module("modeltrans.fields")
        _module.translated_field_factory = translated_field_factory_hacked
        importlib.reload(modeltrans.translator)

    @staticmethod
    def hack_goodtables():
        import goodtables.error

        spec_module = importlib.import_module("goodtables.spec")
        spec_module.spec = goodtables_spec_hacked()
        importlib.reload(goodtables.error)

    @staticmethod
    def hack_django_elasticsearch_dsl():
        sys.meta_path.insert(0, Finder("django_elasticsearch_dsl.management.commands.search_index"))

    @staticmethod
    def register_missing_content_types_rdflib():
        from rdflib.parser import Parser
        from rdflib.plugin import register
        from rdflib.serializer import Serializer

        register(
            "application/trig",
            Serializer,
            "rdflib.plugins.serializers.trig",
            "TrigSerializer",
        )

        register("application/trig", Parser, "rdflib.plugins.parsers.trig", "TrigParser")

    def ready(self):
        self.hack_goodtables()
        self.hack_django_elasticsearch_dsl()
        self.hack_modeltrans()
        self.register_missing_content_types_rdflib()
