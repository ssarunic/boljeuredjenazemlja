# Pydantic V2 Business Entities - Implementation Specification

## Croatian Cadastral API Client - Python Implementation

This document specifies the implementation of Pydantic V2 business entities for the Croatian Cadastral System API client library. It serves as a reference for future features and extensions.

### Project Information

- **Python Version:** 3.12+ (uses modern type hints: `str | None`, `list[T]`)
- **Key Dependencies:** Pydantic V2, httpx
- **Code Quality:** Fully typed, mypy strict mode, ruff linting

---

## Business Entity Architecture

### Design Approach: Pydantic V2

**Selected:** Pydantic V2 models with strict validation

**Reasoning:**
1. **Industry Standard** - Used by FastAPI, SQLModel, and major Python frameworks
2. **API Inconsistencies** - Handles optional fields and type mismatches gracefully
3. **Type Safety** - Full IDE support and automatic validation
4. **Computed Properties** - Business logic via `@computed_field`
5. **Future-Proof** - `extra="allow"` handles undocumented API fields

**Alternative Approaches Considered:**
- ❌ **Plain dataclasses** - No validation, manual JSON parsing
- ❌ **attrs** - Less popular for API work, more manual JSON handling
- ❌ **Plain classes** - Most boilerplate, no type safety

---

## Business Entities

### 1. ParcelSearchResult
**Purpose:** Minimal search response from parcel number lookup

**Fields:**
- `parcel_id` (alias: key1) - Unique identifier
- `parcel_number` (alias: value1) - Cadastral number

**Notes:**
- API returns additional null fields (key2, value2, value3, displayValue1)
- Only key1 and value1 contain actual data

---

### 2. Possessor
**Purpose:** Individual owner/possessor information

**Fields:**
- `name: str` - Owner's full name
- `ownership: str | None` - Ownership fraction (e.g., "1/1", "1/4")
- `address: str` - Owner's address

**Computed Properties:**
- `ownership_decimal: float | None` - Parses "1/4" → 0.25

**Critical Note:**
- ⚠️ **`ownership` field is missing in ~80% of API responses**
- Must be handled as optional throughout the system

---

### 3. PossessionSheet
**Purpose:** Ownership record containing multiple possessors

**Fields:**
- `possession_sheet_id: int` - Unique identifier
- `possession_sheet_number: str` - Sheet reference
- `cad_municipality_id: int` - Municipality ID
- `cad_municipality_reg_num: str | None` - Municipality code
- `cad_municipality_name: str | None` - Municipality name
- `possession_sheet_type_id: int | None` - Sheet type
- `possessors: list[Possessor]` - List of owners

**Computed Properties:**
- `total_ownership: float | None` - Sum of all ownership fractions

**Notes:**
- A parcel can have multiple possession sheets
- Each sheet can have multiple possessors

---

### 4. ParcelPart
**Purpose:** Land use classification for a portion of the parcel

**Fields:**
- `parcel_part_id: int` - Unique identifier
- `name: str` - Land use type (PAŠNJAK, MASLINJAK, ŠUMA, etc.)
- `area: str` - Area in m² (API returns string!)
- `possession_sheet_id: int` - Link to ownership
- `possession_sheet_number: str` - Sheet reference
- `last_change_log_number: str | None` - Last modification
- `building: bool` - Contains buildings flag

**Computed Properties:**
- `area_numeric: int` - String to integer conversion

**Validators:**
- Area must be positive integer string

**Common Land Use Types:**
- PAŠNJAK - Pasture
- MASLINJAK - Olive grove
- ŠUMA - Forest
- ORANICA - Arable land
- VOĆNJAK - Orchard
- VINOGRAD - Vineyard

---

### 5. LandRegistryUnit
**Purpose:** Land registry book (Zemljišnoknjižni uložak) information

**Fields:**
- `lr_unit_id: int` - Registry unit ID
- `lr_unit_number: str` - Unit number
- `main_book_id: int` - Main book ID
- `main_book_name: str | None` - Book name
- `cadastre_municipality_id: int | None` - Municipality ID
- `institution_id: int | None` - Institution ID
- `institution_name: str | None` - Institution name
- `status: str` - Status code
- `status_name: str | None` - Status (e.g., "Aktivan")
- `verificated: bool` - Verification status
- `condominiums: bool` - Condominium flag
- `lr_unit_type_id: int | None` - Type ID
- `lr_unit_type_name: str | None` - Type (e.g., "VLASNIČKI")

**Notes:**
- Most fields are optional (context-dependent)
- Appears in parcel info and parcel links

---

### 6. ParcelLink
**Purpose:** Link to related or historical parcel records

**Fields:**
- `parcel_id: int` - Linked parcel ID
- `parcel_number: str` - Linked parcel number
- `address: str` - Linked parcel address
- `area: str` - Linked parcel area
- `lr_unit: LandRegistryUnit | None` - Registry info
- `parcel_parts: list[ParcelPart]` - Usually empty

**Notes:**
- Some parcels have historical cadastral links
- Useful for tracking parcel subdivisions/mergers

---

### 7. ParcelInfo (Main Entity)
**Purpose:** Complete parcel information with all details

**Core Fields:**
- `parcel_id: int` - Unique identifier
- `parcel_number: str` - Cadastral number
- `cad_municipality_id: int` - Municipality ID
- `cad_municipality_reg_num: str` - Municipality code
- `cad_municipality_name: str` - Municipality name
- `institution_id: int` - Cadastral office ID
- `address: str` - Parcel location
- `area: str` - Total area (string!)

**Building Info:**
- `building_remark: int` - Building code
- `detail_sheet_number: str` - Detail sheet
- `has_building_right: bool` - Construction permitted

