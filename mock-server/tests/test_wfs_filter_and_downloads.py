#!/usr/bin/env python3.12
"""Tests for the mock server's GIS download route and the WFS cql_filter parser.

The ATOM download must never build a file path from the request (the
municipality code is matched against the ZIP files that exist), and the
INTERSECTS clause must be recognised in every spelling the SDK sends without
the parser's cost growing faster than the filter's length.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# The mock server lives in mock-server/src and is imported as a top-level module.
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import main  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(main.app) as test_client:
        yield test_client


def test_download_serves_known_municipality(client: TestClient) -> None:
    resp = client.get("/atom/ko-334979.zip")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    assert 'filename="ko-334979.zip"' in resp.headers["content-disposition"]


def test_download_unknown_municipality_is_404(client: TestClient) -> None:
    resp = client.get("/atom/ko-999999.zip")
    assert resp.status_code == 404
    assert resp.json()["municipality"] == "999999"


@pytest.mark.parametrize(
    "code",
    ["..", "../../src/main.py", "334979/../334979", "%2e%2e%2f%2e%2e", "334979 ", "main"],
)
def test_download_rejects_anything_but_a_registration_number(client: TestClient, code: str) -> None:
    resp = client.get(f"/atom/ko-{code}.zip")
    assert resp.status_code == 404
    assert resp.headers["content-type"].startswith("application/json")


def _matches(filter_text: str) -> str | None:
    match = main._INTERSECTS_RE.search(filter_text)
    return match.group("wkt") if match else None


@pytest.mark.parametrize(
    "filter_text",
    [
        "INTERSECTS(geom, POLYGON((1 2, 3 4, 5 6, 1 2)))",
        "intersects ( geom , polygon (( 1 2 , 3 4 , 5 6 , 1 2 )) )",
        "INTERSECTS(geom,POLYGON((1 2,3 4,5 6,1 2),(2 2,2 3,3 3,2 2)))",
        "plan='GUP' AND INTERSECTS(geom, POLYGON((1 2, 3 4, 5 6, 1 2))) AND kind='x'",
    ],
)
def test_intersects_clause_is_recognised(filter_text: str) -> None:
    wkt = _matches(filter_text)
    assert wkt is not None
    assert wkt.upper().startswith("POLYGON")
    assert main._parse_wkt_polygon(wkt)[0] == (1.0, 2.0)


def test_intersects_regex_is_linear_on_hostile_input() -> None:
    hostile = "INTERSECTS(geom,POLYGON((" * 20_000
    started = time.perf_counter()
    assert _matches(hostile) is None
    assert time.perf_counter() - started < 1.0


def test_wfs_intersects_filter_selects_zones(client: TestClient) -> None:
    hits = client.get(
        "/planning/wfs",
        params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": main._WFS_TYPES[0],
            "outputFormat": "application/json",
            "resultType": "hits",
        },
    )
    assert hits.status_code == 200
    # A polygon far outside every fixture zone intersects nothing.
    resp = client.get(
        "/planning/wfs",
        params={
            "service": "WFS",
            "version": "2.0.0",
            "request": "GetFeature",
            "typeNames": main._WFS_TYPES[0],
            "outputFormat": "application/json",
            "cql_filter": "INTERSECTS(geom, POLYGON((0 0, 0 1, 1 1, 1 0, 0 0)))",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["features"] == []
