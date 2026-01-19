# Land Registry Unit (`/lr/lr-unit`) Implementation Plan

## ⚠️ CRITICAL: DEMO/EDUCATIONAL PROJECT ONLY

**This is a demonstration and educational project showing how cadastral and land registry systems could theoretically be connected to AI systems via modern APIs.**

### ABSOLUTE RESTRICTIONS

1. **DO NOT** configure or connect this code to Croatian government production systems
2. **DO NOT** bypass authorization or terms of service restrictions
3. **DO NOT** access real cadastral or land registry data without proper legal authorization
4. **ALWAYS** use this only with the included mock server
5. **ALWAYS** emphasize this is a theoretical demonstration

### Purpose

This project demonstrates:
- **How LLMs could be connected to land books** in a safe, educational context
- **Modern API architecture patterns** that could be applied to cadastral/registry systems
- **Mock server implementation** that closely mimics the behavior of production servers for testing

The mock server provides a safe environment for:
- Learning about land registry data structures
- Testing API integration patterns
- Demonstrating AI agent capabilities with structured land data
- Educational purposes and proof-of-concept development

**This implementation is NOT authorized for use with production Croatian government systems.** It is designed exclusively for the mock server.

The author is available to advise the Croatian government on AI and API modernization if requested.

---

## Document Purpose

This document outlines the architecture and implementation plan for adding support for the `/lr/lr-unit` endpoint to the **mock server and SDK**, which provides detailed land registry information including:
- Complete ownership data (Sheet B - Vlasnički list)
- Parcel listings (Sheet A - List čestica)
- Legal encumbrances (Sheet C - List tereta)
- Land registry entries and history

**Important:** All development is for the localhost mock server (`http://localhost:8000`). Do not use with production systems.

## Project Scope

**Current Focus:** This is an SDK for consuming mock cadastral and land registry APIs. The primary use case is **simple data retrieval and one-off reports** for educational and demonstration purposes, not building a production land registry system.

**Approach:** Return Pydantic models that mirror the API response structure, with proper domain modeling for clarity and type safety.

---

## Phase 1: API Response Models (Current Implementation)

**Goal:** Create Pydantic models that accurately represent the `/lr/lr-unit` API response for data retrieval and display from the **mock server**.

### Design Principles

1. **Mirror API Structure** - Models closely follow API response JSON structure
2. **Minimal Normalization** - Focus on reading/displaying data, not complex analysis
3. **Type Safety** - Full Pydantic validation with proper types
4. **No Database** - Just return models from API, no persistence layer
5. **Forward Compatible** - Structure allows future evolution to Phase 2
6. **Mock Server First** - Test against localhost mock server, never production

### API Endpoint (Mock Server)

```text
GET http://localhost:8000/lr/lr-unit
Query Parameters:
  - lrUnitNumber: string (required) - Land registry unit number
  - mainBookId: integer (required) - Main book ID
  - historicalOverview: boolean (default: false) - Include historical data

Returns: Array of LandRegistryUnitDetailed objects (typically 1 item)
```

**Note:** This endpoint will be implemented in the mock server first, using realistic test data based on the structure observed in production (but with synthetic data).

### Domain Model - Phase 1

#### 1. Core Entity: Party (Owner/Legal Person)

**Domain Insight:** Separate "who owns" (Party) from "how they own" (OwnershipEntry).

```python
class PartyType(str, Enum):
    """Type of legal person"""
    INDIVIDUAL = "individual"
    COMPANY = "company"
    STATE = "state"
    MUNICIPALITY = "municipality"
    UNKNOWN = "unknown"

class Party(BaseModel):
    """
    Legal person (individual or entity) that can own property or be a beneficiary.

    Represents the entity itself, separate from how they're registered in the land registry.
    The same party can have multiple ownership entries across different properties.
    """
    lr_owner_id: int | None = Field(None, alias="lrOwnerId")
    name: str
    address: str | None = None
    tax_number: str | None = Field(None, alias="taxNumber")  # OIB
    party_type: PartyType = PartyType.UNKNOWN

    model_config = ConfigDict(
        populate_by_name=True,
        use_enum_values=True
    )
```

**Rationale:**
- Same person can own multiple properties → Party is separate from ownership records
- Party should not "carry" entry data (entry date, basis document, etc.)
- Enables future queries like "show all properties owned by OIB X"

#### 2. Land Registry Entry (Generic Event)

**Domain Insight:** Every change in the land registry stems from an entry (upis). Model this explicitly.

```python
class SheetType(str, Enum):
    """Land registry sheet type"""
    A = "A"  # Parcel list (List čestica)
    B = "B"  # Ownership (Vlasnički list)
    C = "C"  # Encumbrances (List tereta)

class ActionType(str, Enum):
    """Type of land registry action"""
    UPIS = "upis"  # Registration
    PREDBILJEŽBA = "predbilježba"  # Preliminary note
    ZABILJEŽBA = "zabilježba"  # Annotation
    BRISANJE = "brisanje"  # Deletion

class LREntry(BaseModel):
    """
    Generic land registry entry (događaj u zemljišnoj knjizi).

    Represents a single event/action in the land registry. Every change to
    Sheet A, B, or C is caused by an entry. This is the audit trail backbone.

    Examples:
    - "Upis prava vlasništva temeljem rješenja o nasljeđivanju"
    - "Zabilježba tražbine socijalne pomoći"
    - "Uknjižba založnog prava"
    """
    description: str
    order_number: str = Field(alias="orderNumber")  # "1.1", "3.2"

    # Optional structured fields (not always present in API)
    lr_entry_id: int | None = Field(None, alias="lrEntryId")
    action_type: ActionType | None = None  # Parsed from description if possible
    diary_number: str | None = None  # "Z-3983/2012" - parsed from description
    entry_date: date | None = None  # Parsed from description
    basis_document: str | None = None  # Parsed from description

    model_config = ConfigDict(populate_by_name=True)
```

