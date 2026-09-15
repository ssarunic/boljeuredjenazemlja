"""Mock FastAPI server for Croatian Cadastral API.

⚠️ DEMO/EDUCATIONAL PROJECT ONLY ⚠️

This is a mock server for testing and demonstration purposes.
It returns static data from JSON files (redacted captures of the public API)
to mimic the behavior of the Croatian cadastral API without accessing real
government systems. See docs/legal.md before using the client with any other server.
"""

import json
import re
from pathlib import Path
from typing import Any

from fastapi import Body, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

# Initialize FastAPI app
app = FastAPI(
    title="Mock Croatian Cadastral API",
    description="Demo server for testing - returns static data only",
    version="1.0.0",
)

# Enable CORS for browser testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directory
DATA_DIR = Path(__file__).parent.parent / "data"

# In-memory data storage (loaded at startup)
_offices: list[dict[str, Any]] = []
_municipalities: list[dict[str, Any]] = []
_parcels: dict[str, list[dict[str, Any]]] = {}  # municipality_code -> parcels
_parcel_by_id: dict[int, dict[str, Any]] = {}  # parcelId -> parcel (built at startup)
_lr_units: dict[str, dict[str, Any]] = {}  # "mainBookId-lrUnitNumber" -> lr_unit_data
_file_status: dict[str, dict[str, Any]] = {}  # "institutionId-code-order-year" -> file status
_main_books: list[dict[str, Any]] = []  # six-key search records (E5)
_books_of_dc: list[dict[str, Any]] = []  # six-key search records (E6)
# municipality_code -> {possessionSheetId: possessionSheetNumber}, derived from the parcels
_possession_sheets: dict[str, dict[int, str]] = {}
_zones: list[dict[str, Any]] = []  # spatial-plan building areas (GeoJSON features)


def _six_key_record(
    key1: Any,
    value1: Any,
    key2: Any = None,
    value2: Any = None,
    value3: Any = None,
    display_value1: Any = None,
) -> dict[str, Any]:
    """The record shape every ``/search-*`` endpoint returns."""
    return {
        "key1": str(key1),
        "value1": value1,
        "key2": key2,
        "value2": value2,
        "value3": value3,
        "displayValue1": display_value1,
    }


