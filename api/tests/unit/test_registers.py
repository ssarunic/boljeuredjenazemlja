"""compare_registers: cadastre possessors against land-registry owners."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cadastral_api.analysis import compare_registers
from cadastral_api.models.entities import LandRegistryUnitDetailed, ParcelInfo, Party

FIXTURES = Path(__file__).resolve().parents[2] / "src" / "cadastral_api" / "tests" / "fixtures"


def _parcel() -> ParcelInfo:
    return ParcelInfo.model_validate(json.loads((FIXTURES / "parcel_info_linked.json").read_text()))


def _unit() -> LandRegistryUnitDetailed:
    raw = json.loads((FIXTURES / "lr_unit_lrparcels.json").read_text())
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)


def _rename_possessors(parcel: ParcelInfo, names: list[str]) -> None:
    possessors = [p for sheet in parcel.possession_sheets for p in sheet.possessors]
    for possessor, name in zip(possessors, names, strict=False):
        possessor.name = name


def test_disjoint_registers_with_the_real_fixtures() -> None:
    parcel, unit = _parcel(), _unit()
    result = compare_registers(parcel, unit, gis_area_m2=1600.0)
    assert result.relationship == "disjoint"
    assert result.lr_unit == {"lr_unit_number": "449", "main_book_id": 21277}
    assert result.matched == []
    assert len(result.possessors_only) == len(result.possessors) == parcel.total_possessors
    assert len(result.owners_only) == len(result.owners) == 4
    assert result.distinct_owners == 3  # one owner on two shares
    assert result.distinct_people == result.distinct_possessors + 3
    assert result.party_types == {"individual": result.distinct_people}
    assert result.public_body_owner_share == 0.0
    # Cadastre 1618 m2 against the land register's 3291 m2 and the map's 1600.
    assert result.area_check.compared == ["cadastre", "land_registry", "gis"]
    assert result.area_check.land_registry_m2 == 3291
    assert result.area_check.mismatch is True
    assert "different people" in result.summary
    assert all(p.register == "cadastre" for p in result.possessors)
    assert all(o.register == "land_registry" for o in result.owners)


def test_same_people_in_both_registers() -> None:
    parcel, unit = _parcel(), _unit()
    owner_names = [row["name"] for row in unit.ownership_sheet_b.owner_rows()]
    # Give the parcel exactly the owners as possessors (one owner sits on two shares).
    sheet = parcel.possession_sheets[0]
    sheet.possessors = sheet.possessors[:3]
    for sheet_ in parcel.possession_sheets[1:]:
        sheet_.possessors = []
    _rename_possessors(parcel, sorted(set(owner_names)))
    for possessor in sheet.possessors:
        possessor.name = possessor.name.lower()  # spelling differs, same person
    result = compare_registers(parcel, unit)
    assert result.relationship == "overlapping"  # the fourth owner record is a second share
    assert len(result.matched) == 3 and result.fuzzy_matches == 0
    assert all(m.by_tax_number is False for m in result.matched)  # possessors carry no OIB
    assert result.possessors_only == []
    assert [o.name for o in result.owners_only] == ["Vlasnik 116"]
    assert result.distinct_people == 3
    assert "3 person(s) appear in both" in result.summary


def test_fuzzy_match_is_flagged_and_noted() -> None:
    parcel, unit = _parcel(), _unit()
    sheet = parcel.possession_sheets[0]
    sheet.possessors = sheet.possessors[:1]
    for sheet_ in parcel.possession_sheets[1:]:
        sheet_.possessors = []
    unit.ownership_sheet_b.lr_unit_shares[0].owners[0].name = "KOLAR RAJKA POK. IVE"
    sheet.possessors[0].name = "Kolar Rajka"
    result = compare_registers(parcel, unit)
    assert result.relationship == "overlapping"
    assert result.matched[0].fuzzy is True and result.fuzzy_matches == 1
    assert any("fuzzy" in note for note in result.notes)


def test_shares_agree_and_public_body_share() -> None:
    parcel, unit = _parcel(), _unit()
    share = unit.ownership_sheet_b.lr_unit_shares[0]
    share.owners[0].name = "REPUBLIKA HRVATSKA"
    sheet = parcel.possession_sheets[0]
    sheet.possessors = sheet.possessors[:1]
    for sheet_ in parcel.possession_sheets[1:]:
        sheet_.possessors = []
    sheet.possessors[0].name = "Republika Hrvatska"
    sheet.possessors[0].ownership = "1/4"
    result = compare_registers(parcel, unit)
    assert result.matched[0].shares_agree is True
    assert result.matched[0].owner.party_type_inferred.party_type == "state"
    assert result.public_body_owner_share == 0.25
    assert result.party_types["state"] == 1


def test_parcel_outside_the_land_registry_and_unreadable_unit() -> None:
    parcel = _parcel()
    result = compare_registers(parcel, None)
    assert result.relationship == "cadastre_only"
    assert result.owners == [] and result.lr_unit is None
    assert result.area_check.compared == ["cadastre"]
    assert "not in the land registry" in result.summary
    unavailable = compare_registers(parcel, None, lr_unit_error="lr_unit_not_found (reason=x)")
    assert unavailable.relationship == "land_registry_unavailable"
    assert unavailable.notes == ["land-registry unit not read: lr_unit_not_found (reason=x)"]


def test_empty_sides() -> None:
    parcel, unit = _parcel(), _unit()
    for sheet in parcel.possession_sheets:
        sheet.possessors = []
    assert compare_registers(parcel, unit).relationship == "no_possessors"
    parcel = _parcel()
    for share in unit.ownership_sheet_b.lr_unit_shares:
        share.owners = []
        share.sub_shares_and_entries = []
    assert compare_registers(parcel, unit).relationship == "no_owners"


def test_tax_number_match_beats_spelling() -> None:
    parcel, unit = _parcel(), _unit()
    sheet = parcel.possession_sheets[0]
    sheet.possessors = sheet.possessors[:1]
    for sheet_ in parcel.possession_sheets[1:]:
        sheet_.possessors = []
    sheet.possessors[0].name = "Vlasnik 114"
    unit.ownership_sheet_b.lr_unit_shares[0].owners = [
        Party.model_validate({"name": "VLASNIK 114", "taxNumber": "00000000010"})
    ]
    result = compare_registers(parcel, unit)
    assert result.matched and result.matched[0].by_tax_number is False  # the possessor has no OIB
    assert result.matched[0].owner.tax_number == "00000000010"


@pytest.mark.parametrize("relationship", ["same", "disjoint"])
def test_result_serialises(relationship: str) -> None:
    parcel, unit = _parcel(), _unit()
    dumped = compare_registers(parcel, unit).model_dump(mode="json")
    assert set(dumped) >= {"relationship", "matched", "area_check", "party_types", "summary"}
    assert dumped["possessors"][0]["party_type_inferred"]["inferred"] is True