**Rationale:**
- Central audit trail - all changes reference an entry
- API returns `description` with embedded metadata (diary number, date, document)
- Phase 1: Store full description, optionally parse key fields
- Phase 2: Could add structured parsing and validation

#### 3. Ownership Share (Sheet B)

**Domain Insight:** One share = one owner. Don't nest sub-shares inside.

```python
class ShareStatus(str, Enum):
    """Status of ownership share"""
    ACTIVE = "active"  # Currently valid (status: 0)
    HISTORICAL = "historical"  # No longer valid
    PRELIMINARY = "preliminary"  # Predbilježba

class LRShare(BaseModel):
    """
    Single ownership share in a land registry unit.

    Represents one owner's fractional ownership (e.g., "4/8 share").
    Sub-shares are modeled as separate LRShare objects with parent_share_id.

    One owner can have multiple shares, and shares can be nested (sub-shares).
    """
    lr_unit_share_id: int = Field(alias="lrUnitShareId")
    description: str  # "1. Suvlasnički dio: 4/8"
    order_number: str = Field(alias="orderNumber")  # "1", "3", "4"
    status: int  # 0 = active

    # Ownership details
    owners: list[Party] = Field(alias="lrOwners", default_factory=list)

    # Fraction (could be parsed from description)
    numerator: int | None = None  # e.g., 4 from "4/8"
    denominator: int | None = None  # e.g., 8 from "4/8"

    # Sub-shares (if any)
    sub_shares_and_entries: list[dict] = Field(
        alias="subSharesAndEntries",
        default_factory=list
    )

    # Status derived property
    @property
    def is_active(self) -> bool:
        return self.status == 0

    model_config = ConfigDict(populate_by_name=True)

class OwnerInShare(BaseModel):
    """
    Represents how a party is registered as an owner in a specific share.

    This is the "how" (not the "who"). It links a Party to a specific ownership
    entry with registration details.
    """
    party: Party  # The owner
    entry: LREntry = Field(alias="lrEntry")  # How they became owner

    model_config = ConfigDict(populate_by_name=True)
```

**Rationale:**
- Simpler querying: one row per owner per share
- Sub-shares can reference parent via separate field (Phase 2)
- API returns nested structure → Phase 1 preserves it, Phase 2 can flatten

#### 4. Sheet B: Ownership Sheet

**Domain Insight:** Sheet B is a logical view/DTO, not a separate table.

```python
class OwnershipSheetB(BaseModel):
    """
    Ownership sheet (List B - Vlasnički list).

    This is a DTO/view that aggregates all ownership shares and entries
    for a land registry unit. It represents the current state of ownership.

    Not a database table - generated from queries over LRShare and LREntry.
    """
    lr_unit_shares: list[LRShare] = Field(alias="lrUnitShares", default_factory=list)
    lr_entries: list[LREntry] = Field(alias="lrEntries", default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    def get_current_owners(self) -> list[Party]:
        """Get all parties with active ownership shares"""
        owners = []
        for share in self.lr_unit_shares:
            if share.is_active:
                owners.extend(share.owners)
        return owners

    def total_ownership_accounted(self) -> tuple[int, int] | None:
        """
        Calculate total ownership fraction across all shares.
        Returns (numerator, denominator) or None if fractions not parsed.
        """
        # TODO: Implement fraction summation
        pass
```

#### 5. Encumbrance (Sheet C)

**Domain Insight:** Model individual charges/rights, not the sheet itself.

```python
class RightType(str, Enum):
    """Type of encumbrance/burden on property"""
    MORTGAGE = "mortgage"  # Založno pravo
    EASEMENT = "easement"  # Služnost
    LIEN = "lien"  # Tražbina
    PROHIBITION = "prohibition"  # Zabrana otuđenja
    ANNOTATION = "annotation"  # Zabilježba
    PREEMPTION = "preemption"  # Pravo prvokupa
    USUFRUCT = "usufruct"  # Pravo plodouživanja
    OTHER = "other"

class EncumbranceGroup(BaseModel):
    """
    Group of related encumbrance entries.

    Example: A single mortgage that affects multiple parcels in the unit
    will have one group with multiple individual encumbrance entries.
    """
    description: str
    share_order_number: str = Field(alias="shareOrderNumber")  # "1", "2"
    lr_entries: list[LREntry] = Field(alias="lrEntries", default_factory=list)

    # Parsed from description (optional)
    right_type: RightType | None = None
    beneficiary: Party | None = None  # Creditor, neighbor, state

    model_config = ConfigDict(populate_by_name=True)

class EncumbranceSheetC(BaseModel):
    """
    Encumbrance sheet (List C - List tereta).

    This is a DTO/view that aggregates all charges, burdens, and legal
    restrictions on the property.

    Examples:
    - Mortgages (hipoteka)
    - Easements (služnost)
    - Social service claims (tražbina socijalne pomoći)
    - Prohibitions on transfer (zabrana otuđenja)
    """
    lr_entry_groups: list[EncumbranceGroup] = Field(
        alias="lrEntryGroups",
        default_factory=list
    )

    model_config = ConfigDict(populate_by_name=True)

    def has_encumbrances(self) -> bool:
        """Check if there are any active encumbrances"""
        return len(self.lr_entry_groups) > 0
```

**Rationale:**
- Sheet C is also a view, like Sheet B
- Each entry group represents one or more related legal burdens
- API returns grouped structure → preserve in Phase 1
- Phase 2 could normalize to individual `Encumbrance` records

#### 6. Sheet A: Parcel List

**Domain Insight:** Don't use "Possession" - that's posjedovni list, a different system.

