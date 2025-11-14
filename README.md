# Croatian Cadastral API Client

## ⚠️ IMPORTANT DISCLAIMER - DEMO/EDUCATIONAL PROJECT

**This is a demonstration and educational project showing how cadastral and land registry systems could theoretically be connected and accessed via an API.**

This project includes a **mock server** that mimics the functionality of a cadastral system for testing and learning purposes only.

### Critical Restrictions

- **NOT ALLOWED**: Using this code with Croatian government production systems
- **NOT ALLOWED**: Accessing real cadastral data without proper authorization
- **REASON**: Sensitive nature of land ownership data and terms of service restrictions

This is purely a theoretical exercise demonstrating modern API design patterns for land registry systems. The author is available to advise the Croatian government on AI and API implementation if requested.

**For testing and learning only - use the included mock server, not production systems.**

---

Python client library demonstrating modern API access patterns for cadastral systems. Access parcel information, ownership data, and land registry records programmatically.

**Requires Python 3.12+** for modern type hint syntax (`str | None`, `list[T]`, etc.)

## Features

### Python SDK
- 🔍 Search for parcels by number and municipality
- 📊 Retrieve detailed parcel information including ownership
- 🗺️ Access parcel geometries and GIS spatial data
- 🏗️ Type-safe Pydantic V2 models with validation
- ⚡ Automatic rate limiting and retry logic
- 🛡️ Comprehensive error handling
- 📝 Fully typed with modern Python 3.12+ type hints
- 💾 Local caching of GIS data for performance

### Command-Line Interface
- 🖥️ Complete CLI for terminal access
- 📋 Multiple output formats (table, JSON, CSV, WKT, GeoJSON)
- 🔄 Batch operations support
- 📦 GIS data download and management
- 💡 User-friendly with helpful error messages
- 🎨 Rich formatted output with colors

See [docs/CLI.md](docs/CLI.md) for complete CLI documentation.

### MCP Server (AI Integration)
- 🤖 **Model Context Protocol** server for AI agents
- 🔌 **Dual transport**: STDIO (Claude Desktop) + HTTP (web/remote)
- 🛠️ **Tools**: AI-invoked actions (search, batch fetch, geometry)
- 📄 **Resources**: Auto-fetched contextual data
- 💬 **Prompts**: Reusable templates for common workflows
- 🎯 **Stateless design**: Horizontally scalable, serverless-ready

See [docs/MCP_SERVER.md](docs/MCP_SERVER.md) for complete MCP server documentation.

## Installation

### From source (development)

```bash
pip install -e .
```

### With development dependencies

```bash
pip install -e ".[dev]"
```

## Quick Start

### Command-Line Interface

```bash
# Search for a parcel
cadastral search 103/2 --municipality SAVAR

# Get detailed information with owners
cadastral get-parcel 103/2 -m 334979 --show-owners

# Get parcel boundary coordinates
cadastral get-geometry 103/2 -m 334979 --format wkt

# List cadastral offices
cadastral list-offices

# Download GIS data for a municipality
cadastral download-gis 334979 --output ./gis_data
```

See [docs/CLI.md](docs/CLI.md) for complete command reference.

### MCP Server (AI Integration)

```bash
# Run with STDIO transport (for Claude Desktop)
cadastral-mcp --transport stdio

# Run with HTTP transport (for web/remote access)
cadastral-mcp --transport http --port 8080
```