def load_json(filepath: Path) -> Any:
    """Load JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


@app.on_event("startup")
async def load_data():
    """Load all static data into memory on startup."""
    global _offices, _municipalities, _parcels, _lr_units, _file_status
    global _main_books, _books_of_dc, _possession_sheets, _zones

    # Load offices
    offices_file = DATA_DIR / "offices.json"
    if offices_file.exists():
        _offices = load_json(offices_file)
        print(f"✓ Loaded {len(_offices)} cadastral offices")

    # Load municipalities
    municipalities_file = DATA_DIR / "municipalities.json"
    if municipalities_file.exists():
        _municipalities = load_json(municipalities_file)
        print(f"✓ Loaded {len(_municipalities)} municipalities")

    # Load parcels for each municipality
    parcels_dir = DATA_DIR / "parcels"
    if parcels_dir.exists():
        for parcel_file in parcels_dir.glob("*.json"):
            municipality_code = parcel_file.stem
            parcels_data = load_json(parcel_file)
            _parcels[municipality_code] = parcels_data
            _parcel_by_id.update(
                (p["parcelId"], p) for p in parcels_data if p.get("parcelId") is not None
            )
            print(f"✓ Loaded {len(parcels_data)} parcels for municipality {municipality_code}")
            # Possession sheets are searchable by number (E4); derive them from the parcels.
            sheets: dict[int, str] = {}
            for parcel in parcels_data:
                for sheet in parcel.get("possessionSheets") or []:
                    sheets[sheet["possessionSheetId"]] = str(sheet["possessionSheetNumber"])
            _possession_sheets[municipality_code] = sheets

    # Load land registry units
    lr_units_dir = DATA_DIR / "lr-units"
    if lr_units_dir.exists():
        for lr_unit_file in lr_units_dir.glob("*.json"):
            # Filename format: mainBookId-lrUnitNumber.json (e.g., 21277-769.json)
            key = lr_unit_file.stem
            lr_unit_data = load_json(lr_unit_file)
            _lr_units[key] = lr_unit_data
            print(f"✓ Loaded LR unit {key}")

    # Load land registry file statuses (plomba/spis detail)
    file_status_dir = DATA_DIR / "lr-file-status"
    if file_status_dir.exists():
        for fs_file in file_status_dir.glob("*.json"):
            # Filename format: institutionId-code-order-year.json (e.g. 284-Z-12564-2026.json)
            key = fs_file.stem.upper()
            _file_status[key] = load_json(fs_file)
            print(f"✓ Loaded file status {key}")

    # Land-registry main books and books of deposited contracts (E5, E6)
    main_books_file = DATA_DIR / "main-books.json"
    if main_books_file.exists():
        _main_books = load_json(main_books_file)
        print(f"✓ Loaded {len(_main_books)} main books")
    books_of_dc_file = DATA_DIR / "books-of-dc.json"
    if books_of_dc_file.exists():
        _books_of_dc = load_json(books_of_dc_file)
        print(f"✓ Loaded {len(_books_of_dc)} books of deposited contracts")

    # Spatial-plan building areas served by the WFS imitation
    zones_file = DATA_DIR / "planning" / "zones.json"
    if zones_file.exists():
        _zones = load_json(zones_file)["features"]
        print(f"✓ Loaded {len(_zones)} spatial-plan zones")

    print(
        f"\n🚀 Mock server ready with {len(_parcels)} municipalities, "
        f"{len(_lr_units)} LR units, {len(_file_status)} file statuses"
    )


@app.get("/")
async def root():
    """Root endpoint with server info."""
    return {
        "service": "Mock Croatian Cadastral API",
        "status": "running",
        "warning": "DEMO SERVER - Static data only, not connected to real systems",
        "endpoints": {
            "offices": "/search-cad-parcels/offices",
            "municipalities": "/search-cad-parcels/municipalities",
            "parcel_search": "/search-cad-parcels/parcel-numbers",
            "possession_sheet_search": "/search-cad-parcels/possession-sheet-numbers",
            "main_books": "/search-lr-parcels/main-books",
            "books_of_dc": "/search-lr-parcels/books-of-dc",
            "parcel_info": "/cad/parcel-info",
            "lr_unit": "/lr/lr-unit",
            "file_status": "/lr/file-status",
            "gis_download": "/atom/ko-{code}.zip",
            "planning_wfs": "/planning/wfs",
        },
        "data_loaded": {
            "offices": len(_offices),
            "municipalities": len(_municipalities),
            "parcel_sets": len(_parcels),
            "lr_units": len(_lr_units),
            "file_statuses": len(_file_status),
            "main_books": len(_main_books),
            "books_of_dc": len(_books_of_dc),
        },
    }


@app.get("/search-cad-parcels/offices")
async def list_offices():
    """
    List all cadastral offices.

    Returns:
        List of cadastral offices with id and name.
    """
    return _offices


@app.get("/search-cad-parcels/municipalities")
async def find_municipalities(
    search: str | None = Query(None, description="Municipality name or code to search"),
    office_id: str | None = Query(
        None, alias="officeId", description="Filter by cadastral office ID"
    ),
    department_id: str | None = Query(
        None, alias="departmentId", description="Filter by department ID"
    ),
):
    """
    Find municipalities by name, code, office, or department.

    Args:
        search: Municipality name or registration code (optional)
        office_id: Cadastral office ID filter (optional)
        department_id: Department ID filter (optional)

    Returns:
        List of matching municipalities.
    """
    results = _municipalities

    # Filter by office ID (value2 field)
    if office_id:
        results = [m for m in results if m.get("value2") == office_id]

    # Filter by department ID (value3 field)
    if department_id:
        results = [m for m in results if m.get("value3") == department_id]

    # Filter by search term (case-insensitive substring match on value1)
    if search:
        search_lower = search.lower()
        results = [
            m
            for m in results
            if search_lower in m.get("value1", "").lower()
            or search_lower in m.get("key2", "").lower()
        ]

    return results


@app.get("/search-cad-parcels/parcel-numbers")
async def find_parcel_numbers(
    search: str = Query(..., description="Parcel number to search"),
    municipality_reg_num: str = Query(
        ..., alias="municipalityRegNum", description="Municipality registration number"
    ),
):
    """
    Find parcel numbers in a municipality.

    Replicates the observed behaviour of the public endpoint (section 4.2 of
    specs/api-coverage-specification.md):

    - prefix match on the parcel number: "114" matches "114", "1140/1", ...;
      "35/1" also matches the building parcel "*35/1" (the asterisk is ignored
      when a plain number is searched);
    - a leading asterisk is a wildcard: "*35/1" matches "*35/1" and "135/1";
    - "35/1 ZGR" is the building parcel "*35/1" exactly; "35/1.ZGR" and
      "35/1ZGR" match nothing, as on the real server.

    Args:
        search: Parcel number (supports partial matching)
        municipality_reg_num: Municipality registration number

    Returns:
        List of matching parcels with parcel IDs.
    """
    parcels = _parcels.get(municipality_reg_num, [])
    return [
        _six_key_record(parcel["parcelId"], parcel.get("parcelNumber", ""))
        for parcel in parcels
        if _parcel_number_matches(str(parcel.get("parcelNumber", "")), search)
    ]


_ZGR_SEARCH_RE = re.compile(r"^(?P<num>\S+)\s+ZGR$", re.IGNORECASE)


def _parcel_number_matches(parcel_number: str, search: str) -> bool:
    term = search.strip()
    if not term:
        return False
    zgr = _ZGR_SEARCH_RE.match(term)
    if zgr:
        return parcel_number == f"*{zgr.group('num')}"
    bare = parcel_number.lstrip("*")
    if term.startswith("*"):
        return bool(term[1:]) and term[1:] in bare  # the asterisk is a wildcard
    return bare.startswith(term)


@app.get("/search-cad-parcels/possession-sheet-numbers")
async def find_possession_sheet_numbers(
    search: str = Query(..., description="Possession sheet number to search"),
    municipality_reg_num: str = Query(
        ..., alias="municipalityRegNum", description="Municipality registration number"
    ),
):
    """
    Find possession sheets (posjedovni listovi) of a municipality by number.

    ``key1`` is the ``possessionSheetId`` the parcel-info ``possessionSheets[]``
    carry, ``value1`` the sheet number; the other keys are null, as on the
    public endpoint. The sheets are derived from the loaded parcels.
    """
    sheets = _possession_sheets.get(municipality_reg_num, {})
    term = search.strip()
    return [
        _six_key_record(sheet_id, number)
        for sheet_id, number in sorted(sheets.items(), key=lambda kv: (len(kv[1]), kv[1]))
        if number.startswith(term)
    ][:50]  # the live search stops at 50 records


def _filter_books(
    books: list[dict[str, Any]],
    search: str | None,
    office_id: str | None,
    institution_name: str | None,
) -> list[dict[str, Any]]:
    results = books
    if search:
        term = search.strip().lower()
        results = [b for b in results if term in str(b.get("value1", "")).lower()]
    if office_id:
        results = [b for b in results if str(b.get("key2")) == office_id.strip()]
    if institution_name:
        term = institution_name.strip().lower()
        results = [b for b in results if term in str(b.get("value2", "")).lower()]
    return results


@app.get("/search-lr-parcels/main-books")
async def find_main_books(
    search: str | None = Query(None, description="Main book name to search"),
    office_id: str | None = Query(None, alias="officeId", description="Land-registry office id"),
    institution_name: str | None = Query(
        None, alias="institutionName", description="Institution name filter"
    ),
):
    """
    Find land-registry main books (glavne knjige).

    ``key1`` is the main book id the ``/lr/lr-unit`` endpoint takes, ``value1``
    the book name, ``key2`` the land-registry office id, ``value2`` the court
    name, ``displayValue1`` "NAME, COURT".
    """
    return _filter_books(_main_books, search, office_id, institution_name)


@app.get("/search-lr-parcels/books-of-dc")
async def find_books_of_dc(
    search: str | None = Query(None, description="Book name to search"),
    office_id: str | None = Query(None, alias="officeId", description="Land-registry office id"),
    institution_name: str | None = Query(
        None, alias="institutionName", description="Institution name filter"
    ),
):
    """
    Find books of deposited contracts (knjige položenih ugovora, KPU).

    Same record shape as the main books; ``value2`` is the office name
    ("Zemljišnoknjižni odjel Zadar").
    """
    return _filter_books(_books_of_dc, search, office_id, institution_name)


@app.get("/cad/parcel-info")
async def get_parcel_info(
    parcel_id: str = Query(..., alias="parcelId", description="Parcel ID"),
):
    """
    Get detailed information about a parcel.

    Args:
        parcel_id: Parcel ID from search endpoint

    Returns:
        Complete parcel information including ownership, land use, and registry data.
    """
    parcel = _parcel_by_id.get(int(parcel_id))
    if parcel is not None:
        return parcel

    # Parcel not found
    return JSONResponse(
        status_code=404,
        content={"error": "Parcel not found", "parcelId": parcel_id},
    )


# ---------------------------------------------------------------------------
# Possession sheets and the parcel search behind the web form
# ---------------------------------------------------------------------------


def _unit_record(data: Any) -> dict[str, Any] | None:
    """A loaded unit file's payload (the server answers with a list of one)."""
    if isinstance(data, list):
        return data[0] if data else None
    return data if isinstance(data, dict) else None


