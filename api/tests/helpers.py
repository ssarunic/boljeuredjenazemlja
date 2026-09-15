"""Shared builders for SDK tests."""

from __future__ import annotations

from cadastral_api.models.gis_entities import ParcelGeometry


def square_parcel(
    number: str, x: float, y: float, size: float = 10.0, municipality: str = "334979"
) -> ParcelGeometry:
    """A square parcel with its lower-left corner at (x, y)."""
    corners = [(x, y), (x + size, y), (x + size, y + size), (x, y + size), (x, y)]
    return ParcelGeometry(
        cestica_id=number.replace("/", "_"),
        broj_cestice=number,
        povrsina_graficka=size * size,
        maticni_broj_ko=municipality,
        coordinates=[{"x": cx, "y": cy} for cx, cy in corners],
    )


def grid_parcels(
    nx: int, ny: int, size: float = 10.0, origin: tuple[float, float] = (400000.0, 4900000.0)
) -> list[ParcelGeometry]:
    """An ``nx`` x ``ny`` grid of adjoining square parcels numbered "r<row>/c<col>"."""
    ox, oy = origin
    return [
        square_parcel(f"{row + 1}/{col + 1}", ox + col * size, oy + row * size, size)
        for row in range(ny)
        for col in range(nx)
    ]