**Claude Desktop Configuration:**

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "cadastral": {
      "command": "cadastral-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "CADASTRAL_API_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

See [docs/MCP_SERVER.md](docs/MCP_SERVER.md) for complete documentation.

### Python SDK

```python
from cadastral_api import CadastralAPIClient

# Initialize client with automatic rate limiting
with CadastralAPIClient() as client:
    # Optional: List all cadastral offices
    offices = client.list_cadastral_offices()
    # offices[0].id -> "114", offices[0].name -> "PODRUČNI URED ZA KATASTAR ZADAR"

    # Search for municipality (if you don't know the code)
    municipalities = client.search_municipality("SAVAR")
    municipality_code = municipalities[0].municipality_reg_num  # "334979"

    # Or filter municipalities by cadastral office
    zadar_municipalities = client.search_municipality(office_id="114")  # 162 results

    # Or filter by office and department
    zadar_dept_municipalities = client.search_municipality(office_id="114", department_id="116")  # 66 results

    # Or use a known municipality code directly
    # Search for parcel
    results = client.search_parcel("103/2", municipality_reg_num="334979")

    # Get detailed information
    parcel_info = client.get_parcel_info(results[0].parcel_id)

    print(f"Parcel: {parcel_info.parcel_number}")
    print(f"Area: {parcel_info.area_numeric} m²")
    print(f"Owners: {parcel_info.total_owners}")

    # View land use
    for land_type, area in parcel_info.land_use_summary.items():
        print(f"  {land_type}: {area} m²")
```

## API Overview

### CadastralAPIClient

Main client for interacting with the API.

```python
client = CadastralAPIClient(
    rate_limit=0.75,  # Seconds between requests (default: 0.75)
    timeout=10.0      # Request timeout (default: 10.0)
)
```

#### Methods

- **`list_cadastral_offices()`** - List all cadastral offices in Croatia
  - Returns: `list[CadastralOffice]`
  - Returns all 21 cadastral offices (Područni uredi za katastar)
  - Office IDs match `institutionId` in other responses

- **`search_municipality(search_term=None, office_id=None, department_id=None)`** - Search for municipalities
  - Returns: `list[MunicipalitySearchResult]`
  - Supports both name and code search (e.g., "SAVAR" or "334979")
  - Can filter by `office_id` (162 municipalities for Zadar office "114")
  - Can further filter by `department_id` (66 municipalities for department "116")
  - All parameters are optional and can be combined
  - Partial name searches return multiple results

- **`search_parcel(parcel_number, municipality_reg_num)`** - Search for parcels
  - Returns: `list[ParcelSearchResult]`
  - Supports partial matching (e.g., "114" returns 114, 1140/1, etc.)

- **`get_parcel_info(parcel_id)`** - Get complete parcel details
  - Returns: `ParcelInfo`
  - Includes ownership, land use, and registry information

- **`get_parcel_by_number(parcel_number, municipality_reg_num, exact_match=True)`** - Convenience method
  - Returns: `ParcelInfo | None`
  - Combines search and detail retrieval

- **`get_map_url(parcel_id)`** - Generate interactive map URL
  - Returns: `str`

- **`get_municipality_gis_download_url(municipality_reg_num)`** - Generate GIS data download URL
  - Returns: `str`
  - Downloads ZIP with parcel boundaries and spatial data in GML format
  - ✅ No authentication required - direct download works
  - INSPIRE-compliant ATOM feed service

## Data Models

### ParcelInfo

Complete parcel information with computed properties:

```python
parcel.parcel_number          # Cadastral parcel number
parcel.area_numeric           # Area as integer (m²)
parcel.total_owners           # Count of all owners
parcel.land_use_summary       # Dict of land use types to areas
parcel.has_building_right     # Building permission flag
parcel.possession_sheets      # List of ownership records
parcel.parcel_parts           # List of land use classifications
```

### Possessor

Owner information with optional ownership fraction:

```python
possessor.name                # Owner's full name
possessor.address             # Owner's address
possessor.ownership           # Fraction (e.g., "1/4") - often None
possessor.ownership_decimal   # Decimal value (e.g., 0.25) - computed
```

### PossessionSheet

Ownership record:

```python
sheet.possession_sheet_number # Sheet reference
sheet.possessors              # List of Possessor objects
sheet.total_ownership         # Sum of ownership fractions - computed
```

### ParcelPart

Land use classification:

```python
part.name                     # Land use type (e.g., "PAŠNJAK", "MASLINJAK")
part.area_numeric             # Area as integer (m²) - computed
part.building                 # Contains buildings flag
```

## Known Municipality Codes

- SAVAR: `334979`
- LUKA: `334731`

## GIS Data Downloads

The API provides INSPIRE-compliant GIS data downloads for each municipality. **No authentication required** - direct downloads work perfectly!

```python
from cadastral_api import CadastralAPIClient
import httpx

with CadastralAPIClient() as client:
    # Get download URL for SAVAR municipality
    url = client.get_municipality_gis_download_url("334979")
    # Returns: "https://oss.uredjenazemlja.hr/oss/public/atom/ko-334979.zip"

    # Direct download - no authentication needed!
    response = httpx.get(url)
    with open("savar_gis.zip", "wb") as f:
        f.write(response.content)
```

**ZIP file contents** (example from SAVAR - 224 KB total):
- `katastarske_cestice.gml` - Cadastral parcels (~1.4 MB uncompressed)
- `katastarske_opcine.gml` - Cadastral municipalities
- `nacini_uporabe_zemljista.gml` - Land use types
- `nacini_uporabe_zgrada.gml` - Building use types

**Notes:**
- ✅ No authentication or session required
- GML files use INSPIRE-compliant schemas
- File sizes range from ~200KB to several MB depending on municipality
- Suitable for automated bulk downloads
- Perfect for GIS applications (QGIS, ArcGIS, etc.)

## Error Handling

```python
from cadastral_api import (
    ParcelNotFoundError,
    APIConnectionError,
    APITimeoutError,
    InvalidResponseError,
)

try:
    parcel = client.get_parcel_by_number("103/2", "334979")
except ParcelNotFoundError as e:
    print(f"Parcel not found: {e}")
except APIConnectionError as e:
    print(f"Connection error: {e}")
except APITimeoutError as e:
    print(f"Request timed out: {e}")
```

## Examples

See [examples/basic_usage.py](examples/basic_usage.py) for a complete working example.

Run the example:

```bash
python examples/basic_usage.py
```

## API Rate Limiting

The client enforces a minimum delay between requests (default: 0.75 seconds) to comply with API best practices. The API documentation recommends 0.5-1 second between requests.

## Important Notes

### Data Inconsistencies

Based on live API testing, be aware of:

1. **Ownership fractions are optional** - Many parcels don't include the `ownership` field in possessor records
2. **Area is string type** - API returns area as string, not integer (automatically converted in models)
3. **Multiple possession sheets** - A single parcel can have multiple ownership records
4. **Municipality search endpoint is broken** - Returns 404 as of November 2025

### Type Safety

All models use Pydantic V2 with strict validation. Invalid data will raise `ValidationError`.

## Documentation

### User Documentation

## Development

### Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking
mypy src/cadastral_api

# Linting
ruff check src/
```

### Project Structure

```
src/cadastral_api/
├── __init__.py           # Package exports
├── client/
│   ├── api_client.py     # HTTP client with rate limiting
│   └── __init__.py
├── models/
│   ├── entities.py       # Pydantic models
│   └── __init__.py
├── exceptions.py         # Custom exceptions
└── tests/                # Test suite
```

## License

MIT License

## Contributing

Contributions welcome! Please ensure:
- Type hints on all functions
- Pydantic models for all API responses
- Tests for new features
- Documentation updates

## Legal Disclaimer

**DEMO PROJECT - NOT FOR PRODUCTION USE**

This is an **unofficial, educational demonstration project** showing how a modern cadastral API could theoretically work. It is:

- **NOT authorized** for use with Croatian government production systems
- **NOT intended** for accessing real cadastral data without proper authorization
- **ONLY for educational purposes** and demonstration of API design patterns
- **Includes a mock server** for safe testing and learning

### Terms of Use

Due to the sensitive nature of land ownership data and the terms of service of official Croatian government systems:

1. This code **must not** be used against production Croatian cadastral systems
2. Real cadastral data access requires proper legal authorization
3. This is a theoretical demonstration only
4. All examples should use the included mock server

### Author's Note

This project demonstrates modern API architecture patterns that could be applied to cadastral systems. If the Croatian government is interested in AI integration or API modernization, the author is available for consultation.

**Use responsibly and only for educational purposes with the mock server.**

---

**Tested with real API data from SAVAR municipality (November 2025)**

### User Documentation
- **[docs/](docs/)** - User guides and CLI documentation
  - [CLI.md](docs/CLI.md) - Complete CLI command reference with examples

### Technical Specifications
- **[specs/](specs/)** - Technical specifications and implementation docs
  - [Croatian_Cadastral_API_Specification.md](specs/Croatian_Cadastral_API_Specification.md) - Complete API documentation
  - [Pydantic_Business_Entities_Implementation.md](specs/Pydantic_Business_Entities_Implementation.md) - Pydantic models specification
  - [I18N_GUIDE.md](specs/I18N_GUIDE.md) - Internationalization developer guide
  - [I18N_IMPLEMENTATION_STATUS.md](specs/I18N_IMPLEMENTATION_STATUS.md) - i18n implementation status

### Project Information
- [CLAUDE.md](CLAUDE.md) - Repository guidance for AI assistants
- [Examples](examples/) - Python code examples