def _sheet_with_municipality(
    sheet: dict[str, Any], parcel: dict[str, Any], by_number: bool = False
) -> dict[str, Any]:
    """A parcel's sheet as the sheet endpoints return it.

    A non-harmonized sheet comes with its possessors and the municipality
    named. A harmonized sheet (``isHarmonized`` with an ``lrUnit``) comes as
    the stub the live server sends: no possessors and the unit's ``lrUnitId``;
    the by-number variant drops the id and the municipality name as well.
    """
    if parcel.get("isHarmonized") and parcel.get("lrUnit"):
        stub: dict[str, Any] = {
            "possessionSheetNumber": str(sheet.get("possessionSheetNumber")),
            "cadMunicipalityId": parcel.get("cadMunicipalityId"),
            "lrUnitId": parcel["lrUnit"].get("lrUnitId"),
            "possessors": [],
        }
        if not by_number:
            stub = {
                "possessionSheetId": sheet.get("possessionSheetId"),
                **stub,
                "cadMunicipalityRegNum": parcel.get("cadMunicipalityRegNum"),
                "cadMunicipalityName": parcel.get("cadMunicipalityName"),
            }
        return stub
    record = dict(sheet)
    record.setdefault("cadMunicipalityId", parcel.get("cadMunicipalityId"))
    record.setdefault("cadMunicipalityRegNum", parcel.get("cadMunicipalityRegNum"))
    record.setdefault("cadMunicipalityName", parcel.get("cadMunicipalityName"))
    return record


