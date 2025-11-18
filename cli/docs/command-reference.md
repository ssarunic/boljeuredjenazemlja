# Croatian Cadastral CLI - Command Reference

## ⚠️ DEMO PROJECT - EDUCATIONAL USE ONLY

**This CLI is part of a demonstration project showing how a modern cadastral API could work.**

### Important Restrictions

- ✅ **USE**: With the included mock server for testing and learning
- ❌ **DO NOT USE**: With Croatian government production systems
- ❌ **DO NOT USE**: To access real cadastral data without authorization

This is a theoretical demonstration of API design patterns. Due to sensitive land ownership data and terms of service restrictions, production use is not authorized.

**For educational and testing purposes only.**

---

Complete command-line interface demonstrating cadastral data access patterns.

## Installation

```bash
# Install the package
pip install -e .

# Verify installation
cadastral --version
cadastral --help
```

## Quick Start

```bash
# Search for a parcel
cadastral search 103/2 --municipality SAVAR

# Get detailed parcel information
cadastral get-parcel 103/2 -m 334979 --show-owners

# List cadastral offices
cadastral list-offices

# Get parcel boundary coordinates
cadastral get-geometry 103/2 -m 334979 --format wkt

# Download GIS data for a municipality
cadastral download-gis 334979 --output ./gis_data
```

---

## Commands

### Search Commands

#### `cadastral search`
Quick search for parcels with basic information.

```bash
# Basic usage
cadastral search 103/2 --municipality SAVAR
cadastral search 103/2 -m 334979

# Partial search
cadastral search 114 -m 334979 --partial

# Export to JSON
cadastral search 103/2 -m 334979 --format json

# Export to file
cadastral search 103/2 -m 334979 --format csv --output parcel.csv
```

**Options:**
- `--municipality, -m` (required) - Municipality name or code
- `--exact/--partial` - Exact match (default) or partial search
- `--format, -f` - Output format: table (default), json, csv
- `--output, -o` - Save output to file

**Output:**
```
Parcel Number      103/2
Municipality       SAVAR (334979)
Address            POLJE
Area               1,200 m²
Land Use           MASLINJAK
Building Permitted No
Owners             2 owner(s)
```

---

#### `cadastral search-municipality`
Search and filter municipalities.

```bash
# Search by name
cadastral search-municipality SAVAR

# Filter by office
cadastral search-municipality --office 114

# Filter by office and department
cadastral search-municipality --office 114 --department 116

# Combine search and filter
cadastral search-municipality SAVAR --office 114

# Count only
cadastral search-municipality --office 114 --count-only

# Export to JSON
cadastral search-municipality --office 114 --format json -out municipalities.json
```

**Options:**
- `search_term` (optional) - Municipality name or code
- `--office, -o` - Filter by cadastral office ID
- `--department, -d` - Filter by department ID
- `--format, -f` - Output format: table, json, csv
- `--output, -out` - Save to file
- `--count-only` - Show count only

---

### Detailed Information

#### `cadastral get-parcel`
Get complete parcel information with ownership details.

```bash
# Full details (default)
cadastral get-parcel 103/2 -m 334979

# Show owners
cadastral get-parcel 103/2 -m SAVAR --show-owners

# Different detail levels
cadastral get-parcel 103/2 -m 334979 --detail basic
cadastral get-parcel 103/2 -m 334979 --detail owners
cadastral get-parcel 103/2 -m 334979 --detail landuse
cadastral get-parcel 103/2 -m 334979 --detail geometry

# With geometry
cadastral get-parcel 103/2 -m 334979 --show-geometry

# Export to JSON
cadastral get-parcel 103/2 -m 334979 --format json -o parcel.json

# Export to YAML
cadastral get-parcel 103/2 -m 334979 --format yaml -o parcel.yaml
```

**Options:**
- `--municipality, -m` (required) - Municipality name or code
- `--detail` - Detail level: basic, full (default), owners, landuse, geometry
- `--show-owners` - Include ownership details
- `--show-geometry` - Include boundary coordinates
- `--format, -f` - Output format: table, json, yaml, csv
- `--output, -o` - Save to file

**Detail Levels:**

**basic** - Core information:
```
Parcel Number: 103/2
Area: 1,200 m²
Address: POLJE
Municipality: SAVAR (334979)
```

**full** (default) - Complete information:
```
=== PARCEL INFORMATION ===
[Core details]

=== LAND USE ===
[Land use breakdown]

=== OWNERSHIP (2 owners) ===
[Owner details with fractions]

=== LAND REGISTRY ===
[Registry information]

=== ADDITIONAL INFO ===
[Map URL, etc.]
```

