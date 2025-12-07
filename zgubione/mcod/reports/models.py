import os

from django.contrib.auth import get_user_model
from django.db import models
from django.utils.translation import gettext_lazy as _, pgettext_lazy
from django_celery_results.models import TaskResult

from mcod import settings
from mcod.core.db.models import TimeStampedModel
from mcod.core.utils import sizeof_fmt

User = get_user_model()


class ReportMixin:

    @property
    def file_name(self):
        return os.path.basename(self.file) if self.file else None

    @property
    def file_url_path(self):
        if self.file:
            return self.file if self.file.startswith("/") else f"/{self.file}"

    @property
    def file_size(self):
        if self.file:
            try:
                return sizeof_fmt(os.path.getsize(os.path.join(settings.ROOT_DIR, self.file.strip("/"))))
            except FileNotFoundError:
                return None
        return "-"


class Report(ReportMixin, TimeStampedModel):
    ordered_by = models.ForeignKey(
        User,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Ordered by"),
        related_name="reports_ordered",
    )
    task = models.ForeignKey(
        TaskResult,
        models.DO_NOTHING,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Task"),
        related_name="report",
    )
    model = models.CharField(null=True, max_length=80)
    file = models.CharField(null=True, max_length=512, verbose_name=_("File path"))

    class Meta:
        verbose_name = _("Report")
        verbose_name_plural = _("Reports")

    @property
    def status(self):
        return self.task.status if self.task else "PENDING"


class MonitoringReport(Report):

    @classmethod
    def accusative_case(cls):
        return _("acc: Monitoring report")

    class Meta:
        proxy = True
        verbose_name = _("Monitoring")
        verbose_name_plural = _("Monitoring")


class UserReport(Report):

    @classmethod
    def accusative_case(cls):
        return _("acc: User report")

    class Meta:
        proxy = True
        verbose_name = _("User report")
        verbose_name_plural = _("User reports")


class DataSourceImportReport(Report):

    @classmethod
    def accusative_case(cls):
        return _("acc: Data source imports report")

    class Meta:
        proxy = True
        verbose_name = _("Data source")
        verbose_name_plural = _("Data source reports")


class ResourceReport(Report):

    @classmethod
    def accusative_case(cls):
        return _("acc: Resource report")

    class Meta:
        proxy = True
        verbose_name = _("Resource report")
        verbose_name_plural = _("Resource reports")


class DatasetReport(Report):

    @classmethod
    def accusative_case(cls):
        return _("acc: Dataset report")

    class Meta:
        proxy = True
        verbose_name = _("Dataset report")
        verbose_name_plural = _("Dataset reports")


class OrganizationReport(Report):

    @classmethod
    def accusative_case(cls):
        return _("acc: Institution report")

    class Meta:
        proxy = True
        verbose_name = _("Institution report")
        verbose_name_plural = _("Institution reports")


class SummaryDailyReport(ReportMixin, TimeStampedModel):
    file = models.CharField(null=True, max_length=512, verbose_name=_("File path"))
    ordered_by = models.ForeignKey(
        User,
        models.SET_NULL,
        blank=False,
        editable=False,
        null=True,
        verbose_name=_("Ordered by"),
        related_name="reports_ordered_by",
    )

    status = models.CharField(max_length=20, default="SUCCESS")

    @classmethod
    def accusative_case(cls):
        return _("acc: Daily report")

    class Meta:
        verbose_name = _("Summary daily report")
        verbose_name_plural = _("Summary daily reports")


class Dashboard(Report):
    class Meta:
        proxy = True
        verbose_name = pgettext_lazy("Metabase Dashboard", "Dashboard")
        verbose_name_plural = pgettext_lazy("Metabase Dashboards", "Dashboards")
