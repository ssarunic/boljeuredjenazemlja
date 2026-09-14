"""Pydantic models for spatial-plan (prostorni plan) data.

The models cover the one nationwide vector layer of spatial-plan content that
exists today: the building areas (građevinska područja) the county
spatial-planning institutes derived from the plans in force, published by the
Ministry as a WFS (see specs/spatial-planning-api-specification.md, section
3). Every zone carries the designation code of the plan it was read from, the
plan's name and ISPU identifier, and the generation of the plan whose code
list applies, because the same letters mean different things in old plans and
in plans made under the 2024 Pravilnik.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .gis_entities import Coordinate

#: Feature type names of the Ministry's building-areas WFS (workspace prefix included).
SETTLEMENT_FEATURE_TYPE = "GradjPodrucje_MGIPU_Public:Gradj_podrucje_naselje"
DETACHED_FEATURE_TYPE = "GradjPodrucje_MGIPU_Public:Gradj_podrucje_izvan_naselja"

#: Disclaimer the building-areas dataset carries in its metadata (translated).
BUILDING_AREAS_DISCLAIMER = (
    "Building areas are an interpretation of the spatial plans by the county "
    "spatial-planning institutes and may deviate from the plans in force. They must "
    "not be used to issue acts for spatial interventions or other public documents; "
    "for official purposes use the original plans in force."
)

#: Meaning of the first letter(s) of an old-generation designation code.
DESIGNATION_CLASSES: dict[str, str] = {
    "GPN": "settlement building area",
    "S": "residential",
    "M": "mixed",
    "D": "public and social",
    "K": "commercial",
    "I": "industrial and production",
    "T": "tourism and hospitality",
    "R": "sport and recreation",
    "Z": "green areas",
    "G": "cemetery",
    "N": "special purpose",
    "E": "mineral extraction",
    "IS": "infrastructure",
    "L": "port",
    "P": "agricultural",
    "Š": "forest",
}


class PlanGeneration(str, Enum):
    """Which code list a zone's designation code belongs to.

    ``old``: plans made under the 1998 Pravilnik (T1 hotel, T2 tourist
    settlement, T3 camp). ``new``: plans made under the 2024 Pravilnik o
    prostornim planovima (T1 inside a settlement, T2 detached with
    accommodation, T3 detached without accommodation). Every zone the
    building-areas WFS serves today is ``old``.
    """

    OLD = "old"
    NEW = "new"


class ZoneKind(str, Enum):
    """The two feature types of the building-areas layer."""

    SETTLEMENT = "settlement"  # građevinsko područje naselja
    DETACHED = "detached"  # izdvojeno građevinsko područje izvan naselja


class ZoningStatus(str, Enum):
    """Where a parcel lies with respect to the building areas.

    ``inside_settlement`` and ``detached_zone`` follow the zone with the largest
    overlap above the threshold. ``touches_below_threshold`` means the service
    reported intersecting zones but none covers the threshold share of the
    parcel (a boundary case, listed in ``below_threshold``); ``outside`` means
    the service reported no intersecting zone at all.
    """

    INSIDE_SETTLEMENT = "inside_settlement"
    DETACHED_ZONE = "detached_zone"
    TOUCHES_BELOW_THRESHOLD = "touches_below_threshold"
    OUTSIDE = "outside"


class PlanningZone(BaseModel):
    """One polygon of the building-areas layer with its plan designation."""

    model_config = ConfigDict(extra="allow")

    feature_id: str | None = Field(default=None, description="WFS feature id")
    zone_kind: ZoneKind = Field(description="settlement or detached building area")
    generation: PlanGeneration = Field(
        default=PlanGeneration.OLD,
        description="Code list the designation code belongs to (old or new Pravilnik)",
    )
    designation_code: str | None = Field(
        default=None, description="Designation code as written in the plan (T2, I1, GPN)"
    )
    designation: str | None = Field(
        default=None, description="Designation text as written in the plan"
    )
    designation_detail: str | None = Field(default=None, description="Designation detail")
    designation_class: str | None = Field(
        default=None, description="Aggregated class letter (T, I, K, R ...)"
    )
    zone_name: str | None = Field(default=None, description="Zone name (settlement - locality)")
    plan_name: str | None = Field(default=None, description="Source plan name")
    plan_id: str | None = Field(
        default=None, description="Source plan ISPU identifier (HR-ISPU-PPGO-03794-R05)"
    )
    municipality_code: str | None = Field(default=None, description="Code of the grad/općina")
    municipality_name: str | None = Field(default=None, description="Name of the grad/općina")
    county_code: str | None = Field(default=None, description="County code")
    source_sheet: str | None = Field(
        default=None, description="Sheet of the plan the zone was read from"
    )
    source_scale: str | None = Field(default=None, description="Scale of that sheet")
    area_m2: float | None = Field(default=None, description="Zone area in m2 as published")
    polygons: list[list[list[Coordinate]]] = Field(
        default_factory=list,
        description="Polygons of the zone; each polygon is its outer ring followed by holes",
    )

    @classmethod
    def from_feature(cls, feature: dict[str, Any], zone_kind: ZoneKind) -> PlanningZone:
        """Build a zone from one GeoJSON feature of the building-areas WFS."""
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        polygons = _polygons_from_geojson(geometry)
        code = props.get("ozn_namjen")
        if zone_kind is ZoneKind.SETTLEMENT and not code:
            code = "GPN"
        return cls(
            feature_id=str(feature["id"]) if feature.get("id") is not None else None,
            zone_kind=zone_kind,
            designation_code=code,
            designation=props.get("namjena"),
            designation_detail=props.get("namjena_vl"),
            designation_class=props.get("az_oznaka") or _class_of(code),
            zone_name=props.get("naz_vl"),
            plan_name=props.get("plan_naziv"),
            plan_id=props.get("ozn_ispu"),
            municipality_code=props.get("jls_mb"),
            municipality_name=props.get("jls_ime"),
            county_code=props.get("zup_rb"),
            source_sheet=props.get("izvor"),
            source_scale=props.get("mj_izvora"),
            area_m2=props.get("pov"),
            polygons=polygons,
        )

    @property
    def designation_class_label(self) -> str | None:
        """English meaning of the designation class, when known."""
        if self.designation_class and self.designation_class in DESIGNATION_CLASSES:
            return DESIGNATION_CLASSES[self.designation_class]
        derived = _class_of(self.designation_code)
        return DESIGNATION_CLASSES.get(derived) if derived else None

    @property
    def rings(self) -> list[list[list[tuple[float, float]]]]:
        """Polygons as plain coordinate tuples, for the geometry helpers."""
        return [[[(c.x, c.y) for c in ring] for ring in polygon] for polygon in self.polygons]

    @property
    def bounds(self) -> tuple[float, float, float, float] | None:
        """Bounding box ``(min_x, min_y, max_x, max_y)`` of every outer ring."""
        points = [c for polygon in self.polygons for c in polygon[0]] if self.polygons else []
        if not points:
            return None
        xs = [c.x for c in points]
        ys = [c.y for c in points]
        return (min(xs), min(ys), max(xs), max(ys))

    def label(self) -> str:
        """One-line description: code, designation text and zone name."""
        parts = [p for p in (self.designation_code, self.designation) if p]
        text = " ".join(parts) if parts else self.zone_kind.value
        if self.zone_name:
            text += f" ({self.zone_name})"
        return text

    def to_geojson(self) -> dict[str, Any]:
        """GeoJSON Feature (Polygon or MultiPolygon) with the zone's attributes."""
        rings = [[[[c.x, c.y] for c in ring] for ring in polygon] for polygon in self.polygons]
        geometry: dict[str, Any]
        if len(rings) == 1:
            geometry = {"type": "Polygon", "coordinates": rings[0]}
        else:
            geometry = {"type": "MultiPolygon", "coordinates": rings}
        properties = self.model_dump(mode="json", exclude={"polygons"})
        properties["srs"] = "EPSG:3765"
        return {
            "type": "Feature",
            "id": self.feature_id,
            "geometry": geometry,
            "properties": properties,
        }


