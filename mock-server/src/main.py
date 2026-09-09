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
from typing import Any, Optional

from fastapi import Body, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

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
_lr_units: dict[str, dict[str, Any]] = {}  # "mainBookId-lrUnitNumber" -> lr_unit_data
_file_status: dict[str, dict[str, Any]] = {}  # "institutionId-code-order-year" -> file status
_main_books: list[dict[str, Any]] = []  # six-key search records (E5)
_books_of_dc: list[dict[str, Any]] = []  # six-key search records (E6)
# municipality_code -> {possessionSheetId: possessionSheetNumber}, derived from the parcels
_possession_sheets: dict[str, dict[int, str]] = {}


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
    global _main_books, _books_of_dc, _possession_sheets

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
    search: Optional[str] = Query(None, description="Municipality name or code to search"),
    office_id: Optional[str] = Query(
        None, alias="officeId", description="Filter by cadastral office ID"
    ),
    department_id: Optional[str] = Query(
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
    ]


def _filter_books(
    books: list[dict[str, Any]],
    search: Optional[str],
    office_id: Optional[str],
    institution_name: Optional[str],
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
    search: Optional[str] = Query(None, description="Main book name to search"),
    office_id: Optional[str] = Query(None, alias="officeId", description="Land-registry office id"),
    institution_name: Optional[str] = Query(
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
    search: Optional[str] = Query(None, description="Book name to search"),
    office_id: Optional[str] = Query(None, alias="officeId", description="Land-registry office id"),
    institution_name: Optional[str] = Query(
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
    parcel_id_int = int(parcel_id)

    # Search for parcel across all municipalities
    for municipality_code, parcels in _parcels.items():
        for parcel in parcels:
            if parcel.get("parcelId") == parcel_id_int:
                return parcel

    # Parcel not found
    return JSONResponse(
        status_code=404,
        content={"error": "Parcel not found", "parcelId": parcel_id},
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
