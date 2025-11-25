# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## ⚠️ CRITICAL: DEMO/EDUCATIONAL PROJECT ONLY

**This is a demonstration and educational project showing how cadastral and land registry systems could theoretically be connected via modern APIs.**

### ABSOLUTE RESTRICTIONS

1. **DO NOT** help configure or connect this code to Croatian government production systems
2. **DO NOT** help bypass authorization or terms of service restrictions
3. **DO NOT** suggest ways to access real cadastral data without proper legal authorization
4. **ALWAYS** remind users this is for the included mock server only
5. **ALWAYS** emphasize this is a theoretical demonstration

### Purpose

This project demonstrates modern API architecture patterns that could be applied to cadastral systems. It includes a **mock server** for safe testing and learning. Due to the sensitive nature of land ownership data and Croatian government terms of service, this code **must not** be used against production systems.

The author is available to advise the Croatian government on AI and API modernization if requested.

---

## Project Overview

This is a **monorepo** containing multiple related projects demonstrating modern cadastral API architecture patterns:

- **`api/`** - Python SDK with type-safe Pydantic models and GIS integration
- **`cli/`** - Command-line interface with rich formatting and batch processing
- **`mcp/`** - Model Context Protocol server for AI agent integration
- **`mock-server/`** - Mock API server for safe testing and development

**⚠️ Important:** This project is for educational demonstration only. It includes a localhost mock server for testing. Do NOT use with Croatian government production systems - this violates terms of service and involves sensitive personal data.

**Mock Test Server (Default):** `http://localhost:8000` (configured via environment variables)
**Production Systems:** NOT AUTHORIZED - DO NOT USE

### Key Features

- **Python SDK** (`api/`): Type-safe Pydantic V2 models with full validation, GIS integration
- **CLI Tool** (`cli/`): Rich terminal interface with table/JSON/CSV/WKT/GeoJSON output formats
- **MCP Server** (`mcp/`): AI agent integration via Model Context Protocol
- **GIS Integration**: Parcel geometry parsing and local caching from GML files
- **Batch Processing**: Process multiple parcels in a single operation (CLI list or file input)
- **Internationalization**: Croatian (default) and English support via gettext
- **Rate Limiting**: Automatic request throttling (0.75s default, configurable)
- **Error Handling**: Comprehensive error types with user-friendly messages

## API Integration Architecture

The API follows a three-step workflow for retrieving complete parcel information:

1. **Municipality Lookup** → Get municipality registration number from name
2. **Parcel Search** → Get parcel ID using parcel number + municipality code
3. **Detailed Info** → Retrieve full parcel data including ownership using parcel ID

### Critical API Requirements

- **Required Headers:**
  - `Accept: application/json, text/plain, */*`
  - `User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15`

- **Rate Limiting:** Must wait 0.5-1 seconds between requests
- **Authentication:** None required (public data)
- **Timeout:** Set to 10 seconds minimum

### Key Data Structures

**Municipality Search Response:**
- `key1`: Municipality registration number (required for parcel searches)
- `name`: Short municipality name
- `fullName`: Full official name

**Parcel Search Response:**
- `key1`: Parcel ID (critical - needed for detailed info)
- `parcelNumber`: Confirmed parcel number
- `municipalityName`: Municipality name
- `address`: Parcel location

**Parcel Detailed Info Response:**
- `possessionSheets[]`: Array of ownership records
  - Each sheet contains `possessors[]` with name, ownership fraction, and address
- `parcelParts[]`: Land use classification (Pašnjak/Pasture, Oranica/Arable, Šuma/Forest, etc.)
- `area`: Total area in square meters
- `hasBuildingRight`: Boolean indicating if construction is permitted

**Land Registry Unit (Zemljišnoknjižni uložak) Response:**

- **Sheet A (Popis čestica)**: All parcels included in the land registry unit
  - Parcel numbers, cadastral municipalities, areas
- **Sheet B (Vlasnički list)**: Ownership information
  - Owner names, addresses, ownership shares/fractions
  - Ownership type (e.g., full ownership, co-ownership)
- **Sheet C (Teretni list)**: Encumbrances and charges
  - Mortgages, liens, easements, usage rights
  - Registration dates and amounts

**Condominium Support (Etažno vlasništvo):**

Condominiums (apartment buildings) have a special structure in the land registry:

- **Unit Types**: `lrUnitTypeName` indicates property type:
  - `VLASNIČKI` - Standard ownership
  - `ETAŽNO VLASNIŠTVO S ODREĐENIM OMJERIMA` - Condominium with defined shares
