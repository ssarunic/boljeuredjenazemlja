"""Spatial queries over the parcels of one cadastral municipality.

The cadastre publishes every parcel outline of a municipality in one GML file
(the ATOM download, cached by ``GISCache``). Loaded once into this index, the
file answers the questions a parcel number cannot: which parcels lie inside
an area, which ones surround a parcel, how much land a set of parcels covers.
A bounding-box grid narrows every query to a few candidates before the exact
ring tests in ``geometry_ops`` run, so a municipality of ten thousand parcels
answers in milliseconds. Coordinates are EPSG:3765 metres throughout.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from ..models.gis_entities import ParcelGeometry
from .geometry_ops import (
    Point,
    Ring,
    _edges,
    point_ring_distance,
    ring_bounds,
    ring_centroid,
    ring_distance,
    rings_intersect,
    shared_boundary_length,
)

Bounds = tuple[float, float, float, float]
#: How a parcel must relate to the query area: touch it anywhere, or lie wholly inside.
Relation = Literal["intersects", "within"]

#: Below this shared length (metres) two touching parcels are corner neighbours.
CORNER_LENGTH_M = 0.5


@dataclass(frozen=True)
class IndexedParcel:
    """One parcel as the index holds it: its outline and the derived figures."""

    geometry: ParcelGeometry
    ring: list[Point]
    bounds: Bounds
    centroid: Point

    @property
    def parcel_number(self) -> str:
        return self.geometry.broj_cestice

    @property
    def area_m2(self) -> float:
        return self.geometry.povrsina_graficka


@dataclass(frozen=True)
class Neighbour:
    """A parcel touching the one asked about."""

    parcel: IndexedParcel
    #: Length of the common boundary in metres (0 for a corner touch).
    shared_boundary_m: float
    #: True when the two parcels meet at a point only.
    touches_at_point: bool


@dataclass(frozen=True)
class RadiusHit:
    """A parcel within a radius of a point."""

    parcel: IndexedParcel
    #: Distance from the point to the parcel's outline (0 when the point is inside it).
    distance_m: float


def _bounds_overlap(a: Bounds, b: Bounds, margin: float = 0.0) -> bool:
    return not (
        a[2] + margin < b[0] or b[2] + margin < a[0] or a[3] + margin < b[1] or b[3] + margin < a[1]
    )


class ParcelIndex:
    """The parcels of one municipality, queryable by area and adjacency."""

    def __init__(self, parcels: Iterable[ParcelGeometry], cell_size: float = 100.0) -> None:
        self.cell_size = cell_size
        self._parcels: list[IndexedParcel] = []
        self._by_number: dict[str, IndexedParcel] = {}
        self._cells: dict[tuple[int, int], list[int]] = {}
        for geometry in parcels:
            ring = geometry.ring
            if len(ring) < 3:
                continue
            item = IndexedParcel(geometry, ring, ring_bounds(ring), ring_centroid(ring))
            index = len(self._parcels)
            self._parcels.append(item)
            self._by_number.setdefault(item.parcel_number, item)
            for cell in self._cells_of(item.bounds):
                self._cells.setdefault(cell, []).append(index)

    def __len__(self) -> int:
        return len(self._parcels)

    @property
    def parcels(self) -> list[IndexedParcel]:
        """Every parcel in the index, in file order."""
        return list(self._parcels)

    def by_number(self, parcel_number: str) -> IndexedParcel | None:
        """The parcel with this number, or None."""
        return self._by_number.get(parcel_number)

    def _cells_of(self, bounds: Bounds) -> Iterable[tuple[int, int]]:
        x0, y0 = int(bounds[0] // self.cell_size), int(bounds[1] // self.cell_size)
        x1, y1 = int(bounds[2] // self.cell_size), int(bounds[3] // self.cell_size)
        for ix in range(x0, x1 + 1):
            for iy in range(y0, y1 + 1):
                yield (ix, iy)

    def _candidates(self, bounds: Bounds, margin: float = 0.0) -> list[IndexedParcel]:
        """Parcels whose bounding box comes within ``margin`` of ``bounds``."""
        widened = (bounds[0] - margin, bounds[1] - margin, bounds[2] + margin, bounds[3] + margin)
        seen: set[int] = set()
        found: list[IndexedParcel] = []
        for cell in self._cells_of(widened):
            for index in self._cells.get(cell, ()):
                if index in seen:
                    continue
                seen.add(index)
                item = self._parcels[index]
                if _bounds_overlap(item.bounds, widened):
                    found.append(item)
        found.sort(key=lambda item: item.parcel_number)
        return found

    def in_bbox(self, bounds: Bounds, relation: Relation = "intersects") -> list[IndexedParcel]:
        """Parcels touching a bounding box, or lying wholly inside it."""
        min_x, min_y, max_x, max_y = bounds
        if min_x > max_x or min_y > max_y:
            raise ValueError("a bounding box is (min_x, min_y, max_x, max_y)")
        box: list[Point] = [(min_x, min_y), (max_x, min_y), (max_x, max_y), (min_x, max_y)]
        return self.in_polygon(box, relation)

    def in_polygon(self, ring: Ring, relation: Relation = "intersects") -> list[IndexedParcel]:
        """Parcels touching a polygon (outer ring), or lying wholly inside it."""
        if len(ring) < 3:
            raise ValueError("a polygon needs at least three vertices")
        found: list[IndexedParcel] = []
        for item in self._candidates(ring_bounds(ring)):
            if relation == "within":
                if _within(item.ring, ring):
                    found.append(item)
            elif rings_intersect(item.ring, ring):
                found.append(item)
        return found

    def within_radius(self, x: float, y: float, radius_m: float) -> list[RadiusHit]:
        """Parcels whose outline comes within ``radius_m`` of a point, nearest first."""
        if radius_m <= 0:
            raise ValueError("radius_m must be positive")
        hits: list[RadiusHit] = []
        for item in self._candidates((x, y, x, y), margin=radius_m):
            distance = point_ring_distance(x, y, item.ring)
            if distance <= radius_m:
                hits.append(RadiusHit(item, round(distance, 2)))
        hits.sort(key=lambda hit: (hit.distance_m, hit.parcel.parcel_number))
        return hits

    def neighbours(self, parcel_number: str, tolerance_m: float = 0.10) -> list[Neighbour]:
        """Parcels sharing a boundary or a corner with the one named, longest boundary first.

        Raises:
            KeyError: the parcel is not in the index
        """
        item = self._by_number.get(parcel_number)
        if item is None:
            raise KeyError(parcel_number)
        found: list[Neighbour] = []
        for other in self._candidates(item.bounds, margin=tolerance_m):
            if other is item:
                continue
            shared = shared_boundary_length(item.ring, other.ring, tolerance_m)
            if shared >= CORNER_LENGTH_M:
                found.append(Neighbour(other, round(shared, 2), False))
            elif _touch(item.ring, other.ring, tolerance_m):
                found.append(Neighbour(other, 0.0, True))
        found.sort(key=lambda n: (-n.shared_boundary_m, n.parcel.parcel_number))
        return found

    @staticmethod
    def total_area(parcels: Iterable[IndexedParcel]) -> float:
        """Sum of the graphical areas of these parcels, in m2."""
        return round(sum(item.area_m2 for item in parcels), 1)


#: How far outside a query area a point may lie and still count as on its boundary.
_ON_BOUNDARY_M = 1e-6


def _within(inner: Ring, outer: Ring) -> bool:
    """Whether ``inner`` lies inside ``outer``, its boundary included.

    Every vertex of the inner ring and the midpoint of every inner edge must
    be inside the outer ring or on its boundary; the midpoints catch an edge
    that cuts across a concave part of the query area. Ray casting alone
    treats a point on the boundary as outside, which would exclude a parcel
    whose edge coincides with the query box.
    """
    points = list(inner) + [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in _edges(inner)]
    return all(point_ring_distance(x, y, outer) <= _ON_BOUNDARY_M for x, y in points)


def _touch(a: Ring, b: Ring, tolerance: float) -> bool:
    """Whether two rings come within ``tolerance`` of each other anywhere."""
    return ring_distance(a, b) <= tolerance


def parcel_numbers(parcels: Sequence[IndexedParcel]) -> list[str]:
    """The parcel numbers of a result, in its order."""
    return [item.parcel_number for item in parcels]