```python
class LRUnitParcel(BaseModel):
    """
    Cadastral parcel that is part of this land registry unit.

    Represents the link between a LR unit and a specific cadastral parcel.
    A single LR unit typically contains multiple parcels.
    """
    parcel_id: int = Field(alias="parcelId")
    parcel_number: str = Field(alias="parcelNumber")
    cad_municipality_id: int = Field(alias="cadMunicipalityId")
    cad_municipality_reg_num: str = Field(alias="cadMunicipalityRegNum")
    cad_municipality_name: str = Field(alias="cadMunicipalityName")
    institution_id: int = Field(alias="institutionId")

    # Parcel details
    address: str | None = None
    area: str = "0"  # Total area in m²
    building_remark: int = Field(0, alias="buildingRemark")
    detail_sheet_number: str | None = Field(None, alias="detailSheetNumber")
    has_building_right: bool = Field(False, alias="hasBuildingRight")

    # Parcel parts (land use classification)
    parcel_parts: list[dict] = Field(alias="parcelParts", default_factory=list)

    # Possession sheets (often empty)
    possession_sheets: list[dict] = Field(
        alias="possessionSheets",
        default_factory=list
    )

    # Status flags
    is_additional_data_set: bool = Field(False, alias="isAdditionalDataSet")
    legal_regime: bool = Field(False, alias="legalRegime")
    graphic: bool = True
    alpha_numeric: bool = Field(True, alias="alphaNumeric")
    status: int = 0
    resource_code: int = Field(0, alias="resourceCode")
    is_harmonized: bool = Field(False, alias="isHarmonized")

    model_config = ConfigDict(populate_by_name=True)

class SheetAParcelList(BaseModel):
    """
    Sheet A1 - Parcel list (List čestica).

    Lists all cadastral parcels that are registered in this land registry unit.
    In Croatian ZK terminology: "List A - popis čestica".

    ⚠️ NOT "Possession Sheet" - that's posjedovni list, a different system.
    """
    cad_parcels: list[LRUnitParcel] = Field(alias="cadParcels", default_factory=list)

    model_config = ConfigDict(populate_by_name=True)

    def total_area(self) -> int:
        """Calculate total area of all parcels in m²"""
        return sum(int(p.area or 0) for p in self.cad_parcels)

    def parcel_numbers(self) -> list[str]:
        """Get list of all parcel numbers"""
        return [p.parcel_number for p in self.cad_parcels]

class SheetAAdditionalInfo(BaseModel):
    """
    Sheet A2 - Additional information.

    Additional data related to parcels and land use.
    In practice, this is often empty in the API response.
    """
    lr_entries: list[LREntry] = Field(alias="lrEntries", default_factory=list)

    model_config = ConfigDict(populate_by_name=True)
```

**Rationale:**
- **Critical naming fix:** "Possession" (posjed) ≠ "Ownership" (vlasništvo)
- Sheet A = List of cadastral parcels in the LR unit
- API returns full parcel objects → reuse existing `ParcelInfo` model where possible
- Phase 2 could normalize the link table separately

#### 7. Complete Land Registry Unit

```python
class LandRegistryUnitDetailed(BaseModel):
    """
    Complete land registry unit with all sheets (A, B, C).

    This is the main DTO returned by the /lr/lr-unit endpoint.
    It aggregates:
    - Basic unit metadata
    - Sheet A: List of parcels
    - Sheet B: Ownership information
    - Sheet C: Encumbrances and burdens

    This is a read model / view - generated from API, not persisted.
    """
    # Basic unit info
    lr_unit_id: int = Field(alias="lrUnitId")
    lr_unit_number: str = Field(alias="lrUnitNumber")
    main_book_id: int = Field(alias="mainBookId")
    main_book_name: str = Field(alias="mainBookName")
    cadastre_municipality_id: int = Field(alias="cadastreMunicipalityId")
    institution_id: int = Field(alias="institutionId")
    institution_name: str = Field(alias="institutionName")

    # Status
    status: str
    status_name: str = Field(alias="statusName")
    verificated: bool
    condominiums: bool

    # Unit type
    lr_unit_type_id: int = Field(alias="lrUnitTypeId")
    lr_unit_type_name: str = Field(alias="lrUnitTypeName")  # "VLASNIČKI", "ETAŽNI"

    # Last activity
    last_diary_number: str = Field(alias="lastDiaryNumber")

    # Active plumbs (liens/restrictions)
    active_plumbs: list[dict] = Field(alias="activePlumbs", default_factory=list)

    # Sheet B: Ownership
    ownership_sheet_b: OwnershipSheetB = Field(alias="ownershipSheetB")

    # Sheet A: Parcels
    possession_sheet_a1: SheetAParcelList = Field(alias="possessionSheetA1")
    possession_sheet_a2: SheetAAdditionalInfo = Field(alias="possessionSheetA2")

    # Sheet C: Encumbrances
    encumbrance_sheet_c: EncumbranceSheetC = Field(alias="encumbranceSheetC")

    model_config = ConfigDict(populate_by_name=True)

    # Convenience methods
    def get_all_owners(self) -> list[Party]:
        """Get all current owners"""
        return self.ownership_sheet_b.get_current_owners()

    def get_all_parcels(self) -> list[LRUnitParcel]:
        """Get all parcels in this unit"""
        return self.possession_sheet_a1.cad_parcels

    def has_encumbrances(self) -> bool:
        """Check if unit has any encumbrances"""
        return self.encumbrance_sheet_c.has_encumbrances()

    def summary(self) -> dict:
        """Get summary statistics"""
        return {
            "unit_number": self.lr_unit_number,
            "main_book": self.main_book_name,
            "total_parcels": len(self.possession_sheet_a1.cad_parcels),
            "total_area_m2": self.possession_sheet_a1.total_area(),
            "num_owners": len(self.get_all_owners()),
            "has_encumbrances": self.has_encumbrances()
        }
```

### Implementation Tasks - Phase 1

#### Task 1: API Models (`api/src/cadastral_api/models/entities.py`)

