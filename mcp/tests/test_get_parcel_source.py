"""Tests for get_parcel register selection and per-parcel results.

The MCP package __init__ imports the MCP SDK (MCPServer), which need not be
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

FIXTURE = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures" / "parcel_info_linked.json"


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
    res = _run(tools.get_parcel([{"parcel_id": "6564741"}], source="cadastre"))
    assert res["source"] == "cadastre"
    result = res["results"][0]
    assert result["register"] == "cadastre"
    possessors = result["data"]["possession_sheets"][0]["possessors"]
    assert all(p["register"] == "cadastre" for p in possessors)


def test_land_registry_source_omits_possessors_and_hints(tools) -> None:
    res = _run(tools.get_parcel([{"parcel_id": "6564741"}], source="land_registry"))
    assert res["source"] == "land_registry"
    data = res["results"][0]["data"]
    assert "possession_sheets" not in data
    hint = data["land_registry_hint"]
    # 1122/1 has no direct lr_unit but resolves via parcel links (F3 scenario).
    assert hint["in_land_registry"] is True
    assert hint["lr_unit_derived_from_links"] is True
    assert hint["lr_unit_ref"]["lr_unit_number"]


def test_none_source_drops_possessors(tools) -> None:
    res = _run(tools.get_parcel([{"parcel_id": "6564741"}], source="none"))
    data = res["results"][0]["data"]
    assert "possession_sheets" not in data
    assert "land_registry_hint" not in data


def test_invalid_source_raises(tools) -> None:
    with pytest.raises(ValueError):
        _run(tools.get_parcel([{"parcel_id": "6564741"}], source="bogus"))


class _FakeClientWithGis(_FakeClient):
    """Like _FakeClient, but the municipality GIS data is available."""

    def __init__(self) -> None:
        super().__init__()
        self.geometry_calls: list[tuple[str, str]] = []

    def get_parcel_geometry(self, parcel_number: str, municipality_reg_num: str):
        from cadastral_api.models.gis_entities import ParcelGeometry

        self.geometry_calls.append((parcel_number, municipality_reg_num))
        return ParcelGeometry(
            cestica_id="1",
            broj_cestice=parcel_number,
            povrsina_graficka=1.0,
            maticni_broj_ko=municipality_reg_num,
            coordinates=[{"x": 380596.77, "y": 4880892.83}, {"x": 380636.77, "y": 4880922.83}],
        )


def test_entry_carries_map_url_when_gis_is_available() -> None:
    client = _FakeClientWithGis()
    res = _run(CadastralTools(client).get_parcel([{"parcel_id": "6564741"}]))

    entry = res["results"][0]
    assert entry["status"] == "success"
    # Resolved from the detailed record, even though the spec gave only parcel_id.
    assert client.geometry_calls == [("1122/1", "334979")]
    assert entry["map_url"].startswith(
        "https://oss.uredjenazemlja.hr/map?center=380616.77,4880907.83&zoom=19&"
    )


def test_entry_omits_map_url_when_gis_is_unavailable(tools) -> None:
    # _FakeClient has no GIS support at all; the lookup must still succeed.
    res = _run(tools.get_parcel([{"parcel_id": "6564741"}]))

    entry = res["results"][0]
    assert entry["status"] == "success"
    assert "map_url" not in entry
    assert res["successful"] == 1


def test_each_reference_gets_its_own_entry_and_bad_refs_are_reported(tools) -> None:
    res = _run(
        tools.get_parcel(
            [{"parcel_id": "6564741"}, {"parcel_number": "103/2"}, {"parcel_id": 6564742}],
            source="none",
        )
    )
    assert [r["status"] for r in res["results"]] == ["success", "error", "success"]
    assert res["total"] == 3 and res["successful"] == 2 and res["failed"] == 1
    assert "municipality" in res["results"][1]["error"]
    assert res["results"][0]["ref"] == {"parcel_id": 6564741}


def test_empty_reference_list_is_refused(tools) -> None:
    with pytest.raises(ValueError):
        _run(tools.get_parcel([], source="cadastre"))


def test_own_output_parcel_id_is_accepted_as_input(tools) -> None:
    first = _run(tools.get_parcel([{"parcel_id": "6564741"}], source="none"))
    parcel_id = first["results"][0]["data"]["parcel_id"]  # an integer, as the model types it
    assert isinstance(parcel_id, int)
    again = _run(tools.get_parcel([{"parcel_id": parcel_id}], source="none"))
    assert again["results"][0]["status"] == "success"
    assert again["results"][0]["ref"] == {"parcel_id": parcel_id}
    # A numeric string is accepted and normalised to the integer id.
    as_text = _run(tools.get_parcel([{"parcel_id": str(parcel_id)}], source="none"))
    assert as_text["results"][0]["ref"] == {"parcel_id": parcel_id}
