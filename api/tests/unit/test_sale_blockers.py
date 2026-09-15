"""Sale blockers: classification, scope, cancellation, verdict, and the composition upstream."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cadastral_api.analysis import (
    DEFAULT_SEVERITY,
    AssemblyInput,
    Blocker,
    acquisition_score,
    blocker_identity,
    build_assembly,
    classify_entry_text,
    compare_registers,
    detect_blockers,
    merge_blockers,
    parcels_csv,
    persons_csv,
    resolve_severities,
)
from cadastral_api.models.entities import FileStatus, LandRegistryUnitDetailed, ParcelInfo

FIXTURES = Path(__file__).resolve().parents[2] / "src" / "cadastral_api" / "tests" / "fixtures"


def _unit(name: str) -> LandRegistryUnitDetailed:
    raw = json.loads((FIXTURES / name).read_text())
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)


def _parcel(name: str) -> ParcelInfo:
    return ParcelInfo.model_validate(json.loads((FIXTURES / name).read_text()))


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("UKNJIŽBA, ZALOŽNO PRAVO, UGOVOR O KREDITU", "mortgage"),
        ("uknjižuje se hipoteka u iznosu", "mortgage"),
        ("UKNJIŽBA, ZALOŽNO PRAVO, RJEŠENJE OPĆINSKOG SUDA OVR-1260/24", "mortgage"),
        ("ZABILJEŽBA, OVRŠIVOST TRAŽBINE", "enforcement"),
        ("ZABILJEŽBA, POKRETANJE POSTUPKA ... OVR-12/25", "enforcement"),
        ("ZABILJEŽBA, SPOR, TUŽBA ZAPRIMLJENA KOD OVOG SUDA", "dispute"),
        ("ZABILJEŽBA, ZABRANA OTUĐENJA I OPTEREĆENJA", "transfer_prohibition"),
        ("ZABILJEŽBA, PRAVO PRVOKUPA", "preemption"),
        ("ZABILJEŽBA, NEKRETNINA JE KULTURNO DOBRO", "preemption"),
        ("ZABILJEŽBA, TRAŽBINA SOCIJALNE POMOĆI", "social_claim"),
        ("UKNJIŽBA, OSOBNA SLUŽNOST – PRAVO STANOVANJA", "personal_servitude"),
        ("UKNJIŽBA, OSOBNA SLUŽNOST - PRAVO PLODOUŽIVANJA", "personal_servitude"),
        ("ZABILJEŽBA, DOŽIVOTNO UZDRŽAVANJE, UGOVOR", "personal_servitude"),
        ("uknjižuje se pravo služnosti prolaza", "easement"),
        (
            "Zabilježuje se da je prijenos prava vlasništva izvršen radi osiguranja",
            "fiduciary_transfer",
        ),
        ("ZABILJEŽBA, ODBIJENI PRIJEDLOG ZA UKNJIŽBU", "rejected_request"),
        ("ZABILJEŽBA, odbijene provedbe rješenja o nasljeđivanju", "rejected_request"),
        ("Zabilježuje se tražbina u korist", "lien"),
        ("ZABILJEŽBA, NEŠTO NEPOZNATO", "other_annotation"),
        ("<span class='lr-entry-black' >Sporazum o kreditu", "other_annotation"),
    ],
)
def test_entry_text_is_classified(text: str, kind: str) -> None:
    got, basis = classify_entry_text(text)
    assert got == kind, basis
    assert basis


def test_severities_default_and_override() -> None:
    assert resolve_severities(None) == DEFAULT_SEVERITY
    assert resolve_severities({"easement": "blocking"})["easement"] == "blocking"
    with pytest.raises(ValueError):
        resolve_severities({"price": "blocking"})
    with pytest.raises(ValueError):
        resolve_severities({"easement": "high"})


def test_the_synthetic_unit_yields_every_kind_of_finding() -> None:
    unit = _unit("lr_unit_sale_blockers.json")
    result = detect_blockers(unit)
    assert result.verdict == "blocked"
    assert result.counts == {"blocking": 3, "conditional": 5, "informational": 3}
    kinds = [(b.kind, b.scope, b.share_order_number, b.condominium_unit) for b in result.blockers]
    assert kinds == [
        ("pending_entry", "unit", None, None),
        ("pending_entry", "share", "3", "E-2"),
        ("mortgage", "share", "1", None),
        ("other_annotation", "share", "3", "E-2"),
        ("preemption", "unit", None, None),
        ("other_annotation", "unit", None, None),
        ("other_annotation", "unit", None, None),
        ("likely_estate", "share", "3", "E-2"),
        ("likely_estate", "share", "5", None),
        ("likely_estate", "share", "6", None),
        ("public_body_share", "share", "7", None),
    ]
    estates = [b for b in result.blockers if b.kind == "likely_estate"]
    assert [b.beneficiary for b in estates] == [
        "POKOJNI HORVAT MARKO",
        "KOVAČ PETAR",
        "BABIĆ JOSIP",
    ]
    assert "pokojni" in estates[0].basis and "ostavina" in estates[0].description
    assert any("estate" in note for note in result.notes)
    mortgage = result.blockers[2]
    assert mortgage.amount == "50.000,00 EUR" and mortgage.amount_value == 50000.0
    assert mortgage.amount_currency == "EUR" and mortgage.beneficiary == "TESTNA BANKA d.d."
    assert mortgage.entry["diary_number"] == "Z-355/2023"
    assert mortgage.basis == "right type mortgage"
    preemption = result.blockers[4]
    assert preemption.beneficiary == "OPĆINA SALI"
    public = next(b for b in result.blockers if b.kind == "public_body_share")
    assert public.beneficiary == "REPUBLIKA HRVATSKA" and "1/24" in public.description
    assert "inferred" in public.basis
    # The deleting entry is visible and informational; the deleted one is cancelled.
    deleting = result.blockers[3]
    assert deleting.basis == "deletes entry 2.1"
    cancelled = [
        (b.kind, b.entry["order_number"], b.cancelled_by) for b in result.blockers_cancelled
    ]
    assert cancelled == [("mortgage", "2.1", "2.2")]
    # A deletion that names no sibling stays in the list, flagged in its basis.
    unnamed = result.blockers[5]
    assert "does not name" in unnamed.basis
    assert result.plombe_detail_included is False
    assert any("blockers_cancelled" in note for note in result.notes)
    assert any("plomba detail" in note for note in result.notes)
    assert any("other_annotation" in note for note in result.notes)
    assert result.rule.startswith("blocked when")


def test_a_key_phrase_split_by_html_is_still_classified() -> None:
    unit = _unit("lr_unit_encumbrances.json")
    group = unit.encumbrance_sheet_c.lr_entry_groups[0]
    group.lr_entries[0].description = (
        "<span class='lr-entry-black' >Zaprimljeno 01.01.2020.g. pod brojem Z-1/2020 "
        "ZABILJEŽBA, PRAVO<br>PRVOKUPA, u korist: OPĆINA SALI"
    )
    group.right_type = None
    result = detect_blockers(unit)
    assert [b.kind for b in result.blockers if b.source != "ownership"] == ["preemption"]


def test_a_deletion_of_a_deletion_cancels_the_deleting_entry_too() -> None:
    unit = _unit("lr_unit_sale_blockers.json")
    group = unit.encumbrance_sheet_c.lr_entry_groups[1]  # 2.1 mortgage, 2.2 deletes 2.1
    revival = group.lr_entries[1].model_copy(
        update={
            "order_number": "2.3",
            "description": "Zaprimljeno 01.03.2016.g. pod brojem Z-30/2016 Briše se brisanje "
            "upisano pod st. 2.2.",
        }
    )
    group.lr_entries.append(revival)
    result = detect_blockers(unit)
    cancelled = {b.entry["order_number"]: b.cancelled_by for b in result.blockers_cancelled}
    assert cancelled == {"2.1": "2.2", "2.2": "2.3"}
    assert [b.entry["order_number"] for b in result.blockers if b.source == "sheet_c"] == [
        "1.1",
        "2.3",
        "3.1",
        "4.1",
        "5.1",
    ]


def test_an_old_personal_servitude_is_flagged_likely_lapsed() -> None:
    from datetime import date

    unit = _unit("lr_unit_encumbrances.json")
    group = unit.encumbrance_sheet_c.lr_entry_groups[0]
    group.lr_entries[0].description = (
        "<span class='lr-entry-black' >Pr. 20. srpnja 1979. Z 2444/79 Na temelju rješenja o "
        "nasljeđivanju od 27. studenog 1967. pod brojem O 533/67, Općinskog suda u Zadru, "
        "uknjižuje se pravo ploduživanja u korist:"
    )
    group.lr_entries[0].entry_date = date(1979, 7, 20)
    group.right_type = None
    result = detect_blockers(unit, today=date(2026, 9, 15))
    blocker = result.blockers[0]
    assert blocker.kind == "personal_servitude" and blocker.severity == "conditional"
    assert blocker.likely_lapsed is True
    assert "47 years ago" in blocker.basis and "death certificate" in blocker.basis
    assert any("likely lapsed" in note for note in result.notes)
    # A recent one is not.
    group.lr_entries[0].entry_date = date(2020, 2, 14)
    assert detect_blockers(unit, today=date(2026, 9, 15)).blockers[0].likely_lapsed is False


def test_a_cadastre_case_behind_a_plomba_is_named() -> None:
    unit = _unit("lr_unit_sale_blockers.json")
    status = FileStatus.model_validate(
        {
            "lrFileNumber": "Z-100/2026",
            "registrationNumber": "UP/I-932-07/26-01/12",
            "statusDescription": "ZAPRIMANJE DODATNIH PODATAKA",
        }
    )
    result = detect_blockers(unit, plombe_detail={"Z-100/2026": status})
    first = result.blockers[0]
    assert first.file_number == "Z-100/2026"
    assert "cadastre administrative case" in first.basis and "survey" in first.basis
    assert result.blockers[1].basis == "a request for registration is pending on the unit"


def test_plombe_detail_names_the_pending_request() -> None:
    unit = _unit("lr_unit_sale_blockers.json")
    status = FileStatus.model_validate(
        json.loads((FIXTURES / "file_status_pending.json").read_text())
    )
    result = detect_blockers(unit, plombe_detail={"Z-100/2026": status})
    assert result.plombe_detail_included is True
    first, second = result.blockers[0], result.blockers[1]
    assert first.file_number == "Z-100/2026"
    assert first.request_kind == status.application_content
    assert first.status_description == status.status_description
    assert first.dates["received"] is not None
    assert second.request_kind is None and "kind unknown" in second.description


def test_condominium_scope_keeps_the_flats_own_and_unit_wide_blockers() -> None:
    unit = _unit("lr_unit_condominium.json")
    whole = detect_blockers(unit)
    assert whole.verdict == "blocked"
    assert whole.counts["blocking"] == 36
    assert {b.kind for b in whole.blockers} >= {
        "pending_entry",
        "mortgage",
        "personal_servitude",
        "transfer_prohibition",
        "enforcement",
        "dispute",
        "fiduciary_transfer",
        "rejected_request",
    }
    flat_80 = detect_blockers(unit, condominium_unit="E-80")
    assert flat_80.scope_filter == {"condominium_unit": "E-80"}
    assert all(
        b.scope == "unit" or b.condominium_unit == "E-80" or b.share_order_number == "80"
        for b in flat_80.blockers
    )
    assert sum(1 for b in flat_80.blockers if b.kind == "pending_entry") == 3
    assert any(b.kind == "dispute" for b in flat_80.blockers)
    # A unit-wide note (the rejected request on sheet B) is counted for every flat.
    assert any(b.kind == "rejected_request" and b.scope == "unit" for b in flat_80.blockers)
    assert any("left out" in note for note in flat_80.notes)
    flat_40 = detect_blockers(unit, condominium_unit="40")
    assert {b.kind for b in flat_40.blockers if b.scope == "share"} == {
        "mortgage",
        "personal_servitude",
    }
    assert not any(b.kind == "dispute" for b in flat_40.blockers)
    nobody = detect_blockers(unit, condominium_unit="E-9999")
    assert all(b.scope == "unit" for b in nobody.blockers)
    assert any("matches no share" in note for note in nobody.notes)


def test_owner_name_scope_and_blank_filters() -> None:
    unit = _unit("lr_unit_sale_blockers.json")
    result = detect_blockers(unit, owner_name="horvat ivan")
    assert result.scope_filter == {"owner_name": "horvat ivan"}
    assert [b.kind for b in result.blockers if b.scope == "share"] == ["mortgage"]
    with pytest.raises(ValueError):
        detect_blockers(unit, owner_name="   ")
    with pytest.raises(ValueError):
        detect_blockers(unit, condominium_unit="()")


def test_real_units_read_as_expected() -> None:
    social = detect_blockers(_unit("lr_unit_encumbrances.json"))
    assert [b.kind for b in social.blockers] == ["social_claim"] + ["likely_estate"] * 3
    assert social.blockers[0].share_order_number == "1"
    assert social.blockers[0].beneficiary == "REPUBLIKE HRVATSKE"
    # The three owners carried over from an earlier unit are estates to expect.
    assert all("carried over" in b.basis for b in social.blockers[1:])
    plomba_only = detect_blockers(_unit("lr_unit_lrparcels.json"))
    assert [b.kind for b in plomba_only.blockers] == ["pending_entry"]
    assert plomba_only.verdict == "blocked"
    share_note = detect_blockers(_unit("lr_unit_share_entries.json"))
    assert {b.kind for b in share_note.blockers if b.source != "ownership"} == {
        "pending_entry",
        "rejected_request",
    }


def test_merge_and_identity() -> None:
    base = detect_blockers(_unit("lr_unit_encumbrances.json"))
    extra = Blocker(
        kind="owner_not_possessor",
        severity="conditional",
        scope="unit",
        source="register_comparison",
        description="x",
        basis="y",
    )
    merged = merge_blockers(base, [extra])
    assert len(merged.blockers) == len(base.blockers) + 1
    assert merged.counts["conditional"] == base.counts["conditional"] + 1
    assert blocker_identity(base.blockers[0]) == ("social_claim", "share", "1", None, "1.1")
    assert merged.model_dump(mode="json")["verdict"] == "blocked"


def test_comparison_adds_the_people_blockers_and_the_flag_counts() -> None:
    parcel, unit = _parcel("parcel_info_linked.json"), _unit("lr_unit_lrparcels.json")
    result = compare_registers(parcel, unit)
    assert result.sale_blockers is not None
    kinds = [b.kind for b in result.sale_blockers.blockers]
    assert kinds[0] == "pending_entry"
    assert kinds.count("owner_not_possessor") == len(result.owners_only) == 4
    first_owner_blocker = result.sale_blockers.blockers[1]
    assert first_owner_blocker.share_order_number == result.owners[0].share_order_number
    assert result.owner_flag_counts == {
        "owners": 4,
        "likely_deceased": 0,
        "address_abroad": 0,
        "address_unknown": 0,
        "public_body": 0,
    }
    assert all(o.flags is not None for o in result.owners)
    assert all(p.flags is None for p in result.possessors)
    without_unit = compare_registers(parcel, None)
    assert without_unit.sale_blockers is None and without_unit.owner_flag_counts is None


def test_assembly_scores_read_the_blockers_and_rank_the_flags() -> None:
    parcel, unit = _parcel("parcel_info_linked.json"), _unit("lr_unit_sale_blockers.json")
    item = AssemblyInput(parcel, unit, compare_registers(parcel, unit))
    score = acquisition_score(item)
    assert score.factors["no_pending_plombe"] is False
    assert score.factors["no_encumbrances"] is False  # a mortgage and a pre-emption right
    # Only informational notes: the encumbrance factor is not counted against the parcel.
    unit.active_plumbs = []
    unit.encumbrance_sheet_c.lr_entry_groups = unit.encumbrance_sheet_c.lr_entry_groups[3:]
    item = AssemblyInput(parcel, unit, compare_registers(parcel, unit))
    score = acquisition_score(item)
    assert score.factors["no_pending_plombe"] is True
    assert score.factors["no_encumbrances"] is True
    analysis = build_assembly([item])
    summary = analysis.parcels[0]
    assert summary.sale_verdict == "conditional"  # the public body and the owners not possessing
    assert summary.blocker_counts["conditional"] >= 1
    assert "public_body_share" in summary.blocker_kinds
    assert analysis.totals.parcels_by_verdict == {"conditional": 1}
    persons = {p.name: p for p in analysis.persons}
    assert persons["POKOJNI HORVAT MARKO"].likely_deceased is True
    assert persons["KOVAČ ANA"].address_abroad is True
    assert persons["REPUBLIKA HRVATSKA"].likely_deceased is None
    assert analysis.totals.persons_likely_deceased == 3
    assert analysis.totals.persons_address_abroad == 2
    groups = {g.surname: g for g in analysis.surname_groups}
    assert groups["horvat"].likely_deceased_count == 1
    assert groups["kovac"].address_abroad_count == 2
    assert any("likely_deceased" in note for note in analysis.notes)
    assert "sale_verdict" in parcels_csv(analysis).splitlines()[0]
    assert "likely_deceased" in persons_csv(analysis).splitlines()[0]