**owners** - Focus on ownership:
```
=== OWNERSHIP (2 owners) ===
Possession Sheet 1
Name             Ownership    Address
--------------   ----------   ------------------
Ivan Šarunić     1/2 (50%)    Zadar, Ulica 123
Marija Šarunić   1/2 (50%)    Zadar, Ulica 123
```

**landuse** - Land use analysis:
```
=== LAND USE ===
Type          Area (m²)    Percentage   Buildings
-----------   ---------    ----------   ---------
MASLINJAK     1,200        100.00%      No
```

**geometry** - Include spatial data:
```
[Full parcel info]

=== GEOMETRY ===
Coordinate System: EPSG:3765
Vertices: 87
Bounding Box: ...
```

---

#### `cadastral get-lr-unit`
Get detailed land registry unit (zemljišnoknjižni uložak) information including ownership, parcels, and encumbrances.

```bash
# Get by LR unit number and main book ID
cadastral get-lr-unit --unit-number 769 --main-book 21277

# Get from parcel (automatic lookup)
cadastral get-lr-unit --from-parcel 279/6 -m SAVAR

# Show only ownership information (Sheet B)
cadastral get-lr-unit -u 769 -b 21277 --show-owners

# Show all parcels in the unit (Sheet A)
cadastral get-lr-unit -u 769 -b 21277 --show-parcels

# Show encumbrances (Sheet C)
cadastral get-lr-unit -u 769 -b 21277 --show-encumbrances

# Show all sheets
cadastral get-lr-unit -p 279/6 -m SAVAR --all

# Export to JSON
cadastral get-lr-unit -u 769 -b 21277 --format json -o lr-unit.json
```

**Options:**
- `--unit-number, -u` - Land registry unit number (e.g., '769')
- `--main-book, -b` - Main book ID (e.g., 21277)
- `--from-parcel, -p` - Get LR unit from parcel number (requires --municipality)
- `--municipality, -m` - Municipality name or code (required with --from-parcel)
- `--show-owners, -o` - Display ownership details (Sheet B)
- `--show-parcels, -P` - Display all parcels in unit (Sheet A)
- `--show-encumbrances, -e` - Display encumbrances (Sheet C)
- `--all, -a` - Show all sheets
- `--format, -f` - Output format: table (default), json, csv
- `--output` - Save output to file
- `--lang` - Language for output (hr, en)

**Output (default - summary):**
```
=== LAND REGISTRY UNIT ===
Unit Number        769
Main Book          TESTMUNICIPALITY
Institution        Test Land Registry Office
Status             Aktivan
Unit Type          VLASNIČKI
Last Diary Number  Z-27986/2025

=== SUMMARY ===
Total Parcels      3
Total Area         2,621 m²
Number of Owners   5
Has Encumbrances   Yes

💡 Use --show-owners to see ownership details
💡 Use --show-parcels to see all parcels
💡 Use --show-encumbrances to see encumbrances
```

**Output (with --show-owners):**
```
=== OWNERSHIP SHEET (LIST B) ===
Share              Owner          Address                    OIB
--------------     -----------    ----------------------     -----------
4/8                Test Owner A   -                          -
1/8                Test Owner B   -                          -
1/8                Test Owner C   -                          -
1/8                Test Owner D   Test Street 123            12345678901
1/8                Test Owner E   Test Avenue 456            98765432109
```

**Output (with --show-parcels):**
```
=== PARCEL LIST (SHEET A) ===
Parcel Number  Address          Area (m²)
-------------  --------------   ---------
118/4          TEST FIELD       409
192/3          TEST AREA        322
279/6          TEST LOCATION    1890

TOTAL                           2621
```

**Output (with --show-encumbrances):**
```
=== ENCUMBRANCES SHEET (LIST C) ===
Description                     Details
-----------------------------   --------------------------------
1. Na suvlasnički dio: 1 (4/8)  • 1.1: Zaprimljeno 05.05.2016...
```

**Land Registry Sheets:**
- **Sheet A (Posjedovni list)** - List of all parcels in the LR unit
- **Sheet B (Vlasnički list)** - Ownership information with shares
- **Sheet C (Teretn list)** - Encumbrances (mortgages, liens, easements)

---

### GIS Commands

#### `cadastral get-geometry`
Get parcel boundary coordinates for GIS integration.

