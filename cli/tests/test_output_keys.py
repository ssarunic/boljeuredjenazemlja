"""Localized JSON field names and CSV column names (cadastral_cli.output_keys).

- Croatian key spellings are ASCII snake_case and unique.
- Keys round-trip: a file written in one language is read back in any.
- The input parsers accept Croatian column names and keys.
- End to end against the mock server: no English key is left in Croatian
  JSON or CSV output, and English output is unchanged.

Run:
    cd cli && pytest tests/test_output_keys.py
"""

from __future__ import annotations

import csv
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from cadastral_api.i18n import set_language

from cadastral_cli import output_keys

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = REPO_ROOT / "docs" / "en" / "cli" / "examples"
_spec = importlib.util.spec_from_file_location(
    "build_docs", REPO_ROOT / "scripts" / "build_docs.py"
)
assert _spec is not None and _spec.loader is not None
build_docs = importlib.util.module_from_spec(_spec)
sys.modules["build_docs"] = build_docs
_spec.loader.exec_module(build_docs)

SNAKE_RE = re.compile(r"^[a-z][a-z0-9_]*$")

# Commands whose structured output is checked end to end.
JSON_COMMANDS = [
    "search 103/2 -m SAVAR",
    "search-municipality SAVAR",
    "get-parcel 103/2 -m SAVAR --show-owners --detail full",
    "get-lr-unit -u 449 -b 21277 --all --plombe-detail",
    "batch-fetch 103/2,45,999 -m SAVAR --detail full --show-owners",
    "batch-lr-unit --input lr_units.csv --show-owners",
    "get-geometry 103/2 -m SAVAR",
    "list-offices",
    "list-municipalities --office 114",
]
CSV_COMMANDS = [
    "search 103/2 -m SAVAR",
    "get-geometry 103/2 -m SAVAR",
    "list-offices",
]


@pytest.fixture(autouse=True)
def restore_language():
    yield
    set_language("hr")


def _hr(key: str, parent: str | None = None) -> str:
    set_language("hr")
    return output_keys.key_display(key, parent)


def test_croatian_key_spellings_are_ascii_snake_case_and_unique() -> None:
    seen: dict[str, str] = {}
    entries = [(k, None) for k in output_keys.KEYS] + [
        (k, p) for (p, k) in output_keys.KEY_OVERRIDES
    ]
    for key, parent in entries:
        spelling = _hr(key, parent)
        assert SNAKE_RE.match(spelling), f"{key}: '{spelling}' is not ASCII snake_case"
        assert spelling not in seen or seen[spelling] == key, (
            f"'{spelling}' is used for both {seen[spelling]} and {key}"
        )
        seen[spelling] = key


def test_keys_round_trip() -> None:
    sample = {
        "parcel_number": "103/2",
        "land_use": {"MASLINJAK": {"area": 1200}},
        "ownership": [{"sheet_number": 4, "possessors": [{"name": "X", "ownership": "1/2"}]}],
        "results": [{"lr_unit_number": "657", "main_book_id": 21277, "status": "success"}],
    }
    set_language("hr")
    localized = output_keys.localize_keys(sample)
    assert "broj_cestice" in localized and "MASLINJAK" in localized["nacin_uporabe"]
    assert localized["posjedovni_listovi"][0]["posjednici"][0]["posjedovni_udio"] == "1/2"
    assert output_keys.canonical_keys(localized) == sample
    set_language("en")
    assert output_keys.localize_keys(sample) == sample