- **Detection**: Use `lr_unit.is_condominium()` method (checks `lrUnitTypeName` for "ETAŽN")
  - ⚠️ The `condominiums` boolean flag is **unreliable** (often `false` for actual condominiums)
- **Ownership Shares**: Each apartment is a separate share with:
  - `condominium_number`: Apartment identifier (e.g., "E-16")
  - `condominium_descriptions`: Detailed apartment info (floor, area, rooms)
- **Nested Co-ownership**: Shared apartments use `subSharesAndEntries` for co-owners
- **Possessor Fields**: `condominiumShareNumber` and `condominiumShareOwnership` for common area shares

## Known Municipality Codes

- SAVAR: `334979`
- LUKA: `334731`

(See [specs/Croatian_Cadastral_API_Specification.md](specs/Croatian_Cadastral_API_Specification.md) for complete API documentation)

## Map Integration

Interactive map URL format:
```
https://oss.uredjenazemlja.hr/map?cad_parcel_id=PARCELID
```

Coordinate system: EPSG:3765 (HTRS96 / Croatia TM)

## Environment Configuration

The API client can be configured via environment variables or a `.env` file:

**Environment Variables:**
- `CADASTRAL_API_BASE_URL`: API base URL (default: `http://localhost:8000`)
- `CADASTRAL_API_TIMEOUT`: Request timeout in seconds (default: `10.0`)
- `CADASTRAL_API_RATE_LIMIT`: Rate limit between requests in seconds (default: `0.75`)
- `CADASTRAL_LANG`: Language for CLI output (`hr`, `en`) - Croatian is default

**Setup:**
1. Copy `.env.example` to `.env`
2. Configure the API base URL (defaults to localhost test server)
3. Only set production URL if you have proper authorization

**Example `.env` file:**
```bash
# Use local test server (default)
CADASTRAL_API_BASE_URL=http://localhost:8000

# Or use production API (requires authorization)
# CADASTRAL_API_BASE_URL=https://oss.uredjenazemlja.hr/oss/public

# Optional: Set language (hr, en)
# CADASTRAL_LANG=hr
```

**Python API Usage:**
```python
from cadastral_api import CadastralAPIClient

# Uses environment variables or defaults to localhost
with CadastralAPIClient() as client:
    offices = client.list_cadastral_offices()

# Override base URL programmatically
with CadastralAPIClient(base_url="http://test-server:9000") as client:
    offices = client.list_cadastral_offices()

# Specify cache directory for GIS data
with CadastralAPIClient(cache_dir="./my_gis_cache") as client:
    geometry = client.get_parcel_geometry("103/2", "334979")

# Get land registry unit from parcel
with CadastralAPIClient() as client:
    lr_unit = client.get_lr_unit_from_parcel("279/6", "334979")
    print(f"Unit: {lr_unit.lr_unit_number}")
    print(f"Owners: {len(lr_unit.ownership_sheet_b.owners)}")
    print(f"Parcels: {len(lr_unit.possessory_sheet_a1.cad_parcels)}")

# Get land registry unit by unit number and main book ID
with CadastralAPIClient() as client:
    lr_unit = client.get_lr_unit_detailed("769", 21277)
    summary = lr_unit.summary()
    print(f"Total area: {summary['total_area_m2']} m²")
    print(f"Number of owners: {summary['num_owners']}")

# Working with condominiums (etažno vlasništvo)
with CadastralAPIClient() as client:
    lr_unit = client.get_lr_unit_detailed("13998", 30783)  # Split condominium
    if lr_unit.is_condominium():
        print(f"Condominium with {lr_unit.get_condominium_units_count()} units")
        for share in lr_unit.ownership_sheet_b.lr_unit_shares:
            if share.is_condominium_share():
                print(f"  {share.condominium_number}: {share.get_apartment_description()}")
```

## CLI Features

The project includes a comprehensive command-line interface (`cadastral`) with multiple commands:

### Core Commands

- **`cadastral search`** - Quick parcel search with basic information
- **`cadastral get-parcel`** - Detailed parcel information with owners
- **`cadastral get-lr-unit`** - Get land registry unit (zemljišnoknjižni uložak) with ownership, parcels, and encumbrances
- **`cadastral batch-fetch`** - Process multiple parcels (CLI list or file input). Returns LR unit references for each parcel.
- **`cadastral batch-lr-unit`** - Process multiple land registry units (from file or batch-fetch output)
- **`cadastral search-municipality`** - Search and filter municipalities
- **`cadastral list-offices`** - List all cadastral offices
- **`cadastral get-geometry`** - Retrieve parcel boundary coordinates
- **`cadastral download-gis`** - Download GIS data for a municipality
- **`cadastral cache-clear`** - Clear local GIS cache