```bash
# WKT format (default)
cadastral get-geometry 103/2 -m 334979

# GeoJSON format
cadastral get-geometry 103/2 -m 334979 --format geojson

# Save to file
cadastral get-geometry 103/2 -m 334979 --format wkt -o parcel.wkt
cadastral get-geometry 103/2 -m 334979 --format geojson -o parcel.geojson

# CSV format (coordinate list)
cadastral get-geometry 103/2 -m 334979 --format csv -o coords.csv

# JSON format with metadata
cadastral get-geometry 103/2 -m 334979 --format json -o geometry.json

# Show statistics
cadastral get-geometry 103/2 -m 334979 --show-stats
```

**Options:**
- `--municipality, -m` (required) - Municipality name or code
- `--format, -f` - Export format: wkt (default), geojson, csv, json
- `--output, -o` - Save to file
- `--show-stats` - Include geometry statistics

**Output Formats:**

**WKT:**
```
POLYGON((380455.97 4882138.52, 380459.6 4882133.45, ...))
```

**GeoJSON:**
```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[380455.97, 4882138.52], ...]]
  },
  "properties": {
    "parcel_number": "103/2",
    "municipality": "334979",
    "area_m2": 1200
  }
}
```

**CSV:**
```csv
x,y,vertex
380455.97,4882138.52,1
380459.60,4882133.45,2
...
```

---

#### `cadastral download-gis`
Download complete GIS data for a municipality.

```bash
# Download and extract
cadastral download-gis 334979 --output ./gis_data

# Download for named municipality
cadastral download-gis SAVAR --output ./savar_gis

# Download without extracting
cadastral download-gis 334979 --output ./data --no-extract

# Clear cache and re-download
cadastral download-gis 334979 -o ./data --clear-cache
```

**Options:**
- `municipality` (required) - Municipality name or code
- `--output, -o` (required) - Output directory
- `--extract/--no-extract` - Extract ZIP file (default: yes)
- `--clear-cache` - Clear cached data first

**Output:**
```
Downloading GIS data for municipality 334979...
✓ Downloaded: ko-334979.zip (224 KB)
✓ Extracted to: ./gis_data

Files:
  • katastarske_cestice.gml (1.4 MB)
  • katastarske_opcine.gml (252 KB)
  • nacini_uporabe_zemljista.gml (77 KB)
  • nacini_uporabe_zgrada.gml (127 KB)

Total parcels: 1,247
```

---

### Discovery Commands

#### `cadastral list-offices`
List all cadastral offices in Croatia.

```bash
# Table format (default)
cadastral list-offices

# JSON format
cadastral list-offices --format json

# Save to file
cadastral list-offices --format csv --output offices.csv
```

**Options:**
- `--format, -f` - Output format: table, json, csv
- `--output, -o` - Save to file

**Output:**
```
21 Cadastral Offices in Croatia:

ID   Name
---  ----------------------------------------
35   PODRUČNI URED ZA KATASTAR KRAPINA
114  PODRUČNI URED ZA KATASTAR ZADAR
130  PODRUČNI URED ZA KATASTAR ŠIBENIK
...
```

---

#### `cadastral list-municipalities`
List municipalities with optional filtering.

```bash
# List all (unfiltered - returns many results)
cadastral list-municipalities

# Filter by office
cadastral list-municipalities --office 114

# Filter by office and department
cadastral list-municipalities --office 114 --department 116

# Search by name
cadastral list-municipalities --search ZADAR

# Combine filters
cadastral list-municipalities --search SAVAR --office 114

# Count only
cadastral list-municipalities --office 114 --count-only

# Export to CSV
cadastral list-municipalities --office 114 --format csv -out munis.csv
```

**Options:**
- `--office, -o` - Filter by cadastral office ID
- `--department, -d` - Filter by department ID
- `--search, -s` - Search by name
- `--format, -f` - Output format: table, json, csv
- `--output, -out` - Save to file
- `--count-only` - Show count only

---

#### `cadastral info`
Display system information and cache status.

```bash
cadastral info
```

**Output:**
```
=== Croatian Cadastral CLI ===
Version: 0.1.0
API Base: https://oss.uredjenazemlja.hr/oss/public

=== Cache Information ===
Cache Directory: /Users/user/.cadastral_api_cache
Cache Size: 45.2 MB
Cached Municipalities: 12
  • 334979 (224 KB)
  • 334731 (189 KB)
  ...

=== API Settings ===
Rate Limit: 0.75 seconds between requests
Timeout: 10.0 seconds
```

---

### Cache Management

#### `cadastral cache list`
List cached municipalities.

```bash
cadastral cache list
```

**Output:**
```
Cached GIS Data (12 municipalities):

Municipality  Size      Last Modified
-----------   -------   ---------------
334979        224 KB    2025-01-15 14:30
334731        189 KB    2025-01-15 14:25
...

Total Cache Size: 45.2 MB
Cache Location: /Users/user/.cadastral_api_cache
```

