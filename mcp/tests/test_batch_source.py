"""Tests for batch_fetch_parcels register selection (Phase 1).

The MCP package __init__ imports the MCP SDK (FastMCP), which need not be
installed to exercise the pure handler logic. tools.py only depends on
cadastral_api, so we load it as a standalone module and drive it with a fake
client backed by a real (redacted) parcel-info fixture.
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api.models.entities import ParcelInfo  # noqa: E402

# Load mcp/src/cadastral_mcp/tools.py without triggering the package __init__.
_TOOLS_PATH = REPO / "mcp" / "src" / "cadastral_mcp" / "tools.py"
_spec = importlib.util.spec_from_file_location("cadastral_mcp_tools_standalone", _TOOLS_PATH)
_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools)
CadastralTools = _tools.CadastralTools

FIXTURE = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures" / "parcel_info_1122_1.json"


class _FakeClient:
    """Returns a fixed ParcelInfo regardless of id (1122/1: lr_unit is null,
    but reachable via parcel links)."""

    def __init__(self) -> None:
        self._parcel = ParcelInfo.model_validate(
            json.loads(FIXTURE.read_text(encoding="utf-8"))
        )

    def get_parcel_info(self, parcel_id: str) -> ParcelInfo:
        return self._parcel


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def tools() -> "CadastralTools":
    return CadastralTools(_FakeClient())


def test_cadastre_source_includes_tagged_possessors(tools) -> None:
    res = _run(tools.batch_fetch_parcels([{"parcel_id": "x"}], source="cadastre"))
    assert res["source"] == "cadastre"
    result = res["results"][0]
    assert result["register"] == "cadastre"
    possessors = result["data"]["possession_sheets"][0]["possessors"]
    assert all(p["register"] == "cadastre" for p in possessors)


def test_land_registry_source_omits_possessors_and_hints(tools) -> None:
    res = _run(tools.batch_fetch_parcels([{"parcel_id": "x"}], source="land_registry"))
    assert res["source"] == "land_registry"
    data = res["results"][0]["data"]
    assert "possession_sheets" not in data
    hint = data["land_registry_hint"]
    # 1122/1 has no direct lr_unit but resolves via parcel links (F3 scenario).
    assert hint["in_land_registry"] is True
    assert hint["lr_unit_derived_from_links"] is True
    assert hint["lr_unit_ref"]["lr_unit_number"]


def test_none_source_drops_possessors(tools) -> None:
    res = _run(tools.batch_fetch_parcels([{"parcel_id": "x"}], source="none"))
    data = res["results"][0]["data"]
    assert "possession_sheets" not in data
    assert "land_registry_hint" not in data


def test_include_owners_deprecated_maps_to_cadastre(tools) -> None:
    res = _run(tools.batch_fetch_parcels([{"parcel_id": "x"}], include_owners=True))
    assert res["source"] == "cadastre"
    assert "deprecation_notice" in res
    assert "possession_sheets" in res["results"][0]["data"]


def test_invalid_source_raises(tools) -> None:
    with pytest.raises(ValueError):
        _run(tools.batch_fetch_parcels([{"parcel_id": "x"}], source="bogus"))
