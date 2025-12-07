from datetime import datetime, timezone
from unittest.mock import patch

import pytest
import pytz

from mcod.core.api.fields import (  # isort: skip
    DateTime,
    LocalDateTime,
    iso_format_in_local_timezone,
)


class TestLocalDateTimeField:
    DATETIME_FORMAT = "iso8601T"

    @pytest.mark.parametrize(
        ["local_tz", "dt_input", "dt_output", "dt_utc_output"],
        [
            (
                "Europe/Warsaw",
                datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
                "2024-01-01T13:00:00+01:00",
                "2024-01-01T12:00:00Z",
            ),
            (
                "Europe/Warsaw",
                datetime(2024, 7, 1, 12, 0, 0, tzinfo=timezone.utc),
                "2024-07-01T14:00:00+02:00",
                "2024-07-01T12:00:00Z",
            ),
        ],
    )
    def test_iso_format_in_local_timezone(self, local_tz, dt_input, dt_output, dt_utc_output):
        """
        Tests that iso_format_in_local_timezone handles winter and summer time
        for a single timezone.
        """
        with patch(
            "mcod.core.api.fields.get_localzone",
            return_value=pytz.timezone(local_tz),
        ) as mock_get_localzone:
            local_date = LocalDateTime.SERIALIZATION_FUNCS[self.DATETIME_FORMAT](dt_input)
            utc_date = DateTime.SERIALIZATION_FUNCS[self.DATETIME_FORMAT](dt_input)
            mock_get_localzone.assert_called_once()
            assert local_date == dt_output, f"Expected {dt_output} but got {local_date}."
            assert utc_date == dt_utc_output, f"Expected {dt_utc_output} but got {utc_date}."

    def test_field_extends_serialization_funcs_for_iso8601t_format(self):
        """
        Test to ensure that LocalDateTime's SERIALIZATION_FUNCS dictionary
        extends the DateTime's SERIALIZATION_FUNCS with a function that converts
        the date in iso format to local time for the system.
        """
        assert LocalDateTime.DEFAULT_FORMAT == self.DATETIME_FORMAT
        assert (
            self.DATETIME_FORMAT in LocalDateTime.SERIALIZATION_FUNCS
        ), f"{self.DATETIME_FORMAT} not found in SERIALIZATION_FUNCS"
        assert (
            LocalDateTime.SERIALIZATION_FUNCS[self.DATETIME_FORMAT] == iso_format_in_local_timezone
        ), f"{self.DATETIME_FORMAT} doesn't map to iso_format_in_local_timezone"
