"""F4: MCP LR-unit response shaping (detail levels + owners_limit).

Loads tools.py standalone (no MCP SDK needed) and shapes a real LR unit
(449/21277, redacted owners) via the pure _shape_lr_unit classmethod.
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api.models.entities import LandRegistryUnitDetailed  # noqa: E402

_TOOLS_PATH = REPO / "mcp" / "src" / "cadastral_mcp" / "tools.py"
_spec = importlib.util.spec_from_file_location("cadastral_mcp_tools_shaping", _TOOLS_PATH)
_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools)
CadastralTools = _tools.CadastralTools

FIXTURE = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures" / "lr_unit_lrparcels.json"


@pytest.fixture
def unit() -> LandRegistryUnitDetailed:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)


def test_full_includes_all_sheets(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "full", None)
    assert "ownership_sheet_b" in shaped
    assert "encumbrance_sheet_c" in shaped
    assert shaped["summary"]["total_parcels"] == 1


def test_summary_is_minimal(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "summary", None)
    assert "ownership_sheet_b" not in shaped
    assert "owners" not in shaped
    assert shaped["summary"]["num_owners"] == 4


def test_ownership_returns_tagged_owners_with_structured_shares(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "ownership", None)
    assert "ownership_sheet_b" not in shaped  # raw sheets dropped
    assert "encumbrance_sheet_c" not in shaped
    assert shaped["in_land_registry"] is True
    assert shaped["total_owners"] == 4
    assert shaped["owners_truncated"] is False
    owners = shaped["owners"]
    assert len(owners) == 4
    assert all(o["register"] == "land_registry" for o in owners)
    assert all(o["name_normalized"] for o in owners)
    # Structured share, not a description string.
    assert all(isinstance(o["share"], dict) and "decimal" in o["share"] for o in owners)


def test_owners_limit_truncates_and_reports_total(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "ownership", 2)
    assert len(shaped["owners"]) == 2
    assert shaped["total_owners"] == 4
    assert shaped["owners_truncated"] is True


def test_invalid_detail_raises(unit) -> None:
    with pytest.raises(ValueError):
        CadastralTools._shape_lr_unit(unit, "bogus", None)
