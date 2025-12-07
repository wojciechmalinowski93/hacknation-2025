import pytest

from mcod.celeryapp import get_beat_schedule


@pytest.fixture
def beat_schedule_fixture() -> dict:
    return get_beat_schedule(enable_monthly_reports=False, enable_create_xml_metadata_report=True)
