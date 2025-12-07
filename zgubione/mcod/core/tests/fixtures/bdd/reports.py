import pytest

from mcod.reports.factories import SummaryDailyReportFactory


@pytest.fixture
def summary_daily_report():
    return SummaryDailyReportFactory.create()