**Nested Structures:**
- `parcel_parts: list[ParcelPart]` - Land use classifications
- `possession_sheets: list[PossessionSheet]` - Ownership records
- `lr_unit: LandRegistryUnit | None` - Land registry info
- `parcel_links: list[ParcelLink] | None` - Related parcels
- `lr_units_from_parcel_links: list[LandRegistryUnit] | None` - Extended registry info

**Status Flags:**
- `is_additional_data_set: bool`
- `legal_regime: bool`
- `graphic: bool` - Graphical data available
- `alpha_numeric: bool` - Alphanumeric data available
- `status: int` - Status code
- `resource_code: int` - Resource code
- `is_harmonized: bool` - Data harmonization status

**Computed Properties:**
- `area_numeric: int` - Area as integer
- `total_owners: int` - Count of all owners across sheets
- `land_use_summary: dict[str, int]` - Land types → areas mapping

**Validators:**
- Area must be positive

---

## API Client Features

### CadastralAPIClient

**Features:**
- ✅ Automatic rate limiting (0.75s between requests)
- ✅ Exponential backoff retry for 5xx errors
- ✅ Context manager support (`with` statement)
- ✅ Type-safe method signatures
- ✅ Comprehensive error handling

**Methods:**

1. **`search_parcel(parcel_number, municipality_reg_num) -> list[ParcelSearchResult]`**
   - Search by parcel number
   - Supports partial matching
   - Returns all matches

2. **`get_parcel_info(parcel_id) -> ParcelInfo`**
   - Get complete parcel details
   - Validates response with Pydantic

3. **`get_parcel_by_number(parcel_number, municipality_reg_num, exact_match=True) -> ParcelInfo | None`**
   - Convenience method
   - Combines search + detail retrieval
   - Optional exact matching

4. **`get_map_url(parcel_id) -> str`**
   - Generate interactive map URL

**Error Handling:**
- `ParcelNotFoundError` - Parcel doesn't exist
- `APIConnectionError` - Network issues
- `APITimeoutError` - Request timeout
- `InvalidResponseError` - Malformed response
- `RateLimitExceededError` - Too many requests

---

## Testing Results

### Verified Parcels (SAVAR Municipality, Code: 334979)

1. **103/2** - Simple (2 owners, no fractions) ✅
2. **103/3** - Simple (2 owners, no fractions) ✅
3. **114** - Simple (2 owners, no fractions) ✅
4. **45** - Complex (2 sheets, with fractions, parcel links) ✅
5. **396/1** - Very complex (18 owners, no fractions) ✅

### Key Findings

**API Discrepancies:**
1. ❌ Municipality search endpoint returns 404
2. ❌ Parcel search response differs from docs (key1/value1 vs detailed fields)
3. ⚠️ Ownership field missing in most responses
4. ⚠️ Area always string, never integer
5. ✅ 17+ undocumented fields discovered

**Data Patterns:**
- Simple parcels: Few owners, no ownership fractions
- Complex parcels: Multiple sheets, ownership fractions present
- Very complex: Many owners (18+), no fractions, often shared family land

---

## Type Hints & Modern Python

**Python 3.12+ Features Used:**
- `str | None` instead of `Optional[str]`
- `list[T]` instead of `List[T]`
- `dict[K, V]` instead of `Dict[K, V]`
- Type unions with `|` operator

**Type Safety:**
- All functions fully typed
- Mypy strict mode enabled
- No `Any` types used
- Pydantic ensures runtime validation

---

## Files Created

1. **`src/cadastral_api/models/entities.py`** (330 lines)
   - All 7 Pydantic models
   - Computed properties and validators

2. **`src/cadastral_api/client/api_client.py`** (256 lines)
   - HTTP client with rate limiting
   - Error handling and retries

3. **`src/cadastral_api/exceptions.py`** (53 lines)
   - Custom exception hierarchy

4. **`specs/Croatian_Cadastral_API_Specification.md`** (507 lines)
   - Complete API documentation
   - Real response examples
   - Testing data

5. **`pyproject.toml`** (67 lines)
   - Package configuration
   - Python 3.12+ requirement

6. **`examples/basic_usage.py`** (103 lines)
   - Working demonstration
   - Uses all 3 test parcels

7. **`README.md`** (280 lines)
   - Full documentation
   - Usage examples

---

## Usage Example

```python
from cadastral_api import CadastralAPIClient

# Initialize with automatic rate limiting
with CadastralAPIClient() as client:
    # Search for parcel
    results = client.search_parcel("103/2", municipality_reg_num="334979")

    # Get complete information
    parcel = client.get_parcel_info(results[0].parcel_id)

    # Access data via computed properties
    print(f"Parcel: {parcel.parcel_number}")
    print(f"Area: {parcel.area_numeric} m²")
    print(f"Owners: {parcel.total_owners}")

    # Land use breakdown
    for land_type, area in parcel.land_use_summary.items():
        print(f"  {land_type}: {area} m²")

    # Ownership details
    for sheet in parcel.possession_sheets:
        for owner in sheet.possessors:
            fraction = owner.ownership or "not specified"
            print(f"  {owner.name}: {fraction}")
```

---

## Conclusion

The implementation provides a production-ready, type-safe Python client for the Croatian Cadastral API with:

✅ **Pydantic V2 models** for all response structures
✅ **Modern Python 3.12+** type hints
✅ **Comprehensive validation** and error handling
✅ **Computed properties** for business logic
✅ **Rate limiting** and retry logic
✅ **Tested with real data** from 5 different parcels
✅ **Complete documentation** with examples

The choice of Pydantic V2 was justified by API inconsistencies (missing ownership fields, type mismatches) and the need for robust validation in production environments.