---

#### `cadastral cache clear`
Clear cached GIS data.

```bash
# Clear specific municipality
cadastral cache clear --municipality 334979
cadastral cache clear -m SAVAR

# Clear all cache
cadastral cache clear --all

# Force (skip confirmation)
cadastral cache clear --all --force
```

**Options:**
- `--municipality, -m` - Clear specific municipality
- `--all, -a` - Clear all cache
- `--force, -f` - Skip confirmation

---

#### `cadastral cache info`
Show detailed cache information.

```bash
cadastral cache info
```

**Output:**
```
=== CACHE INFORMATION ===
Location: /Users/user/.cadastral_api_cache
Status: Active
Total Size: 45.20 MB
Municipalities: 12
ZIP Files: 12
GML Files: 48
```

---

## Global Options

All commands support these global options:

- `--verbose, -v` - Detailed logging
- `--help, -h` - Show command help
- `--version` - Show CLI version

---

## Examples

### Example 1: Property Research
```bash
# Find parcel
cadastral search 103/2 --municipality SAVAR

# Get full details
cadastral get-parcel 103/2 -m 334979 --show-owners

# Export to JSON for analysis
cadastral get-parcel 103/2 -m 334979 --format json -o parcel.json
```

### Example 2: GIS Integration
```bash
# Download GIS data
cadastral download-gis 334979 --output ./gis_data

# Get parcel boundary
cadastral get-geometry 103/2 -m 334979 --format wkt -o parcel.wkt

# Import WKT into QGIS or PostGIS
```

### Example 3: Bulk Analysis
```bash
# List all municipalities in office
cadastral list-municipalities --office 114 --format csv -out municipalities.csv

# For each municipality, download GIS data (script this)
for code in $(cat municipality_codes.txt); do
    cadastral download-gis $code --output ./gis_data/$code
done
```

### Example 4: Land Registry Research
```bash
# Get land registry unit from parcel
cadastral get-lr-unit --from-parcel 279/6 -m SAVAR

# Show only ownership (Sheet B)
cadastral get-lr-unit -u 769 -b 21277 --show-owners

# Show all parcels in the unit (Sheet A)
cadastral get-lr-unit -u 769 -b 21277 --show-parcels

# Complete information (all sheets)
cadastral get-lr-unit -u 769 -b 21277 --all

# Export complete data for analysis
cadastral get-lr-unit -p 279/6 -m SAVAR --all --format json -o lr-unit.json
```

### Example 5: Cache Management
```bash
# Check cache status
cadastral info

# List cached data
cadastral cache list

# Clear old data
cadastral cache clear --municipality 334979

# Clear everything
cadastral cache clear --all
```

---

## Tips & Tricks

### Municipality Resolution
You can use either municipality name or code:
```bash
# By name (automatic lookup)
cadastral search 103/2 -m SAVAR

# By code (faster, no lookup needed)
cadastral search 103/2 -m 334979
```

### Output Formats
Different formats for different needs:
- **table** - Human-readable terminal output
- **json** - Structured data for processing
- **csv** - Spreadsheet import
- **yaml** - Human-readable structured format

### Performance
- First GIS download for a municipality: ~1-3 seconds (downloads ZIP)
- Subsequent geometry lookups: instant (uses cache)
- API rate limit: 0.75 seconds between requests (automatic)

### Error Messages
The CLI provides helpful suggestions:
```bash
$ cadastral search 999 -m INVALID
✗ Error: Municipality 'INVALID' not found

Suggestions:
  • Search for municipalities: cadastral search-municipality INVALID
  • Use municipality code instead: --municipality 334979
  • List all municipalities: cadastral list-municipalities
```

---

## Troubleshooting

### Module Not Found
```bash
# Install in development mode
pip install -e .

# Or install dependencies
pip install click rich tabulate
```

### Municipality Not Found
```bash
# Search for municipality
cadastral search-municipality <name>

# List all municipalities
cadastral list-municipalities --office 114
```

### Cache Issues
```bash
# Check cache
cadastral cache info

# Clear and retry
cadastral cache clear --municipality 334979
cadastral download-gis 334979 --output ./data --clear-cache
```

---

## Future Features (Phase 2+)

- Batch operations with file input
- Parallel processing
- Configuration file support
- Interactive mode
- Shell completion (bash/zsh)
- MCP server integration for LLMs

---

## See Also

- [README.md](README.md) - SDK documentation
- [examples/](examples/) - Python examples
- API Specification - specs/Croatian_Cadastral_API_Specification.md
