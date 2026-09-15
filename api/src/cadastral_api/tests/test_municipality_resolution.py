"""One municipality resolver for the SDK, the CLI and the MCP server.

``resolve_municipality_reg_num`` is the rule every caller shares: a number
passes through, an exact name wins, a single match is taken, and an
ambiguous name is refused with the candidates instead of silently picking
the first (``LUKA`` names 16 municipalities on the live server).
"""

import httpx
import pytest

from cadastral_api.client.api_client import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType


def _record(code: str, name: str) -> dict:
    return {"key1": "1", "value1": f"{code} {name}", "key2": code, "value2": "114",
            "value3": "116", "displayValue1": f"{code} {name}, ZADAR"}


def _client(records: list[dict]) -> tuple[CadastralAPIClient, list[httpx.Request]]:
    """A client whose server answers every municipality search with ``records``."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=records)

    client = CadastralAPIClient(base_url="http://mock", rate_limit=0)
    client.client = httpx.Client(base_url="http://mock", transport=httpx.MockTransport(handler))
    return client, requests


def test_a_number_passes_through_without_a_request() -> None:
    client, requests = _client([])
    assert client.resolve_municipality_reg_num("334979") == "334979"
    assert client.resolve_municipality_reg_num(334979) == "334979"
    assert requests == []


def test_the_exact_name_wins_over_longer_matches() -> None:
    client, requests = _client([_record("334731", "LUKA"), _record("335000", "LUKAVAC")])
    assert client.resolve_municipality_reg_num("luka") == "334731"
    assert len(requests) == 1 and requests[0].url.params["search"] == "luka"


def test_a_single_partial_match_is_taken() -> None:
    client, _requests = _client([_record("334979", "SAVAR")])
    assert client.resolve_municipality_reg_num("SAV") == "334979"


def test_several_matches_and_no_exact_name_are_refused_with_candidates() -> None:
    client, _requests = _client([_record("334731", "LUKA"), _record("335000", "LUKAVAC")])
    with pytest.raises(CadastralAPIError) as excinfo:
        client.resolve_municipality_reg_num("LUK")
    error = excinfo.value
    assert error.error_type == ErrorType.MUNICIPALITY_NOT_FOUND
    assert error.details["reason"] == "municipality_ambiguous"
    assert error.details["candidates"] == "334731 LUKA, 335000 LUKAVAC"


def test_two_municipalities_of_the_same_name_are_ambiguous() -> None:
    client, _requests = _client(
        [_record("1", "LUKA"), _record("2", "LUKA"), _record("3", "LUKAVAC")]
    )
    with pytest.raises(CadastralAPIError) as excinfo:
        client.resolve_municipality_reg_num("LUKA")
    assert excinfo.value.details["candidates"] == "1 LUKA, 2 LUKA"


def test_an_empty_answer_is_not_found_with_a_reason() -> None:
    # The server answers an unknown name with an empty list, which
    # find_municipality already turns into MUNICIPALITY_NOT_FOUND; the
    # resolver adds the reason so that callers see one contract.
    client, _requests = _client([])
    with pytest.raises(CadastralAPIError) as excinfo:
        client.resolve_municipality_reg_num("NOWHERE")
    assert excinfo.value.error_type == ErrorType.MUNICIPALITY_NOT_FOUND
    assert excinfo.value.details == {"search_term": "NOWHERE", "reason": "municipality_not_found"}
    assert isinstance(excinfo.value.__cause__, CadastralAPIError)
