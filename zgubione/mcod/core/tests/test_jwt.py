import json
from calendar import timegm
from datetime import datetime, timedelta

import falcon
import pytest

from mcod.lib.jwt import DateTimeToISOEncoder, decode_jwt_token, parse_auth_token


@pytest.fixture(scope="module")
def now():
    return datetime(2018, 3, 1, 0, 1, 0, 0)


@pytest.fixture(scope="module")
def valid_header():
    return (
        "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyIjp7InNlc3Npb25f"
        "a2V5IjoiMSIsImVtYWlsIjoiYSIsInJvbGUiOiJ1c2VyIn0sImlhdCI6MTUxOTg2MjQ2"
        "MCwibmJmIjoxNTE5ODYyNDYwLCJleHAiOjE4MzUyMjI0NjB9.2fYmOkgXgvy-G1xENejWaI27Ix_J8CPORaM0vHrHLCU"
    )


class TestJWT:
    @pytest.mark.run(order=1)
    def test_jwt_json_encoder(self, now):
        result = json.dumps({"abcd": 1234}, cls=DateTimeToISOEncoder)
        assert result == '{"abcd": 1234}'

        result = json.dumps({"date": now}, cls=DateTimeToISOEncoder)
        assert result == '{"date": "2018-03-01T00:01:00"}'
        assert json.loads(result)["date"] == "2018-03-01T00:01:00"

    @pytest.mark.run(order=1)
    def test_parse_auth_header(self):
        with pytest.raises(falcon.HTTPUnauthorized):
            parse_auth_token(None)

        with pytest.raises(falcon.HTTPUnauthorized):
            parse_auth_token("BBB ccc")

        with pytest.raises(falcon.HTTPUnauthorized):
            parse_auth_token("Bearer")

        with pytest.raises(falcon.HTTPUnauthorized):
            parse_auth_token("Bearer abc def")

        result = parse_auth_token("Bearer abcdef")
        assert result == "abcdef"

    @pytest.mark.run(order=1)
    def test_decode_token(self, now, valid_header, token_exp_delta):
        now_ts = timegm(now.utctimetuple())
        exp_ts = timegm((now + timedelta(seconds=token_exp_delta)).utctimetuple())

        payload = decode_jwt_token(valid_header)

        assert payload["iat"] == now_ts
        assert payload["nbf"] == now_ts
        assert payload["exp"] == exp_ts
        assert payload["user"]["session_key"] == "1"
        assert payload["user"]["role"] == "user"
        assert payload["user"]["email"] == "a"
