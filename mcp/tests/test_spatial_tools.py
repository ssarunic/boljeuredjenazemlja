"""find_parcels_in_area and find_parcel_neighbours over a synthetic municipality."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "tests"))
from cadastral_api.gis import ParcelIndex  # noqa: E402
from helpers import grid_parcels, square_parcel  # noqa: E402

from cadastral_mcp.tools import CadastralTools  # noqa: E402

OX, OY = 400000.0, 4900000.0


def _tools() -> CadastralTools:
    index = ParcelIndex(grid_parcels(3, 3) + [square_parcel("far", OX + 100.0, OY)])
    client = MagicMock()
    client.get_parcel_index.return_value = index
    client.gis_cache.get_source.return_value = "http://localhost:8000"
    client.gis_cache.downloaded_at.return_value = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    tools = CadastralTools(client)
    tools._resolve_municipality = lambda name_or_code: "334979"  # type: ignore[method-assign]
    return tools


def _run(coro):
    return asyncio.run(coro)


def test_bbox_query_pages_and_totals() -> None:
    res = _run(
        _tools().find_parcels_in_area(
            "SAVAR", bbox=[OX + 5, OY + 5, OX + 15, OY + 15], limit=3
        )
    )
    assert res["municipality_code"] == "334979"
    assert res["query"] == {"bbox": [OX + 5, OY + 5, OX + 15, OY + 15], "relation": "intersects"}
    assert res["total"] == 4 and res["total_area_m2"] == 400.0
    assert [p["parcel_number"] for p in res["parcels"]] == ["1/1", "1/2", "2/1"]
    assert res["page"] == {
        "offset": 0, "limit": 3, "total": 4, "returned": 3, "truncated": True, "next_offset": 3,
    }
    row = res["parcels"][0]
    assert row["area_m2"] == 100.0 and row["centroid"] == [OX + 5.0, OY + 5.0]
    assert row["bounds"] == [OX, OY, OX + 10.0, OY + 10.0]
    assert row["map_url"].startswith("https://oss.uredjenazemlja.hr/map?center=")
    assert "distance_m" not in row
    dataset = res["dataset"]
    assert dataset["parcel_count"] == 10 and dataset["crs"] == "EPSG:3765"
    assert dataset["downloaded_at"] == "2026-09-15T12:00:00+00:00"
    assert dataset["source"] == "http://localhost:8000"
    assert "geojson" not in res


def test_polygon_query_accepts_wkt_and_within() -> None:
    # A triangle whose hypotenuse is x + y = 24 (relative): the corner parcel
    # 1/1 (far corner at 10 + 10) lies inside it; the parcels along the two
    # axes and 2/2 (near corner at 10 + 10) touch it.
    wkt = f"POLYGON(({OX - 1} {OY - 1}, {OX + 25} {OY - 1}, {OX - 1} {OY + 25}, {OX - 1} {OY - 1}))"
    res = _run(_tools().find_parcels_in_area("SAVAR", polygon=wkt, relation="within"))
    assert [p["parcel_number"] for p in res["parcels"]] == ["1/1"]
    assert len(res["query"]["polygon"]) == 3
    res = _run(
        _tools().find_parcels_in_area(
            "SAVAR", polygon=[[OX - 1, OY - 1], [OX + 25, OY - 1], [OX - 1, OY + 25]],
            include_geojson=True,
        )
    )
    numbers = [p["parcel_number"] for p in res["parcels"]]
    assert numbers == ["1/1", "1/2", "1/3", "2/1", "2/2", "3/1"]
    assert res["geojson"]["type"] == "FeatureCollection"
    assert len(res["geojson"]["features"]) == 6
    assert res["geojson"]["features"][0]["properties"]["parcel_number"] == "1/1"


def test_radius_query_carries_distances() -> None:
    res = _run(
        _tools().find_parcels_in_area("SAVAR", center=[OX + 15, OY + 15], radius_m=6)
    )
    assert res["query"] == {"center": [OX + 15.0, OY + 15.0], "radius_m": 6.0}
    assert [(p["parcel_number"], p["distance_m"]) for p in res["parcels"]] == [
        ("2/2", 0.0), ("1/2", 5.0), ("2/1", 5.0), ("2/3", 5.0), ("3/2", 5.0),
    ]


@pytest.mark.parametrize(
    "kwargs, fragment",
    [
        ({}, "exactly one area"),
        ({"bbox": [0, 0, 1, 1], "center": [OX, OY], "radius_m": 5}, "exactly one area"),
        ({"center": [OX, OY]}, "go together"),
        ({"bbox": [OX, OY, OX + 1]}, "min_x, min_y, max_x, max_y"),
        ({"bbox": [OX + 1, OY, OX, OY + 1]}, "min <= max"),
        ({"bbox": [15.98, 45.81, 16.0, 45.9]}, "longitude/latitude"),
        ({"center": [15.98, 45.81], "radius_m": 5}, "longitude/latitude"),
        ({"center": [OX, OY], "radius_m": 0}, "positive"),
        ({"polygon": [[OX, OY], [OX + 1, OY]]}, "three"),
        ({"bbox": [OX, OY, OX + 1, OY + 1], "relation": "near"}, "relation"),
        ({"bbox": [OX, OY, OX + 1, OY + 1], "limit": 0}, "limit"),
    ],
)
def test_area_query_validation(kwargs, fragment) -> None:
    with pytest.raises(ValueError) as excinfo:
        _run(_tools().find_parcels_in_area("SAVAR", **kwargs))
    assert fragment in str(excinfo.value)


def test_neighbours_of_the_middle_parcel() -> None:
    res = _run(_tools().find_parcel_neighbours("2/2", "SAVAR", limit=5, include_geojson=True))
    assert res["parcel"]["parcel_number"] == "2/2"
    assert res["total"] == 8 and res["total_area_m2"] == 800.0
    assert res["tolerance_m"] == 0.10
    rows = res["neighbours"]
    assert len(rows) == 5 and res["page"]["truncated"] is True
    assert all(r["shared_boundary_m"] == 10.0 and r["touches_at_point"] is False for r in rows[:4])
    assert rows[4]["shared_boundary_m"] == 0.0 and rows[4]["touches_at_point"] is True
    # Seed first, then the page.
    numbers = [f["properties"]["parcel_number"] for f in res["geojson"]["features"]]
    assert numbers[0] == "2/2" and len(numbers) == 6


def test_neighbours_of_an_unknown_parcel_is_a_clear_error() -> None:
    with pytest.raises(ValueError) as excinfo:
        _run(_tools().find_parcel_neighbours("999", "SAVAR"))
    assert "999" in str(excinfo.value) and "334979" in str(excinfo.value)


def test_index_failure_is_a_clear_error() -> None:
    tools = _tools()
    tools.client.get_parcel_index.side_effect = OSError("connection refused")
    with pytest.raises(ValueError) as excinfo:
        _run(tools.find_parcels_in_area("SAVAR", bbox=[OX, OY, OX + 1, OY + 1]))
    assert "connection refused" in str(excinfo.value)
