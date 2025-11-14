"""GML parser for cadastral parcel data."""

import xml.etree.ElementTree as ET
from pathlib import Path

from ..models.gis_entities import Coordinate, ParcelGeometry


class GMLParser:
    """
    Parser for GML files containing cadastral parcel geometries.

    Parses katastarske_cestice.gml files from the Croatian Cadastral ATOM feed.
    """

    # XML namespaces used in GML files
    NAMESPACES = {
        "gml": "http://www.opengis.net/gml",
        "oss": "http://oss",
        "wfs": "http://www.opengis.net/wfs",
    }

    def __init__(self, gml_file_path: Path | str) -> None:
        """
        Initialize GML parser.

        Args:
            gml_file_path: Path to GML file
        """
        self.gml_file_path = Path(gml_file_path)
        self._tree: ET.ElementTree | None = None
        self._root: ET.Element | None = None

    def _ensure_parsed(self) -> None:
        """Lazy load and parse GML file."""
        if self._tree is None:
            self._tree = ET.parse(self.gml_file_path)
            self._root = self._tree.getroot()

    def get_parcel_by_number(self, parcel_number: str) -> ParcelGeometry | None:
        """
        Find parcel by parcel number.

        Args:
            parcel_number: Parcel number (e.g., "103/2", "114")

        Returns:
            ParcelGeometry object if found, None otherwise
        """
        self._ensure_parsed()

        for feature in self._root.findall(".//gml:featureMember", self.NAMESPACES):  # type: ignore
            cestice = feature.find("oss:CESTICE", self.NAMESPACES)
            if cestice is None:
                continue

            broj_elem = cestice.find("oss:BROJ_CESTICE", self.NAMESPACES)
            if broj_elem is None or broj_elem.text is None:
                continue

            if broj_elem.text == parcel_number:
                return self._parse_parcel(cestice)

        return None

    def get_all_parcels(self) -> list[ParcelGeometry]:
        """
        Get all parcels from GML file.

        Returns:
            List of ParcelGeometry objects

        Warning:
            Can be memory intensive for large municipalities.
            Consider using get_parcel_by_number() for single parcels.
        """
        self._ensure_parsed()

        parcels: list[ParcelGeometry] = []

        for feature in self._root.findall(".//gml:featureMember", self.NAMESPACES):  # type: ignore
            cestice = feature.find("oss:CESTICE", self.NAMESPACES)
            if cestice is not None:
                parcel = self._parse_parcel(cestice)
                if parcel is not None:
                    parcels.append(parcel)

        return parcels

    def _parse_parcel(self, cestice: ET.Element) -> ParcelGeometry | None:
        """
        Parse single parcel from CESTICE element.

        Args:
            cestice: CESTICE XML element

        Returns:
            ParcelGeometry object or None if parsing fails
        """
        try:
            # Extract basic attributes
            cestica_id = self._get_text(cestice, "oss:CESTICA_ID")
            broj_cestice = self._get_text(cestice, "oss:BROJ_CESTICE")
            povrsina = self._get_text(cestice, "oss:POVRSINA_GRAFICKA")
            maticni_broj = self._get_text(cestice, "oss:MATICNI_BROJ_KO")

            if not all([cestica_id, broj_cestice, povrsina, maticni_broj]):
                return None

            # Parse geometry
            geom_elem = cestice.find(".//oss:GEOM", self.NAMESPACES)
            if geom_elem is None:
                return None

            polygon = geom_elem.find(".//gml:Polygon", self.NAMESPACES)
            if polygon is None:
                return None

            # Extract SRS (coordinate system)
            srs_name = polygon.get("srsName", "")
            # Extract EPSG code from full URI if present
            if "epsg.xml#" in srs_name:
                epsg_code = srs_name.split("#")[-1]
                srs_name = f"EPSG:{epsg_code}"

            # Parse coordinates
            coords_elem = polygon.find(".//gml:coordinates", self.NAMESPACES)
            if coords_elem is None or coords_elem.text is None:
                return None

            coordinates = self._parse_coordinates(coords_elem.text)

            return ParcelGeometry(
                cestica_id=cestica_id,
                broj_cestice=broj_cestice,
                povrsina_graficka=float(povrsina),
                maticni_broj_ko=maticni_broj,
                coordinates=coordinates,
                srs_name=srs_name,
            )

        except (ValueError, AttributeError):
            return None

    def _get_text(self, element: ET.Element, tag_name: str) -> str:
        """
        Safely extract text content from element.

        Args:
            element: Parent XML element
            tag_name: Tag name to find

        Returns:
            Text content or empty string
        """
        child = element.find(tag_name, self.NAMESPACES)
        return child.text.strip() if child is not None and child.text else ""

    def _parse_coordinates(self, coord_text: str) -> list[Coordinate]:
        """
        Parse GML coordinates string to list of Coordinate objects.

        Format: "x1,y1 x2,y2 x3,y3 ..."

        Args:
            coord_text: GML coordinates text

        Returns:
            List of Coordinate objects
        """
        coordinates: list[Coordinate] = []

        # Split by spaces to get individual coordinate pairs
        pairs = coord_text.strip().split()

        for pair in pairs:
            if "," not in pair:
                continue

            x_str, y_str = pair.split(",", 1)
            try:
                x = float(x_str.strip())
                y = float(y_str.strip())
                coordinates.append(Coordinate(x=x, y=y))
            except ValueError:
                continue

        return coordinates

    def count_parcels(self) -> int:
        """
        Count total number of parcels in GML file.

        Returns:
            Number of parcels
        """
        self._ensure_parsed()
        return len(list(self._root.findall(".//gml:featureMember", self.NAMESPACES)))  # type: ignore
