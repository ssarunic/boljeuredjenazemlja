"""ParcelIndex: parcels by bounding box, polygon, radius and adjacency."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from helpers import grid_parcels, square_parcel  # noqa: E402

from cadastral_api.gis import ParcelIndex  # noqa: E402

OX, OY = 400000.0, 4900000.0


@pytest.fixture
def index() -> ParcelIndex:
    # A 3 x 3 grid of 10 m squares, plus one parcel 100 m away.
    parcels = grid_parcels(3, 3) + [square_parcel("far", OX + 100.0, OY)]
    return ParcelIndex(parcels, cell_size=10.0)


def _numbers(items) -> list[str]:
    return sorted(item.parcel_number for item in items)


def test_index_holds_every_parcel_and_finds_by_number(index: ParcelIndex) -> None:
    assert len(index) == 10
    assert index.by_number("2/2") is not None
    assert index.by_number("2/2").centroid == (OX + 15.0, OY + 15.0)
    assert index.by_number("nope") is None
    assert ParcelIndex([]).parcels == []


def test_bbox_intersects_and_within(index: ParcelIndex) -> None:
    box = (OX + 5.0, OY + 5.0, OX + 15.0, OY + 15.0)
    assert _numbers(index.in_bbox(box)) == ["1/1", "1/2", "2/1", "2/2"]
    assert index.in_bbox(box, "within") == []
    whole_middle = (OX + 10.0, OY + 10.0, OX + 20.0, OY + 20.0)
    assert _numbers(index.in_bbox(whole_middle, "within")) == ["2/2"]
    # Touching the edge counts as intersecting: the whole middle row and column.
    assert len(index.in_bbox(whole_middle)) == 9
    with pytest.raises(ValueError):
        index.in_bbox((1.0, 1.0, 0.0, 0.0))


def test_polygon_query(index: ParcelIndex) -> None:
    # Hypotenuse x + y = 24 (relative): 1/1 lies inside; 1/2, 1/3, 2/1, 3/1
    # and 2/2 (its near corner at 10 + 10) touch it.
    triangle = [(OX - 1.0, OY - 1.0), (OX + 25.0, OY - 1.0), (OX - 1.0, OY + 25.0)]
    assert _numbers(index.in_polygon(triangle)) == ["1/1", "1/2", "1/3", "2/1", "2/2", "3/1"]
    assert _numbers(index.in_polygon(triangle, "within")) == ["1/1"]
    # A parcel is within an area whose boundary it shares.
    own_outline = [(OX, OY), (OX + 10.0, OY), (OX + 10.0, OY + 10.0), (OX, OY + 10.0)]
    assert _numbers(index.in_polygon(own_outline, "within")) == ["1/1"]
    # A concave area: an L shape around the middle parcel excludes it even
    # though its vertices lie on the L's boundary.
    ell = [(OX, OY), (OX + 30.0, OY), (OX + 30.0, OY + 10.0), (OX + 10.0, OY + 10.0),
           (OX + 10.0, OY + 30.0), (OX, OY + 30.0)]
    assert _numbers(index.in_polygon(ell, "within")) == ["1/1", "1/2", "1/3", "2/1", "3/1"]
    with pytest.raises(ValueError):
        index.in_polygon([(0.0, 0.0), (1.0, 1.0)])


def test_within_radius_orders_by_distance(index: ParcelIndex) -> None:
    hits = index.within_radius(OX + 15.0, OY + 15.0, 6.0)
    assert [(hit.parcel.parcel_number, hit.distance_m) for hit in hits] == [
        ("2/2", 0.0),
        ("1/2", 5.0),
        ("2/1", 5.0),
        ("2/3", 5.0),
        ("3/2", 5.0),
    ]
    assert len(index.within_radius(OX + 15.0, OY + 15.0, 8.0)) == 9  # corners at 7.07 m
    assert [h.parcel.parcel_number for h in index.within_radius(OX + 95.0, OY + 5.0, 6.0)] == [
        "far"
    ]
    with pytest.raises(ValueError):
        index.within_radius(OX, OY, 0.0)


def test_neighbours_share_edges_or_corners(index: ParcelIndex) -> None:
    around = index.neighbours("2/2")
    by_number = {n.parcel.parcel_number: n for n in around}
    assert sorted(by_number) == ["1/1", "1/2", "1/3", "2/1", "2/3", "3/1", "3/2", "3/3"]
    for number in ("1/2", "2/1", "2/3", "3/2"):
        assert by_number[number].shared_boundary_m == 10.0
        assert by_number[number].touches_at_point is False
    for number in ("1/1", "1/3", "3/1", "3/3"):
        assert by_number[number].shared_boundary_m == 0.0
        assert by_number[number].touches_at_point is True
    # Edge neighbours come first.
    assert [n.touches_at_point for n in around] == [False] * 4 + [True] * 4
    assert _numbers(n.parcel for n in index.neighbours("1/1")) == ["1/2", "2/1", "2/2"]
    assert index.neighbours("far") == []
    with pytest.raises(KeyError):
        index.neighbours("nope")


def test_total_area(index: ParcelIndex) -> None:
    assert ParcelIndex.total_area(index.parcels) == 1000.0
    assert ParcelIndex.total_area(index.in_bbox((OX, OY, OX + 10.0, OY + 10.0), "within")) == 100.0


def test_degenerate_outlines_are_skipped() -> None:
    from cadastral_api.models.gis_entities import ParcelGeometry

    line = ParcelGeometry(
        cestica_id="x", broj_cestice="line", povrsina_graficka=0.0, maticni_broj_ko="1",
        coordinates=[{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 1.0}],
    )
    assert len(ParcelIndex([line, square_parcel("ok", 0.0, 0.0)])) == 1
