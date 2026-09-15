"""build_assembly: matrix, ranking, scores and exports over a small set of parcels."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import pytest

from cadastral_api.analysis import (
    DEFAULT_WEIGHTS,
    AssemblyInput,
    acquisition_score,
    build_assembly,
    compare_registers,
    matrix_csv,
    parcels_csv,
    parcels_geojson,
    persons_csv,
    resolve_weights,
)
from cadastral_api.models.entities import LandRegistryUnitDetailed, ParcelInfo
from cadastral_api.models.gis_entities import ParcelGeometry
from cadastral_api.models.planning_entities import (
    ParcelZoning,
    PlanningDataset,
    PlanningZone,
    ZoneKind,
    ZoneMatch,
    ZoningStatus,
)

FIXTURES = Path(__file__).resolve().parents[2] / "src" / "cadastral_api" / "tests" / "fixtures"


def _parcel(name: str) -> ParcelInfo:
    return ParcelInfo.model_validate(json.loads((FIXTURES / name).read_text()))


def _unit(name: str) -> LandRegistryUnitDetailed:
    raw = json.loads((FIXTURES / name).read_text())
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)


def _keep_possessors(parcel: ParcelInfo, names: list[str]) -> None:
    sheet = parcel.possession_sheets[0]
    sheet.possessors = sheet.possessors[: len(names)]
    for possessor, name in zip(sheet.possessors, names, strict=True):
        possessor.name = name
    for other in parcel.possession_sheets[1:]:
        other.possessors = []


def _zoning(number: str, inside: bool) -> ParcelZoning:
    zone = PlanningZone(
        zone_kind=ZoneKind.SETTLEMENT, designation_code="GPN", plan_name="PPUO SALI"
    )
    return ParcelZoning(
        parcel_number=number,
        municipality_code="334979",
        status=ZoningStatus.INSIDE_SETTLEMENT if inside else ZoningStatus.OUTSIDE,
        in_building_area=inside,
        matches=[ZoneMatch(zone=zone, overlap_fraction=1.0)] if inside else [],
        dataset=PlanningDataset(name="test"),
    )


@pytest.fixture
def items() -> list[AssemblyInput]:
    # A: 1122/1, unit 449 (4 owner records, 3 people, pending plomba), possessors
    #    disjoint from the owners; inside a building area.
    a_parcel, a_unit = _parcel("parcel_info_linked.json"), _unit("lr_unit_lrparcels.json")
    _keep_possessors(a_parcel, ["Posjednik 2", "Posjednik 3"])
    a = AssemblyInput(
        a_parcel, a_unit, compare_registers(a_parcel, a_unit), _zoning("1122/1", True)
    )
    # B: 1139/4 (cadastre area 1848665), unit 625 (5 owners, no sheet C, no plomba);
    #    its one possessor is owner "Vlasnik 117" (share 4/8); outside building areas.
    b_parcel, b_unit = _parcel("parcel_info_direct.json"), _unit("lr_unit_cadparcels.json")
    _keep_possessors(b_parcel, ["vlasnik 117"])
    b = AssemblyInput(
        b_parcel, b_unit, compare_registers(b_parcel, b_unit), _zoning("1139/4", False)
    )
    # C: a cadastre-only parcel (no unit), possessed by "Vlasnik 117" too; no zoning.
    c_parcel = _parcel("parcel_info_direct.json")
    c_parcel.parcel_number = "1139/5"
    c_parcel.area = "1000"
    _keep_possessors(c_parcel, ["VLASNIK 117"])
    c = AssemblyInput(c_parcel, None, compare_registers(c_parcel, None), None, map_url="http://m")
    return [a, b, c]


def test_scores_leave_unevaluated_factors_out(items) -> None:
    a, b, c = items
    score_a = acquisition_score(a)
    assert score_a.factors == {
        "single_owner": False,
        "owner_is_possessor": False,
        "no_encumbrances": True,
        "no_pending_plombe": False,
        "in_building_area": True,
    }
    assert score_a.weight_evaluated == 1.0 and score_a.score == 0.35
    score_b = acquisition_score(b)
    assert score_b.factors["owner_is_possessor"] is False  # overlapping, not same
    assert score_b.factors["no_encumbrances"] is True
    assert score_b.factors["no_pending_plombe"] is True
    assert score_b.score == 0.35  # 0.20 + 0.15 of 1.0
    score_c = acquisition_score(c)
    assert score_c.factors == {k: None for k in DEFAULT_WEIGHTS}
    assert score_c.score is None and score_c.weight_evaluated == 0.0
    assert any("no land-registry unit" in note for note in score_c.notes)
    # Without zoning the building-area factor drops out of the denominator.
    b.zoning = None
    assert acquisition_score(b).score == round(0.35 / 0.85, 3)


def test_weights_are_validated_and_applied(items) -> None:
    assert resolve_weights(None) == DEFAULT_WEIGHTS
    assert resolve_weights({"in_building_area": 0.5})["in_building_area"] == 0.5
    with pytest.raises(ValueError):
        resolve_weights({"price": 1.0})
    with pytest.raises(ValueError):
        resolve_weights({"single_owner": -1})
    with pytest.raises(ValueError):
        resolve_weights({k: 0 for k in DEFAULT_WEIGHTS})
    only_area = {k: 0.0 for k in DEFAULT_WEIGHTS} | {"in_building_area": 1.0}
    assert acquisition_score(items[0], only_area).score == 1.0
    assert acquisition_score(items[1], only_area).score == 0.0


def test_assembly_ranks_persons_and_parcels(items) -> None:
    analysis = build_assembly(items)
    assert [p.parcel_number for p in analysis.parcels] == ["1122/1", "1139/4", "1139/5"]
    assert analysis.parcels[2].score is None
    assert analysis.parcels[2].relationship == "cadastre_only"
    assert analysis.parcels[0].pending_plombe and analysis.parcels[0].has_pending_plombe is True
    assert analysis.parcels[0].designation_code == "GPN"
    assert analysis.parcels[0].plan_name == "PPUO SALI"
    assert analysis.parcels[2].zoning_status is None

    top = analysis.persons[0]
    assert top.name == "vlasnik 117" or top.name == "Vlasnik 117"
    assert top.owner_of == ["1139/4"] and top.possessor_of == ["1139/4", "1139/5"]
    assert top.owned_area_m2 == 0.5 * 1848665
    assert top.possessed_area_m2 == 1848665 + 1000
    assert top.controlled_area_m2 == 0.5 * 1848665 + 1000  # owned, plus the parcel only possessed
    assert top.surname == "vlasnik"
    keys = {p.key for p in analysis.persons}
    assert len(keys) == len(analysis.persons)
    # Owners of 1122/1 (3 people) + owners of 1139/4 (5) + 2 possessors of 1122/1.
    assert len(analysis.persons) == 10
    assert analysis.surname_groups[0].surname == "vlasnik"
    assert analysis.surname_groups[0].person_count == 8
    assert sum(g.person_count for g in analysis.surname_groups) == 10

    roles = {(c.person_key.split("#")[0], c.parcel_number): c.role for c in analysis.matrix}
    assert roles[("vlasnik 117", "1139/4")] == "both"
    assert roles[("vlasnik 117", "1139/5")] == "possessor"
    assert roles[("posjednik 2", "1122/1")] == "possessor"
    assert roles[("vlasnik 114", "1122/1")] == "owner"

    totals = analysis.totals
    assert totals.parcel_count == 3 and totals.total_area_m2 == 1618 + 1848665 + 1000
    assert totals.distinct_owners == 8 and totals.distinct_possessors == 3
    assert totals.distinct_people == 10
    assert totals.area_by_relationship == {
        "disjoint": 1618, "overlapping": 1848665, "cadastre_only": 1000,
    }
    assert totals.area_by_zoning_status == {"inside_settlement": 1618, "outside": 1848665}
    assert totals.parcels_with_pending_plombe == 1 and totals.parcels_with_encumbrances == 0
    assert totals.parcels_in_building_area == 1
    assert totals.party_types == {"individual": 10}
    assert set(analysis.weights) == set(DEFAULT_WEIGHTS)
    assert any("inferred" in note for note in analysis.notes)


def test_exports(items) -> None:
    analysis = build_assembly(items)
    parcels = list(csv.DictReader(io.StringIO(parcels_csv(analysis))))
    assert [row["parcel_number"] for row in parcels] == ["1122/1", "1139/4", "1139/5"]
    assert parcels[0]["lr_unit_number"] == "449" and parcels[0]["has_pending_plombe"] == "true"
    assert parcels[2]["score"] == "" and parcels[2]["lr_unit_number"] == ""
    persons = list(csv.DictReader(io.StringIO(persons_csv(analysis))))
    assert persons[0]["possessor_of"] == "1139/4;1139/5"
    assert persons[0]["party_type_inferred"] == "individual"
    matrix = list(csv.DictReader(io.StringIO(matrix_csv(analysis))))
    assert {row["role"] for row in matrix} == {"owner", "possessor", "both"}
    both = next(row for row in matrix if row["role"] == "both")
    assert both["owner_share"] == "4/8" and both["fuzzy"] == "false"

    geometry = ParcelGeometry(
        cestica_id="1", broj_cestice="1122/1", povrsina_graficka=1600.0, maticni_broj_ko="334979",
        coordinates=[{"x": 0, "y": 0}, {"x": 10, "y": 0}, {"x": 10, "y": 10}, {"x": 0, "y": 10}],
    )
    collection = parcels_geojson(analysis, {"1122/1": geometry})
    assert collection["type"] == "FeatureCollection"
    assert [f["properties"]["parcel_number"] for f in collection["features"]] == ["1122/1"]
    assert collection["features"][0]["properties"]["score"] == 0.35
    assert collection["skipped"] == ["1139/4", "1139/5"]
