"""Owner flags: likely deceased, address abroad, public body, all inferred with a basis."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from cadastral_api.analysis import (
    count_owner_flags,
    infer_address_abroad,
    infer_deceased,
    owner_flags,
    owner_flags_for_unit,
)
from cadastral_api.analysis.owner_flags import name_marks_deceased
from cadastral_api.models.entities import LandRegistryUnitDetailed, LREntry

FIXTURES = Path(__file__).resolve().parents[2] / "src" / "cadastral_api" / "tests" / "fixtures"
TODAY = date(2026, 9, 15)


def _unit(name: str) -> LandRegistryUnitDetailed:
    raw = json.loads((FIXTURES / name).read_text())
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)


def _entry(text: str) -> LREntry:
    return LREntry.model_validate({"orderNumber": "1.1", "description": text})


def test_a_death_marker_on_the_person_not_on_a_relative() -> None:
    assert name_marks_deceased("POKOJNI HORVAT MARKO") == "pokojni"
    assert name_marks_deceased("HORVAT MARKO POK.") == "pok"
    assert name_marks_deceased("POK. HORVAT MARKO") == "pok"
    # "pok. Marka" names Ivan's late father; Ivan is not marked.
    assert name_marks_deceased("HORVAT IVAN POK. MARKA") is None
    assert name_marks_deceased("TEST OSOBA UD. BOŽE") is None
    assert name_marks_deceased("") is None


def test_deceased_by_entry_age_transfer_or_marker_each_with_a_basis() -> None:
    old = _entry("Stig. 23. svibnja 1975. Z 487/75 UKNJIŽBA, PRAVO VLASNIŠTVA")
    recent = _entry("Zaprimljeno 12.03.2019.g. pod brojem Z-1/2019 UKNJIŽBA, PRAVO VLASNIŠTVA")
    transferred = _entry(
        "Zaprimljeno 05.04.2012.g. pod brojem Z-3983/2012 UKNJIŽBA, PRAVO VLASNIŠTVA"
        "<br><br>IZ ZK ULOŠKA PRENESENI VLASNICI"
    )
    by_age = infer_deceased("HORVAT IVAN", old, today=TODAY)
    assert by_age.likely_deceased is True and by_age.signals == ["entry_age"]
    assert by_age.entry_date == "1975-05-23" and by_age.entry_age_years == 51
    assert "1975-05-23" in by_age.basis and "51 years" in by_age.basis
    assert by_age.inferred is True

    not_yet = infer_deceased("HORVAT IVAN", recent, today=TODAY)
    assert not_yet.likely_deceased is False and not_yet.signals == []
    assert "under 40" in not_yet.basis

    migrated = infer_deceased("HORVAT IVAN", transferred, today=TODAY)
    assert migrated.likely_deceased is True and migrated.signals == ["transferred_from_unit"]
    assert "original registration is older" in migrated.basis

    marked = infer_deceased("POKOJNI HORVAT MARKO", recent, today=TODAY)
    assert marked.signals == ["name_marker"] and marked.marker == "pokojni"

    # The threshold is a parameter; the entry-row dict shape is accepted too.
    assert infer_deceased("X", recent, threshold_years=5, today=TODAY).likely_deceased is True
    row = {"entry_date": "1975-05-23", "transferred_from_unit": False}
    assert infer_deceased("X", row, today=TODAY).signals == ["entry_age"]
    # No entry and no OIB: a legacy record from the paper register, likely an estate.
    legacy = infer_deceased("X", None, today=TODAY)
    assert legacy.likely_deceased is True and legacy.signals == ["legacy_record"]
    # No entry but an OIB: a living, digitally registered person as far as the rule knows.
    assert infer_deceased("X", None, tax_number="1", today=TODAY).likely_deceased is False


def test_address_abroad_by_country_name_postcode_or_unknown() -> None:
    berlin = infer_address_abroad("Musterstraße 1, 10115 Berlin, Njemačka")
    assert berlin.abroad is True and berlin.country == "Germany"
    assert berlin.confidence == "keyword" and "njemacka" in berlin.basis
    assert infer_address_abroad("Main St 1, Sydney, Australia").country == "Australia"
    vienna = infer_address_abroad("Hauptstrasse 5, A-1010 Wien")
    assert vienna.abroad is True and vienna.confidence == "postcode_pattern"
    assert vienna.country is None
    home = infer_address_abroad("ULICA 1, 10000 ZAGREB")
    assert home.abroad is False and home.confidence is None
    assert infer_address_abroad("HR-23281 SAVAR, Hrvatska").abroad is False
    assert infer_address_abroad("SAVAR").abroad is False
    unknown = infer_address_abroad(None)
    assert unknown.abroad is None and unknown.basis == "no address on record"
    assert infer_address_abroad("   ").abroad is None


def test_public_bodies_and_companies_get_no_deceased_flag() -> None:
    state = owner_flags("REPUBLIKA HRVATSKA", "ZAGREB", None)
    assert state.public_body is True and state.likely_deceased is None
    assert state.party_type_inferred.party_type == "state"
    town = owner_flags("GRAD ZADAR", None, None)
    assert town.public_body is True
    company = owner_flags("TESTNA BANKA d.d.", "ZAGREB", None)
    assert company.public_body is False and company.likely_deceased is None
    person = owner_flags("HORVAT IVAN", "ZAGREB", None, tax_number="1")
    assert person.public_body is False and person.likely_deceased is not None
    assert person.likely_deceased.likely_deceased is False


def test_flags_of_a_whole_unit_follow_the_owner_rows() -> None:
    unit = _unit("lr_unit_sale_blockers.json")
    rows = owner_flags_for_unit(unit, today=TODAY)
    assert [r.name for r in rows] == [
        row["name"] for row in unit.ownership_sheet_b.owner_rows()
    ]
    by_name = {r.name: r for r in rows}
    assert by_name["POKOJNI HORVAT MARKO"].flags.likely_deceased.signals == ["name_marker"]
    assert by_name["POKOJNI HORVAT MARKO"].condominium_number == "E-2"
    assert by_name["KOVAČ PETAR"].flags.likely_deceased.signals == ["transferred_from_unit"]
    assert by_name["KOVAČ PETAR"].flags.address_abroad.confidence == "postcode_pattern"
    assert by_name["BABIĆ JOSIP"].flags.likely_deceased.signals == ["entry_age"]
    assert by_name["KOVAČ ANA"].flags.address_abroad.country == "Germany"
    assert by_name["REPUBLIKA HRVATSKA"].flags.public_body is True
    assert by_name["HORVAT IVAN POK. MARKA"].flags.likely_deceased.likely_deceased is False
    assert rows[0].share_order_number == "1"
    assert count_owner_flags(r.flags for r in rows) == {
        "owners": 7,
        "likely_deceased": 3,
        "address_abroad": 2,
        "address_unknown": 1,
        "public_body": 1,
    }


def test_transferred_owners_of_the_real_fixture_are_flagged() -> None:
    # Unit 769: three owners carried over from an earlier unit in 2012.
    rows = owner_flags_for_unit(_unit("lr_unit_encumbrances.json"), today=TODAY)
    flagged = [
        r for r in rows if r.flags.likely_deceased and r.flags.likely_deceased.likely_deceased
    ]
    assert len(flagged) == 3
    assert all(r.flags.likely_deceased.signals == ["transferred_from_unit"] for r in flagged)


def test_inference_serialises_marked_inferred() -> None:
    dumped = owner_flags("HORVAT IVAN", "Wien, Austrija", None, tax_number="1").model_dump(
        mode="json"
    )
    assert dumped["likely_deceased"]["inferred"] is True
    assert dumped["address_abroad"] == {
        "abroad": True,
        "inferred": True,
        "basis": "the address names Austria ('austrija')",
        "country": "Austria",
        "confidence": "keyword",
        "matched": "austrija",
    }