def _find_sheet(
    predicate: Any,
) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """The first (sheet, parcel) pair whose sheet satisfies ``predicate``."""
    for parcels in _parcels.values():
        for parcel in parcels:
            for sheet in parcel.get("possessionSheets") or []:
                if predicate(sheet, parcel):
                    return sheet, parcel
    return None


def searched_parcel_record(
    parcel: dict[str, Any], sheet_number: str | None = None
) -> dict[str, Any]:
    """A parcel-info record reshaped as ``POST /cad/search-parcels`` returns it.

    Two shapes, as observed live: a harmonized parcel carries an inline
    ``lrUnit`` with sheet B (taken from the loaded unit when the mock has it)
    and neither sheet nor links; a non-harmonized one carries one
    ``possessionSheet`` (the sheet asked for, else the first) and its
    ``parcelLinks``.
    """
    dropped = {"possessionSheets", "lrUnit", "parcelLinks", "lrUnitsFromParcelLinks"}
    record = {key: value for key, value in parcel.items() if key not in dropped}
    if parcel.get("isHarmonized") and parcel.get("lrUnit"):
        unit = dict(parcel["lrUnit"])
        full = _unit_record(_lr_units.get(f"{unit.get('mainBookId')}-{unit.get('lrUnitNumber')}"))
        if full and "ownershipSheetB" in full:
            unit["ownershipSheetB"] = full["ownershipSheetB"]
        record["lrUnit"] = unit
        return record
    sheets = parcel.get("possessionSheets") or []
    chosen = next(
        (s for s in sheets if str(s.get("possessionSheetNumber")) == str(sheet_number)),
        sheets[0] if sheets else None,
    )
    if chosen is not None:
        record["possessionSheet"] = chosen
    record["parcelLinks"] = parcel.get("parcelLinks") or []
    return record