def test_input_parsers_accept_croatian_names(tmp_path: Path) -> None:
    from cadastral_cli.commands.batch_lr_unit import _parse_lr_unit_csv, _parse_lr_unit_json
    from cadastral_cli.input_parsers import parse_csv_file, parse_json_file

    csv_file = tmp_path / "cestice.csv"
    csv_file.write_text("broj_cestice,opcina\n103/2,SAVAR\n45,\n", encoding="utf-8")
    parcels = parse_csv_file(csv_file)
    assert [(p.parcel_number, p.municipality) for p in parcels] == [
        ("103/2", "SAVAR"),
        ("45", "SAVAR"),
    ]

    json_file = tmp_path / "cestice.json"
    json_file.write_text(
        json.dumps([{"broj_cestice": "103/2", "opcina": "334979"}]), encoding="utf-8"
    )
    assert parse_json_file(json_file)[0].municipality == "334979"

    lr_csv = tmp_path / "ulosci.csv"
    lr_csv.write_text("broj_zk_uloska,id_glavne_knjige\n657,21277\n", encoding="utf-8")
    assert _parse_lr_unit_csv(lr_csv)[0].main_book_id == 21277
    lr_json = tmp_path / "ulosci.json"
    lr_json.write_text(
        json.dumps([{"broj_zk_uloska": "657", "id_glavne_knjige": 21277}]), encoding="utf-8"
    )
    assert _parse_lr_unit_json(lr_json)[0].lr_unit_number == "657"


# ---------------------------------------------------------------------------
# End to end
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def mock_server():
    with build_docs.MockServer() as server:
        yield server


def _run(server, lang: str, cmdline: str, fmt: str, tmp_path: Path) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CADASTRAL_")}
    env.update(
        {
            "CADASTRAL_API_BASE_URL": server.base_url,
            "CADASTRAL_API_RATE_LIMIT": "0",
            "HOME": str(tmp_path),
            "PYTHONIOENCODING": "utf-8",
        }
    )
    result = subprocess.run(
        [sys.executable, "-m", "cadastral_cli", "--lang", lang, *cmdline.split(), "--format", fmt],
        cwd=EXAMPLES,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.stdout


def _json_keys(text: str) -> list[tuple[str, str]]:
    """(parent, key) pairs of the first JSON document in ``text``."""
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    document, _ = json.JSONDecoder().raw_decode(text[min(starts) :])
    found: list[tuple[str, str]] = []

    def walk(node, parent: str | None, data_keyed: bool) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if not data_keyed:
                    found.append((parent or "", key))
                walk(value, key, key in output_keys.DATA_KEYED or _hr_data_keyed(key))
        elif isinstance(node, list):
            for item in node:
                walk(item, parent, data_keyed)

    walk(document, None, False)
    return found


def _hr_data_keyed(key: str) -> bool:
    return output_keys.canonical_key(key) in output_keys.DATA_KEYED


@pytest.mark.parametrize("cmdline", JSON_COMMANDS)
def test_croatian_json_has_no_english_keys(mock_server, cmdline: str, tmp_path: Path) -> None:
    english = {(p, k) for p, k in _json_keys(_run(mock_server, "en", cmdline, "json", tmp_path))}
    croatian = {(p, k) for p, k in _json_keys(_run(mock_server, "hr", cmdline, "json", tmp_path))}
    left = sorted(k for _, k in croatian if k in output_keys.KEYS and _hr(k) != k)
    assert not left, f"English keys in Croatian output of '{cmdline}': {left}"
    unknown = sorted(k for _, k in english if k not in output_keys.KEYS)
    assert not unknown, f"keys without an entry in output_keys.KEYS: {unknown}"


@pytest.mark.parametrize("cmdline", CSV_COMMANDS)
def test_croatian_csv_header_is_localized(mock_server, cmdline: str, tmp_path: Path) -> None:
    text = _run(mock_server, "hr", cmdline, "csv", tmp_path)
    header_line = next(line for line in text.splitlines() if "," in line)
    header = next(csv.reader(io.StringIO(header_line)))
    left = [h for h in header if h in output_keys.KEYS and _hr(h) != h]
    assert not left, f"English column names in Croatian CSV of '{cmdline}': {left}"


def test_batch_pipeline_round_trips_in_croatian(mock_server, tmp_path: Path) -> None:
    written = _run(mock_server, "hr", "batch-fetch 103/2,45 -m SAVAR", "json", tmp_path)
    starts = [i for i in (written.find("{"), written.find("[")) if i != -1]
    document, _ = json.JSONDecoder().raw_decode(written[min(starts) :])
    assert "rezultati" in document
    out = tmp_path / "pronadjene.json"
    out.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    text = _run(mock_server, "hr", f"batch-lr-unit --from-batch-output {out}", "json", tmp_path)
    assert "broj_zk_uloska" in text and '"657"' in text