- [ ] Add `PartyType` enum
- [ ] Add `Party` model
- [ ] Add `SheetType`, `ActionType`, `ShareStatus`, `RightType` enums
- [ ] Add `LREntry` model
- [ ] Add `LRShare` model
- [ ] Add `OwnerInShare` model
- [ ] Add `OwnershipSheetB` model
- [ ] Add `EncumbranceGroup` model
- [ ] Add `EncumbranceSheetC` model
- [ ] Add `LRUnitParcel` model
- [ ] Add `SheetAParcelList` model
- [ ] Add `SheetAAdditionalInfo` model
- [ ] Add `LandRegistryUnitDetailed` model
- [ ] Add helper methods for fraction parsing from description strings
- [ ] Update existing `LandRegistryUnit` model if needed (keep for basic info)

#### Task 2: API Client (`api/src/cadastral_api/client/api_client.py`)

- [ ] Add `get_lr_unit_detailed()` method:
  ```python
  def get_lr_unit_detailed(
      self,
      lr_unit_number: str,
      main_book_id: int,
      historical_overview: bool = False
  ) -> LandRegistryUnitDetailed:
      """Get detailed land registry unit information (from mock server only)"""
  ```

- [ ] Add convenience method `get_lr_unit_from_parcel()`:
  ```python
  def get_lr_unit_from_parcel(
      self,
      parcel_number: str,
      municipality: str | int
  ) -> LandRegistryUnitDetailed:
      """
      Get LR unit details by first looking up parcel.

      This is a helper that:
      1. Calls get_parcel_info() to get lr_unit data
      2. Extracts lr_unit_number and main_book_id
      3. Calls get_lr_unit_detailed()
      """
  ```

- [ ] Add error handling for LR unit not found

#### Task 3: Exceptions (`api/src/cadastral_api/exceptions.py`)

- [ ] Add `LR_UNIT_NOT_FOUND = "lr_unit_not_found"` to `ErrorType` enum

#### Task 4: CLI Command (`cli/src/cadastral_cli/commands/registry.py`)

Create new command file for land registry operations:

- [ ] `get-lr-unit` command:
  ```bash
  cadastral get-lr-unit <lr_unit_number> --main-book <id>
  cadastral get-lr-unit --from-parcel <number> -m <municipality>
  ```

- [ ] Command options:
  - `--show-owners` / `-o` - Display ownership sheet B in detail
  - `--show-parcels` / `-p` - Display all parcels in unit (sheet A1)
  - `--show-encumbrances` / `-e` - Display encumbrances (sheet C)
  - `--all` / `-a` - Show all sheets
  - `--format` / `-f` - Output format (table, json, csv)
  - `--output` - Output to file
  - `--lang` - Language selection

- [ ] Default output: Summary table with basic info + owner count + parcel count

#### Task 5: CLI Formatters (`cli/src/cadastral_cli/formatters.py`)

- [ ] `format_lr_unit_summary()` - Summary table with key stats
- [ ] `format_ownership_sheet()` - Display ownership shares and owners
- [ ] `format_encumbrance_sheet()` - Display mortgages/liens/charges
- [ ] `format_lr_parcels()` - Display all parcels in unit with areas
- [ ] `format_lr_entry()` - Format single entry with metadata

#### Task 6: Mock Server (`mock-server/`)

**CRITICAL:** This is where primary development happens. Create realistic mock data based on production structure but with synthetic values.

- [ ] Add `/lr/lr-unit` endpoint in `mock-server/src/main.py`
- [ ] Create test data directory: `mock-server/data/lr-units/`
- [ ] Add test data file based on provided example: `21277-769.json`
- [ ] Add 2-3 more test cases:
  - Simple case: 1 owner, 2 parcels, no encumbrances
  - Complex case: Multiple co-owners with sub-shares
  - Encumbrance case: Mortgage and social service claim
  - Historical case: Previous owner visible (if available)

#### Task 7: Documentation

- [ ] Update `docs/croatian-cadastral-api-specification.md` with `/lr/lr-unit` endpoint
- [ ] Add **DEMO/EDUCATIONAL** warnings to new sections
- [ ] Update `api/README.md` with usage examples (mock server only)
- [ ] Update `cli/README.md` with new command examples
- [ ] Update `cli/docs/command-reference.md` with full reference
- [ ] Create `api/examples/lr_unit_ownership.py` example (localhost only)

#### Task 8: Internationalization

Add translation strings to `po/cadastral.pot`:

```po
# Land Registry Unit
msgid "Land registry unit"
msgid "Land registry unit not found"
msgid "Fetching land registry unit details..."
msgid "Unit number"
msgid "Main book"
msgid "Institution"

# Sheet B
msgid "OWNERSHIP SHEET (B)"
msgid "Ownership share"
msgid "Co-owner"
msgid "Owner"
msgid "Address"
msgid "OIB (Tax Number)"
msgid "Share fraction"
msgid "Entry"
msgid "Diary number"

# Sheet A
msgid "PARCEL LIST (SHEET A)"
msgid "Total parcels in unit"
msgid "Total area"

# Sheet C
msgid "ENCUMBRANCES SHEET (C)"
msgid "Encumbrance"
msgid "Beneficiary"
msgid "Type"
msgid "Priority rank"
msgid "No encumbrances found"
```

- [ ] Translate to Croatian (`po/hr.po`)
- [ ] Translate to English (`po/en.po`)
- [ ] Run `./scripts/compile_translations.sh`

#### Task 9: Testing

- [ ] Unit tests: `api/tests/unit/test_lr_models.py`
- [ ] Unit tests: `api/tests/unit/test_lr_client.py`
- [ ] Integration tests: `api/tests/integration/test_lr_unit_flow.py` - **mock server only**
- [ ] CLI tests: `cli/tests/test_registry_command.py` - **mock server only**
- [ ] Manual testing with mock server
- [ ] **DO NOT test with production API**

#### Task 10: Batch Processing (Optional)

- [ ] Extend `cadastral batch-fetch` with `--include-lr-details` flag
- [ ] Update `BatchResult` model to include LR unit data
- [ ] Add output formatting for batch LR results

---

## Phase 2: Normalized Domain Model (Future)

