"""Result sets as CSV text or GeoJSON, for a spreadsheet, an email or a map.

Pure string and dict builders; nothing is written to disk. CSV columns are
fixed per table and named in English snake_case; the matrix is in long form
(one row per person and parcel), which keeps the columns the same however
many parcels there are.
"""

from __future__ import annotations

import csv
import io
from typing import Any

from ..models.gis_entities import ParcelGeometry
from .assembly import AssemblyAnalysis

PARCEL_COLUMNS = [
    "parcel_number",
    "municipality_code",
    "area_m2",
    "lr_unit_number",
    "main_book_id",
    "relationship",
    "distinct_owners",
    "distinct_possessors",
    "has_encumbrances",
    "has_pending_plombe",
    "public_body_owner_share",
    "zoning_status",
    "in_building_area",
    "designation_code",
    "plan_name",
    "area_mismatch",
    "score",
    "map_url",
]
PERSON_COLUMNS = [
    "name",
    "surname",
    "tax_number",
    "party_type_inferred",
    "parcel_count",
    "owner_of",
    "possessor_of",
    "owned_area_m2",
    "possessed_area_m2",
    "controlled_area_m2",
    "shares_unknown",
    "fuzzy_matches",
]
MATRIX_COLUMNS = [
    "name",
    "parcel_number",
    "role",
    "owner_share",
    "possessor_share",
    "fuzzy",
]


def rows_to_csv(rows: list[dict[str, Any]], columns: list[str]) -> str:
    """CSV text with a header row; missing values are empty cells, lists joined with ';'."""
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=columns, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({c: _cell(row.get(c)) for c in columns})
    return out.getvalue()


def _cell(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return ";".join(str(v) for v in value)
    if isinstance(value, dict):
        if {"num", "den"} <= set(value):
            return f"{value['num']}/{value['den']}"
        return ";".join(f"{k}={v}" for k, v in value.items())
    return value


def parcels_csv(analysis: AssemblyAnalysis) -> str:
    """One row per parcel, easiest to acquire first."""
    rows = []
    for summary in analysis.parcels:
        row = summary.model_dump(mode="json")
        row["lr_unit_number"] = (summary.lr_unit or {}).get("lr_unit_number")
        row["main_book_id"] = (summary.lr_unit or {}).get("main_book_id")
        rows.append(row)
    return rows_to_csv(rows, PARCEL_COLUMNS)


def persons_csv(analysis: AssemblyAnalysis) -> str:
    """One row per person, largest controlled area first."""
    rows = []
    for person in analysis.persons:
        row = person.model_dump(mode="json")
        row["party_type_inferred"] = person.party_type_inferred.party_type
        row["parcel_count"] = len(person.parcels)
        rows.append(row)
    return rows_to_csv(rows, PERSON_COLUMNS)


def matrix_csv(analysis: AssemblyAnalysis) -> str:
    """One row per person and parcel (long form)."""
    names = {person.key: person.name for person in analysis.persons}
    rows = [
        {**cell.model_dump(mode="json"), "name": names.get(cell.person_key, cell.person_key)}
        for cell in analysis.matrix
    ]
    return rows_to_csv(rows, MATRIX_COLUMNS)


def parcels_geojson(
    analysis: AssemblyAnalysis, geometries: dict[str, ParcelGeometry]
) -> dict[str, Any]:
    """A FeatureCollection of the parcels that have an outline, scored in the properties.

    Parcels without an outline are named in ``skipped`` rather than dropped.
    Coordinates stay in EPSG:3765.
    """
    features = []
    skipped = []
    for summary in analysis.parcels:
        geometry = geometries.get(summary.parcel_number)
        if geometry is None:
            skipped.append(summary.parcel_number)
            continue
        feature = geometry.to_geojson()
        feature["properties"].update(
            summary.model_dump(mode="json", exclude={"provenance", "land_use", "map_url"})
        )
        features.append(feature)
    return {"type": "FeatureCollection", "features": features, "skipped": skipped}