@app.get("/cad/possession-sheet")
async def get_possession_sheet(
    possession_sheet_id: str = Query(..., alias="possessionSheetId", description="Sheet id"),
):
    """One possession sheet with its possessors, by id (``{}`` when unknown)."""
    found = _find_sheet(lambda s, p: str(s.get("possessionSheetId")) == possession_sheet_id)
    if found is None:
        return {}
    sheet, parcel = found
    return _sheet_with_municipality(sheet, parcel)


@app.get("/cad/possession-sheet-by-number")
async def get_possession_sheet_by_number(
    possession_sheet_number: str = Query(..., alias="possessionSheetNumber"),
    cad_municipality_id: str = Query(..., alias="cadMunicipalityId"),
):
    """One possession sheet by number and internal municipality id (``{}`` when unknown)."""
    found = _find_sheet(
        lambda s, p: str(s.get("possessionSheetNumber")) == possession_sheet_number.strip()
        and str(p.get("cadMunicipalityId")) == cad_municipality_id
    )
    if found is None:
        return {}
    sheet, parcel = found
    return _sheet_with_municipality(sheet, parcel, by_number=True)


@app.get("/cad/cad-parcels-search-data")
async def get_cad_parcels_search_data(
    possession_sheet_id: str = Query(..., alias="possessionSheetId"),
):
    """A sheet id -> its number and the municipality registration number (``{}`` when unknown)."""
    found = _find_sheet(lambda s, p: str(s.get("possessionSheetId")) == possession_sheet_id)
    if found is None:
        return {}
    sheet, parcel = found
    return {
        "possessionSheetNumber": str(sheet.get("possessionSheetNumber")),
        "municipalityNumber": parcel.get("cadMunicipalityRegNum"),
    }


@app.post("/cad/search-parcels")
async def search_parcels(body: dict[str, Any] = Body(...)):
    """The parcel search behind the web form (``Pregledaj``).

    Body keys ``parcelId``, ``cadMunicipalityId``, ``parcelNumber``,
    ``possessionSheetNumber`` (empty strings when unused). ``parcelId`` alone
    answers that parcel; ``cadMunicipalityId`` with ``possessionSheetNumber``
    every parcel on the sheet, sorted by number; ``cadMunicipalityId`` with
    ``parcelNumber`` that parcel, matched exactly. Anything else, and an
    unknown reference, answers ``[]`` with HTTP 200, as the live server does.
    ``possessionSheetId`` and the registration number are ignored.
    """
    parcel_id = str(body.get("parcelId") or "").strip()
    municipality_id = str(body.get("cadMunicipalityId") or "").strip()
    parcel_number = str(body.get("parcelNumber") or "").strip()
    sheet_number = str(body.get("possessionSheetNumber") or "").strip()
    if parcel_id:
        parcel = _parcel_by_id.get(int(parcel_id)) if parcel_id.isdigit() else None
        return [searched_parcel_record(parcel)] if parcel else []
    if not municipality_id:
        return []
    candidates = [
        p
        for parcels in _parcels.values()
        for p in parcels
        if str(p.get("cadMunicipalityId")) == municipality_id
    ]
    if sheet_number:
        matched = [
            p
            for p in candidates
            if any(
                str(s.get("possessionSheetNumber")) == sheet_number
                for s in p.get("possessionSheets") or []
            )
        ]
        matched.sort(key=lambda p: _parcel_sort_key(str(p.get("parcelNumber", ""))))
        return [searched_parcel_record(p, sheet_number) for p in matched]
    if parcel_number:
        return [
            searched_parcel_record(p)
            for p in candidates
            if str(p.get("parcelNumber")) == parcel_number
        ]
    return []


