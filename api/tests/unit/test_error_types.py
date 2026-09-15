"""A refusal is access denied, any other 4xx keeps its status code.

401 and 403 used to fall through ``raise_for_status`` into the generic
transport branch and reach the caller as ``connection``, indistinguishable
from a network failure; an agent could read a refusal as an empty parcel.
"""

from __future__ import annotations

import httpx
import pytest

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType


def _client(status: int, body: bytes = b"denied") -> CadastralAPIClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, content=body, request=request)

    client = CadastralAPIClient(base_url="http://mock", rate_limit=0)
    client.client = httpx.Client(base_url="http://mock", transport=httpx.MockTransport(handler))
    return client


@pytest.mark.parametrize("status", [401, 403])
def test_401_and_403_are_access_denied(status: int) -> None:
    with pytest.raises(CadastralAPIError) as excinfo:
        _client(status).list_cadastral_offices()
    error = excinfo.value
    assert error.error_type is ErrorType.ACCESS_DENIED
    assert error.details["status_code"] == status
    assert error.details["endpoint"] == "/search-cad-parcels/offices"
    assert str(error).startswith("access_denied")


def test_other_4xx_keep_the_status_code_and_body() -> None:
    with pytest.raises(CadastralAPIError) as excinfo:
        _client(404, b"no such route").list_cadastral_offices()
    error = excinfo.value
    assert error.error_type is ErrorType.HTTP_ERROR
    assert error.details["status_code"] == 404
    assert error.details["response_text"] == "no such route"


def test_a_transport_failure_is_still_a_connection_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    client = CadastralAPIClient(base_url="http://mock", rate_limit=0)
    client.client = httpx.Client(base_url="http://mock", transport=httpx.MockTransport(handler))
    with pytest.raises(CadastralAPIError) as excinfo:
        client.list_cadastral_offices()
    assert excinfo.value.error_type is ErrorType.CONNECTION
