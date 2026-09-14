"""get-zoning serializers: below-threshold zones appear in every structured form.

- CSV rows and GeoJSON features cover matches and below-threshold zones,
  each marked ``match`` or ``below_threshold``; a boundary case is never
  exported as an empty result.
- JSON without ``--show-geometry`` strips polygons from both collections.
- ``--min-overlap`` rejects NaN and infinity before anything else happens.

Run:
    cd cli && pytest tests/test_zoning_output.py
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any
from unittest.mock import MagicMock

import pytest
from cadastral_api.i18n import set_language
from cadastral_api.models.planning_entities import (
    ParcelZoning,
    PlanningDataset,
    PlanningZone,
    ZoneKind,
    ZoneMatch,
    ZoningStatus,
)
from click.testing import CliRunner

from cadastral_cli.commands import zoning as zoning_cmd
from cadastral_cli.main import cli

SQUARE = [
    [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}, {"x": 0, "y": 1}, {"x": 0, "y": 0}]
]
GPN = PlanningZone(
    feature_id="Gradj_podrucje_naselje.1",
    zone_kind=ZoneKind.SETTLEMENT,
    designation_code="GPN",
    zone_name="SAVAR",
    plan_name="PPUO SALI - III. ID",
    polygons=[SQUARE],
)
CAMP = PlanningZone(
    feature_id="Gradj_podrucje_izvan_naselja.12",
    zone_kind=ZoneKind.DETACHED,
    designation_code="T3",
    designation="GOSPODARSKA - UGOSTITELJSKO TURISTIČKA (KAMP)",
    zone_name="SAVAR - KAMP",
    plan_name="UPU KAMP - I. ID",
    polygons=[SQUARE],
)
BELOW_ONLY = ParcelZoning(
    parcel_number="45",
    municipality_code="334979",
    parcel_area_m2=981.0,
    status=ZoningStatus.TOUCHES_BELOW_THRESHOLD,
    in_building_area=False,
    below_threshold=[ZoneMatch(zone=CAMP, overlap_fraction=0.01, overlap_m2=9.8)],
    intersecting_zones=1,
    plans=["UPU KAMP - I. ID"],
    dataset=PlanningDataset(name="test"),
)
MIXED = ParcelZoning(
    parcel_number="45",
    municipality_code="334979",
    parcel_area_m2=981.0,
    status=ZoningStatus.INSIDE_SETTLEMENT,
    in_building_area=True,
    matches=[ZoneMatch(zone=GPN, overlap_fraction=0.5, overlap_m2=490.5)],
    below_threshold=[ZoneMatch(zone=CAMP, overlap_fraction=0.01, overlap_m2=9.8)],
    intersecting_zones=2,
    plans=["PPUO SALI - III. ID", "UPU KAMP - I. ID"],
    dataset=PlanningDataset(name="test"),
)


@pytest.fixture(autouse=True)
def english():
    set_language("en")
    yield
    set_language("hr")


def _fake_client(result: ParcelZoning | None, monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    client = MagicMock()
    client.get_parcel_zoning.return_value = result

    @contextmanager
    def make():
        yield client

    monkeypatch.setattr(zoning_cmd, "CadastralAPIClient", make)
    monkeypatch.setattr(zoning_cmd, "_resolve_municipality", lambda c, m: "334979")
    return client


def test_csv_rows_mark_matches_and_below_threshold_zones() -> None:
    rows = zoning_cmd._zoning_rows(MIXED)
    assert [(r["match"], r["designation_code"]) for r in rows] == [
        ("match", "GPN"),
        ("below_threshold", "T3"),
    ]
    assert all(r["buildability"] == "unknown" for r in rows)
    only_below = zoning_cmd._zoning_rows(BELOW_ONLY)
    assert len(only_below) == 1 and only_below[0]["match"] == "below_threshold"
    assert only_below[0]["status"] == "touches_below_threshold"


def test_geojson_features_cover_both_collections() -> None:
    collection = zoning_cmd._zoning_geojson(MIXED)
    kinds = [f["properties"]["match"] for f in collection["features"]]
    assert kinds == ["match", "below_threshold"]
    assert collection["properties"]["buildability"] == "unknown"
    assert len(zoning_cmd._zoning_geojson(BELOW_ONLY)["features"]) == 1


def _run(args: list[str]) -> Any:
    return CliRunner().invoke(cli, ["--lang", "en", "get-zoning", *args], catch_exceptions=False)


def test_json_strips_polygons_from_below_threshold_zones(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_client(MIXED, monkeypatch)
    result = _run(["45", "-m", "SAVAR", "--format", "json"])
    assert result.exit_code == 0, result.output
    document = json.loads(result.output)
    assert "polygons" not in document["matches"][0]["zone"]
    assert "polygons" not in document["below_threshold"][0]["zone"]
    with_geometry = _run(["45", "-m", "SAVAR", "--format", "json", "--show-geometry"])
    document = json.loads(with_geometry.output)
    assert document["below_threshold"][0]["zone"]["polygons"]


def test_table_lists_below_threshold_zones(monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_client(BELOW_ONLY, monkeypatch)
    result = _run(["45", "-m", "SAVAR"])
    assert result.exit_code == 0, result.output
    assert "Touches a building area, below the overlap threshold" in result.output
    assert "KAMP" in result.output and "1.0%" in result.output  # rich may wrap the line
    assert "Not determined (screening only)" in result.output


@pytest.mark.parametrize("bad", ["nan", "inf", "-1", "101"])
def test_min_overlap_rejects_nan_infinity_and_out_of_range(
    bad: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = _fake_client(MIXED, monkeypatch)
    result = CliRunner().invoke(
        cli, ["--lang", "en", "get-zoning", "45", "-m", "SAVAR", "--min-overlap", bad]
    )
    assert result.exit_code == 2, result.output
    client.get_parcel_zoning.assert_not_called()