def _parcel_sort_key(number: str) -> tuple[int, int, int, str]:
    bare = number.lstrip("*")
    main, _, sub = bare.partition("/")
    return (
        1 if number.startswith("*") else 0,
        int(main) if main.isdigit() else 10**9,
        int(sub) if sub.isdigit() else 0,
        number,
    )


@app.get("/lr/lr-unit")
async def get_lr_unit(
    lr_unit_number: str = Query(
        ..., alias="lrUnitNumber", description="Land registry unit number"
    ),
    main_book_id: int = Query(..., alias="mainBookId", description="Main book ID"),
    historical_overview: bool = Query(
        False, alias="historicalOverview", description="Include historical data"
    ),
):
    """
    Get detailed land registry unit information.

    This endpoint returns complete information about a land registry unit (zemljišnoknjižni uložak),
    including ownership (Sheet B), parcels (Sheet A), and encumbrances (Sheet C).

    Args:
        lr_unit_number: Land registry unit number (e.g., "769")
        main_book_id: Main book ID (e.g., 21277)
        historical_overview: Include historical data (default: False)

    Returns:
        List containing land registry unit data (typically 1 element).

    Note:
        ⚠️ DEMO/EDUCATIONAL USE ONLY - Returns static test data.
        The real API returns a list with typically one element.
    """
    # Create lookup key
    key = f"{main_book_id}-{lr_unit_number}"

    # Check if LR unit exists
    if key in _lr_units:
        lr_unit_data = _lr_units[key]
        # Return as list (matching real API behavior)
        return [lr_unit_data]

    # LR unit not found
    return JSONResponse(
        status_code=404,
        content={
            "error": "Land registry unit not found",
            "lrUnitNumber": lr_unit_number,
            "mainBookId": main_book_id,
        },
    )


@app.post("/lr/file-status")
async def get_file_status(body: dict[str, Any] = Body(...)):
    """Get processing status for a single land registry file (plomba / spis).

    Mirrors the production endpoint: it takes the file number split into parts
    (``lrFileCode``, ``lrFileOrderNumber``, ``lrFileYear``) plus the owning
    ``institutionId``, and returns the file's status detail.

    Args:
        body: JSON object with ``lrFileCode``, ``lrFileOrderNumber``,
            ``lrFileYear`` (all required) and ``institutionId``.

    Returns:
        File status object, or an empty object ``{}`` when no record matches
        (the production endpoint also answers unknown files with ``{}``).

    Note:
        ⚠️ DEMO/EDUCATIONAL USE ONLY - Returns static test data.
    """
    # Validate required fields, matching the production 400 shape.
    missing = [
        field
        for field in ("lrFileCode", "lrFileOrderNumber", "lrFileYear")
        if body.get(field) in (None, "")
    ]
    if missing:
        return JSONResponse(
            status_code=400,
            content={
                "status": "BAD_REQUEST",
                "message": "Dogodio se problem sa vašim zahtjevom.",
                "errors": [f"{field}: ne smije bit blank" for field in missing],
                "statusCode": 400,
            },
        )

    institution_id = body.get("institutionId")
    code = str(body["lrFileCode"]).upper()
    order = body["lrFileOrderNumber"]
    year = body["lrFileYear"]
    key = f"{institution_id}-{code}-{order}-{year}".upper()

    # Unknown file (or missing institution context) -> empty object, as in production.
    return _file_status.get(key, {})


