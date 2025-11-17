"""
Pydantic models for Croatian Cadastral API responses.

⚠️ CRITICAL: DEMO/EDUCATIONAL PROJECT ONLY

This is a demonstration project showing how cadastral and land registry systems
could theoretically be connected to AI systems via modern APIs.

ABSOLUTE RESTRICTIONS:
- DO NOT configure or connect this code to Croatian government production systems
- DO NOT bypass authorization or terms of service restrictions
- DO NOT access real cadastral or land registry data without proper legal authorization
- ALWAYS use this only with the included mock server (http://localhost:8000)
- ALWAYS emphasize this is a theoretical demonstration

Purpose: Demonstrating how LLMs could be connected to land books in a safe,
educational context using a mock server that closely mimics production behavior.
"""

from fractions import Fraction
from enum import Enum
from datetime import date

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


class MunicipalitySearchResult(BaseModel):
    """
    Municipality information from search endpoint.

    Response from /search-cad-parcels/municipalities endpoint.
    Can be filtered by cadastral office and department using optional parameters.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    municipality_id: str = Field(
        alias="key1", description="Municipality internal ID (cadMunicipalityId)"
    )
    code_and_name: str = Field(
        alias="value1", description="Municipality code and name combined"
    )
    municipality_reg_num: str = Field(
        alias="key2", description="Municipality registration number for parcel searches"
    )
    institution_id: str = Field(
        alias="value2", description="Cadastral office ID (matches officeId parameter)"
    )
    department_id: str | None = Field(
        default=None, alias="value3", description="Department ID (matches departmentId parameter)"
    )
    display_value: str = Field(
        alias="displayValue1", description="Full display name with court information"
    )

    @computed_field  # type: ignore[misc]
    @property
    def municipality_name(self) -> str:
        """Extract municipality name from code_and_name field."""
        # Format: "334979 SAVAR" -> "SAVAR"
        parts = self.code_and_name.split(" ", 1)
        return parts[1] if len(parts) > 1 else self.code_and_name


class CadastralOffice(BaseModel):
    """
    Cadastral office (Područni ured za katastar) information.

    Response from /search-cad-parcels/offices endpoint.
    Lists all cadastral offices in Croatia.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(description="Cadastral office ID (matches institutionId in other responses)")
    name: str = Field(description="Full name of cadastral office")


class ParcelSearchResult(BaseModel):
    """
    Minimal parcel information from search endpoint.

    Note: The API returns more fields (key2, value2, value3, displayValue1)
    but they are always null in tested responses.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    parcel_id: str = Field(alias="key1", description="Unique parcel identifier")
    parcel_number: str = Field(alias="value1", description="Cadastral parcel number")


class Possessor(BaseModel):
    """
    Individual owner/possessor information.

    IMPORTANT: The 'ownership' and 'address' fields are frequently missing in API responses.
    Many parcels do not include ownership fractions or owner addresses.
    """

    model_config = ConfigDict(extra="allow")

    name: str = Field(description="Owner's full name")
    ownership: str | None = Field(
        default=None, description="Ownership fraction (e.g., '1/1', '1/4')"
    )
    address: str | None = Field(
        default=None, description="Owner's address"
    )

    @computed_field  # type: ignore[misc]
    @property
    def ownership_decimal(self) -> float | None:
        """
        Parse ownership fraction to decimal.

        Returns:
            Float between 0.0 and 1.0, or None if ownership is not specified

        Examples:
            "1/1" -> 1.0
            "1/4" -> 0.25
            "3/8" -> 0.375
        """
        if not self.ownership:
            return None
        try:
            frac = Fraction(self.ownership)
            return float(frac)
        except (ValueError, ZeroDivisionError):
            return None


class PossessionSheet(BaseModel):
    """
    Ownership record containing possessor information.

    A parcel can have multiple possession sheets, each with multiple possessors.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    possession_sheet_id: int = Field(
        alias="possessionSheetId", description="Unique possession sheet identifier"
    )
    possession_sheet_number: str = Field(
        alias="possessionSheetNumber", description="Sheet reference number"
    )
    cad_municipality_id: int = Field(
        alias="cadMunicipalityId", description="Municipality internal ID"
    )
    cad_municipality_reg_num: str | None = Field(
        default=None,
        alias="cadMunicipalityRegNum",
        description="Municipality registration number",
    )
    cad_municipality_name: str | None = Field(
        default=None, alias="cadMunicipalityName", description="Municipality name"
    )
    possession_sheet_type_id: int | None = Field(
        default=None, alias="possessionSheetTypeId", description="Type of possession sheet"
    )
    possessors: list[Possessor] = Field(
        default_factory=list, description="List of owners/possessors"
    )

    @computed_field  # type: ignore[misc]
    @property
    def total_ownership(self) -> float | None:
        """
        Calculate total ownership fraction for this possession sheet.

        Returns:
            Sum of all ownership fractions, or None if no ownership data available
        """
        ownerships = [p.ownership_decimal for p in self.possessors if p.ownership_decimal]
        return sum(ownerships) if ownerships else None


