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
    # The fourth owner record is a second share of a matched person: matched too.
    assert result.relationship == "same"
    assert len(result.matched) == 4 and result.fuzzy_matches == 0
    assert all(m.by_tax_number is False for m in result.matched)  # possessors carry no OIB
    assert result.possessors_only == [] and result.owners_only == []
    second = [m for m in result.matched if m.owner.name == "Vlasnik 116"]
    assert len(second) == 2 and second[0].possessor is second[1].possessor
    assert second[0].via == "name" and second[0].extended_from is None
    assert second[1].via == "tax_number_extension"
    assert second[1].extended_from == second[0].owner.share_order_number
    assert second[1].shares_agree is None
    assert result.distinct_people == 3
    # Four pairs, three people: the summary counts people.
    assert "same 3 person(s)" in result.summary
    assert not any(b.kind == "owner_not_possessor" for b in result.sale_blockers.blockers)


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


def test_reversed_and_comma_written_possessors_match_the_owners_fuzzily() -> None:
    parcel, unit = _parcel(), _unit()
    sheet = parcel.possession_sheets[0]
    sheet.possessors = sheet.possessors[:2]
    for sheet_ in parcel.possession_sheets[1:]:
        sheet_.possessors = []
    shares = unit.ownership_sheet_b.lr_unit_shares
    shares[0].owners[0].name = "ŠARUNIĆ AUGUSTIN POK. BOŽE"
    shares[1].owners[0].name = "ŠARUNIĆ FJORDANA"
    _rename_possessors(parcel, ["ŠARUNIĆ AUGUSTIN, BOŽO", "Fjordana Šarunić"])
    # Without a corroborating share or address, a reordered name is fuzzy:
    # Savar is full of namesakes across generations.
    sheet.possessors[1].ownership = None
    sheet.possessors[1].address = None
    result = compare_registers(parcel, unit)
    assert result.relationship == "overlapping"
    assert len(result.matched) == 2 and result.possessors_only == []
    assert result.fuzzy_matches == 2
    # The same share on both sides corroborates it; the relative stays a guess.
    sheet.possessors[1].ownership = "1/4"
    result = compare_registers(parcel, unit)
    assert [m.fuzzy for m in sorted(result.matched, key=lambda m: m.owner.name)] == [True, False]
    assert result.fuzzy_matches == 1
    assert any("fuzzy" in note for note in result.notes)
    # So does the same address when the shares are not given.
    sheet.possessors[1].ownership = None
    sheet.possessors[1].address = "Split, A. Stepinca 31"
    shares[1].owners[0].address = "SPLIT, A. STEPINCA 31"
    assert compare_registers(parcel, unit).fuzzy_matches == 1


def test_a_match_extends_to_a_persons_other_shares_by_oib_only() -> None:
    parcel, unit = _parcel(), _unit()
    sheet = parcel.possession_sheets[0]
    sheet.possessors = sheet.possessors[:1]
    for sheet_ in parcel.possession_sheets[1:]:
        sheet_.possessors = []
    shares = unit.ownership_sheet_b.lr_unit_shares
    # Two owner records of one name: a grandfather without an OIB and a grandson with one.
    shares[0].owners[0].name = "ŠARUNIĆ AUGUSTIN"
    shares[0].owners[0].tax_number = None
    shares[1].owners[0].name = "ŠARUNIĆ AUGUSTIN"
    shares[1].owners[0].tax_number = "63061048570"
    for share in shares[2:]:
        share.owners[0].name = "OTHER OWNER"
    sheet.possessors[0].name = "ŠARUNIĆ AUGUSTIN"
    result = compare_registers(parcel, unit)
    # The possessor matches one record exactly; the namesake record is not
    # pulled in on the name alone.
    assert len(result.matched) == 1
    assert "ŠARUNIĆ AUGUSTIN" in [o.name for o in result.owners_only]
    # Give both records the OIB: the second is the same person and matches too.
    shares[0].owners[0].tax_number = "63061048570"
    result = compare_registers(parcel, unit)
    assert len(result.matched) == 2
    assert "ŠARUNIĆ AUGUSTIN" not in [o.name for o in result.owners_only]