@app.get("/atom/ko-{municipality_code}.zip")
async def download_gis_data(municipality_code: str):
    """
    Download GIS data ZIP file for a municipality.

    Args:
        municipality_code: Municipality registration number

    Returns:
        ZIP file containing GML data (if available).
    """
    zip_file = DATA_DIR / "geometry" / f"{municipality_code}.zip"

    if zip_file.exists():
        return FileResponse(
            path=zip_file,
            media_type="application/zip",
            filename=f"ko-{municipality_code}.zip",
        )

    # Return 404 if ZIP doesn't exist
    return JSONResponse(
        status_code=404,
        content={"error": "GIS data not available", "municipality": municipality_code},
    )


# ============================================================================
# Spatial-plan building areas: an imitation of the Ministry's GeoServer WFS
# (specs/spatial-planning-api-specification.md, section 3). Supports the
# subset the SDK uses: GetCapabilities, GetFeature with typeNames, cql_filter
# (INTERSECTS(geom, WKT) and attr='value' clauses joined by AND), bbox,
# count/startIndex, propertyName, resultType=hits, GeoJSON output.
# ============================================================================

_WFS_TYPES = (
    "GradjPodrucje_MGIPU_Public:Gradj_podrucje_naselje",
    "GradjPodrucje_MGIPU_Public:Gradj_podrucje_izvan_naselja",
)
_INTERSECTS_RE = re.compile(
    r"INTERSECTS\s*\(\s*geom\s*,\s*(?P<wkt>POLYGON\s*\(\(.*?\)\))\s*\)", re.I | re.S
)
_CLAUSE_RE = re.compile(r"^\s*(?P<attr>[a-z_0-9]+)\s*=\s*'(?P<value>(?:[^']|'')*)'\s*$", re.I)


def _wfs_exception(code: str, locator: str, text: str) -> Any:
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<ows:ExceptionReport xmlns:ows="http://www.opengis.net/ows/1.1" version="2.0.0">'
        f'<ows:Exception exceptionCode="{code}" locator="{locator}">'
        f"<ows:ExceptionText>{text}</ows:ExceptionText></ows:Exception></ows:ExceptionReport>"
    )

    return Response(content=body, status_code=400, media_type="application/xml")


def _parse_wkt_polygon(wkt: str) -> list[tuple[float, float]]:
    inner = wkt[wkt.index("((") + 2 : wkt.index("))")]
    first_ring = inner.split("),(")[0]  # outer ring only (holes ignored)
    points = []
    for pair in first_ring.split(","):
        x, y = pair.split()
        points.append((float(x), float(y)))
    return points


