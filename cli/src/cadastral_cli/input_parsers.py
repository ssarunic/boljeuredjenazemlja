"""Parsers for the lists that ``get-parcel`` and ``get-lr-unit`` accept.

A list comes either from the command line (parcel numbers separated by commas
or given as several arguments) or from a file (``--input``): CSV or JSON,
with column names and keys in any supported language (see ``output_keys``).
"""

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cadastral_api.utils import normalize_parcel_number

from cadastral_cli.output_keys import canonical_key, canonical_keys


class ParcelInput:
    """Represents a single parcel input specification."""

    def __init__(
        self,
        parcel_number: str | None = None,
        parcel_id: str | None = None,
        municipality: str | None = None,
    ):
        """Initialize parcel input.

        Args:
            parcel_number: Parcel number (e.g., "103/2")
            parcel_id: Direct parcel ID (e.g., "12345678")
            municipality: Municipality code or name (required if parcel_number provided)

        Raises:
            ValueError: If neither or both parcel_number and parcel_id are provided
        """
        if parcel_number and parcel_id:
            msg = "Cannot specify both parcel_number and parcel_id"
            raise ValueError(msg)

        if not parcel_number and not parcel_id:
            msg = "Must specify either parcel_number or parcel_id"
            raise ValueError(msg)

        if parcel_number and not municipality:
            msg = "Municipality required when using parcel_number"
            raise ValueError(msg)

        # Building parcels in any spelling ("35/1.ZGR", "zgr. 35/1") -> "*35/1"
        self.parcel_number = normalize_parcel_number(parcel_number) if parcel_number else None
        self.parcel_id = parcel_id
        self.municipality = municipality

    @property
    def is_direct_id(self) -> bool:
        """Check if this is a direct parcel ID lookup."""
        return self.parcel_id is not None

    def __repr__(self) -> str:
        """String representation."""
        if self.parcel_id:
            return f"ParcelInput(parcel_id={self.parcel_id})"
        return f"ParcelInput(parcel_number={self.parcel_number}, municipality={self.municipality})"


def parse_cli_list(
    parcel_list: str | tuple[str, ...] | list[str], municipality: str
) -> list[ParcelInput]:
    """Parse the parcels typed on the command line.

    Args:
        parcel_list: Comma-separated string ("103/2,45,396/1") or the
            positional arguments as given (each may itself contain commas)
        municipality: Municipality code or name for all parcels

    Returns:
        List of ParcelInput objects

    Raises:
        ValueError: If input format is invalid
    """
    if not isinstance(parcel_list, str):
        parcel_list = ",".join(parcel_list)

    if not parcel_list or not parcel_list.strip():
        msg = "Parcel list cannot be empty"
        raise ValueError(msg)

    if not municipality or not municipality.strip():
        msg = "Municipality required when parcels are given by number"
        raise ValueError(msg)

    # Split and clean
    items = [item.strip() for item in parcel_list.split(",") if item.strip()]

    if not items:
        msg = "No valid parcels found in list"
        raise ValueError(msg)

    # Detect if all items are parcel IDs (8+ digit numeric) or parcel numbers
    # Parcel IDs are typically 8 digits, parcel numbers can be "103/2", "45", etc.
    def is_parcel_id(item: str) -> bool:
        """Check if item looks like a parcel ID (8+ digit numeric string)."""
        return item.isdigit() and len(item) >= 8

    all_parcel_ids = all(is_parcel_id(item) for item in items)
    has_parcel_ids = any(is_parcel_id(item) for item in items)
    has_parcel_numbers = any(not is_parcel_id(item) for item in items)

    # Check for mixed input (not allowed)
    if has_parcel_ids and has_parcel_numbers:
        msg = "Cannot mix parcel numbers and parcel IDs in the same list"
        raise ValueError(msg)

    # Parse based on type
    parcels = []
    if all_parcel_ids:
        # All items are parcel IDs
        for item in items:
            parcels.append(ParcelInput(parcel_id=item))
    else:
        # All items are parcel numbers
        for item in items:
            parcels.append(ParcelInput(parcel_number=item, municipality=municipality))

    return parcels


