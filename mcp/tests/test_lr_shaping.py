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


def test_full_is_paged_by_share_and_drops_the_shares_outside_the_window(condominium) -> None:
    # Emptying the owners is not enough: each share carries its own description
    # and registration entry, so this unit's 85 emptied shares still serialise
    # to 135,000 characters. Sheet B is cut to the window of shares instead.
    dump = condominium.model_dump(mode="json")
    before = dump["ownership_sheet_b"]["lr_unit_shares"]
    total, returned, omitted = CadastralTools._window_shares(dump, 0, 5)
    shares = dump["ownership_sheet_b"]["lr_unit_shares"]
    assert (total, returned) == (85, 5)
    assert len(shares) == 5 < len(before)
    assert omitted == CadastralTools._count_shares(before) - CadastralTools._count_shares(shares)


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


# --- paging and the per-sheet detail levels -------------------------------


def test_every_level_names_the_unit_and_its_office(unit) -> None:
    for detail in CadastralTools.VALID_DETAIL:
        shaped = CadastralTools._shape_lr_unit(unit, detail, 3)
        assert shaped["lr_unit_number"] == unit.lr_unit_number
        assert shaped["institution_id"] == unit.institution_id
        if detail != "summary":
            assert shaped["page"]["total"] >= shaped["page"]["returned"]


def test_ownership_pages_with_offset(unit) -> None:
    first = CadastralTools._shape_lr_unit(unit, "ownership", 3, 0)
    assert first["page"] == {
        "offset": 0, "limit": 3, "total": 4, "returned": 3, "truncated": True, "next_offset": 3
    }
    rest = CadastralTools._shape_lr_unit(unit, "ownership", 3, first["page"]["next_offset"])
    assert len(rest["owners"]) == 1
    assert rest["owners_truncated"] is False
    assert rest["page"]["truncated"] is False
    names = [o["name"] for o in first["owners"]] + [o["name"] for o in rest["owners"]]
    assert names == [o["name"] for o in unit.ownership_sheet_b.owner_rows()]


def test_full_pages_shares_with_offset_and_loses_none(condominium) -> None:
    pages, owners, offset = [], 0, 0
    while True:
        dump = condominium.model_dump(mode="json")
        total, returned, omitted = CadastralTools._window_shares(dump, offset, 40)
        pages.append(returned)
        owners += _dumped_owners(dump)
        assert omitted > 0
        offset += returned
        if offset >= total:
            break
    assert pages == [40, 40, 5]
    assert owners == 103  # every owner record of every share, once


def test_paging_reaches_a_trailing_share_without_owners() -> None:
    # A share that holds only annotations is a page item like any other: with
    # limit=1 the first page says there is more, and the second page is it.
    def dump() -> dict:
        return {"ownership_sheet_b": {"lr_unit_shares": [
            {"order_number": "1", "owners": [{"name": "A"}], "sub_shares_and_entries": []},
            {"order_number": "2", "owners": [], "sub_shares_and_entries": [{"entry": "x"}]},
        ]}}

    first = dump()
    assert CadastralTools._window_shares(first, 0, 1) == (2, 1, 1)
    page = CadastralTools._page(0, 1, 2, 1)
    assert page["truncated"] is True and page["next_offset"] == 1
    second = dump()
    assert CadastralTools._window_shares(second, page["next_offset"], 1) == (2, 1, 1)
    assert second["ownership_sheet_b"]["lr_unit_shares"][0]["order_number"] == "2"


def test_shares_level_is_raw_sheet_b_paged(condominium) -> None:
    # The condominium's list C alone overruns the full-dump ceiling, so full
    # is refused even with limit=1; the raw sheet B is still reachable here.
    with pytest.raises(ValueError):
        CadastralTools._shape_lr_unit(condominium, "full", 1)
    first = CadastralTools._shape_lr_unit(condominium, "shares", 10, 0)
    sheet = first["ownership_sheet_b"]
    assert len(sheet["lr_unit_shares"]) == 10
    assert sheet["lr_entries"]  # the sheet-level B entries come along
    share = sheet["lr_unit_shares"][0]
    assert {"status", "sub_shares_and_entries", "owners"} <= set(share)  # raw, not flattened
    assert first["total_shares"] == 85
    assert first["total_owners"] == 103
    assert first["owners_truncated"] is True
    assert first["page"]["next_offset"] == 10
    assert "encumbrance_sheet_c" not in first and "possessory_sheet_a1" not in first
    # The pages cover the whole sheet exactly once.
    seen, offset = [], 0
    while True:
        page = CadastralTools._shape_lr_unit(condominium, "shares", 10, offset)
        seen += [s["order_number"] for s in page["ownership_sheet_b"]["lr_unit_shares"]]
        if not page["page"]["truncated"]:
            break
        offset = page["page"]["next_offset"]
    assert seen == [s.order_number for s in condominium.ownership_sheet_b.lr_unit_shares]


def test_full_window_past_the_end_is_empty_not_an_error(unit) -> None:
    shaped = CadastralTools._shape_lr_unit(unit, "full", 2, 10)
    assert _dumped_owners(shaped) == 0
    assert shaped["page"]["returned"] == 0
    assert shaped["page"]["truncated"] is False


def test_parcels_level_is_sheet_a_paged(encumbered) -> None:
    shaped = CadastralTools._shape_lr_unit(encumbered, "parcels", 3, 0)
    assert "ownership_sheet_b" not in shaped and "owners" not in shaped
    assert shaped["total_parcels"] == 7
    assert len(shaped["parcels"]) == 3
    assert shaped["page"]["next_offset"] == 3
    assert shaped["sheet_a1_source_key"] in ("lrParcels", "cadParcels")
    assert "sheet_a2_entries" in shaped
    numbers = [p["parcel_number"] for p in shaped["parcels"]]
    assert numbers == encumbered.possessory_sheet_a1.parcel_numbers()[:3]


def test_encumbrances_level_is_sheet_c_paged(condominium) -> None:
    # The condominium's sheet C alone overruns the full-dump ceiling; paged
    # by entry group it comes back a window at a time.
    groups = condominium.encumbrance_sheet_c.lr_entry_groups
    first = CadastralTools._shape_lr_unit(condominium, "encumbrances", 5, 0)
    assert first["total_entry_groups"] == len(groups) == 30
    assert len(first["entry_groups"]) == 5
    assert first["page"]["truncated"] is True
    assert "ownership_sheet_b" not in first and "owners" not in first
    last = CadastralTools._shape_lr_unit(condominium, "encumbrances", 5, 25)
    assert len(last["entry_groups"]) == 5
    assert last["page"]["truncated"] is False


def test_a_paged_level_too_large_says_how_to_page_smaller(condominium) -> None:
    with pytest.raises(ValueError) as excinfo:
        CadastralTools._shape_lr_unit(condominium, "encumbrances", None, 0)
    message = str(excinfo.value)
    assert "encumbrances" in message and "limit=" in message and "offset" in message


def test_refused_full_dump_names_the_per_sheet_levels(condominium) -> None:
    with pytest.raises(ValueError) as excinfo:
        CadastralTools._shape_lr_unit(condominium, "full", None)
    assert 'detail="encumbrances"' in str(excinfo.value)
    assert 'detail="shares"' in str(excinfo.value)


ENCUMBERED = (
    REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures" / "lr_unit_encumbrances.json"
)


@pytest.fixture
def encumbered() -> LandRegistryUnitDetailed:
    raw = json.loads(ENCUMBERED.read_text(encoding="utf-8"))
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)