**Goal:** Create a fully normalized domain model for complex analysis and querying. This phase is for when the SDK needs to support application development, not just data retrieval.

**⚠️ Important:** Phase 2 is also for demonstration purposes only. If implemented, it would work with locally stored mock data, not production systems.

### Design Principles - Phase 2

1. **Full Normalization** - Separate entities for Party, Share, Entry, Encumbrance
2. **Database Layer** - Optional SQLAlchemy models for persistence (local SQLite for demo)
3. **Historical Tracking** - Support for `from_entry_id` and `to_entry_id`
4. **Complex Queries** - "Show all properties owned by person X" (on mock data)
5. **Graph Relationships** - Track inheritance chains, transfers, subdivisions (demonstration only)

### Normalized Schema - Phase 2

#### Database Tables (SQLite for Demo)

```sql
-- Core Entities
CREATE TABLE parties (
    id INTEGER PRIMARY KEY,
    name VARCHAR NOT NULL,
    oib VARCHAR(11) UNIQUE,
    address VARCHAR,
    party_type VARCHAR CHECK (party_type IN ('individual', 'company', 'state', 'municipality'))
);

CREATE TABLE land_registry_units (
    id INTEGER PRIMARY KEY,
    unit_number VARCHAR NOT NULL,
    main_book_id INTEGER NOT NULL,
    main_book_name VARCHAR NOT NULL,
    municipality_id INTEGER NOT NULL,
    institution_id INTEGER NOT NULL,
    status VARCHAR,
    unit_type VARCHAR,  -- 'VLASNIČKI', 'ETAŽNI'
    last_diary_number VARCHAR,
    UNIQUE (unit_number, main_book_id)
);

-- Generic Entry Log (Audit Trail)
CREATE TABLE lr_entries (
    id INTEGER PRIMARY KEY,
    unit_id INTEGER NOT NULL REFERENCES land_registry_units(id),
    sheet_type VARCHAR(1) CHECK (sheet_type IN ('A', 'B', 'C')),
    entry_number VARCHAR NOT NULL,  -- "1.1", "3.2"
    action_type VARCHAR CHECK (action_type IN ('upis', 'predbilježba', 'zabilježba', 'brisanje')),
    diary_number VARCHAR NOT NULL,  -- "Z-3983/2012"
    entry_date DATE NOT NULL,
    description TEXT NOT NULL,
    basis_document VARCHAR,
    registrar_id INTEGER,
    metadata JSON,  -- For API-specific fields
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sheet B: Ownership Shares
CREATE TABLE lr_shares (
    id INTEGER PRIMARY KEY,
    unit_id INTEGER NOT NULL REFERENCES land_registry_units(id),
    party_id INTEGER NOT NULL REFERENCES parties(id),
    numerator INTEGER NOT NULL,
    denominator INTEGER NOT NULL,
    from_entry_id INTEGER NOT NULL REFERENCES lr_entries(id),
    to_entry_id INTEGER REFERENCES lr_entries(id),  -- NULL = still active
    parent_share_id INTEGER REFERENCES lr_shares(id),  -- For sub-shares
    status VARCHAR CHECK (status IN ('active', 'historical', 'preliminary')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_fraction CHECK (numerator > 0 AND denominator > 0)
);

-- Sheet C: Encumbrances
CREATE TABLE encumbrance_groups (
    id INTEGER PRIMARY KEY,
    description VARCHAR,
    creditor_id INTEGER REFERENCES parties(id)
);

CREATE TABLE encumbrances (
    id INTEGER PRIMARY KEY,
    unit_id INTEGER NOT NULL REFERENCES land_registry_units(id),
    parcel_id INTEGER REFERENCES cadastral_parcels(id),  -- Optional: specific parcel
    right_type VARCHAR CHECK (right_type IN ('mortgage', 'easement', 'lien', 'prohibition', 'annotation', 'preemption', 'usufruct', 'other')),
    beneficiary_id INTEGER NOT NULL REFERENCES parties(id),
    amount DECIMAL(15,2),
    currency VARCHAR(3),
    priority_rank INTEGER,
    from_entry_id INTEGER NOT NULL REFERENCES lr_entries(id),
    to_entry_id INTEGER REFERENCES lr_entries(id),
    group_id INTEGER REFERENCES encumbrance_groups(id),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Sheet A: Unit-Parcel Link
CREATE TABLE lr_unit_parcels (
    id INTEGER PRIMARY KEY,
    unit_id INTEGER NOT NULL REFERENCES land_registry_units(id),
    parcel_id INTEGER NOT NULL REFERENCES cadastral_parcels(id),
    from_entry_id INTEGER NOT NULL REFERENCES lr_entries(id),
    to_entry_id INTEGER REFERENCES lr_entries(id),
    area INTEGER,  -- m²
    land_use VARCHAR,
    remark TEXT,
    status VARCHAR CHECK (status IN ('active', 'historical')),
    UNIQUE (unit_id, parcel_id, from_entry_id)
);

-- Indexes
CREATE INDEX idx_shares_unit ON lr_shares(unit_id);
CREATE INDEX idx_shares_party ON lr_shares(party_id);
CREATE INDEX idx_shares_active ON lr_shares(unit_id) WHERE to_entry_id IS NULL;
CREATE INDEX idx_entries_unit ON lr_entries(unit_id);
CREATE INDEX idx_entries_diary ON lr_entries(diary_number);
CREATE INDEX idx_encumbrances_unit ON encumbrances(unit_id);
CREATE INDEX idx_encumbrances_beneficiary ON encumbrances(beneficiary_id);
CREATE INDEX idx_unit_parcels_unit ON lr_unit_parcels(unit_id);
CREATE INDEX idx_unit_parcels_parcel ON lr_unit_parcels(parcel_id);
```

#### SQLAlchemy Models - Phase 2