def test_the_savar_pattern_of_owners_yields_the_expected_severities() -> None:
    # Five owners as on a typical Savar unit: a legacy half matched fuzzily to
    # the possessor, two recent heirs with an OIB, two legacy owners without.
    from datetime import date

    from cadastral_api.models.entities import LREntry

    parcel, unit = _parcel(), _unit()
    sheet = parcel.possession_sheets[0]
    sheet.possessors = sheet.possessors[:1]
    for sheet_ in parcel.possession_sheets[1:]:
        sheet_.possessors = []
    sheet.possessors[0].name = "TESTIĆ AUGUSTIN, BOŽO"
    shares = unit.ownership_sheet_b.lr_unit_shares
    recent = LREntry.model_validate(
        {
            "orderNumber": "6.1",
            "description": "Zaprimljeno 21.03.2018.g. pod brojem Z-6789/2018 UKNJIŽBA, PRAVO "
            "VLASNIŠTVA, RJEŠENJE O NASLJEĐIVANJU",
        }
    )
    rows = [
        ("TESTIĆ AUGUSTIN POK. BOŽE", None, None),
        ("TESTIĆ MILIVOJ", "31272660898", recent),
        ("VUKIĆ MILENA", "15925300262", recent),
        ("DRAGIĆ BISERA Ž. MIRA", None, None),
    ]
    for share, (name, oib, entry) in zip(shares, rows, strict=True):
        share.owners[0].name = name
        share.owners[0].tax_number = oib
        share.owners[0].entry = entry
        share.owners[0].address = None
    result = compare_registers(parcel, unit)
    assert result.relationship == "overlapping" and result.fuzzy_matches == 1
    by_kind: dict[str, set[tuple[str | None, str]]] = {}
    for b in result.sale_blockers.blockers:
        by_kind.setdefault(b.kind, set()).add((b.beneficiary, b.severity))
    # A deceased owner not appearing as possessor is expected: the estate row
    # stands for that share, without an owner_not_possessor row beside it.
    assert by_kind["owner_not_possessor"] == {
        ("TESTIĆ MILIVOJ", "informational"),
        ("VUKIĆ MILENA", "informational"),
    }
    assert by_kind["fuzzy_owner_match"] == {("TESTIĆ AUGUSTIN POK. BOŽE", "informational")}
    fuzzy = next(b for b in result.sale_blockers.blockers if b.kind == "fuzzy_owner_match")
    assert "written differently" in fuzzy.description and "name_loose" in fuzzy.basis
    # Conditional: the two estates and the fixture's own area mismatch.
    assert result.sale_blockers.counts == {"blocking": 1, "conditional": 3, "informational": 3}
    assert any(b.kind == "area_mismatch" for b in result.sale_blockers.blockers)
    # The matched legacy half is an estate: a blocker of its own, share scoped.
    assert by_kind["likely_estate"] == {
        ("TESTIĆ AUGUSTIN POK. BOŽE", "conditional"),
        ("DRAGIĆ BISERA Ž. MIRA", "conditional"),
    }
    estate = next(b for b in result.sale_blockers.blockers if b.kind == "likely_estate")
    assert estate.scope == "share" and estate.share_order_number == shares[0].order_number
    assert "legacy record" in estate.basis
    assert result.sale_blockers.verdict == "blocked"  # the fixture's plomba
    unit.active_plumbs = []
    assert compare_registers(parcel, unit).sale_blockers.verdict == "conditional"
    assert result.owner_flag_counts["likely_deceased"] == 2
    assert date.today()  # keeps the import honest


def test_owner_not_possessor_is_informational_for_a_recent_owner_with_an_oib() -> None:
    parcel, unit = _parcel(), _unit()
    result = compare_registers(parcel, unit)  # disjoint: every owner is owner only
    kinds = {
        (b.beneficiary, b.severity)
        for b in result.sale_blockers.blockers
        if b.kind == "owner_not_possessor"
    }
    # Unit 449's owners all carry an OIB and a 2025/2026 entry: the cadastre lags.
    assert kinds and all(severity == "informational" for _, severity in kinds)
    assert result.sale_blockers.verdict == "blocked"  # the plomba, not the owners
    # Strip one owner's OIB and entry: a legacy record, an estate. The share
    # gets a likely_estate row and no owner_not_possessor row.
    share = unit.ownership_sheet_b.lr_unit_shares[0]
    share.owners[0].tax_number = None
    share.owners[0].entry = None
    result = compare_registers(parcel, unit)
    mine = [b for b in result.sale_blockers.blockers if b.beneficiary == share.owners[0].name]
    assert [b.kind for b in mine] == ["likely_estate"]
    assert mine[0].severity == "conditional" and mine[0].share_order_number == share.order_number
    assert "legacy" in result.owners[0].flags.likely_deceased.basis
    assert result.owner_flag_counts["likely_deceased"] == 1
    # Old-entry owners keep a conditional owner_not_possessor row (no estate row
    # is raised only for the flagged ones).
    share.owners[0].tax_number = "00000000010"
    old_owner = unit.ownership_sheet_b.lr_unit_shares[1].owners[0]
    old_owner.tax_number = None
    old_owner.entry = None
    result = compare_registers(parcel, unit)
    kinds = {
        b.beneficiary: b.kind
        for b in result.sale_blockers.blockers
        if b.source in ("ownership", "register_comparison") and b.kind != "fuzzy_owner_match"
    }
    assert kinds[old_owner.name] == "likely_estate"


def test_an_area_mismatch_is_a_conditional_blocker() -> None:
    parcel, unit = _parcel(), _unit()
    result = compare_registers(parcel, unit, gis_area_m2=1600.0)
    assert result.area_check.mismatch is True
    mismatch = [b for b in result.sale_blockers.blockers if b.kind == "area_mismatch"]
    assert len(mismatch) == 1 and mismatch[0].severity == "conditional"
    assert mismatch[0].scope == "unit" and "3,291" in mismatch[0].description
    assert "tolerance" in mismatch[0].basis
    parcel.area = "3291"
    agreed = compare_registers(parcel, unit)
    assert not any(b.kind == "area_mismatch" for b in agreed.sale_blockers.blockers)


def test_plombe_detail_reaches_the_comparison_blockers() -> None:
    from cadastral_api.models.entities import FileStatus

    parcel, unit = _parcel(), _unit()
    status = FileStatus.model_validate(
        {"lrFileNumber": "Z-12564/2026", "applicationContent": "Rješenje o nasljeđivanju"}
    )
    result = compare_registers(parcel, unit, plombe_detail={"Z-12564/2026": status})
    pending = [b for b in result.sale_blockers.blockers if b.kind == "pending_entry"]
    assert pending[0].request_kind == "Rješenje o nasljeđivanju"
    assert result.sale_blockers.plombe_detail_included is True
    # Asked for on a unit without plombe: included, with nothing fetched.
    unit.active_plumbs = []
    assert compare_registers(parcel, unit, plombe_detail={}).sale_blockers.plombe_detail_included
    assert compare_registers(parcel, unit).sale_blockers.plombe_detail_included is False