class ParcelPart(BaseModel):
    """
    Land use classification for a part of the parcel.

    Each parcel can have multiple parts with different land use types.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    parcel_part_id: int = Field(
        alias="parcelPartId", description="Unique parcel part identifier"
    )
    name: str = Field(description="Land use type (e.g., 'PAŠNJAK', 'MASLINJAK', 'ŠUMA')")
    area: str = Field(description="Area in square meters (string format)")
    possession_sheet_id: int = Field(
        alias="possessionSheetId", description="Link to possession sheet"
    )
    possession_sheet_number: str = Field(
        alias="possessionSheetNumber", description="Possession sheet reference"
    )
    last_change_log_number: str | None = Field(
        default=None, alias="lastChangeLogNumber", description="Last change log entry"
    )
    building: bool = Field(description="Whether this part contains buildings")

    @computed_field  # type: ignore[misc]
    @property
    def area_numeric(self) -> int:
        """Convert string area to integer."""
        try:
            return int(self.area)
        except ValueError:
            return 0

    @field_validator("area")
    @classmethod
    def validate_area(cls, v: str) -> str:
        """Validate that area is a positive number string."""
        try:
            area_int = int(v)
            if area_int < 0:
                raise ValueError("Area must be positive")
        except ValueError as e:
            raise ValueError(f"Invalid area value: {v}") from e
        return v


class LandRegistryUnit(BaseModel):
    """
    Land registry book information (Zemljišnoknjižni ulo¾ak).

    Many fields are optional and only appear in certain contexts.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    lr_unit_id: int = Field(alias="lrUnitId", description="Unique land registry unit ID")
    lr_unit_number: str = Field(alias="lrUnitNumber", description="Registry unit number")
    main_book_id: int = Field(alias="mainBookId", description="Main book ID")
    main_book_name: str | None = Field(
        default=None, alias="mainBookName", description="Main book name"
    )
    cadastre_municipality_id: int | None = Field(
        default=None, alias="cadastreMunicipalityId", description="Municipality ID"
    )
    institution_id: int | None = Field(
        default=None, alias="institutionId", description="Land registry institution ID"
    )
    institution_name: str | None = Field(
        default=None,
        alias="institutionName",
        description="Institution name (e.g., 'Zemljišnoknjižni odjel Zadar')",
    )
    status: str = Field(description="Status code")
    status_name: str | None = Field(
        default=None, alias="statusName", description="Status name (e.g., 'Aktivan')"
    )
    verificated: bool = Field(description="Verification status")
    condominiums: bool = Field(description="Condominium flag")
    lr_unit_type_id: int | None = Field(
        default=None, alias="lrUnitTypeId", description="Type ID"
    )
    lr_unit_type_name: str | None = Field(
        default=None,
        alias="lrUnitTypeName",
        description="Type name (e.g., 'VLASNIČKI')",
    )

    @computed_field  # type: ignore[misc]
    @property
    def active(self) -> bool:
        """Determine if the land registry unit is active based on status."""
        if self.status_name:
            return self.status_name.lower() in ("aktivan", "active")
        # Fallback to checking status code if status_name is not available
        return self.status.lower() in ("a", "1", "active", "aktivan")

    @computed_field  # type: ignore[misc]
    @property
    def verified(self) -> bool:
        """Convenience property for verificated field."""
        return self.verificated