### CLI Usage Examples

```bash
# Search for a parcel
cadastral search 103/2 --municipality SAVAR

# Get detailed info with owners
cadastral get-parcel 103/2 -m 334979 --show-owners

# Get land registry unit from parcel
cadastral get-lr-unit --from-parcel 279/6 -m SAVAR --all

# Get land registry unit by unit number and main book ID
cadastral get-lr-unit --unit-number 769 --main-book 21277 --show-owners

# Batch processing from CLI list (returns LR unit refs)
cadastral batch-fetch "103/2,45,396/1" --municipality SAVAR

# Batch processing from file
cadastral batch-fetch --input parcels.csv --format json --output results.json

# Pipeline: batch parcels → batch LR units
cadastral batch-fetch "103/2,45,396/1" -m SAVAR --format json -o parcels.json
cadastral batch-lr-unit --from-batch-output parcels.json

# Direct LR unit batch processing
cadastral batch-lr-unit --input lr_units.csv --show-owners

# Get parcel geometry in WKT format
cadastral get-geometry 103/2 -m 334979 --format wkt

# Get geometry as GeoJSON
cadastral get-geometry 103/2 -m 334979 --format geojson --output parcel.json

# List cadastral offices
cadastral list-offices

# Download GIS data for municipality
cadastral download-gis 334979 --output ./gis_data

# Change language
cadastral search 103/2 -m SAVAR --lang en
```

### Output Formats

All commands support multiple output formats:
- **table** - Rich formatted tables (default for terminal)
- **json** - JSON output
- **csv** - CSV format
- **wkt** - Well-Known Text (geometry commands)
- **geojson** - GeoJSON format (geometry commands)

### Internationalization

The CLI supports multiple languages via the `--lang` flag or `CADASTRAL_LANG` environment variable:

- **Croatian (hr)** - Default language
- **English (en)** - Full English translation

Language selection priority:
1. `--lang` CLI flag
2. `CADASTRAL_LANG` environment variable
3. System locale
4. Default: Croatian

**Note:** Command names and JSON keys remain in English (standard practice), only user-facing text is localized.

## GIS Integration

The project includes robust GIS data handling:

### GIS Cache System

- **Local caching** of downloaded GML files (default: `~/.cadastral_api_cache`)
- **Automatic downloads** when geometry is requested
- **Cache management** via CLI (`cadastral cache-clear`)
- **Municipality-based** organization

### GML Parser

The `GMLParser` class parses INSPIRE-compliant GML files from the ATOM feed:

```python
from cadastral_api import GMLParser

parser = GMLParser("path/to/katastarske_cestice.gml")

# Get single parcel geometry
geometry = parser.get_parcel_by_number("103/2")

# Get all parcels (memory intensive for large municipalities)
all_parcels = parser.get_all_parcels()
```

### Parcel Geometry

The `ParcelGeometry` model includes:
- **parcel_number**: Cadastral parcel number
- **coordinates**: List of Coordinate objects (EPSG:3765)
- **area**: Calculated area in m²
- **centroid**: Calculated center point
- **bounds**: Bounding box (min/max lat/lon)
- **to_wkt()**: Export to Well-Known Text format
- **to_geojson()**: Export to GeoJSON format

### API Method

```python
with CadastralAPIClient() as client:
    # Automatically downloads and caches GML if not present
    geometry = client.get_parcel_geometry("103/2", "334979")

    print(f"Area: {geometry.area} m²")
    print(f"Centroid: {geometry.centroid}")
    print(f"WKT: {geometry.to_wkt()}")
```

## Batch Processing

Process multiple parcels and land registry units efficiently:

### CLI Batch Mode

```bash
# Comma-separated list (returns LR unit refs for each parcel)
cadastral batch-fetch "103/2,45,396/1" -m SAVAR

# From CSV file
cadastral batch-fetch --input parcels.csv --format json -o results.json

# Continue on errors (default)
cadastral batch-fetch --input parcels.csv --continue-on-error

# Stop on first error
cadastral batch-fetch --input parcels.csv --stop-on-error

# Include full parcel details
cadastral batch-fetch "103/2,45" -m SAVAR --detail full --show-owners

# Pipeline: Parcels → LR Units (for detailed ownership/encumbrances)
cadastral batch-fetch "103/2,45,396/1" -m SAVAR --format json -o parcels.json
cadastral batch-lr-unit --from-batch-output parcels.json --show-owners

# Direct LR unit batch (from CSV with lr_unit_number,main_book_id)
cadastral batch-lr-unit --input lr_units.csv --format json -o lr_results.json
```