```python
from sqlalchemy import Column, Integer, String, Date, Boolean, ForeignKey, DECIMAL, TIMESTAMP, JSON, CheckConstraint
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base
from datetime import date, datetime

Base = declarative_base()

class PartyORM(Base):
    __tablename__ = "parties"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    oib: Mapped[str | None] = mapped_column(String(11), unique=True)
    address: Mapped[str | None]
    party_type: Mapped[str]

    # Relationships
    shares: Mapped[list["LRShareORM"]] = relationship(back_populates="party")
    encumbrances: Mapped[list["EncumbranceORM"]] = relationship(back_populates="beneficiary")

class LandRegistryUnitORM(Base):
    __tablename__ = "land_registry_units"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_number: Mapped[str]
    main_book_id: Mapped[int]
    main_book_name: Mapped[str]
    municipality_id: Mapped[int]
    institution_id: Mapped[int]
    status: Mapped[str | None]
    unit_type: Mapped[str | None]
    last_diary_number: Mapped[str | None]

    # Relationships
    entries: Mapped[list["LREntryORM"]] = relationship(back_populates="unit")
    shares: Mapped[list["LRShareORM"]] = relationship(back_populates="unit")
    encumbrances: Mapped[list["EncumbranceORM"]] = relationship(back_populates="unit")
    parcels: Mapped[list["LRUnitParcelORM"]] = relationship(back_populates="unit")

class LREntryORM(Base):
    __tablename__ = "lr_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("land_registry_units.id"))
    sheet_type: Mapped[str] = mapped_column(String(1))
    entry_number: Mapped[str]
    action_type: Mapped[str | None]
    diary_number: Mapped[str]
    entry_date: Mapped[date]
    description: Mapped[str]
    basis_document: Mapped[str | None]
    registrar_id: Mapped[int | None]
    metadata: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    unit: Mapped["LandRegistryUnitORM"] = relationship(back_populates="entries")
    shares_from: Mapped[list["LRShareORM"]] = relationship(
        foreign_keys="LRShareORM.from_entry_id",
        back_populates="from_entry"
    )
    shares_to: Mapped[list["LRShareORM"]] = relationship(
        foreign_keys="LRShareORM.to_entry_id",
        back_populates="to_entry"
    )

class LRShareORM(Base):
    __tablename__ = "lr_shares"
    __table_args__ = (
        CheckConstraint("numerator > 0 AND denominator > 0", name="valid_fraction"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("land_registry_units.id"))
    party_id: Mapped[int] = mapped_column(ForeignKey("parties.id"))
    numerator: Mapped[int]
    denominator: Mapped[int]
    from_entry_id: Mapped[int] = mapped_column(ForeignKey("lr_entries.id"))
    to_entry_id: Mapped[int | None] = mapped_column(ForeignKey("lr_entries.id"))
    parent_share_id: Mapped[int | None] = mapped_column(ForeignKey("lr_shares.id"))
    status: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    unit: Mapped["LandRegistryUnitORM"] = relationship(back_populates="shares")
    party: Mapped["PartyORM"] = relationship(back_populates="shares")
    from_entry: Mapped["LREntryORM"] = relationship(foreign_keys=[from_entry_id])
    to_entry: Mapped["LREntryORM"] = relationship(foreign_keys=[to_entry_id])
    parent_share: Mapped["LRShareORM"] = relationship(remote_side=[id])

    @property
    def is_active(self) -> bool:
        return self.to_entry_id is None

    @property
    def fraction_decimal(self) -> float:
        return self.numerator / self.denominator

class EncumbranceORM(Base):
    __tablename__ = "encumbrances"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("land_registry_units.id"))
    parcel_id: Mapped[int | None]
    right_type: Mapped[str]
    beneficiary_id: Mapped[int] = mapped_column(ForeignKey("parties.id"))
    amount: Mapped[DECIMAL | None]
    currency: Mapped[str | None] = mapped_column(String(3))
    priority_rank: Mapped[int | None]
    from_entry_id: Mapped[int] = mapped_column(ForeignKey("lr_entries(id))
    to_entry_id: Mapped[int | None] = mapped_column(ForeignKey("lr_entries.id"))
    group_id: Mapped[int | None] = mapped_column(ForeignKey("encumbrance_groups.id"))
    description: Mapped[str | None]
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    # Relationships
    unit: Mapped["LandRegistryUnitORM"] = relationship(back_populates="encumbrances")
    beneficiary: Mapped["PartyORM"] = relationship(back_populates="encumbrances")
    from_entry: Mapped["LREntryORM"] = relationship(foreign_keys=[from_entry_id])
    to_entry: Mapped["LREntryORM"] = relationship(foreign_keys=[to_entry_id])
    group: Mapped["EncumbranceGroupORM"] = relationship(back_populates="encumbrances")

    @property
    def is_active(self) -> bool:
        return self.to_entry_id is None

class LRUnitParcelORM(Base):
    __tablename__ = "lr_unit_parcels"

    id: Mapped[int] = mapped_column(primary_key=True)
    unit_id: Mapped[int] = mapped_column(ForeignKey("land_registry_units.id"))
    parcel_id: Mapped[int]
    from_entry_id: Mapped[int] = mapped_column(ForeignKey("lr_entries.id"))
    to_entry_id: Mapped[int | None] = mapped_column(ForeignKey("lr_entries.id"))
    area: Mapped[int | None]
    land_use: Mapped[str | None]
    remark: Mapped[str | None]
    status: Mapped[str]

    # Relationships
    unit: Mapped["LandRegistryUnitORM"] = relationship(back_populates="parcels")
    from_entry: Mapped["LREntryORM"] = relationship(foreign_keys=[from_entry_id])
    to_entry: Mapped["LREntryORM"] = relationship(foreign_keys=[to_entry_id])
```

### Data Transformation Layer - Phase 2

Convert Phase 1 API response models to Phase 2 normalized models:

```python
class LRDataNormalizer:
    """
    Transform Phase 1 API response DTOs into Phase 2 normalized entities.

    ⚠️ DEMO ONLY: Works with mock server data, not production.
    """

    def __init__(self, db_session):
        self.session = db_session

    def import_lr_unit(self, detailed: LandRegistryUnitDetailed) -> LandRegistryUnitORM:
        """
        Import a complete LR unit from API response into normalized database.

        Steps:
        1. Extract and deduplicate all Party entities
        2. Create LandRegistryUnit record
        3. Parse and create LREntry records
        4. Create LRShare records linking to parties and entries
        5. Create Encumbrance records
        6. Create LRUnitParcel link records
        """
        # 1. Extract unique parties
        parties = self._extract_and_merge_parties(detailed)

        # 2. Create unit
        unit = self._create_unit(detailed)

        # 3. Create entries
        entries = self._create_entries(detailed, unit)

        # 4. Create shares
        shares = self._create_shares(detailed.ownership_sheet_b, unit, parties, entries)

        # 5. Create encumbrances
        encumbrances = self._create_encumbrances(
            detailed.encumbrance_sheet_c,
            unit,
            parties,
            entries
        )

        # 6. Create parcel links
        parcel_links = self._create_parcel_links(
            detailed.possession_sheet_a1,
            unit,
            entries
        )

        self.session.commit()
        return unit

    def _extract_and_merge_parties(
        self,
        detailed: LandRegistryUnitDetailed
    ) -> dict[str, PartyORM]:
        """
        Extract all Party objects from ownership and encumbrances,
        deduplicate by OIB/name, and create/update in database.
        """
        parties = {}

        # From ownership sheet
        for share in detailed.ownership_sheet_b.lr_unit_shares:
            for owner in share.owners:
                key = owner.tax_number or owner.name
                if key not in parties:
                    party = self._get_or_create_party(owner)
                    parties[key] = party

        # From encumbrances (beneficiaries)
        # ...

        return parties

    def _create_entries(
        self,
        detailed: LandRegistryUnitDetailed,
        unit: LandRegistryUnitORM
    ) -> dict[str, LREntryORM]:
        """
        Parse all LREntry descriptions and create normalized entry records.
        """
        entries = {}

        # From ownership sheet
        for share in detailed.ownership_sheet_b.lr_unit_shares:
            for owner in share.owners:
                entry = owner.entry
                parsed = self._parse_entry_description(entry.description)

                db_entry = LREntryORM(
                    unit_id=unit.id,
                    sheet_type="B",
                    entry_number=entry.order_number,
                    diary_number=parsed['diary_number'],
                    entry_date=parsed['entry_date'],
                    description=entry.description,
                    basis_document=parsed.get('basis_document'),
                    action_type=parsed.get('action_type')
                )
                self.session.add(db_entry)
                entries[entry.order_number] = db_entry

        # From encumbrances, Sheet A entries, etc.
        # ...

        return entries

    def _parse_entry_description(self, description: str) -> dict:
        """
        Parse structured data from entry description text.

        Example input:
        "Zaprimljeno 05.04.2012.g. pod brojem Z-3983/2012<br><br>
         UKNJIŽBA, PRAVO VLASNIŠTVA<br><br>
         IZ ZK ULOŠKA PRENESENI VLASNICI"

        Extracts:
        - entry_date: 2012-04-05
        - diary_number: Z-3983/2012
        - action_type: UKNJIŽBA
        - basis_document: ...
        """
        import re
        from datetime import datetime

        result = {}

        # Extract diary number
        diary_match = re.search(r'pod brojem (Z-\d+/\d+)', description)
        if diary_match:
            result['diary_number'] = diary_match.group(1)

        # Extract date
        date_match = re.search(r'Zaprimljeno (\d{2}\.\d{2}\.\d{4})', description)
        if date_match:
            date_str = date_match.group(1)
            result['entry_date'] = datetime.strptime(date_str, '%d.%m.%Y').date()

        # Extract action type
        if 'UKNJIŽBA' in description:
            result['action_type'] = 'upis'
        elif 'PREDBILJEŽBA' in description:
            result['action_type'] = 'predbilježba'
        elif 'ZABILJEŽBA' in description:
            result['action_type'] = 'zabilježba'

        # Extract basis document
        basis_match = re.search(r'(RJEŠENJE[^<]+)', description)
        if basis_match:
            result['basis_document'] = basis_match.group(1).strip()

        return result
```

### Complex Queries - Phase 2

Examples of queries enabled by normalized model (on mock data):

```python
from sqlalchemy import select, func
from sqlalchemy.orm import Session

def get_all_properties_by_owner(session: Session, oib: str) -> list[LandRegistryUnitORM]:
    """Get all LR units where person with given OIB has active ownership (demo data)"""
    return session.execute(
        select(LandRegistryUnitORM)
        .join(LRShareORM)
        .join(PartyORM)
        .where(PartyORM.oib == oib)
        .where(LRShareORM.to_entry_id == None)  # Active shares only
    ).scalars().all()

def get_ownership_history(session: Session, unit_id: int) -> list[LRShareORM]:
    """Get all ownership shares for a unit, including historical (demo data)"""
    return session.execute(
        select(LRShareORM)
        .where(LRShareORM.unit_id == unit_id)
        .order_by(LRShareORM.from_entry_id)
    ).scalars().all()

def get_properties_with_mortgages(session: Session) -> list[LandRegistryUnitORM]:
    """Get all units with active mortgages (demo data)"""
    return session.execute(
        select(LandRegistryUnitORM)
        .join(EncumbranceORM)
        .where(EncumbranceORM.right_type == 'mortgage')
        .where(EncumbranceORM.to_entry_id == None)
    ).scalars().all()

def calculate_total_land_area_by_owner(session: Session, party_id: int) -> int:
    """Calculate total land area owned by a party across all properties (demo data)"""
    return session.execute(
        select(func.sum(LRUnitParcelORM.area))
        .join(LRShareORM, LRShareORM.unit_id == LRUnitParcelORM.unit_id)
        .where(LRShareORM.party_id == party_id)
        .where(LRShareORM.to_entry_id == None)
        .where(LRUnitParcelORM.to_entry_id == None)
    ).scalar() or 0

def find_co_owners(session: Session, party_id: int) -> list[PartyORM]:
    """Find all people who co-own properties with given party (demo data)"""
    return session.execute(
        select(PartyORM).distinct()
        .join(LRShareORM, LRShareORM.party_id == PartyORM.id)
        .where(LRShareORM.unit_id.in_(
            select(LRShareORM.unit_id)
            .where(LRShareORM.party_id == party_id)
            .where(LRShareORM.to_entry_id == None)
        ))
        .where(PartyORM.id != party_id)
        .where(LRShareORM.to_entry_id == None)
    ).scalars().all()
```