class ParcelLink(BaseModel):
    """
    Link to related or historical parcel records.

    Some parcels have links to previous cadastral records or related parcels.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    parcel_id: int = Field(alias="parcelId", description="Linked parcel ID")
    parcel_number: str = Field(alias="parcelNumber", description="Linked parcel number")
    address: str = Field(description="Linked parcel address")
    area: str = Field(description="Linked parcel area")
    lr_unit: LandRegistryUnit | None = Field(
        default=None, alias="lrUnit", description="Land registry unit information"
    )
    parcel_parts: list[ParcelPart] = Field(
        default_factory=list,
        alias="parcelParts",
        description="Parcel parts (usually empty)",
    )


class ParcelInfo(BaseModel):
    """
    Complete parcel information including ownership data.

    This is the main entity returned by the /cad/parcel-info endpoint.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # Core parcel information
    parcel_id: int = Field(alias="parcelId", description="Unique parcel identifier")
    parcel_number: str = Field(alias="parcelNumber", description="Cadastral parcel number")
    cad_municipality_id: int = Field(
        alias="cadMunicipalityId", description="Municipality internal ID"
    )
    cad_municipality_reg_num: str = Field(
        alias="cadMunicipalityRegNum", description="Municipality registration number"
    )
    cad_municipality_name: str = Field(
        alias="cadMunicipalityName", description="Municipality name"
    )
    institution_id: int = Field(
        alias="institutionId", description="Cadastral institution/office ID"
    )
    address: str = Field(description="Parcel location/address")
    area: str = Field(description="Total parcel area in m² (string format)")

    # Building and status information
    building_remark: int = Field(alias="buildingRemark", description="Building remark code")
    detail_sheet_number: str = Field(
        alias="detailSheetNumber", description="Detail sheet number"
    )
    has_building_right: bool = Field(
        alias="hasBuildingRight", description="Whether building is permitted"
    )

    # Nested structures
    parcel_parts: list[ParcelPart] = Field(
        default_factory=list, alias="parcelParts", description="Land use classifications"
    )
    possession_sheets: list[PossessionSheet] = Field(
        default_factory=list,
        alias="possessionSheets",
        description="Ownership information",
    )
    lr_unit: LandRegistryUnit | None = Field(
        default=None, alias="lrUnit", description="Land registry unit"
    )

    # Optional linked parcels
    parcel_links: list[ParcelLink] | None = Field(
        default=None, alias="parcelLinks", description="Links to related parcels"
    )
    lr_units_from_parcel_links: list[LandRegistryUnit] | None = Field(
        default=None,
        alias="lrUnitsFromParcelLinks",
        description="Extended land registry info from links",
    )

    # Status flags
    is_additional_data_set: bool = Field(
        alias="isAdditionalDataSet", description="Additional data availability flag"
    )
    legal_regime: bool = Field(alias="legalRegime", description="Legal regime indicator")
    graphic: bool = Field(description="Graphical data available")
    alpha_numeric: bool = Field(alias="alphaNumeric", description="Alphanumeric data available")
    status: int = Field(description="Parcel status code")
    resource_code: int = Field(alias="resourceCode", description="Resource code")
    is_harmonized: bool = Field(alias="isHarmonized", description="Data harmonization status")

    @computed_field  # type: ignore[misc]
    @property
    def area_numeric(self) -> int:
        """Convert string area to integer."""
        try:
            return int(self.area)
        except ValueError:
            return 0

    @computed_field  # type: ignore[misc]
    @property
    def total_owners(self) -> int:
        """Count total number of owners across all possession sheets."""
        return sum(len(sheet.possessors) for sheet in self.possession_sheets)

    @computed_field  # type: ignore[misc]
    @property
    def land_use_summary(self) -> dict[str, int]:
        """
        Summarize land use by type with total areas.

        Returns:
            Dictionary mapping land use type to total area in m²
        """
        summary: dict[str, int] = {}
        for part in self.parcel_parts:
            area = part.area_numeric
            if part.name in summary:
                summary[part.name] += area
            else:
                summary[part.name] = area
        return summary

    @computed_field  # type: ignore[misc]
    @property
    def municipality_name(self) -> str:
        """Convenience property for cad_municipality_name."""
        return self.cad_municipality_name

    @computed_field  # type: ignore[misc]
    @property
    def municipality_reg_num(self) -> str:
        """Convenience property for cad_municipality_reg_num."""
        return self.cad_municipality_reg_num

    @field_validator("area")
    @classmethod
    def validate_area(cls, v: str) -> str:
        """Validate that area is a positive number string."""
        try:
            area_int = int(v)
            if area_int < 0:
                raise ValueError("Area must be positive")
        except ValueError as e:
            raise ValueError(f"Invalid area value: {v}") from e
        return v


# ============================================================================
# Land Registry Unit (lr-unit) Models
# ============================================================================
# The following models support the /lr/lr-unit endpoint, which provides
# detailed land registry information including ownership (Sheet B),
# parcel listings (Sheet A), and encumbrances (Sheet C).
# ============================================================================


