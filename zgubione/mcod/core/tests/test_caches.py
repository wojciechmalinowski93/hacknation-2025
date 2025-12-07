from __future__ import annotations

import json
import time
from typing import TYPE_CHECKING, Optional
from unittest.mock import Mock, patch

import pytest
from falcon.testing import create_req as create_falcon_request

from mcod.core.api.middlewares import FalconCacheMiddleware
from mcod.core.api.versions import VERSIONS
from mcod.core.caches import flush_sessions
from mcod.core.tests.fixtures.api_test_views import ApiTestView

if TYPE_CHECKING:
    from falcon.testing import Result, TestClient


@pytest.mark.parametrize(
    "prefix",
    ["test_key", " ", "_", "_test_key_", " test key", "", None],
)
def test_flush_sessions(prefix: Optional[str]):
    with patch("mcod.core.caches.caches") as mock_caches:
        session_cache = Mock()
        session_cache.key_prefix = prefix

        mock_caches.__getitem__.return_value = session_cache

        flush_sessions()

    mock_caches.__getitem__.assert_called_once_with("sessions")
    if prefix:
        session_cache.delete_pattern.assert_called_once_with(f"{prefix}*")
    else:
        session_cache.delete_pattern.assert_called_once_with("*")


@pytest.mark.usefixtures("api_with_routes_for_test")
@pytest.mark.parametrize("api_version", [ver.as_string for ver in VERSIONS])
def test_falcon_endpoint_cached(client: "TestClient", api_version: str):

    # First request
    resp_1: Result = client.simulate_get(f"/{api_version}/test_endpoint")
    assert resp_1.status_code == 200
    assert json.loads(resp_1.text) == {"message": f"OK from API version {api_version}"}
    assert ApiTestView.call_counter[api_version] == 1

    # Second request (before cache timeout)
    resp_2: Result = client.simulate_get(f"/{api_version}/test_endpoint")
    assert resp_2.status_code == 200
    assert json.loads(resp_2.text) == {"message": f"OK from API version {api_version}"}
    assert ApiTestView.call_counter[api_version] == 1, (
        f"call_counter should not be incremented by calling request."
        f" Expected value = 1 is {ApiTestView.call_counter[api_version]}"
    )

    # Third request (after cache timeout)
    time.sleep(2)
    resp_3: Result = client.simulate_get(f"/{api_version}/test_endpoint")
    assert resp_3.status_code == 200
    assert json.loads(resp_3.text) == {"message": f"OK from API version {api_version}"}
    assert ApiTestView.call_counter[api_version] == 2, (
        f"call_counter should be incremented by calling request."
        f"  Expected value = 2 is {ApiTestView.call_counter[api_version]}"
    )


class TestCacheKeyGeneration:
    @pytest.mark.parametrize(
        "query_string, expected_cache_key",
        [
            ("param1=abc&param2=def&lang=pl", "/api/some-endpoint:GET:param1=abc&param2=def&lang=pl:pl"),
            ("param1=abc&param2=def&lang=en", "/api/some-endpoint:GET:param1=abc&param2=def&lang=en:en"),
            ("lang=en&param2=def&param1=abc", "/api/some-endpoint:GET:lang=en&param2=def&param1=abc:en"),
            ("param1=abc&param2=def", "/api/some-endpoint:GET:param1=abc&param2=def:pl"),
            ("", "/api/some-endpoint:GET::pl"),
            ("lang=en", "/api/some-endpoint:GET:lang=en:en"),
        ],
    )
    def test_generate_cache_key(self, query_string: str, expected_cache_key: str):
        # GIVEN
        mock_request = create_falcon_request(
            method="GET",
            path="/api/some-endpoint",
            query_string=query_string,
        )
        # WHEN
        key: str = FalconCacheMiddleware.generate_cache_key(mock_request)
        # THEN
        assert key == expected_cache_key

    @pytest.mark.xfail(
        reason="the key generated for the cache is currently not sensitive to the order of parameters in the query string",
        run=True,
        strict=True,
    )
    def test_generate_cache_key_parameter_order_independent(self):
        # GIVEN
        param1 = "param1=abc"
        param2 = "param2=def"
        # GIVEN
        mock_request = create_falcon_request(
            method="GET",
            path="/api/some-endpoint",
            query_string=f"{param1}&{param2}",
        )
        # WHEN
        key_1: str = FalconCacheMiddleware.generate_cache_key(mock_request)

        # GIVEN
        mock_request = create_falcon_request(
            method="GET",
            path="/api/some-endpoint",
            query_string=f"{param2}&{param1}",
        )
        # WHEN
        key_2: str = FalconCacheMiddleware.generate_cache_key(mock_request)
        # THEN
        assert key_1 == key_2
