from unittest import mock

import pytest

from mcod.resources.type_guess import TypeGuesser


@pytest.fixture
def guesser():
    return TypeGuesser()


@mock.patch("mcod.unleash.is_enabled", lambda x: True)
class TestTypeGuesser:

    @pytest.mark.parametrize("int_value", (-123, 0, 10))
    def test_int(self, guesser: TypeGuesser, int_value: int):
        assert list(guesser.cast(int_value)) == [
            ("integer", "default", 9),
            ("number", "default", 10),
            ("any", "default", 13),
        ]

    @pytest.mark.parametrize("int_str", ("-123", "10"))
    def test_int_str(self, guesser: TypeGuesser, int_str: str):
        assert list(guesser.cast(int_str)) == [
            ("integer", "default", 9),
            ("number", "default", 10),
            ("string", "default", 12),
            ("any", "default", 13),
        ]

    @pytest.mark.parametrize(
        "float_value",
        (10.1, 10.123123123123123123123123123123123123123123123123123123123),
    )
    def test_float(self, guesser: TypeGuesser, float_value: float):
        assert list(guesser.cast(float_value)) == [
            ("number", "default", 10),
            ("any", "default", 13),
        ]

    @pytest.mark.parametrize(
        "float_str",
        ("10.1", "15.04510682", "15.0451068212332312312231111111111111112222222222233333333333333"),
    )
    def test_float_str(self, guesser: TypeGuesser, float_str: str):
        assert list(guesser.cast(float_str)) == [
            ("number", "default", 10),
            ("string", "default", 12),
            ("any", "default", 13),
        ]

    @pytest.mark.parametrize("time", ("10:10", "23:59:59", "00:00:00", "00:00"))
    def test_time(self, guesser: TypeGuesser, time: str):
        assert list(guesser.cast(time)) == [
            ("time", "any", 6),
            ("string", "default", 12),
            ("any", "default", 13),
        ]

    @pytest.mark.parametrize("time_with_ms", ("00:00:00.00", "00:00:01.10"))
    def test_time_with_ms(self, guesser: TypeGuesser, time_with_ms: str):
        assert list(guesser.cast(time_with_ms)) == [
            ("time", "any", 6),
            ("datetime", "any", 8),
            ("string", "default", 12),
            ("any", "default", 13),
        ]

    @pytest.mark.parametrize(
        "date_value",
        (
            "11-02-2019",
            "11/02/2019",
            "11.02.2019",
            "2019-11-02",
            "2019/11/02",
            "2019.11.02",
        ),
    )
    def test_date(self, guesser: TypeGuesser, date_value: str):
        assert list(guesser.cast(date_value)) == [
            ("date", "any", 7),
            ("string", "default", 12),
            ("any", "default", 13),
        ]

    @pytest.mark.parametrize(
        "datetime_str",
        (
            # yyyy-MM-dd HH:mm
            "2019-11-02 11:12",
            "2019-11-02 00:00",
            # yyyy-MM-dd HH:mm:ss
            "2019-11-02 11:12:12",
            "2019-11-02 00:00:00",
            # yyyy-MM-dd HH:mm:ss.SSSSSS
            "2019-11-02 11:12:12.123",
            "2019-11-02 11:12:12.123456",
            "2019-11-02 00:00:00.000000",
            # yyyy-MM-dd'T'HH:mm:ss.SSSSSS
            "2019-11-02T11:12:12.123",
            "2019-11-02T00:00:00.000",
            # yyyy/MM/dd HH:mm
            "2019/11/02 11:12",
            "2019/11/02 00:00",
            # yyyy/MM/dd HH:mm:ss
            "2019/11/02 11:12:12",
            "2019/11/02 00:00:00",
            # yyyy/MM/dd HH:mm:ss.SSSSSS
            "2019/11/02 11:12:12.123",
            "2019/11/02 11:12:12.123456",
            "2019/11/02 00:00:00.000000",
            # yyyy/MM/dd'T'HH:mm:ss.SSSSSS
            "2019/11/02T11:12:12.123",
            "2019/11/02T00:00:00.000",
            # yyyy.MM.dd HH:mm
            "2019.11.02 11:12",
            "2019.11.02 00:00",
            # yyyy.MM.dd HH:mm:ss
            "2019.11.02 11:12:12",
            "2019.11.02 00:00:00",
            # yyyy.MM.dd HH:mm:ss.SSSSSS
            "2019.11.02 11:12:12.123",
            "2019.11.02 11:12:12.123456",
            "2019.11.02 00:00:00.000000",
            # yyyy.MM.dd'T'HH:mm:ss.SSSSSS
            "2019.11.02T11:12:12.123",
            "2019.11.02T00:00:00.000",
        ),
    )
    def test_datetime(self, guesser: TypeGuesser, datetime_str: str):
        assert list(guesser.cast(datetime_str)) == [
            ("datetime", "any", 8),
            ("string", "default", 12),
            ("any", "default", 13),
        ]

    @pytest.mark.parametrize(
        "string_value",
        (
            "2019.30.02 11:12",
            "66:12",
            "123a",
            "12.123123123123:1",
            "100 000 000",
            "100 000 000.10",
        ),
    )
    def test_string(self, guesser: TypeGuesser, string_value: str):
        assert list(guesser.cast(string_value)) == [
            ("string", "default", 12),
            ("any", "default", 13),
        ]