class PartyType(str, Enum):
    """Type of legal person that can own property or be a beneficiary."""

    INDIVIDUAL = "individual"
    COMPANY = "company"
    STATE = "state"
    MUNICIPALITY = "municipality"
    UNKNOWN = "unknown"


class Party(BaseModel):
    """
    Legal person (individual or entity) that can own property or be a beneficiary.

    Represents the entity itself, separate from how they're registered in the
    land registry. The same party can have multiple ownership entries across
    different properties.

    Design principle: Separate "who" (Party) from "how they own" (OwnershipEntry).
    """

    model_config = ConfigDict(populate_by_name=True, use_enum_values=True)

    lr_owner_id: int | None = Field(None, alias="lrOwnerId", description="Owner ID from API")
    name: str = Field(description="Full name of the party")
    address: str | None = Field(None, description="Address of the party")
    tax_number: str | None = Field(
        None, alias="taxNumber", description="Tax identification number (OIB in Croatia)"
    )
    party_type: PartyType = Field(
        PartyType.UNKNOWN, description="Type of legal person"
    )


class SheetType(str, Enum):
    """Land registry sheet type (List u zemljišnoj knjizi)."""

    A = "A"  # Parcel list (List čestica)
    B = "B"  # Ownership (List vlasništva)
    C = "C"  # Encumbrances (List tereta)


class ActionType(str, Enum):
    """Type of land registry action (Vrsta upisa)."""

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

    model_config = ConfigDict(populate_by_name=True)

    description: str = Field(description="Full text description of the entry")
    order_number: str = Field(
        alias="orderNumber", description="Entry order number (e.g., '1.1', '3.2')"
    )

    # Optional structured fields (not always present in API)
    lr_entry_id: int | None = Field(None, alias="lrEntryId", description="Entry ID")
    action_type: ActionType | None = Field(
        None, description="Type of action (parsed from description if possible)"
    )
    diary_number: str | None = Field(
        None, description="Diary number (e.g., 'Z-3983/2012') - parsed from description"
    )
    entry_date: date | None = Field(None, description="Date of entry (parsed from description)")
    basis_document: str | None = Field(
        None, description="Basis document (parsed from description)"
    )


class ShareStatus(str, Enum):
    """Status of ownership share."""

    ACTIVE = "active"  # Currently valid (status: 0)
    HISTORICAL = "historical"  # No longer valid
    PRELIMINARY = "preliminary"  # Predbilježba


class LRShare(BaseModel):
    """
    Single ownership share in a land registry unit.

    Represents one owner's fractional ownership (e.g., "4/8 share").
    Sub-shares are modeled as separate LRShare objects.

    Design principle: One share = one owner. Don't nest sub-shares inside.
    """

    model_config = ConfigDict(populate_by_name=True)

    lr_unit_share_id: int = Field(
        alias="lrUnitShareId", description="Unique share identifier"
    )
    description: str = Field(description="Share description (e.g., '1. Suvlasnički dio: 4/8')")
    order_number: str = Field(alias="orderNumber", description="Order number (e.g., '1', '3')")
    status: int = Field(description="Status code (0 = active)")

    # Ownership details
    owners: list[Party] = Field(
        default_factory=list, alias="lrOwners", description="List of owners for this share"
    )

    # Fraction (could be parsed from description)
    numerator: int | None = Field(None, description="Numerator of ownership fraction")
    denominator: int | None = Field(None, description="Denominator of ownership fraction")

    # Sub-shares (if any)
    sub_shares_and_entries: list[dict] = Field(
        default_factory=list,
        alias="subSharesAndEntries",
        description="Sub-shares if this share is divided",
    )

    @computed_field  # type: ignore[misc]
    @property
    def is_active(self) -> bool:
        """Check if share is currently active."""
        return self.status == 0

    @computed_field  # type: ignore[misc]
    @property
    def fraction_decimal(self) -> float | None:
        """
        Calculate decimal value of ownership fraction.

        Returns:
            Float between 0.0 and 1.0, or None if fraction not available
        """
        if self.numerator is not None and self.denominator and self.denominator > 0:
            return self.numerator / self.denominator
        return None


