#!/usr/bin/env python3.12
"""Tests for land-registry file (plomba / spis) status parsing, model, and client.

Covers the ``--plombe-detail`` / ``include_plombe_detail`` feature stack:
- ``parse_file_number`` splitting a rendered number into its parts,
- the ``FileStatus`` model (date coercion, resolution, institution flattening),
- the client's ``get_file_status`` / ``get_plombe_details`` against a mocked
  transport (no network), including the POST body it sends and the
  empty-response -> ``None`` behaviour.
"""

from __future__ import annotations

import json

import httpx
import pytest

from cadastral_api import CadastralAPIClient
from cadastral_api.models.entities import FileStatus, LandRegistryUnitDetailed
from cadastral_api.utils import parse_file_number

# --- parse_file_number -------------------------------------------------------

class TestParseFileNumber:
    def test_parses_standard_number(self) -> None:
        assert parse_file_number("Z-12564/2026") == ("Z", 12564, 2026)

    def test_tolerates_surrounding_whitespace(self) -> None:
        assert parse_file_number("  Z-18444/2026 ") == ("Z", 18444, 2026)

    def test_multiletter_code(self) -> None:
        assert parse_file_number("Zs-5/2001") == ("Zs", 5, 2001)

    @pytest.mark.parametrize("bad", ["", None, "bad", "Z12564/2026", "12564/2026", "Z-12564-2026"])
    def test_rejects_unparseable(self, bad: str | None) -> None:
        assert parse_file_number(bad) is None


# --- FileStatus model --------------------------------------------------------

RESOLVED = {
    "fileId": 45835794,
    "lrFileNumber": "Z-15677/2026",
    "institution": {"institutionId": 284, "institutionName": "ZK Zadar"},
    "resolutionTypeName": "Udovoljeno",
    "statusDescription": "OTPREMA",
    "applicationContent": "Uknjižba prava vlasništva temeljem Ugovor o darovanju",
    "receivingDate": "2026-05-14T13:51:39.000+02:00",
    "solvingDate": "2026-05-18",
    "executionDate": "2026-05-18T13:00:11.000+02:00",
}

PENDING = {
    "lrFileNumber": "Z-18444/2026",
    "statusDescription": "IZRADA NACRTA RJEŠENJA",
    "applicationContent": "Uknjižba prava vlasništva",
    "receivingDate": "2026-06-09T09:48:21.000+02:00",
}


class TestFileStatusModel:
    def test_resolved_file(self) -> None:
        fs = FileStatus.model_validate(RESOLVED)
        assert fs.lr_file_number == "Z-15677/2026"
        assert fs.is_resolved is True
        assert fs.institution_id == 284
        # date-only solvingDate coerces to a midnight datetime
        assert fs.solving_date is not None and fs.solving_date.day == 18

    def test_pending_file(self) -> None:
        fs = FileStatus.model_validate(PENDING)
        assert fs.is_resolved is False
        assert fs.execution_date is None
        # no nested institution -> institution_id is None, not an error
        assert fs.institution_id is None
        assert fs.application_content == "Uknjižba prava vlasništva"


# --- client get_file_status / get_plombe_details -----------------------------

def _mock_client(handler: object) -> CadastralAPIClient:
    """Build a client whose HTTP layer is backed by a MockTransport (no network)."""
    client = CadastralAPIClient(base_url="http://mock.test")
    client.rate_limit = 0.0  # don't sleep in tests
    client.client = httpx.Client(
        base_url="http://mock.test",
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
    )
    return client


class TestGetFileStatus:
    def test_posts_split_number_and_returns_status(self) -> None:
        seen: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            assert request.method == "POST"
            assert request.url.path == "/lr/file-status"
            seen["body"] = json.loads(request.content)
            return httpx.Response(200, json=RESOLVED)

        client = _mock_client(handler)
        fs = client.get_file_status("Z-15677/2026", 284)

        assert seen["body"] == {
            "lrFileCode": "Z",
            "lrFileOrderNumber": 15677,
            "lrFileYear": 2026,
            "institutionId": 284,
        }
        assert isinstance(fs, FileStatus)
        assert fs.resolution_type_name == "Udovoljeno"

    def test_empty_object_means_none(self) -> None:
        client = _mock_client(lambda request: httpx.Response(200, json={}))
        assert client.get_file_status("Z-1/2026", 284) is None

    def test_unparseable_number_skips_request(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover
            raise AssertionError("must not call the endpoint for an unparseable number")

        client = _mock_client(handler)
        assert client.get_file_status("not-a-number", 284) is None


def _unit_with_plombe() -> LandRegistryUnitDetailed:
    return LandRegistryUnitDetailed.model_validate({
        "lrUnitId": 1,
        "lrUnitNumber": "449",
        "mainBookId": 21277,
        "mainBookName": "TEST",
        "cadastreMunicipalityId": 2387,
        "institutionId": 284,
        "institutionName": "ZK Zadar",
        "status": "0",
        "statusName": "Aktivan",
        "verificated": False,
        "condominiums": False,
        "lrUnitTypeId": 1,
        "lrUnitTypeName": "VLASNIČKI",
        "lastDiaryNumber": "Z-15677/2026",
        "activePlumbs": [
            {"cadPlumb": False, "fileNumber": "Z-12564/2026"},
            {"cadPlumb": True, "fileNumber": "Z-99999/2026"},   # cadastre -> skipped
            {"cadPlumb": False, "fileNumber": "Z-18444/2026"},
        ],
        "ownershipSheetB": {"lrUnitShares": [], "lrEntries": []},
        "possessionSheetA1": {"lrParcels": []},
        "possessionSheetA2": {"lrEntries": []},
        "encumbranceSheetC": {"lrEntryGroups": []},
    })


class TestGetPlombeDetails:
    def test_skips_cadastre_and_maps_by_file_number(self) -> None:
        calls: list[dict[str, object]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            calls.append(body)
            # institution always carried from the unit
            assert body["institutionId"] == 284
            number = f"{body['lrFileCode']}-{body['lrFileOrderNumber']}/{body['lrFileYear']}"
            return httpx.Response(200, json={**PENDING, "lrFileNumber": number})

        client = _mock_client(handler)
        details = client.get_plombe_details(_unit_with_plombe())

        # cadastre plomba Z-99999 is never requested
        requested = {f"{c['lrFileCode']}-{c['lrFileOrderNumber']}/{c['lrFileYear']}" for c in calls}
        assert requested == {"Z-12564/2026", "Z-18444/2026"}
        assert set(details) == {"Z-12564/2026", "Z-18444/2026"}
        assert all(isinstance(v, FileStatus) for v in details.values())

    def test_unresolved_files_are_omitted(self) -> None:
        # endpoint returns {} for every file -> nothing resolves
        client = _mock_client(lambda request: httpx.Response(200, json={}))
        assert client.get_plombe_details(_unit_with_plombe()) == {}