def parse_csv_file(file_path: str | Path) -> list[ParcelInput]:
    """Parse CSV file with parcel specifications.

    Supports two formats:
    1. Parcel numbers with municipality:
       parcel_number,municipality
       103/2,334979
       45,
       396/1,

    2. Direct parcel IDs:
       parcel_id
       12345678
       87654321

    Municipality inheritance: If municipality column is empty, uses the last
    specified municipality from a previous row.

    Args:
        file_path: Path to CSV file

    Returns:
        List of ParcelInput objects

    Raises:
        ValueError: If CSV format is invalid or mixed types detected
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)

    if not file_path.exists():
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg)

    parcels = []
    last_municipality = None

    with file_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            msg = "CSV file is empty or has no header"
            raise ValueError(msg)

        # Column names may be in any supported language (see output_keys).
        fieldnames = [canonical_key(name) for name in reader.fieldnames]

        # Detect CSV format
        has_parcel_number = "parcel_number" in fieldnames
        has_parcel_id = "parcel_id" in fieldnames

        if has_parcel_number and has_parcel_id:
            msg = "Cannot have both parcel_number and parcel_id columns (no mixing allowed)"
            raise ValueError(msg)

        if not has_parcel_number and not has_parcel_id:
            msg = "CSV must have either 'parcel_number' or 'parcel_id' column"
            raise ValueError(msg)

        # Parse rows
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (after header)
            row = canonical_keys(row)
            if has_parcel_id:
                # Direct parcel ID format
                parcel_id = row.get("parcel_id", "").strip()
                if not parcel_id:
                    msg = f"Row {row_num}: parcel_id cannot be empty"
                    raise ValueError(msg)

                parcels.append(ParcelInput(parcel_id=parcel_id))

            else:
                # Parcel number + municipality format
                parcel_number = row.get("parcel_number", "").strip()
                municipality = row.get("municipality", "").strip()

                if not parcel_number:
                    msg = f"Row {row_num}: parcel_number cannot be empty"
                    raise ValueError(msg)

                # Municipality inheritance
                if municipality:
                    last_municipality = municipality
                elif last_municipality:
                    municipality = last_municipality
                else:
                    msg = (
                        f"Row {row_num}: municipality required "
                        "(no previous municipality to inherit)"
                    )
                    raise ValueError(msg)

                parcels.append(
                    ParcelInput(parcel_number=parcel_number, municipality=municipality)
                )

    if not parcels:
        msg = "No valid parcels found in CSV file"
        raise ValueError(msg)

    return parcels


def parse_json_file(file_path: str | Path) -> list[ParcelInput]:
    """Parse JSON file with parcel specifications.

    Expected format:
    [
        {"parcel_number": "103/2", "municipality": "334979"},
        {"parcel_number": "45", "municipality": "SAVAR"}
    ]

    Or:
    [
        {"parcel_id": "12345678"},
        {"parcel_id": "87654321"}
    ]

    Args:
        file_path: Path to JSON file

    Returns:
        List of ParcelInput objects

    Raises:
        ValueError: If JSON format is invalid or mixed types detected
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)

    if not file_path.exists():
        msg = f"File not found: {file_path}"
        raise FileNotFoundError(msg)

    with file_path.open(encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        msg = "JSON must be an array of parcel objects"
        raise ValueError(msg)

    if not data:
        msg = "JSON array is empty"
        raise ValueError(msg)

    parcels = []
    has_parcel_number = False
    has_parcel_id = False

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            msg = f"Item {idx}: must be an object with parcel_number or parcel_id"
            raise ValueError(msg)
        item = canonical_keys(item)

        parcel_number = item.get("parcel_number", "").strip() if "parcel_number" in item else None
        parcel_id = item.get("parcel_id", "").strip() if "parcel_id" in item else None
        municipality = item.get("municipality", "").strip() if "municipality" in item else None

        # Track types
        if parcel_number:
            has_parcel_number = True
        if parcel_id:
            has_parcel_id = True

        # Check for mixing
        if has_parcel_number and has_parcel_id:
            msg = f"Item {idx}: Cannot mix parcel numbers and parcel IDs in the same list"
            raise ValueError(msg)

        # Validate
        if parcel_number and not municipality:
            msg = f"Item {idx}: municipality required when using parcel_number"
            raise ValueError(msg)

        if not parcel_number and not parcel_id:
            msg = f"Item {idx}: must have either parcel_number or parcel_id"
            raise ValueError(msg)

        # Create input
        if parcel_id:
            parcels.append(ParcelInput(parcel_id=parcel_id))
        else:
            parcels.append(ParcelInput(parcel_number=parcel_number, municipality=municipality))

    return parcels


def parse_input_file(file_path: str | Path) -> list[ParcelInput]:
    """Auto-detect file format and parse.

    Args:
        file_path: Path to input file (.csv or .json)

    Returns:
        List of ParcelInput objects

    Raises:
        ValueError: If file format is not supported or invalid
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        return parse_csv_file(file_path)
    if suffix == ".json":
        return parse_json_file(file_path)
    msg = f"Unsupported file format: {suffix} (use .csv or .json)"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# Land registry units
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LRUnitInput:
    """One land registry unit to read: its number and the main book ID."""

    lr_unit_number: str
    main_book_id: int


def _lr_unit_from_record(
    record: dict[str, Any], where: str, strict: bool
) -> LRUnitInput | None:
    """Build an ``LRUnitInput`` from a CSV row or JSON object (canonical keys).

    With ``strict`` False (records of a ``get-parcel`` result), records that
    failed or carry no unit reference are skipped instead of rejected.
    """
    if not strict and record.get("status") not in (None, "success"):
        return None
    lr_unit_number = record.get("lr_unit_number")
    main_book_id = record.get("main_book_id")
    lr_unit_number = str(lr_unit_number).strip() if lr_unit_number is not None else ""
    if isinstance(main_book_id, str):
        main_book_id = main_book_id.strip()
        if main_book_id.isdigit():
            main_book_id = int(main_book_id)
    if not lr_unit_number or main_book_id in (None, ""):
        if strict:
            raise ValueError(f"{where}: lr_unit_number and main_book_id are required")
        return None
    if not isinstance(main_book_id, int):
        raise ValueError(f"{where}: main_book_id must be an integer")
    return LRUnitInput(lr_unit_number=lr_unit_number, main_book_id=main_book_id)


def parse_lr_unit_csv(file_path: str | Path) -> list[LRUnitInput]:
    """Parse a CSV file with ``lr_unit_number`` and ``main_book_id`` columns.

    A CSV written by ``get-parcel --format csv`` for a list of parcels works
    too: it has the same two columns, and rows without a unit are skipped.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    units: list[LRUnitInput] = []
    with file_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no header")
        fieldnames = [canonical_key(name) for name in reader.fieldnames]
        if "lr_unit_number" not in fieldnames or "main_book_id" not in fieldnames:
            raise ValueError("CSV must have 'lr_unit_number' and 'main_book_id' columns")
        strict = "status" not in fieldnames  # a get-parcel result carries a status column
        for row_num, row in enumerate(reader, start=2):
            unit = _lr_unit_from_record(canonical_keys(row), f"Row {row_num}", strict)
            if unit is not None:
                units.append(unit)

    if not units:
        raise ValueError("No land registry units found in CSV file")
    return _unique(units)


def parse_lr_unit_json(file_path: str | Path) -> list[LRUnitInput]:
    """Parse a JSON file with land registry units.

    Accepted shapes: an array of ``{"lr_unit_number": ..., "main_book_id": ...}``
    objects, or the document ``get-parcel --format json`` writes for a list
    of parcels (its ``results`` carry the unit reference of each parcel).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with file_path.open(encoding="utf-8") as f:
        data = canonical_keys(json.load(f))

    strict = True
    if isinstance(data, dict) and isinstance(data.get("results"), list):
        data = data["results"]
        strict = False
    if not isinstance(data, list):
        raise ValueError("JSON must be an array of land registry unit objects")
    if not data:
        raise ValueError("JSON array is empty")

    units: list[LRUnitInput] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {idx}: must be an object with lr_unit_number and main_book_id")
        if "status" in item:
            strict = False
        unit = _lr_unit_from_record(item, f"Item {idx}", strict)
        if unit is not None:
            units.append(unit)

    if not units:
        raise ValueError("No land registry units found in JSON file")
    return _unique(units)


def parse_lr_unit_file(file_path: str | Path) -> list[LRUnitInput]:
    """Auto-detect the file format (.csv or .json) and parse it."""
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return parse_lr_unit_csv(file_path)
    if suffix == ".json":
        return parse_lr_unit_json(file_path)
    raise ValueError(f"Unsupported file format: {suffix} (use .csv or .json)")


def _unique(units: list[LRUnitInput]) -> list[LRUnitInput]:
    """Drop repeated units (several parcels of one list often share a unit)."""
    seen: set[LRUnitInput] = set()
    out: list[LRUnitInput] = []
    for unit in units:
        if unit not in seen:
            seen.add(unit)
            out.append(unit)
    return out
