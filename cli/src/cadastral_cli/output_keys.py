"""Localized field names for the CLI's JSON and CSV output.

The English key names are canonical: they are what the code builds, what the
SDK models and the MCP server expose, and what a script written against the
English CLI expects. When the CLI runs in another language, ``print_output``
rewrites the keys through the tables below, so a Croatian user gets
``broj_cestice`` and ``opcina`` in the file, and the input parsers accept
either spelling when such a file is read back (the batch pipeline, CSV input
files).

Croatian key names are ASCII ``snake_case`` (``povrsina_m2``, not
``površina_m2``): they are identifiers for spreadsheets and scripts, and
identifiers with diacritics break more tools than they help.

Every key the CLI emits must be in ``KEYS`` (or ``KEY_OVERRIDES`` when the
same English key means something else under a particular parent).
``cli/tests/test_output_keys.py`` runs the commands against the mock server
and fails on a key that is still English in Croatian output. Dicts whose
keys are data (``land_use`` keyed by culture, ``plombe_detail`` keyed by file
number) are listed in ``DATA_KEYED`` and left alone. GeoJSON output is a
standard format and is never localized.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from cadastral_api.i18n import SUPPORTED_LANGUAGES, pgettext

from cadastral_cli.localized import _catalog, _lookup, active_spelling, fold

KEY_CONTEXT = "key"

# Canonical key -> spelling in the active language.
KEYS: dict[str, str] = {
    # Parcels (cadastre)
    "parcel_number": pgettext("key", "parcel_number"),
    "parcel_id": pgettext("key", "parcel_id"),
    "map_url": pgettext("key", "map_url"),
    "parcel": pgettext("key", "parcel"),
    "parcels": pgettext("key", "parcels"),
    "municipality": pgettext("key", "municipality"),
    "municipality_code": pgettext("key", "municipality_code"),
    "municipality_name": pgettext("key", "municipality_name"),
    "address": pgettext("key", "address"),
    "area": pgettext("key", "area"),
    "area_m2": pgettext("key", "area_m2"),
    "total_area_m2": pgettext("key", "total_area_m2"),
    "land_use": pgettext("key", "land_use"),
    "parcel_parts": pgettext("key", "parcel_parts"),
    "type": pgettext("key", "type"),
    "has_building": pgettext("key", "has_building"),
    "building_permitted": pgettext("key", "building_permitted"),
    "cadastre_lr_harmonized": pgettext("key", "cadastre_lr_harmonized"),
    "cadastre_harmonized": pgettext("key", "cadastre_harmonized"),
    "total_owners": pgettext("key", "total_owners"),
    "ownership": pgettext("key", "ownership"),
    "sheet_number": pgettext("key", "sheet_number"),
    "possessors": pgettext("key", "possessors"),
    "ownership_decimal": pgettext("key", "ownership_decimal"),
    "name": pgettext("key", "name"),
    "name_normalized": pgettext("key", "name_normalized"),
    # Land registry
    "land_registry": pgettext("key", "land_registry"),
    "lr_unit_number": pgettext("key", "lr_unit_number"),
    "unit_number": pgettext("key", "unit_number"),
    "unit_type": pgettext("key", "unit_type"),
    "main_book": pgettext("key", "main_book"),
    "main_book_id": pgettext("key", "main_book_id"),
    "main_book_name": pgettext("key", "main_book_name"),
    "institution": pgettext("key", "institution"),
    "institution_id": pgettext("key", "institution_id"),
    "institution_name": pgettext("key", "institution_name"),
    "active": pgettext("key", "active"),
    "status": pgettext("key", "status"),
    "status_name": pgettext("key", "status_name"),
    "status_description": pgettext("key", "status_description"),
    "last_diary_number": pgettext("key", "last_diary_number"),
    "owners": pgettext("key", "owners"),
    "num_owners": pgettext("key", "num_owners"),
    "share": pgettext("key", "share"),
    "share_description": pgettext("key", "share_description"),
    "num": pgettext("key", "num"),
    "den": pgettext("key", "den"),
    "decimal": pgettext("key", "decimal"),
    "register": pgettext("key", "register"),
    "tax_number": pgettext("key", "tax_number"),
    "condominium_number": pgettext("key", "condominium_number"),
    "is_condominium": pgettext("key", "is_condominium"),
    "encumbrances": pgettext("key", "encumbrances"),
    "has_encumbrances": pgettext("key", "has_encumbrances"),
    "description": pgettext("key", "description"),
    "share_order_number": pgettext("key", "share_order_number"),
    "right_type": pgettext("key", "right_type"),
    "entries": pgettext("key", "entries"),
    "order_number": pgettext("key", "order_number"),
    "action_type": pgettext("key", "action_type"),
    "diary_number": pgettext("key", "diary_number"),
    "entry_date": pgettext("key", "entry_date"),
    "basis_document": pgettext("key", "basis_document"),
    "basis_date": pgettext("key", "basis_date"),
    "beneficiaries": pgettext("key", "beneficiaries"),
    "source_fields": pgettext("key", "source_fields"),
    "total_parcels": pgettext("key", "total_parcels"),
    "summary": pgettext("key", "summary"),
    # Pending entries (plombe)
    "active_plumbs": pgettext("key", "active_plumbs"),
    "cad_plumb": pgettext("key", "cad_plumb"),
    "file_number": pgettext("key", "file_number"),
    "has_pending_plombe": pgettext("key", "has_pending_plombe"),
    "pending_plombe": pgettext("key", "pending_plombe"),
    "plombe_detail": pgettext("key", "plombe_detail"),
    "application_content": pgettext("key", "application_content"),
    "execution_date": pgettext("key", "execution_date"),
    "file_id": pgettext("key", "file_id"),
    "file_shipment_date": pgettext("key", "file_shipment_date"),
    "info_date": pgettext("key", "info_date"),
    "is_resolved": pgettext("key", "is_resolved"),
    "lr_file_number": pgettext("key", "lr_file_number"),
    "receiving_date": pgettext("key", "receiving_date"),
    "registration_number": pgettext("key", "registration_number"),
    "resolution_type_name": pgettext("key", "resolution_type_name"),
    "solving_date": pgettext("key", "solving_date"),
    # Batch processing
    "results": pgettext("key", "results"),
    "total": pgettext("key", "total"),
    "successful": pgettext("key", "successful"),
    "failed": pgettext("key", "failed"),
    "success_rate": pgettext("key", "success_rate"),
    "error_type": pgettext("key", "error_type"),
    "error_message": pgettext("key", "error_message"),
    "full_data": pgettext("key", "full_data"),
    # Geometry
    "coordinates": pgettext("key", "coordinates"),
    "bounds": pgettext("key", "bounds"),
    "min_x": pgettext("key", "min_x"),
    "min_y": pgettext("key", "min_y"),
    "max_x": pgettext("key", "max_x"),
    "max_y": pgettext("key", "max_y"),
    "srs": pgettext("key", "srs"),
    "vertex_count": pgettext("key", "vertex_count"),
    "vertex": pgettext("key", "vertex"),
    "x": pgettext("key", "x"),
    "y": pgettext("key", "y"),
    # Municipalities and offices
    "code": pgettext("key", "code"),
    "display_name": pgettext("key", "display_name"),
    "office_id": pgettext("key", "office_id"),
    "office_name": pgettext("key", "office_name"),
    "department_id": pgettext("key", "department_id"),
}

# (parent key, key) -> spelling when the same English key means something
# else under that parent. ``ownership`` is the list of possession sheets at
# the top of a parcel, but the possessor's share inside a sheet.
KEY_OVERRIDES: dict[tuple[str, str], str] = {
    ("possessors", "ownership"): pgettext("key possessors", "ownership"),
}

# Dicts whose keys are data, not field names.
DATA_KEYED = frozenset({"land_use", "plombe_detail", "source_fields"})


def _context(parent: str | None, key: str) -> str:
    if parent is not None and (parent, key) in KEY_OVERRIDES:
        return f"{KEY_CONTEXT} {parent}"
    return KEY_CONTEXT


def key_display(key: str, parent: str | None = None) -> str:
    """The active-language spelling of a canonical key."""
    if key not in KEYS and (parent, key) not in KEY_OVERRIDES:
        return key
    return active_spelling(_context(parent, key), key)


@lru_cache(maxsize=None)
def _canonical_map() -> dict[str, str]:
    """Folded spelling in any language -> canonical key."""
    mapping: dict[str, str] = {}
    entries = [(KEY_CONTEXT, key) for key in KEYS] + [
        (f"{KEY_CONTEXT} {parent}", key) for (parent, key) in KEY_OVERRIDES
    ]
    for context, key in entries:
        mapping.setdefault(fold(key), key)
        for lang in SUPPORTED_LANGUAGES:
            mapping.setdefault(fold(_lookup(_catalog(lang), context, key)), key)
    return mapping


def canonical_key(key: str) -> str:
    """The canonical (English) key for a spelling in any language."""
    return _canonical_map().get(fold(key), key)


def localize_keys(data: Any, parent: str | None = None, data_keyed: bool = False) -> Any:
    """Rewrite the dict keys of ``data`` (recursively) into the active language."""
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for key, value in data.items():
            child_data_keyed = key in DATA_KEYED
            if data_keyed or not isinstance(key, str):
                child_parent = key if isinstance(key, str) else None
                out[key] = localize_keys(value, child_parent, child_data_keyed)
            else:
                out[key_display(key, parent)] = localize_keys(value, key, child_data_keyed)
        return out
    if isinstance(data, list):
        return [localize_keys(item, parent, data_keyed) for item in data]
    return data


def canonical_keys(data: Any, data_keyed: bool = False) -> Any:
    """Rewrite the dict keys of ``data`` (recursively) back to the canonical keys."""
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for key, value in data.items():
            canonical = key if data_keyed or not isinstance(key, str) else canonical_key(key)
            out[canonical] = canonical_keys(value, canonical in DATA_KEYED)
        return out
    if isinstance(data, list):
        return [canonical_keys(item, data_keyed) for item in data]
    return data