### Implementation Tasks - Phase 2

This is a major undertaking and should only be started if there's a clear need for:
- Long-term data storage and analysis (of mock data)
- Complex property portfolio management demonstrations
- Historical tracking and audit trail examples
- Multi-property query demonstrations

#### High-Level Tasks

1. **Database Design** - Finalize schema, add missing tables (SQLite for demo)
2. **SQLAlchemy Models** - Complete ORM models with all relationships
3. **Migration System** - Set up Alembic for schema migrations
4. **Data Normalizer** - Build transformation layer from Phase 1 → Phase 2
5. **Parser Library** - Robust parsing of entry descriptions (dates, diary numbers, documents)
6. **Query API** - High-level query functions for common use cases (demo queries)
7. **Historical Tracking** - Handle `to_entry_id` updates when ownership changes
8. **CLI Extensions** - Add commands for database management and complex queries
9. **Documentation** - Comprehensive guide for using normalized model (with demo warnings)
10. **Testing** - Extensive tests for data transformation and queries (mock data only)

---

## Additional Discoveries

### File Status API

A new endpoint was discovered: `/lr/file-status` (POST)

**Purpose:** Track status of land registry file processing (applications, resolutions)

**Example Response:**
```json
{
    "fileId": 44857905,
    "lrFileNumber": "Z-32597/2025",
    "institution": {
        "institutionId": 284,
        "institutionName": "Zemljišnoknjižni odjel Zadar"
    },
    "resolutionTypeName": "Udovoljeno",
    "statusDescription": "OTPREMA",
    "applicationContent": "Uknjižba prava vlasništva",
    "registrationNumber": "OV-4820/2025",
    "infoDate": "2025-11-17T17:41:33.000+01:00",
    "receivingDate": "2025-10-09T09:14:06.000+02:00",
    "solvingDate": "2025-10-16T13:55:52.000+02:00",
    "executionDate": "2025-10-16T13:56:50.000+02:00",
    "fileShipmentDate": "2025-10-16T13:57:10.000+02:00"
}
```

**Use Cases (Educational):**
- Track pending ownership transfers
- Check status of registration applications
- Monitor when changes are executed

**Phase 1 Implementation:** Could be added as a separate endpoint if needed (mock server).

**Phase 2 Integration:** Link `LREntry` records to `LRFile` records for complete audit trail demonstration.

### Historical Data Question

**Question:** Does the API return historical ownership data?

**Investigation:** Check parcel 5846 in municipality 334731 (LUKA):
- Previous owner: Fjordana (sold to Rino Bubica)
- Need to check if old ownership appears in response

**If Historical Data Available:**
- Phase 1: Model will capture it (via `to_entry_id` or similar)
- Phase 2: Full historical reconstruction possible (demo)

**If No Historical Data:**
- Phase 1: Models still support it (forward compatible)
- Phase 2: Could track changes over time via repeated API calls (demo)

**Mock Server:** Can simulate historical data regardless of production API capabilities.

---

## Conclusion

### Phase 1 Summary

**Scope:** API consumption and data display (mock server only)
**Complexity:** Medium
**Timeline:** 2-3 weeks
**Dependencies:** None
**Value:** Immediate - demonstrates LR unit queries and reporting
**Purpose:** Educational - shows how AI could interact with land registry data

### Phase 2 Summary

**Scope:** Full normalized domain model with persistence (demo/educational)
**Complexity:** High
**Timeline:** 2-3 months
**Dependencies:** Clear need for advanced demonstration features
**Value:** Long-term - demonstrates complex analysis and property management patterns
**Purpose:** Proof of concept for advanced AI agent integration with structured legal data

### Recommendation

1. **Start with Phase 1** - Implement API models and CLI commands for mock server
2. **Test thoroughly** - Ensure models handle all API edge cases and mock scenarios
3. **Gather feedback** - Understand real-world educational use cases
4. **Evaluate Phase 2** - Only proceed if there's demonstrated need for:
   - Local data storage examples
   - Complex query demonstrations across multiple properties
   - Historical tracking and analysis examples
   - Application development patterns for legal AI agents

### Final Warnings

⚠️ **DO NOT:**
- Connect to production Croatian government systems
- Use this code to access real personal or land registry data without authorization
- Deploy this as a production service without proper legal authorization
- Suggest this code can be used for real estate transactions

✅ **DO:**
- Use only with included mock server (`http://localhost:8000`)
- Treat as educational and demonstration code
- Learn about modern API patterns for legal/cadastral systems
- Explore AI agent integration patterns with structured legal data
- Share as a proof-of-concept for government modernization discussions

---

## References

- Main specification: [docs/croatian-cadastral-api-specification.md](docs/croatian-cadastral-api-specification.md)
- API models: [api/src/cadastral_api/models/entities.py](api/src/cadastral_api/models/entities.py)
- Project instructions: [CLAUDE.md](CLAUDE.md) - Contains additional warnings and restrictions
- Domain modeling discussion: This document (sections above)
- Example API response: Provided in initial request (279/6, SAVAR - example data)

---

**Document Version:** 1.0
**Created:** 2025-11-17
**Last Updated:** 2025-11-17
**Status:** Planning - Not Yet Implemented
**License:** Demo/Educational Use Only - See CLAUDE.md for full restrictions
