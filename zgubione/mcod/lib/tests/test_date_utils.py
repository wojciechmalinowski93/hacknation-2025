from datetime import date, datetime

import pytest
import pytz

from mcod.lib.date_utils import date_at_midnight


@pytest.mark.parametrize("tz_name", [None, "UTC", "Europe/Warsaw"])
def test_date_at_midnight_returns_midnight_datetime(tz_name):
    # Given
    tested_date = date(2025, 10, 20)
    tz = pytz.timezone(tz_name) if tz_name else None
    # When
    result = date_at_midnight(tested_date, tz=tz)
    # Then
    assert isinstance(result, datetime)
    assert result.date() == tested_date
    assert result.hour == 0
    assert result.minute == 0
    assert result.second == 0
    if tz_name:
        naive_result = result.replace(tzinfo=None)
        assert result.tzinfo.zone == tz_name
        assert result.utcoffset() == tz.utcoffset(naive_result)
