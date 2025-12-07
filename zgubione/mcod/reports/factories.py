import factory

from mcod.core.registries import factories_registry
from mcod.reports.models import (
    DatasetReport,
    DataSourceImportReport,
    MonitoringReport,
    OrganizationReport,
    Report,
    ResourceReport,
    SummaryDailyReport,
    UserReport,
)


class ReportFactory(factory.django.DjangoModelFactory):
    file = factory.Faker("text", max_nb_chars=100, locale="pl_PL")

    class Meta:
        model = Report


class OrganizationReportFactory(ReportFactory):
    model = "organizations.Organization"

    class Meta:
        model = OrganizationReport


class UserReportFactory(ReportFactory):
    model = "users.User"

    class Meta:
        model = UserReport


class ResourceReportFactory(ReportFactory):
    model = "resources.Resource"

    class Meta:
        model = ResourceReport


class DatasetReportFactory(ReportFactory):
    model = "datasets.Dataset"

    class Meta:
        model = DatasetReport


class SummaryDailyReportFactory(ReportFactory):
    class Meta:
        model = SummaryDailyReport


class MonitoringReportFactory(ReportFactory):
    model = "applications.ApplicationProposal"

    class Meta:
        model = MonitoringReport


class DataSourceImportReportFactory(ReportFactory):
    model = "harvester.DataSourceImport"

    class Meta:
        model = DataSourceImportReport


factories_registry.register("organizationreport", OrganizationReportFactory)
factories_registry.register("userreport", UserReportFactory)
factories_registry.register("resourcereport", ResourceReportFactory)
factories_registry.register("datasetreport", DatasetReportFactory)
factories_registry.register("summarydailyreport", SummaryDailyReportFactory)
factories_registry.register("monitoringreport", MonitoringReportFactory)
factories_registry.register("datasourceimportreport", DataSourceImportReportFactory)