**batch-fetch output now includes:**
- `lr_unit_number` - Land registry unit number
- `main_book_id` - Main book ID

These can be passed to `batch-lr-unit` for detailed ownership and encumbrance info.

### Input File Formats

**Parcel CSV format:**
```csv
parcel_number,municipality
103/2,334979
45,SAVAR
396/1,334979
```

**Parcel JSON format:**
```json
[
  {"parcel_number": "103/2", "municipality": "334979"},
  {"parcel_number": "45", "municipality": "SAVAR"},
  {"parcel_id": "direct_parcel_id_if_known"}
]
```

**LR Unit CSV format (for batch-lr-unit):**
```csv
lr_unit_number,main_book_id
769,21277
123,45678
```

**LR Unit JSON format (for batch-lr-unit):**
```json
[
  {"lr_unit_number": "769", "main_book_id": 21277},
  {"lr_unit_number": "123", "main_book_id": 45678}
]
```

### Python Batch Processing

```python
from cadastral_api.cli.batch_processor import process_batch
from cadastral_api.cli.input_parsers import ParcelInput

inputs = [
    ParcelInput(parcel_number="103/2", municipality="334979"),
    ParcelInput(parcel_number="45", municipality="SAVAR"),
]

results = process_batch(inputs, continue_on_error=True)

for result in results:
    if result.status == "success":
        print(f"✓ {result.parcel_data.parcel_number}")
    else:
        print(f"✗ Error: {result.error_message}")
```

## Monorepo Structure

**Note:** This repository has been refactored to a monorepo structure. See [refactoring-todo.md](docs/refactoring-todo.md) for the migration checklist.

### Target Structure (Monorepo)

```
boljeuredjenazemlja/
├── api/                          # Python SDK project
│   ├── src/cadastral_api/
│   │   ├── client/              # HTTP client with rate limiting
│   │   │   └── api_client.py
│   │   ├── models/              # Pydantic data models
│   │   │   ├── entities.py      # Core business entities
│   │   │   └── gis_entities.py  # GIS geometry models
│   │   ├── gis/                 # GIS functionality
│   │   │   ├── parser.py        # GML file parser
│   │   │   └── cache.py         # Local GIS cache
│   │   ├── locale/              # Compiled translations
│   │   ├── exceptions.py        # Custom exceptions
│   │   └── i18n.py              # Internationalization
│   ├── tests/unit/              # Unit tests
│   ├── tests/integration/       # Integration tests
│   ├── examples/                # Usage examples
│   ├── docs/                    # API-specific documentation
│   └── pyproject.toml
│
├── cli/                          # CLI application project
│   ├── src/cadastral_cli/
│   │   ├── main.py              # CLI entry point
│   │   ├── commands/            # Command modules
│   │   │   ├── search.py
│   │   │   ├── parcel.py
│   │   │   ├── batch.py
│   │   │   ├── discovery.py
│   │   │   ├── gis.py
│   │   │   └── cache.py
│   │   ├── formatters.py        # Output formatting
│   │   ├── input_parsers.py     # Input parsing
│   │   └── batch_processor.py   # Batch processing
│   ├── tests/                   # CLI tests
│   ├── docs/                    # CLI documentation
│   └── pyproject.toml
│
├── mcp/                          # MCP server project
│   ├── src/cadastral_mcp/
│   │   ├── server.py            # MCP server
│   │   ├── tools.py             # MCP tools
│   │   ├── resources.py         # MCP resources
│   │   ├── prompts.py           # MCP prompts
│   │   └── http_server.py       # HTTP transport
│   ├── tests/                   # MCP tests
│   ├── docs/                    # MCP documentation
│   └── pyproject.toml
│
├── mock-server/                  # Mock API server
│   ├── src/main.py              # FastAPI server
│   ├── data/                    # Test data
│   │   ├── municipalities.json
│   │   ├── offices.json
│   │   └── parcels/
│   ├── docs/                    # Mock server docs
│   └── requirements.txt
│
├── docs/                         # Repository-wide documentation
│   ├── architecture.md          # Overall architecture
│   ├── contributing.md          # Contribution guide
│   └── development-guide.md     # Dev setup
│
├── scripts/                      # Repository-wide scripts
│   ├── compile_translations.sh
│   ├── generate_pot.sh
│   └── update_translations.sh
│
├── po/                           # Translation source files (shared)
│   ├── cadastral.pot
│   ├── hr.po
│   └── en.po
│
├── README.md                     # Main repository README
├── CLAUDE.md                     # This file
├── .env.example                  # Environment variables template
└── pyproject.toml                # Legacy (for reference)
```

