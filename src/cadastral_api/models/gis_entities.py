"""Pydantic models for GIS spatial data from ATOM feed downloads."""

from pydantic import BaseModel, ConfigDict, Field


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
