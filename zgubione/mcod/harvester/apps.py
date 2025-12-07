from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
from rdflib.parser import Parser
from rdflib.plugin import register
from rdflib.query import ResultParser

from mcod.core.apps import ExtendedAppMixin


class HarvesterConfig(ExtendedAppMixin, AppConfig):
    name = "mcod.harvester"
    verbose_name = _("Data Sources")

    def ready(self):
        import mcod.harvester.signals.handlers  # noqa
        from mcod.harvester.models import DataSource

        self.connect_history(DataSource)
        register(
            "application/rdf+xml; charset=UTF-8",
            ResultParser,
            "rdflib.plugins.sparql.results.graph",
            "GraphResultParser",
        )
        register(
            "application/rdf+xml; charset=UTF-8",
            Parser,
            "rdflib.plugins.parsers.rdfxml",
            "RDFXMLParser",
        )