## Development Guidelines

### Naming Conventions

**IMPORTANT:** All new code must follow the naming conventions in [naming-conventions.md](docs/naming-conventions.md):

- **Top-level projects**: `kebab-case/` (e.g., `api/`, `mock-server/`)
- **Python packages**: `snake_case/` (e.g., `cadastral_api/`, `cadastral_cli/`)
- **Python modules**: `snake_case.py` (e.g., `api_client.py`)
- **Documentation**: `kebab-case.md` or `UPPERCASE.md` (e.g., `api-reference.md`, `README.md`)
- **Test files**: `test_<module>.py` (e.g., `test_api_client.py`)

### Adding New Features

1. **Models**: Use Pydantic V2 with strict validation
2. **Type hints**: Required on all functions (Python 3.12+ syntax)
3. **CLI commands**: Keep command/option names in English
4. **Localization**: Wrap user-facing strings in `_()` from `i18n` module
5. **Error handling**: Use typed exceptions from `exceptions.py`
6. **Testing**: Add tests for new features
7. **File naming**: Follow [naming-conventions.md](docs/naming-conventions.md)

### Internationalization Workflow

When adding user-facing text:

```python
from ...i18n import _, ngettext, pgettext

# Simple translation
print(_("Parcel not found"))

# Plural forms
msg = ngettext("{n} parcel", "{n} parcels", count)

# Context-specific (when same word has different meanings)
label = pgettext("table_header", "Name")
```

After adding strings:
```bash
# Extract strings to template
./scripts/generate_pot.sh

# Update translation files
./scripts/update_translations.sh

# Edit po/hr.po, po/en.po with translations

# Compile translations
./scripts/compile_translations.sh
```

### Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=cadastral_api

# Type checking
mypy src/cadastral_api

# Linting
ruff check src/
```

## Documentation

### Repository Documentation
- **[README.md](README.md)** - Main repository README
- **[CLAUDE.md](CLAUDE.md)** - This file (AI assistant instructions)
- **[docs/naming-conventions.md](docs/naming-conventions.md)** - File and folder naming standards
- **[docs/refactoring-todo.md](docs/refactoring-todo.md)** - Monorepo refactoring checklist

### Project Documentation
- **[api/README.md](api/README.md)** - Python SDK documentation
- **[api/docs/pydantic-entities-implementation.md](api/docs/pydantic-entities-implementation.md)** - Pydantic models specification
- **[cli/README.md](cli/README.md)** - CLI application documentation
- **[cli/docs/command-reference.md](cli/docs/command-reference.md)** - Complete CLI command reference
- **[mcp/README.md](mcp/README.md)** - MCP server documentation
- **[mcp/docs/mcp-server.md](mcp/docs/mcp-server.md)** - MCP protocol details
- **[mock-server/README.md](mock-server/README.md)** - Mock server documentation

### Technical Specifications
- **[docs/croatian-cadastral-api-specification.md](docs/croatian-cadastral-api-specification.md)** - Complete API specification
- **[docs/i18n-guide.md](docs/i18n-guide.md)** - Internationalization developer guide
- **[docs/i18n-implementation-status.md](docs/i18n-implementation-status.md)** - i18n implementation status
- **[docs/translation-status.md](docs/translation-status.md)** - Translation progress tracking

### Examples
- **[api/examples/basic_usage.py](api/examples/basic_usage.py)** - Basic SDK usage
- **[api/examples/municipality_search.py](api/examples/municipality_search.py)** - Municipality search
- **[api/examples/gis_parcel_geometry.py](api/examples/gis_parcel_geometry.py)** - GIS geometry examples

## Related Services

- **WFS INSPIRE Service:** `https://oss.uredjenazemlja.hr/wfs` - Download cadastral geometries in GML format
- **ATOM Download Service:** Bulk municipality data downloads via catalog.uredjenazemlja.hr
- **Interactive Map:** `https://oss.uredjenazemlja.hr/map?cad_parcel_id=PARCELID` - View parcels on map

## Important Notes

### Python Version
Requires Python 3.12+ for modern type hint syntax (`str | None`, `list[T]`, etc.)

### Data Inconsistencies
Based on live API testing:
- **Ownership fractions are optional** - Many parcels don't include the `ownership` field
- **Area is string type** - API returns area as string, automatically converted in models
- **Multiple possession sheets** - A single parcel can have multiple ownership records

### Translation Status
The i18n infrastructure is complete, but translation files are still being populated:
- Core i18n module: ✅ Complete
- Translation scripts: ✅ Complete
- CLI commands: 🔄 Partially localized (ongoing work)
- Translation files (.po): 🔄 In progress
