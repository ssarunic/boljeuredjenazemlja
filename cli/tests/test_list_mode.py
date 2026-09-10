"""One item or a list: ``get-parcel`` and ``get-lr-unit`` against the mock server.

- A single parcel number gives the single-item document and fails fast.
- A comma list, several arguments or ``--input`` give the list document
  (``summary`` + ``results``), exit code 1 when any item failed, and each
  successful result carries the single-item record under ``full_data``
  (except with ``--detail registry``).
- ``get-lr-unit --input`` reads a CSV of units, a JSON array, or the JSON a
  ``get-parcel`` list wrote, once per distinct unit.
- ``--stop-on-error`` aborts at the first failure.

Run:
    cd cli && pytest tests/test_list_mode.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "docs" / "en" / "cli" / "examples"
_spec = importlib.util.spec_from_file_location(
    "build_docs", REPO_ROOT / "scripts" / "build_docs.py"
)
assert _spec is not None and _spec.loader is not None
build_docs = importlib.util.module_from_spec(_spec)
sys.modules["build_docs"] = build_docs
_spec.loader.exec_module(build_docs)


@pytest.fixture(scope="module")
def mock_server():
    with build_docs.MockServer() as server:
        yield server


def _run(
    server, args: list[str], tmp_path: Path, cwd: Path = EXAMPLES
) -> subprocess.CompletedProcess[str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CADASTRAL_")}
    env.update(
        {
            "CADASTRAL_API_BASE_URL": server.base_url,
            "CADASTRAL_API_RATE_LIMIT": "0",
            "HOME": str(tmp_path),
            "PYTHONIOENCODING": "utf-8",
            "NO_COLOR": "1",
            "TERM": "dumb",
        }
    )
    return subprocess.run(
        [sys.executable, "-m", "cadastral_cli", "--lang", "en", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


def _json(text: str):
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    document, _ = json.JSONDecoder().raw_decode(text[min(starts) :])
    return document


def test_single_parcel_is_a_single_document(mock_server, tmp_path: Path) -> None:
    result = _run(mock_server, ["get-parcel", "103/2", "-m", "SAVAR", "--format", "json"], tmp_path)
    assert result.returncode == 0, result.stderr
    document = _json(result.stdout)
    assert document["parcel_number"] == "103/2"
    assert "results" not in document


def test_single_missing_parcel_fails_fast(mock_server, tmp_path: Path) -> None:
    result = _run(mock_server, ["get-parcel", "999", "-m", "SAVAR"], tmp_path)
    assert result.returncode == 1
    assert "not found" in result.stdout + result.stderr


def test_comma_list_gives_results_with_full_data(mock_server, tmp_path: Path) -> None:
    result = _run(
        mock_server, ["get-parcel", "103/2,45", "-m", "SAVAR", "--format", "json"], tmp_path
    )
    assert result.returncode == 0, result.stderr
    document = _json(result.stdout)
    assert document["summary"] == {
        "total": 2,
        "successful": 2,
        "failed": 0,
        "success_rate": "100.0%",
    }
    numbers = [row["parcel_number"] for row in document["results"]]
    assert numbers == ["103/2", "45"]
    first = document["results"][0]
    assert first["status"] == "success"
    assert first["lr_unit_number"] == "657" and first["main_book_id"] == 21277
    # The single-item record travels with each result (default detail is full).
    assert first["full_data"]["parcel_number"] == "103/2"
    assert "land_use" in first["full_data"] and "land_registry" in first["full_data"]


def test_separate_arguments_are_a_list_too(mock_server, tmp_path: Path) -> None:
    result = _run(
        mock_server,
        ["get-parcel", "103/2", "45", "-m", "SAVAR", "--detail", "registry", "--format", "json"],
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    document = _json(result.stdout)
    assert len(document["results"]) == 2
    assert all("full_data" not in row for row in document["results"])  # registry mode


def test_failed_item_is_recorded_and_exit_code_is_one(mock_server, tmp_path: Path) -> None:
    result = _run(
        mock_server,
        ["get-parcel", "103/2,999", "-m", "SAVAR", "--detail", "registry", "--format", "json"],
        tmp_path,
    )
    assert result.returncode == 1
    document = _json(result.stdout)
    assert document["summary"]["successful"] == 1 and document["summary"]["failed"] == 1
    failed = document["results"][1]
    assert failed["status"] == "error"
    assert failed["error_type"] == "parcel_not_found"
    assert failed["parcel_number"] == "999"


def test_stop_on_error_aborts(mock_server, tmp_path: Path) -> None:
    result = _run(
        mock_server,
        ["get-parcel", "999,103/2", "-m", "SAVAR", "--detail", "registry", "--stop-on-error"],
        tmp_path,
    )
    assert result.returncode == 1
    assert "RESULTS" not in result.stdout
    assert "API error" in result.stdout


def test_registry_table_lists_units(mock_server, tmp_path: Path) -> None:
    args = ["get-parcel", "103/2,45,396/1", "-m", "SAVAR", "--detail", "registry"]
    result = _run(mock_server, args, tmp_path)
    assert result.returncode == 0, result.stderr
    assert "RESULTS" in result.stdout
    assert "657" in result.stdout and "138" in result.stdout and "645" in result.stdout
    # Progress is on stderr, the table on stdout.
    assert "Processing" not in result.stdout


def test_list_from_csv_file(mock_server, tmp_path: Path) -> None:
    result = _run(
        mock_server,
        ["get-parcel", "--input", "parcels.csv", "--detail", "registry", "--format", "json"],
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    document = _json(result.stdout)
    assert [row["parcel_number"] for row in document["results"]] == ["103/2", "45", "396/1"]


def test_list_csv_output_has_one_header_for_mixed_rows(mock_server, tmp_path: Path) -> None:
    result = _run(
        mock_server,
        ["get-parcel", "103/2,999", "-m", "SAVAR", "--format", "csv", "--show-owners"],
        tmp_path,
    )
    lines = [line for line in result.stdout.splitlines() if "," in line]
    header = lines[0].split(",")
    assert "possessors" in header and "error_type" in header
    assert len(lines) == 3


def test_argument_validation(mock_server, tmp_path: Path) -> None:
    no_parcels = _run(mock_server, ["get-parcel", "-m", "SAVAR"], tmp_path)
    assert no_parcels.returncode == 1 and "--input" in no_parcels.stdout
    no_municipality = _run(mock_server, ["get-parcel", "103/2,45"], tmp_path)
    assert no_municipality.returncode == 1 and "--municipality" in no_municipality.stdout
    both = _run(
        mock_server, ["get-parcel", "103/2", "--input", "parcels.csv", "-m", "SAVAR"], tmp_path
    )
    assert both.returncode == 1 and "Cannot use both" in both.stdout


def test_lr_units_from_csv(mock_server, tmp_path: Path) -> None:
    result = _run(
        mock_server,
        ["get-lr-unit", "--input", "lr_units.csv", "--show-owners", "--format", "json"],
        tmp_path,
    )
    assert result.returncode == 0, result.stderr
    document = _json(result.stdout)
    assert [row["lr_unit_number"] for row in document["results"]] == ["657", "769", "449"]
    first = document["results"][0]
    assert first["num_owners"] == 2
    assert len(first["full_data"]["owners"]) == 2


def test_lr_units_without_sheets_have_no_full_data(mock_server, tmp_path: Path) -> None:
    result = _run(
        mock_server, ["get-lr-unit", "--input", "lr_units.csv", "--format", "json"], tmp_path
    )
    assert result.returncode == 0, result.stderr
    assert all("full_data" not in row for row in _json(result.stdout)["results"])


def test_lr_units_from_get_parcel_output_are_deduplicated(mock_server, tmp_path: Path) -> None:
    found = tmp_path / "found.json"
    listed = _run(
        mock_server,
        [
            "get-parcel", "103/2,279/6,1122/1,103/2", "-m", "SAVAR",
            "--detail", "registry", "--format", "json", "--output", str(found),
        ],
        tmp_path,
    )
    assert listed.returncode == 0, listed.stderr
    result = _run(
        mock_server, ["get-lr-unit", "--input", str(found), "--all", "--format", "json"], tmp_path
    )
    assert result.returncode == 0, result.stderr
    document = _json(result.stdout)
    assert [row["lr_unit_number"] for row in document["results"]] == ["657", "769", "449"]
    assert "encumbrances" in document["results"][0]["full_data"]


def test_lr_unit_input_excludes_the_single_item_options(mock_server, tmp_path: Path) -> None:
    result = _run(
        mock_server, ["get-lr-unit", "--input", "lr_units.csv", "--unit-number", "769"], tmp_path
    )
    assert result.returncode == 1 and "Cannot combine --input" in result.stdout


def test_missing_lr_unit_in_list_is_reported(mock_server, tmp_path: Path) -> None:
    units = tmp_path / "units.csv"
    units.write_text("lr_unit_number,main_book_id\n657,21277\n999999,21277\n", encoding="utf-8")
    result = _run(
        mock_server, ["get-lr-unit", "--input", str(units), "--format", "json"], tmp_path
    )
    assert result.returncode == 1
    document = _json(result.stdout)
    assert document["summary"]["failed"] == 1
    assert document["results"][1]["status"] == "error"
