"""Pydantic models for GIS spatial data from ATOM feed downloads."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

#: Interactive map viewer. Centred links use EPSG:3765 coordinates.
MAP_BASE_URL = "https://oss.uredjenazemlja.hr/map"
#: Layers shown in map links: orthophoto, parcels, municipalities, addresses.
MAP_LAYERS = "DOF5_2023_2024,DKP_CESTICE,DKP_KATASTARSKE_OPCINE,zupanija,ulica,kucni_broj"
#: Zoom level at which a single parcel fills the viewer.
DEFAULT_MAP_ZOOM = 19


def build_map_url(
    center: tuple[float, float] | None = None, zoom: int = DEFAULT_MAP_ZOOM
) -> str:
    """
    Build an interactive map URL.

    Args:
        center: (x, y) in EPSG:3765 to centre the map on, or None for the
            layer set without a position
        zoom: Map zoom level (19 shows one parcel; 20 for very small parcels)

    Returns:
        Map URL, coordinates rounded to two decimals (centimetres)
    """
    if center is None:
        return f"{MAP_BASE_URL}?layers={MAP_LAYERS}"
    x, y = center
    return f"{MAP_BASE_URL}?center={x:.2f},{y:.2f}&zoom={zoom}&layers={MAP_LAYERS}"


class Coordinate(BaseModel):
    """2D coordinate in EPSG:3765 projection (HTRS96/TM)."""

    x: float = Field(description="Easting coordinate (m)")
    y: float = Field(description="Northing coordinate (m)")

    def __str__(self) -> str:
        """String representation."""
        return f"({self.x}, {self.y})"


class ParcelGeometry(BaseModel):
    """
    Parcel geometry with boundary coordinates.

    Coordinates are in EPSG:3765 (HTRS96/TM) projection system.
    """

    model_config = ConfigDict(extra="allow")

    cestica_id: str = Field(description="Internal parcel ID from GIS system")
    broj_cestice: str = Field(description="Parcel number (matches API parcel_number)")
    povrsina_graficka: float = Field(description="Graphical area in m² from GIS data")
    maticni_broj_ko: str = Field(
        description="Municipality registration number (matches municipality_reg_num)"
    )
    coordinates: list[Coordinate] = Field(
        description="Polygon boundary coordinates (outer ring)"
    )
    srs_name: str = Field(
        default="EPSG:3765", description="Spatial reference system (HTRS96/TM)"
    )

    @property
    def coordinate_count(self) -> int:
        """Number of vertices in polygon."""
        return len(self.coordinates)

    @property
    def bounds(self) -> tuple[float, float, float, float]:
        """
        Get bounding box (min_x, min_y, max_x, max_y).

        Returns:
            Tuple of (min_x, min_y, max_x, max_y) coordinates
        """
        if not self.coordinates:
            return (0.0, 0.0, 0.0, 0.0)

        xs = [c.x for c in self.coordinates]
        ys = [c.y for c in self.coordinates]
        return (min(xs), min(ys), max(xs), max(ys))

    @property
    def center(self) -> tuple[float, float]:
        """
        Get center point of the bounding box.

        Returns:
            Tuple of (center_x, center_y) coordinates
        """
        if not self.coordinates:
            return (0.0, 0.0)

        min_x, min_y, max_x, max_y = self.bounds
        return ((min_x + max_x) / 2, (min_y + max_y) / 2)

    def to_wkt(self) -> str:
        """
        Export geometry as WKT (Well-Known Text) format.

        Returns:
            WKT POLYGON string

        Example:
            "POLYGON((380455.97 4882138.52, 380459.6 4882133.45, ...))"
        """
        coords_str = ", ".join(f"{c.x} {c.y}" for c in self.coordinates)
        return f"POLYGON(({coords_str}))"

    def to_geojson_coords(self) -> list[list[float]]:
        """
        Export coordinates in GeoJSON format.

        Returns:
            List of [x, y] coordinate pairs

        Note:
            GeoJSON typically uses WGS84 (EPSG:4326).
            These coordinates are in EPSG:3765 - transform if needed.
        """
        return [[c.x, c.y] for c in self.coordinates]

    def map_url(self, zoom: int = DEFAULT_MAP_ZOOM) -> str:
        """
        Interactive map URL centred on this parcel.

        Args:
            zoom: Map zoom level (default 19; use 20 for very small parcels)

        Returns:
            URL of the map viewer centred on the parcel's bounding-box centre
        """
        return build_map_url(self.center, zoom)

    def to_geojson(self, zoom: int = DEFAULT_MAP_ZOOM) -> dict[str, Any]:
        """
        Export geometry as a GeoJSON Feature.

        Args:
            zoom: Zoom level used for the ``map_url`` property

        Returns:
            GeoJSON Feature (Polygon) with parcel properties and a map link

        Note:
            Coordinates stay in EPSG:3765; ``properties.srs`` records that.
        """
        return {
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [self.to_geojson_coords()]},
            "properties": {
                "parcel_number": self.broj_cestice,
                "municipality": self.maticni_broj_ko,
                "area_m2": self.povrsina_graficka,
                "srs": self.srs_name,
                "map_url": self.map_url(zoom),
            },
        }