class OwnershipSheetB(BaseModel):
    """
    Ownership sheet (List B - List vlasništva).

    This is a DTO/view that aggregates all ownership shares and entries
    for a land registry unit. It represents the current state of ownership.

    Design principle: Sheet B is a logical view/DTO, not a separate table.
    """

    model_config = ConfigDict(populate_by_name=True)

    lr_unit_shares: list[LRShare] = Field(
        default_factory=list,
        alias="lrUnitShares",
        description="List of ownership shares",
    )
    lr_entries: list[LREntry] = Field(
        default_factory=list, alias="lrEntries", description="List of land registry entries"
    )

    def get_current_owners(self) -> list[Party]:
        """Get all parties with active ownership shares."""
        owners = []
        for share in self.lr_unit_shares:
            if share.is_active:
                owners.extend(share.owners)
        return owners

    def total_ownership_accounted(self) -> float | None:
        """
        Calculate total ownership fraction across all shares.

        Returns:
            Total ownership as decimal, or None if fractions not available
        """
        total = 0.0
        has_fractions = False

        for share in self.lr_unit_shares:
            if share.is_active and share.fraction_decimal is not None:
                total += share.fraction_decimal
                has_fractions = True

        return total if has_fractions else None


class RightType(str, Enum):
    """Type of encumbrance/burden on property (Vrste tereta)."""

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

    model_config = ConfigDict(populate_by_name=True)

    description: str = Field(description="Description of the encumbrance group")
    share_order_number: str = Field(
        alias="shareOrderNumber", description="Order number (e.g., '1', '2')"
    )
    lr_entries: list[LREntry] = Field(
        default_factory=list,
        alias="lrEntries",
        description="List of entries for this encumbrance",
    )

    # Parsed from description (optional)
    right_type: RightType | None = Field(None, description="Type of right/encumbrance")
    beneficiary: Party | None = Field(None, description="Creditor, neighbor, state, etc.")


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

    model_config = ConfigDict(populate_by_name=True)

    lr_entry_groups: list[EncumbranceGroup] = Field(
        default_factory=list,
        alias="lrEntryGroups",
        description="List of encumbrance groups",
    )

    def has_encumbrances(self) -> bool:
        """Check if there are any active encumbrances."""
        return len(self.lr_entry_groups) > 0


class LRUnitParcel(BaseModel):
    """
    Cadastral parcel that is part of this land registry unit.

    Represents the link between a LR unit and a specific cadastral parcel.
    A single LR unit typically contains multiple parcels.
    """

    model_config = ConfigDict(populate_by_name=True)

    parcel_id: int = Field(alias="parcelId", description="Parcel identifier")
    parcel_number: str = Field(alias="parcelNumber", description="Cadastral parcel number")
    cad_municipality_id: int = Field(
        alias="cadMunicipalityId", description="Municipality internal ID"
    )
    cad_municipality_reg_num: str = Field(
        alias="cadMunicipalityRegNum", description="Municipality registration number"
    )
    cad_municipality_name: str = Field(
        alias="cadMunicipalityName", description="Municipality name"
    )
    institution_id: int = Field(alias="institutionId", description="Cadastral institution ID")

    # Parcel details
    address: str | None = Field(None, description="Parcel address")
    area: str = Field("0", description="Total area in m²")
    building_remark: int = Field(0, alias="buildingRemark", description="Building remark code")
    detail_sheet_number: str | None = Field(
        None, alias="detailSheetNumber", description="Detail sheet number"
    )
    has_building_right: bool = Field(
        False, alias="hasBuildingRight", description="Whether building is permitted"
    )

    # Parcel parts (land use classification)
    parcel_parts: list[dict] = Field(
        default_factory=list, alias="parcelParts", description="Land use classifications"
    )

    # Possession sheets (often empty)
    possession_sheets: list[dict] = Field(
        default_factory=list,
        alias="possessionSheets",
        description="Possession sheets (often empty)",
    )

    # Status flags
    is_additional_data_set: bool = Field(
        False, alias="isAdditionalDataSet", description="Additional data availability flag"
    )
    legal_regime: bool = Field(False, alias="legalRegime", description="Legal regime indicator")
    graphic: bool = Field(True, description="Graphical data available")
    alpha_numeric: bool = Field(True, alias="alphaNumeric", description="Alphanumeric data available")
    status: int = Field(0, description="Parcel status code")
    resource_code: int = Field(0, alias="resourceCode", description="Resource code")
    is_harmonized: bool = Field(False, alias="isHarmonized", description="Data harmonization status")

    @computed_field  # type: ignore[misc]
    @property
    def area_numeric(self) -> int:
        """Convert string area to integer."""
        try:
            return int(self.area)
        except ValueError:
            return 0


