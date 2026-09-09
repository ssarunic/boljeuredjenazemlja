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


CONDOMINIUM = (
    REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures" / "lr_unit_condominium.json"
)


@pytest.fixture
def condominium() -> LandRegistryUnitDetailed:
    raw = json.loads(CONDOMINIUM.read_text(encoding="utf-8"))
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)


def _dumped_owners(shaped: dict) -> int:
    """Owner records left in a full dump, sub-shares included."""
    def walk(shares) -> int:
        count = 0
        for share in shares:
            count += len(share.get("owners") or [])
            nested = share.get("sub_shares_and_entries") or []
            count += walk([item for item in nested if isinstance(item, dict) and "owners" in item])
        return count

    return walk(shaped["ownership_sheet_b"]["lr_unit_shares"])


def test_full_reports_owner_count_when_nothing_is_capped(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "full", None)
    assert shaped["total_owners"] == 4
    assert shaped["owners_truncated"] is False
    assert _dumped_owners(shaped) == 4


def test_owners_limit_applies_to_full_not_only_ownership(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "full", 2)
    assert _dumped_owners(shaped) == 2
    assert shaped["total_owners"] == 4
    assert shaped["owners_truncated"] is True
    # The other sheets are still there; only sheet B was cut off.
    assert "encumbrance_sheet_c" in shaped
    assert "possessory_sheet_a1" in shaped


def test_owners_limit_drops_the_shares_past_the_cap_not_only_their_owners(condominium) -> None:
    # Emptying the owners is not enough: each share carries its own description
    # and registration entry, so this unit's 85 emptied shares still serialise
    # to 135,000 characters. Sheet B is cut off at the cap instead.
    dump = condominium.model_dump(mode="json")
    before = len(dump["ownership_sheet_b"]["lr_unit_shares"])
    total, truncated, omitted = CadastralTools._cap_dumped_owners(dump, 5)
    shares = dump["ownership_sheet_b"]["lr_unit_shares"]
    assert len(shares) == 5 < before
    assert _dumped_owners(dump) == 5
    assert (total, truncated) == (103, True)
    assert omitted == CadastralTools._count_shares(
        # every share dropped, sub-shares included
        condominium.model_dump(mode="json")["ownership_sheet_b"]["lr_unit_shares"]
    ) - CadastralTools._count_shares(shares)


def test_a_capped_full_dump_is_still_refused_when_another_sheet_is_the_bulk(condominium) -> None:
    # This unit's encumbrances alone overrun the ceiling, so owners_limit
    # cannot rescue the full dump; the refusal names the sheet at fault and
    # does not suggest owners_limit again.
    with pytest.raises(ValueError) as excinfo:
        CadastralTools._shape_lr_unit(condominium, "full", 5)
    message = str(excinfo.value)
    assert "encumbrance_sheet_c" in message
    assert "owners_limit" not in message
    assert 'detail="ownership"' in message


def test_full_dump_too_large_to_return_is_refused_with_the_smaller_options(condominium) -> None:
    with pytest.raises(ValueError) as excinfo:
        CadastralTools._shape_lr_unit(condominium, "full", None)
    message = str(excinfo.value)
    assert condominium.lr_unit_number in message
    assert "owners_limit" in message
    assert 'detail="ownership"' in message
    # The smaller views still work for the same unit.
    assert CadastralTools._shape_lr_unit(condominium, "ownership", 3)["owners_truncated"] is True
    assert CadastralTools._shape_lr_unit(condominium, "summary", None)["summary"]
