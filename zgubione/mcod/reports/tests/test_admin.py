import re
from typing import List

import factory
from bs4 import BeautifulSoup
from django.contrib.auth import get_user_model
from django.db.models import QuerySet
from django.http import HttpResponse
from django.test import Client
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from pytest_bdd import scenarios

from mcod.reports.factories import DataSourceImportReportFactory
from mcod.reports.models import DataSourceImportReport
from mcod.resources.documents import TaskResult
from mcod.resources.factories import TaskResultFactory

scenarios("features/admin/reports_list.feature")

User = get_user_model()


class TestDataSourceImportsReports:

    url: str = reverse("admin:reports_datasourceimportreport_changelist")
    client: Client = Client()

    def test_none_admin_cant_see_page(self, active_editor: User):
        """Test if non-admin user can see the page."""
        self.client.force_login(active_editor)
        res: HttpResponse = self.client.get(self.url)
        assert res.status_code == 403

    def test_data_source_imports_admin_reports(self, tmp_path, admin):
        """
        Test endpoint with given reports in DB. As a result, user should see the table with the
        reports links.
        """
        # GIVEN reports with specified file paths
        file_paths: List[str] = [f"{tmp_path}/{element}.csv" for element in range(5)]
        tasks: QuerySet[TaskResult] = TaskResultFactory.create_batch(size=len(file_paths))
        reports: QuerySet[DataSourceImportReport] = DataSourceImportReportFactory.create_batch(
            size=len(file_paths),
            file=factory.Iterator(file_paths),
            task=factory.Iterator(tasks),
        )

        # GIVEN admin login
        self.client.force_login(admin)
        res: HttpResponse = self.client.get(self.url)

        # WHEN
        data: str = res.content.decode()

        # THEN status code is 200
        assert res.status_code == 200
        assert str(_("Generated report file")) in data
        for report in reports:
            # THEN table with active links are generated in page
            assert f'<a href="{report.file}">' in data
            assert report.task.status in data

    def test_data_source_imports_admin_no_reports(self, admin):
        """Test if specified message appears in the html, when no reports generated."""
        # GIVEN admin login and not reports in DB.
        self.client.force_login(admin)

        # WHEN
        res: HttpResponse = self.client.get(self.url)

        # THEN status code is 200
        assert res.status_code == 200

        # THEN clean data
        soup: BeautifulSoup = BeautifulSoup(res.content, "html.parser")
        clean_html: str = re.sub(r"\s+", " ", soup.body.decode_contents()).strip()

        # THEN message appears in html
        message = f"{DataSourceImportReport._meta.verbose_name_plural} nie są jeszcze utworzone."
        assert message in clean_html
