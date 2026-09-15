"""Distances, shared boundaries, centroids and ring parsing (pure geometry)."""

from __future__ import annotations

import math

import pytest

from cadastral_api.gis.geometry_ops import (
    parse_ring,
    point_ring_distance,
    point_segment_distance,
    ring_centroid,
    ring_distance,
    segment_distance,
    shared_boundary_length,
)

SQUARE = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]
EAST = [(10.0, 0.0), (20.0, 0.0), (20.0, 10.0), (10.0, 10.0)]  # shares the x=10 edge
CORNER = [(10.0, 10.0), (20.0, 10.0), (20.0, 20.0), (10.0, 20.0)]  # touches at (10, 10)
FAR = [(30.0, 0.0), (40.0, 0.0), (40.0, 10.0), (30.0, 10.0)]
HALF_EAST = [(10.0, 2.0), (20.0, 2.0), (20.0, 7.0), (10.0, 7.0)]  # shares 5 m of the edge


def test_point_segment_distance() -> None:
    assert point_segment_distance((5.0, 3.0), (0.0, 0.0), (10.0, 0.0)) == 3.0
    assert point_segment_distance((15.0, 0.0), (0.0, 0.0), (10.0, 0.0)) == 5.0
    assert point_segment_distance((1.0, 1.0), (2.0, 2.0), (2.0, 2.0)) == pytest.approx(math.sqrt(2))


def test_segment_distance_is_zero_when_touching() -> None:
    assert segment_distance((0, 0), (10, 0), (5, -5), (5, 5)) == 0.0
    assert segment_distance((0, 0), (10, 0), (0, 3), (10, 3)) == 3.0


def test_point_ring_distance() -> None:
    assert point_ring_distance(5.0, 5.0, SQUARE) == 0.0  # inside
    assert point_ring_distance(15.0, 5.0, SQUARE) == 5.0
    assert point_ring_distance(13.0, 14.0, SQUARE) == 5.0  # to the corner (10, 10)
    assert point_ring_distance(0.0, 0.0, [(0.0, 0.0), (1.0, 1.0)]) == math.inf


def test_ring_distance() -> None:
    assert ring_distance(SQUARE, EAST) == 0.0
    assert ring_distance(SQUARE, CORNER) == 0.0
    assert ring_distance(SQUARE, FAR) == 20.0


def test_ring_centroid() -> None:
    assert ring_centroid(SQUARE) == (5.0, 5.0)
    assert ring_centroid([(0.0, 0.0), (10.0, 0.0), (0.0, 10.0)]) == pytest.approx((10 / 3, 10 / 3))
    assert ring_centroid([(0.0, 0.0), (4.0, 0.0)]) == (2.0, 0.0)  # degenerate: bbox centre


def test_shared_boundary_length() -> None:
    assert shared_boundary_length(SQUARE, EAST) == 10.0
    assert shared_boundary_length(EAST, SQUARE) == 10.0
    assert shared_boundary_length(SQUARE, HALF_EAST) == 5.0
    assert shared_boundary_length(SQUARE, CORNER) == 0.0
    assert shared_boundary_length(SQUARE, FAR) == 0.0
    # A digitising gap within the tolerance still counts.
    shifted = [(x + 0.05, y) for x, y in EAST]
    assert shared_boundary_length(SQUARE, shifted, tolerance=0.10) == 10.0
    assert shared_boundary_length(SQUARE, shifted, tolerance=0.01) == 0.0


def test_parse_ring_from_wkt_and_lists() -> None:
    wkt = "POLYGON((0 0, 10 0, 10 10, 0 10, 0 0))"
    assert parse_ring(wkt) == SQUARE
    assert parse_ring([[0, 0], [10, 0], [10, 10], [0, 10]]) == SQUARE
    assert parse_ring("polygon ((0 0,10 0,10 10))") == [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]
    with pytest.raises(ValueError):
        parse_ring("LINESTRING(0 0, 1 1)")
    with pytest.raises(ValueError):
        parse_ring([[0, 0], [10, 0]])
    with pytest.raises(ValueError):
        parse_ring([[0, 0, 1], [10, 0], [10, 10]])
    with pytest.raises(ValueError):
        parse_ring("POLYGON((0 0 0, 1 1, 2 2))")
