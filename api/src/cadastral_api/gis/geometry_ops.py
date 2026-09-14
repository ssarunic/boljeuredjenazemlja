"""Plain-Python planar geometry for parcel and zone polygons.

Everything here works on rings, i.e. lists of ``(x, y)`` tuples in a metric
projection (EPSG:3765). The functions are deliberately dependency-free: the
SDK has no shapely, and the only geometric question the spatial-plan lookup
asks is "how much of this parcel lies inside that zone", which point sampling
answers to within a few per cent, well inside the accuracy of plan boundaries
drawn at 1:5000.
"""

from __future__ import annotations

from collections.abc import Sequence

Point = tuple[float, float]
Ring = Sequence[Point]
#: A polygon is its outer ring followed by any number of holes.
Polygon = Sequence[Ring]


def ring_area(ring: Ring) -> float:
    """Area enclosed by a ring (shoelace formula), always non-negative."""
    if len(ring) < 3:
        return 0.0
    total = 0.0
    for (x1, y1), (x2, y2) in zip(ring, list(ring[1:]) + [ring[0]], strict=True):
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def ring_bounds(ring: Ring) -> tuple[float, float, float, float]:
    """Bounding box ``(min_x, min_y, max_x, max_y)`` of a ring."""
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return (min(xs), min(ys), max(xs), max(ys))


def point_in_ring(x: float, y: float, ring: Ring) -> bool:
    """Ray-casting point-in-polygon test for a single ring."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y):
            x_cross = (xj - xi) * (y - yi) / (yj - yi) + xi
            if x < x_cross:
                inside = not inside
        j = i
    return inside


def point_in_polygon(x: float, y: float, polygon: Polygon) -> bool:
    """True when the point is inside the outer ring and outside every hole."""
    if not polygon or not point_in_ring(x, y, polygon[0]):
        return False
    return not any(point_in_ring(x, y, hole) for hole in polygon[1:])


Edge = tuple[float, float, float, float]


def _edges_near(ring: Ring, bounds: tuple[float, float, float, float]) -> list[Edge]:
    """The edges of ``ring`` that a ray cast from a point inside ``bounds`` can cross.

    A ray runs from the point towards +x, so an edge entirely below, above
    or to the left of the box never counts; dropping such edges keeps the
    crossing parity of every point inside the box unchanged. A settlement
    polygon of thousands of vertices shrinks to the few edges near the parcel.
    """
    min_x, min_y, _max_x, max_y = bounds
    edges: list[Edge] = []
    n = len(ring)
    for i in range(n):
        xi, yi = ring[i]
        xj, yj = ring[i - 1]
        if max(yi, yj) <= min_y or min(yi, yj) > max_y or max(xi, xj) < min_x:
            continue
        edges.append((xi, yi, xj, yj))
    return edges


def _point_in_edges(x: float, y: float, edges: list[Edge]) -> bool:
    """Ray-casting parity over a pre-filtered edge list (see ``_edges_near``)."""
    inside = False
    for xi, yi, xj, yj in edges:
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
    return inside


def _orientation(p: Point, q: Point, r: Point) -> int:
    value = (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])
    if abs(value) < 1e-12:
        return 0
    return 1 if value > 0 else 2


def _on_segment(p: Point, q: Point, r: Point) -> bool:
    return min(p[0], r[0]) <= q[0] <= max(p[0], r[0]) and min(p[1], r[1]) <= q[1] <= max(
        p[1], r[1]
    )


def segments_intersect(p1: Point, p2: Point, p3: Point, p4: Point) -> bool:
    """True when segment p1-p2 touches or crosses segment p3-p4."""
    o1 = _orientation(p1, p2, p3)
    o2 = _orientation(p1, p2, p4)
    o3 = _orientation(p3, p4, p1)
    o4 = _orientation(p3, p4, p2)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and _on_segment(p1, p3, p2):
        return True
    if o2 == 0 and _on_segment(p1, p4, p2):
        return True
    if o3 == 0 and _on_segment(p3, p1, p4):
        return True
    return o4 == 0 and _on_segment(p3, p2, p4)


def _edges(ring: Ring) -> list[tuple[Point, Point]]:
    return [(ring[i], ring[(i + 1) % len(ring)]) for i in range(len(ring))]


def rings_intersect(a: Ring, b: Ring) -> bool:
    """True when two rings share any interior or boundary point.

    Checks the bounding boxes first, then vertex containment both ways, then
    edge crossings, so containment and partial overlap are both detected.
    """
    if len(a) < 3 or len(b) < 3:
        return False
    ax0, ay0, ax1, ay1 = ring_bounds(a)
    bx0, by0, bx1, by1 = ring_bounds(b)
    if ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0:
        return False
    if any(point_in_ring(x, y, b) for x, y in a):
        return True
    if any(point_in_ring(x, y, a) for x, y in b):
        return True
    for e1 in _edges(a):
        for e2 in _edges(b):
            if segments_intersect(e1[0], e1[1], e2[0], e2[1]):
                return True
    return False


def polygons_intersect(a: Polygon, b: Polygon) -> bool:
    """True when the outer rings of two polygons intersect (holes ignored)."""
    return bool(a) and bool(b) and rings_intersect(a[0], b[0])


def sample_points(ring: Ring, grid: int = 40) -> list[Point]:
    """Points of a ``grid`` x ``grid`` lattice over the ring's bounding box that fall inside it.

    The lattice is offset by half a cell so that no sample lies on the
    bounding box itself; a rectangle parcel therefore samples its interior
    only.
    """
    if len(ring) < 3 or grid < 1:
        return []
    min_x, min_y, max_x, max_y = ring_bounds(ring)
    step_x = (max_x - min_x) / grid
    step_y = (max_y - min_y) / grid
    if step_x <= 0 or step_y <= 0:
        return []
    points: list[Point] = []
    for i in range(grid):
        x = min_x + (i + 0.5) * step_x
        for j in range(grid):
            y = min_y + (j + 0.5) * step_y
            if point_in_ring(x, y, ring):
                points.append((x, y))
    return points


def overlap_fraction(
    parcel: Ring, zone: Sequence[Polygon], grid: int = 40, samples: list[Point] | None = None
) -> float:
    """Estimated share of the parcel's area covered by a (multi)polygon zone.

    The parcel is sampled on a lattice (``sample_points``) and the fraction of
    samples that fall inside any of the zone's polygons is returned. With the
    default 40 x 40 lattice the estimate is accurate to about one per cent for
    an ordinary parcel. ``samples`` lets a caller reuse one lattice for many
    zones.
    """
    points = samples if samples is not None else sample_points(parcel, grid)
    if not points:
        return 0.0
    # Every sample lies inside the parcel's bounding box, so each zone ring is
    # reduced once to the edges near that box before the samples are tested.
    bounds = ring_bounds(points)
    polygons = [
        [_edges_near(ring, bounds) for ring in polygon] for polygon in zone if polygon
    ]
    inside = 0
    for x, y in points:
        for rings in polygons:
            if _point_in_edges(x, y, rings[0]) and not any(
                _point_in_edges(x, y, hole) for hole in rings[1:]
            ):
                inside += 1
                break
    return inside / len(points)
