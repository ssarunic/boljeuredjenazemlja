"""The client waits longer for the endpoints that return a whole record.

``/lr/lr-unit`` and ``/cad/parcel-info`` are assembled by the server on every
request, unpaged; a large condominium takes it 20 s or more before the first
byte. Those two calls get ``long_timeout`` as their read timeout while
connecting, and every other endpoint, keeps ``timeout``.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType

FIXTURES = Path(__file__).resolve().parents[2] / "src" / "cadastral_api" / "tests" / "fixtures"


def _client(handler, **kwargs) -> tuple[CadastralAPIClient, list[httpx.Request]]:
    """A client on a MockTransport that records every request it sends."""
    seen: list[httpx.Request] = []

    def recording(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return handler(request)

    client = CadastralAPIClient(base_url="http://mock", rate_limit=0, **kwargs)
    client.client = httpx.Client(
        base_url="http://mock", transport=httpx.MockTransport(recording)
    )
    return client, seen


def _timeout_of(request: httpx.Request) -> httpx.Timeout:
    return httpx.Timeout(**request.extensions["timeout"])


_FIXTURE_FOR_PATH = {
    "/lr/lr-unit": "lr_unit_lrparcels.json",
    "/cad/parcel-info": "parcel_info_direct.json",
    "/search-cad-parcels/offices": "offices.json",
}


def _serve_fixtures(request: httpx.Request) -> httpx.Response:
    name = _FIXTURE_FOR_PATH[request.url.path]
    return httpx.Response(200, json=json.loads((FIXTURES / name).read_text()))


def test_default_long_timeout_is_the_class_constant() -> None:
    client = CadastralAPIClient(base_url="http://mock", timeout=10.0)
    assert client.long_timeout == CadastralAPIClient.LONG_READ_TIMEOUT == 120.0


def test_a_larger_base_timeout_wins_and_long_timeout_can_be_set() -> None:
    assert CadastralAPIClient(base_url="http://mock", timeout=300.0).long_timeout == 300.0
    assert CadastralAPIClient(base_url="http://mock", long_timeout=45.0).long_timeout == 45.0


def test_heavy_endpoints_read_with_the_long_timeout_and_connect_with_the_base() -> None:
    client, seen = _client(_serve_fixtures, timeout=10.0)
    client.get_lr_unit_detailed("449", 21277)
    client.get_parcel_info("6564741")
    assert [r.url.path for r in seen] == ["/lr/lr-unit", "/cad/parcel-info"]
    for request in seen:
        timeout = _timeout_of(request)
        assert timeout.read == 120.0
        assert timeout.connect == 10.0


def test_other_endpoints_keep_the_base_timeout() -> None:
    client, seen = _client(_serve_fixtures, timeout=10.0)
    client.list_cadastral_offices()
    timeout = _timeout_of(seen[0])
    assert timeout.read == 10.0 and timeout.connect == 10.0


def test_a_timeout_error_names_the_timeout_that_applied() -> None:
    def slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    client, _ = _client(slow, timeout=10.0, long_timeout=90.0)
    with pytest.raises(CadastralAPIError) as excinfo:
        client.get_lr_unit_detailed("8974", 34097)
    assert excinfo.value.error_type == ErrorType.TIMEOUT
    assert excinfo.value.details["timeout_seconds"] == 90.0
    with pytest.raises(CadastralAPIError) as excinfo:
        client.list_cadastral_offices()
    assert excinfo.value.details["timeout_seconds"] == 10.0