class SheetAParcelList(BaseModel):
    """
    Sheet A1 - Parcel list (List čestica).

    Lists all cadastral parcels that are registered in this land registry unit.
    In Croatian ZK terminology: "List A - popis čestica".

    ⚠️ NOT "Possession Sheet" - that's posjedovni list, a different system.
    """

    model_config = ConfigDict(populate_by_name=True)

    cad_parcels: list[LRUnitParcel] = Field(
        default_factory=list, alias="cadParcels", description="List of cadastral parcels"
    )

    def total_area(self) -> int:
        """Calculate total area of all parcels in m²."""
        return sum(p.area_numeric for p in self.cad_parcels)

    def parcel_numbers(self) -> list[str]:
        """Get list of all parcel numbers."""
        return [p.parcel_number for p in self.cad_parcels]


class SheetAAdditionalInfo(BaseModel):
    """
    Sheet A2 - Additional information.

    Additional data related to parcels and land use.
    In practice, this is often empty in the API response.
    """

    model_config = ConfigDict(populate_by_name=True)

    lr_entries: list[LREntry] = Field(
        default_factory=list, alias="lrEntries", description="Additional entries"
    )


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

    ⚠️ DEMO/EDUCATIONAL USE ONLY - For mock server testing only.
    """

    model_config = ConfigDict(populate_by_name=True)

    # Basic unit info
    lr_unit_id: int = Field(alias="lrUnitId", description="Unique land registry unit ID")
    lr_unit_number: str = Field(alias="lrUnitNumber", description="Registry unit number")
    main_book_id: int = Field(alias="mainBookId", description="Main book ID")
    main_book_name: str = Field(alias="mainBookName", description="Main book name")
    cadastre_municipality_id: int = Field(
        alias="cadastreMunicipalityId", description="Municipality ID"
    )
    institution_id: int = Field(alias="institutionId", description="Land registry institution ID")
    institution_name: str = Field(
        alias="institutionName", description="Institution name (e.g., 'Zemljišnoknjižni odjel Zadar')"
    )

    # Status
    status: str = Field(description="Status code")
    status_name: str = Field(alias="statusName", description="Status name (e.g., 'Aktivan')")
    verificated: bool = Field(description="Verification status")
    condominiums: bool = Field(description="Condominium flag")

    # Unit type
    lr_unit_type_id: int = Field(alias="lrUnitTypeId", description="Type ID")
    lr_unit_type_name: str = Field(
        alias="lrUnitTypeName", description="Type name (e.g., 'VLASNIČKI', 'ETAŽNI')"
    )

    # Last activity
    last_diary_number: str = Field(alias="lastDiaryNumber", description="Last diary number")

    # Active plumbs (liens/restrictions)
    active_plumbs: list[dict] = Field(
        default_factory=list, alias="activePlumbs", description="Active plumbs/liens"
    )

    # Sheet B: Ownership
    ownership_sheet_b: OwnershipSheetB = Field(
        alias="ownershipSheetB", description="Ownership sheet (List B)"
    )

    # Sheet A: Parcels
    possession_sheet_a1: SheetAParcelList = Field(
        alias="possessionSheetA1", description="Parcel list (Sheet A1)"
    )
    possession_sheet_a2: SheetAAdditionalInfo = Field(
        alias="possessionSheetA2", description="Additional info (Sheet A2)"
    )

    # Sheet C: Encumbrances
    encumbrance_sheet_c: EncumbranceSheetC = Field(
        alias="encumbranceSheetC", description="Encumbrance sheet (List C)"
    )

    # Convenience methods
    def get_all_owners(self) -> list[Party]:
        """Get all current owners."""
        return self.ownership_sheet_b.get_current_owners()

    def get_all_parcels(self) -> list[LRUnitParcel]:
        """Get all parcels in this unit."""
        return self.possession_sheet_a1.cad_parcels

    def has_encumbrances(self) -> bool:
        """Check if unit has any encumbrances."""
        return self.encumbrance_sheet_c.has_encumbrances()

    def summary(self) -> dict:
        """
        Get summary statistics for this land registry unit.

        Returns:
            Dictionary with key statistics
        """
        return {
            "unit_number": self.lr_unit_number,
            "main_book": self.main_book_name,
            "total_parcels": len(self.possession_sheet_a1.cad_parcels),
            "total_area_m2": self.possession_sheet_a1.total_area(),
            "num_owners": len(self.get_all_owners()),
            "has_encumbrances": self.has_encumbrances(),
        }