def _point_in_ring(x: float, y: float, ring: list[tuple[float, float]]) -> bool:
    inside = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def _segments_cross(p1, p2, p3, p4) -> bool:
    def orient(a, b, c) -> float:
        return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])

    d1, d2 = orient(p3, p4, p1), orient(p3, p4, p2)
    d3, d4 = orient(p1, p2, p3), orient(p1, p2, p4)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def _rings_intersect(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> bool:
    if any(_point_in_ring(x, y, b) for x, y in a) or any(_point_in_ring(x, y, a) for x, y in b):
        return True
    for i in range(len(a)):
        for j in range(len(b)):
            if _segments_cross(a[i], a[(i + 1) % len(a)], b[j], b[(j + 1) % len(b)]):
                return True
    return False


def _feature_rings(feature: dict[str, Any]) -> list[list[tuple[float, float]]]:
    geometry = feature["geometry"]
    coords = geometry["coordinates"]
    polygons = [coords] if geometry["type"] == "Polygon" else coords
    return [[(float(x), float(y)) for x, y in polygon[0]] for polygon in polygons]


def _feature_bbox(feature: dict[str, Any]) -> tuple[float, float, float, float]:
    points = [p for ring in _feature_rings(feature) for p in ring]
    return (
        min(p[0] for p in points),
        min(p[1] for p in points),
        max(p[0] for p in points),
        max(p[1] for p in points),
    )


@app.get("/planning/wfs")
async def planning_wfs(
    request: str | None = Query(None),
    type_names: str | None = Query(None, alias="typeNames"),
    type_name_11: str | None = Query(None, alias="typeName"),
    cql_filter: str | None = Query(None),
    bbox: str | None = Query(None),
    count: int | None = Query(None),
    start_index: int = Query(0, alias="startIndex"),
    result_type: str | None = Query(None, alias="resultType"),
    property_name: str | None = Query(None, alias="propertyName"),
):
    """Imitation of the building-areas WFS (GetCapabilities and GetFeature)."""

    op = (request or "").lower()
    if op == "getcapabilities":
        types = "".join(
            f"<FeatureType><Name>{t}</Name><Title>{t.split(':')[1]}</Title>"
            "<DefaultCRS>urn:ogc:def:crs:EPSG::3765</DefaultCRS></FeatureType>"
            for t in _WFS_TYPES
        )
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<wfs:WFS_Capabilities xmlns:wfs="http://www.opengis.net/wfs/2.0" '
            'xmlns:ows="http://www.opengis.net/ows/1.1" version="2.0.0">'
            "<ows:ServiceIdentification><ows:Title>Mock building-areas WFS</ows:Title>"
            "<ows:Fees>NONE</ows:Fees><ows:AccessConstraints>NONE</ows:AccessConstraints>"
            f"</ows:ServiceIdentification><FeatureTypeList>{types}</FeatureTypeList>"
            "</wfs:WFS_Capabilities>"
        )
        return Response(content=body, media_type="application/xml")
    if op != "getfeature":
        return _wfs_exception("OperationNotSupported", "request", f"Unsupported request {request}")

    type_name = type_names or type_name_11 or ""
    if type_name not in _WFS_TYPES:
        return _wfs_exception(
            "InvalidParameterValue", "typeName", f"Feature type {type_name} unknown"
        )
    kind = type_name.split(":", 1)[1]
    selected = [f for f in _zones if f.get("typeName") == type_name]

    if cql_filter:
        text = cql_filter
        match = _INTERSECTS_RE.search(text)
        if match:
            ring = _parse_wkt_polygon(match.group("wkt"))
            selected = [
                f for f in selected if any(_rings_intersect(ring, r) for r in _feature_rings(f))
            ]
            text = text[: match.start()] + text[match.end() :]
        for clause in re.split(r"\bAND\b", text, flags=re.I):
            if not clause.strip():
                continue
            parsed = _CLAUSE_RE.match(clause)
            if not parsed:
                return _wfs_exception(
                    "NoApplicableCode", "cql_filter", f"Could not parse: {clause.strip()}"
                )
            attr, value = parsed.group("attr"), parsed.group("value").replace("''", "'")
            known = selected[0]["properties"] if selected else {attr: None}
            if attr != "geom" and attr not in known:
                return _wfs_exception(
                    "InvalidParameterValue", "cql_filter", f"Attribute {attr} not found on {kind}"
                )
            selected = [f for f in selected if str(f["properties"].get(attr)) == value]

    if bbox:
        parts = bbox.split(",")
        x0, y0, x1, y1 = (float(v) for v in parts[:4])

        def overlaps(f: dict[str, Any]) -> bool:
            fx0, fy0, fx1, fy1 = _feature_bbox(f)
            return not (fx1 < x0 or x1 < fx0 or fy1 < y0 or y1 < fy0)

        selected = [f for f in selected if overlaps(f)]

    matched = len(selected)
    if (result_type or "").lower() == "hits":
        body = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0" '
            f'numberMatched="{matched}" numberReturned="0" timeStamp="2026-01-01T00:00:00Z"/>'
        )
        return Response(content=body, media_type="application/xml")

    page = selected[start_index:]
    if count is not None:
        page = page[:count]

    wanted = [p.strip() for p in property_name.split(",")] if property_name else None
    features = []
    for feature in page:
        props = feature["properties"]
        if wanted is not None:
            props = {k: v for k, v in props.items() if k in wanted}
        features.append(
            {
                "type": "Feature",
                "id": feature["id"],
                "geometry": feature["geometry"] if wanted is None or "geom" in wanted else None,
                "geometry_name": "geom",
                "properties": props,
            }
        )
    return {
        "type": "FeatureCollection",
        "totalFeatures": matched,
        "numberMatched": matched,
        "numberReturned": len(features),
        "timeStamp": "2026-01-01T00:00:00Z",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::3765"}},
        "features": features,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
