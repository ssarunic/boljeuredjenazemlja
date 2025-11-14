"""Mock FastAPI server for Croatian Cadastral API.

⚠️ DEMO/EDUCATIONAL PROJECT ONLY ⚠️

This is a mock server for testing and demonstration purposes.
It returns static data from JSON files to mimic the behavior of
the Croatian cadastral API without accessing real government systems.

DO NOT use this to connect to production systems.
"""

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Query
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
DATA_DIR = Path(__file__).parent / "data"

# In-memory data storage (loaded at startup)
_offices: list[dict[str, Any]] = []
_municipalities: list[dict[str, Any]] = []
_parcels: dict[str, list[dict[str, Any]]] = {}  # municipality_code -> parcels


def load_json(filepath: Path) -> Any:
    """Load JSON file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


@app.on_event("startup")
async def load_data():
    """Load all static data into memory on startup."""
    global _offices, _municipalities, _parcels

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

    print(f"\n🚀 Mock server ready with {len(_parcels)} municipalities")


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
            "parcel_info": "/cad/parcel-info",
            "gis_download": "/atom/ko-{code}.zip",
        },
        "data_loaded": {
            "offices": len(_offices),
            "municipalities": len(_municipalities),
            "parcel_sets": len(_parcels),
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
async def search_municipalities(
    search: Optional[str] = Query(None, description="Municipality name or code to search"),
    officeId: Optional[str] = Query(None, description="Filter by cadastral office ID"),
    departmentId: Optional[str] = Query(None, description="Filter by department ID"),
):
    """
    Search municipalities by name, code, office, or department.

    Args:
        search: Municipality name or registration code (optional)
        officeId: Cadastral office ID filter (optional)
        departmentId: Department ID filter (optional)

    Returns:
        List of matching municipalities.
    """
    results = _municipalities

    # Filter by office ID (value2 field)
    if officeId:
        results = [m for m in results if m.get("value2") == officeId]

    # Filter by department ID (value3 field)
    if departmentId:
        results = [m for m in results if m.get("value3") == departmentId]

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
async def search_parcel_numbers(
    search: str = Query(..., description="Parcel number to search"),
    municipalityRegNum: str = Query(..., description="Municipality registration number"),
):
    """
    Search for parcel numbers in a municipality.

    Supports partial matching (e.g., "114" will match "114", "1140/1", "1141", etc.)

    Args:
        search: Parcel number (supports partial matching)
        municipalityRegNum: Municipality registration number

    Returns:
        List of matching parcels with parcel IDs.
    """
    # Get parcels for this municipality
    parcels = _parcels.get(municipalityRegNum, [])

    # Perform partial search on parcel numbers
    search_normalized = search.strip()
    matches = []

    for parcel in parcels:
        parcel_number = parcel.get("parcelNumber", "")

        # Partial match: search term appears at start of parcel number
        if parcel_number.startswith(search_normalized):
            matches.append(
                {
                    "key1": str(parcel["parcelId"]),
                    "value1": parcel_number,
                    "key2": None,
                    "value2": None,
                    "value3": None,
                    "displayValue1": None,
                }
            )

    return matches


@app.get("/cad/parcel-info")
async def get_parcel_info(
    parcelId: str = Query(..., description="Parcel ID"),
):
    """
    Get detailed information about a parcel.

    Args:
        parcelId: Parcel ID from search endpoint

    Returns:
        Complete parcel information including ownership, land use, and registry data.
    """
    parcel_id_int = int(parcelId)

    # Search for parcel across all municipalities
    for municipality_code, parcels in _parcels.items():
        for parcel in parcels:
            if parcel.get("parcelId") == parcel_id_int:
                return parcel

    # Parcel not found
    return JSONResponse(
        status_code=404,
        content={"error": "Parcel not found", "parcelId": parcelId},
    )


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
