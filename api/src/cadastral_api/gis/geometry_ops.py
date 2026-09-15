"""Plain-Python planar geometry for parcel and zone polygons.

Everything here works on rings, i.e. lists of ``(x, y)`` tuples in a metric
projection (EPSG:3765). The functions are deliberately dependency-free: the
SDK has no shapely, and the only geometric question the spatial-plan lookup
asks is "how much of this parcel lies inside that zone", which point sampling
answers to within a few per cent, well inside the accuracy of plan boundaries
drawn at 1:5000.
"""

from __future__ import annotations

import math
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


# ---------------------------------------------------------------------------
# Distances and shared boundaries (for the spatial index)
# ---------------------------------------------------------------------------


def point_segment_distance(p: Point, a: Point, b: Point) -> float:
    """Distance from point ``p`` to the segment ``a``-``b``."""
    ax, ay = a
    bx, by = b
    px, py = p
    dx, dy = bx - ax, by - ay
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length_sq))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def segment_distance(p1: Point, p2: Point, p3: Point, p4: Point) -> float:
    """Distance between segments p1-p2 and p3-p4 (0 when they touch or cross)."""
    if segments_intersect(p1, p2, p3, p4):
        return 0.0
    return min(
        point_segment_distance(p1, p3, p4),
        point_segment_distance(p2, p3, p4),
        point_segment_distance(p3, p1, p2),
        point_segment_distance(p4, p1, p2),
    )


def point_ring_distance(x: float, y: float, ring: Ring) -> float:
    """Distance from a point to a ring's area: 0 inside, else to the nearest edge."""
    if len(ring) < 3:
        return math.inf
    if point_in_ring(x, y, ring):
        return 0.0
    return min(point_segment_distance((x, y), a, b) for a, b in _edges(ring))


def ring_distance(a: Ring, b: Ring) -> float:
    """Distance between two rings' areas: 0 when they touch, cross or nest."""
    if len(a) < 3 or len(b) < 3:
        return math.inf
    if rings_intersect(a, b):
        return 0.0
    return min(segment_distance(e1[0], e1[1], e2[0], e2[1]) for e1 in _edges(a) for e2 in _edges(b))


def ring_centroid(ring: Ring) -> Point:
    """Area-weighted centroid of a ring (its bounding-box centre when degenerate)."""
    if len(ring) < 3:
        xs = [p[0] for p in ring] or [0.0]
        ys = [p[1] for p in ring] or [0.0]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    twice_area = 0.0
    cx = 0.0
    cy = 0.0
    for (x1, y1), (x2, y2) in _edges(ring):
        cross = x1 * y2 - x2 * y1
        twice_area += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    if abs(twice_area) < 1e-9:
        min_x, min_y, max_x, max_y = ring_bounds(ring)
        return ((min_x + max_x) / 2, (min_y + max_y) / 2)
    return (cx / (3 * twice_area), cy / (3 * twice_area))


def shared_boundary_length(a: Ring, b: Ring, tolerance: float = 0.10) -> float:
    """Length of the boundary two rings share, in the rings' units (metres).

    Two edges share boundary where they are collinear within ``tolerance``
    (both endpoints of one within that distance of the other's line) and
    overlap along that line; the overlaps are summed over every edge pair.
    Adjoining cadastral parcels are digitised with common vertices, so their
    common edges coincide exactly; the tolerance absorbs rounding. Two
    parcels that merely touch at a corner share no length.
    """
    total = 0.0
    for (ax, ay), (bx, by) in _edges(a):
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        if length == 0.0:
            continue
        ux, uy = dx / length, dy / length
        for p, q in _edges(b):
            # Perpendicular distance of both endpoints of the other edge to this edge's line.
            if abs((p[0] - ax) * uy - (p[1] - ay) * ux) > tolerance:
                continue
            if abs((q[0] - ax) * uy - (q[1] - ay) * ux) > tolerance:
                continue
            t1 = (p[0] - ax) * ux + (p[1] - ay) * uy
            t2 = (q[0] - ax) * ux + (q[1] - ay) * uy
            overlap = min(length, max(t1, t2)) - max(0.0, min(t1, t2))
            if overlap > 0.0:
                total += overlap
    return total


def parse_ring(polygon: str | Sequence[Sequence[float]]) -> list[Point]:
    """A ring from WKT (``POLYGON((x y, x y, ...))``) or a list of ``[x, y]`` pairs.

    The outer ring only; a closing vertex equal to the first is dropped.

    Raises:
        ValueError: fewer than three distinct vertices, or unreadable input
    """
    points: list[Point] = []
    if isinstance(polygon, str):
        text = polygon.strip()
        upper = text.upper()
        if not upper.startswith("POLYGON"):
            raise ValueError(
                "a polygon must be WKT 'POLYGON((x y, ...))' or a list of [x, y] pairs"
            )
        inner = text[text.find("((") + 2 :]
        outer = inner.split(")")[0]
        for pair in outer.split(","):
            parts = pair.split()
            if len(parts) != 2:
                raise ValueError(f"cannot read the WKT vertex {pair.strip()!r}")
            points.append((float(parts[0]), float(parts[1])))
    else:
        for vertex in polygon:
            if len(vertex) != 2:
                raise ValueError(f"a vertex is [x, y], got {list(vertex)!r}")
            points.append((float(vertex[0]), float(vertex[1])))
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if len(points) < 3:
        raise ValueError("a polygon needs at least three distinct vertices")
    return points