class ZoneMatch(BaseModel):
    """A zone that intersects a parcel, with the estimated share of the parcel it covers."""

    zone: PlanningZone
    overlap_fraction: float = Field(
        description="Share of the parcel area inside the zone (0 to 1, estimated by sampling)"
    )
    overlap_m2: float | None = Field(
        default=None, description="Parcel area inside the zone in m2 (fraction x parcel area)"
    )


class PlanningDataset(BaseModel):
    """Provenance of the layer a lookup was answered from."""

    name: str = Field(description="Dataset name")
    state: str | None = Field(
        default=None,
        description="State of the plans the dataset reflects, when the service publishes one",
    )
    state_note: str | None = Field(
        default=None, description="What the catalogues say about the dataset's date"
    )
    source_url: str | None = Field(
        default=None, description="Endpoint that actually answered the request"
    )
    retrieved_at: str | None = Field(
        default=None, description="When the answer was retrieved (ISO 8601, UTC)"
    )
    disclaimer: str = Field(default=BUILDING_AREAS_DISCLAIMER)


class ParcelZoning(BaseModel):
    """Screening result: what the building-areas layer says about one parcel.

    Being inside a building area does not establish that anything may be
    built: plan provisions, plot size, access, infrastructure, protection
    regimes and the need for a lower-level plan are not evaluated, and the
    layer itself is an interpretation of the plans. ``buildability`` is
    therefore always ``"unknown"``; the result says where the parcel lies with
    respect to the building areas and which plan to read next.
    """

    parcel_number: str
    municipality_code: str
    parcel_area_m2: float | None = Field(
        default=None, description="Graphical area of the parcel from the cadastral map"
    )
    status: ZoningStatus
    in_building_area: bool = Field(
        description="True when a building area covers at least the threshold share of the parcel"
    )
    buildability: Literal["unknown"] = Field(
        default="unknown",
        description="Never determined by this lookup; a plan or a lokacijska informacija is needed",
    )
    matches: list[ZoneMatch] = Field(
        default_factory=list, description="Zones above the overlap threshold, largest first"
    )
    below_threshold: list[ZoneMatch] = Field(
        default_factory=list,
        description="Zones the service reported as intersecting that fall under the threshold",
    )
    intersecting_zones: int = Field(
        default=0, description="Number of zones the service reported as intersecting the parcel"
    )
    min_overlap: float = Field(
        default=0.02, description="Threshold share of the parcel a zone had to cover"
    )
    plans: list[str] = Field(default_factory=list, description="Distinct plans the zones come from")
    dataset: PlanningDataset

    def summary(self) -> dict[str, Any]:
        """Short dictionary for tables and MCP answers."""
        best = self.matches[0] if self.matches else None
        return {
            "parcel_number": self.parcel_number,
            "municipality_code": self.municipality_code,
            "status": self.status.value,
            "in_building_area": self.in_building_area,
            "buildability": self.buildability,
            "designation_code": best.zone.designation_code if best else None,
            "designation": best.zone.designation if best else None,
            "zone_name": best.zone.zone_name if best else None,
            "plan_name": best.zone.plan_name if best else None,
            "overlap_fraction": best.overlap_fraction if best else 0.0,
            "zones": len(self.matches),
            "intersecting_zones": self.intersecting_zones,
        }


def _class_of(code: str | None) -> str | None:
    """Class letters of a designation code: ``T2`` gives ``T``, ``IS5`` gives ``IS``."""
    if not code:
        return None
    code = code.strip().upper()
    if code in DESIGNATION_CLASSES:
        return code
    letters = ""
    for ch in code:
        if ch.isalpha():
            letters += ch
        else:
            break
    if letters in DESIGNATION_CLASSES:
        return letters
    return letters[:1] if letters[:1] in DESIGNATION_CLASSES else None


def _polygons_from_geojson(geometry: dict[str, Any]) -> list[list[list[Coordinate]]]:
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        polygons = [coords]
    elif kind == "MultiPolygon":
        polygons = coords
    else:
        return []
    return [
        [[Coordinate(x=float(x), y=float(y)) for x, y in ring] for ring in polygon]
        for polygon in polygons
    ]
