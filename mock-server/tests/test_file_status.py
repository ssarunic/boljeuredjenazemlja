#!/usr/bin/env python3.12
"""Tests for the mock server's POST /lr/file-status route.

Verifies the production-shaped contract the client relies on: the endpoint
takes the file number split into parts plus an institution, validates the
required parts (400), and answers unknown files with an empty object.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# The mock server lives in mock-server/src and is imported as a top-level module.
SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SRC))

import main  # noqa: E402


@pytest.fixture(scope="module")
def client() -> TestClient:
    # `with` triggers the startup event that loads the JSON fixtures.
    with TestClient(main.app) as test_client:
        yield test_client


def test_resolves_known_pending_file(client: TestClient) -> None:
    resp = client.post(
        "/lr/file-status",
        json={"lrFileCode": "Z", "lrFileOrderNumber": 18444, "lrFileYear": 2026, "institutionId": 284},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["lrFileNumber"] == "Z-18444/2026"
    assert body["applicationContent"] == "Uknjižba prava vlasništva"
    assert "executionDate" not in body  # still pending


def test_resolves_known_resolved_file(client: TestClient) -> None:
    resp = client.post(
        "/lr/file-status",
        json={"lrFileCode": "Z", "lrFileOrderNumber": 15677, "lrFileYear": 2026, "institutionId": 284},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["resolutionTypeName"] == "Udovoljeno"
    assert body["executionDate"].startswith("2026-05-18")


def test_unknown_file_returns_empty_object(client: TestClient) -> None:
    resp = client.post(
        "/lr/file-status",
        json={"lrFileCode": "Z", "lrFileOrderNumber": 99999, "lrFileYear": 2026, "institutionId": 284},
    )
    assert resp.status_code == 200
    assert resp.json() == {}


def test_missing_institution_returns_empty_object(client: TestClient) -> None:
    # File parts are valid but no institution context -> no match, as in production.
    resp = client.post(
        "/lr/file-status",
        json={"lrFileCode": "Z", "lrFileOrderNumber": 18444, "lrFileYear": 2026},
    )
    assert resp.status_code == 200
    assert resp.json() == {}


def test_missing_required_parts_is_400(client: TestClient) -> None:
    resp = client.post("/lr/file-status", json={"institutionId": 284})
    assert resp.status_code == 400
    body = resp.json()
    assert body["statusCode"] == 400
    # all three required parts reported missing
    joined = " ".join(body["errors"])
    for field in ("lrFileCode", "lrFileOrderNumber", "lrFileYear"):
        assert field in joined
