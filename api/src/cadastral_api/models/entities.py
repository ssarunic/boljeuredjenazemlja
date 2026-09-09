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

from datetime import date, datetime
from enum import Enum
from fractions import Fraction
from typing import Any

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    field_validator,
    model_validator,
)

from ..utils import (
    first_date,
    normalize_name,
    parse_fraction,
    parse_lr_entry,
    parse_right_type,
    split_name_share,
)


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

    For condominiums (etažno vlasništvo), additional fields indicate the apartment/unit
    number and the share of common areas.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: str = Field(description="Owner's full name")
    ownership: str | None = Field(
        default=None, description="Ownership fraction (e.g., '1/1', '1/4')"
    )
    address: str | None = Field(
        default=None, description="Owner's address"
    )

    # Condominium-specific fields
    condominium_share_number: str | None = Field(
        default=None,
        alias="condominiumShareNumber",
        description="Apartment/unit number in condominium (e.g., '35', '0' for common areas)",
    )
    condominium_share_ownership: str | None = Field(
        default=None,
        alias="condominiumShareOwnership",
        description="Share of common areas (e.g., '61/4651')",
    )

    @computed_field  # type: ignore[misc]
    @property
    def register(self) -> str:
        """Source register: cadastre (kataster / posjedovni list).

        A possessor is NOT necessarily the land-registry owner; the registered
        owner (vlasnik) lives in the land registry B-list (vlastovnica). See
        the Party model, tagged ``land_registry``.
        """
        return "cadastre"

    @computed_field  # type: ignore[misc]
    @property
    def name_normalized(self) -> str:
        """Display/matching-normalized form of ``name`` (raw value preserved)."""
        return normalize_name(self.name)

    @computed_field  # type: ignore[misc]
    @property
    def ownership_fraction(self) -> dict | None:
        """Structured ownership fraction ``{num, den, decimal}`` or None."""
        parsed = parse_fraction(self.ownership)
        if parsed is None:
            return None
        num, den = parsed
        return {"num": num, "den": den, "decimal": num / den}

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

    def resolved_lr_unit(self) -> "LandRegistryUnit | None":
        """The parcel's land-registry unit, falling back to parcel links.

        Returns the direct ``lr_unit`` when present, otherwise the first unit
        reachable via ``lr_units_from_parcel_links`` / ``parcel_links``. Returns
        None only when the parcel is genuinely not in the land registry. A null
        direct ``lr_unit`` does NOT mean "no land registry data".
        """
        if self.lr_unit is not None:
            return self.lr_unit
        for unit in self.lr_units_from_parcel_links or []:
            return unit
        for link in self.parcel_links or []:
            if link.lr_unit is not None:
                return link.lr_unit
        return None

    @property
    def lr_unit_from_links(self) -> bool:
        """True if the LR unit is reachable only via parcel links (no direct lr_unit)."""
        return self.lr_unit is None and self.resolved_lr_unit() is not None

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

    @computed_field  # type: ignore[misc]
    @property
    def register(self) -> str:
        """Source register: land registry (zemljišne knjige / vlastovnica B-list).

        Distinguishes a registered land-registry party from a cadastre
        possessor (see the Possessor model, tagged ``cadastre``).
        """
        return "land_registry"

    @computed_field  # type: ignore[misc]
    @property
    def name_normalized(self) -> str:
        """Display/matching-normalized form of ``name`` (raw value preserved).

        A share suffix in the name (``"... ZA 2/6"``) is not part of the name;
        it is exposed as ``share`` instead.
        """
        return normalize_name(split_name_share(self.name)[0])

    @computed_field  # type: ignore[misc]
    @property
    def share(self) -> dict | None:
        """Share of the right carried in the name, ``{num, den, decimal}`` or None.

        Sheet C beneficiaries: ``"ŠARUNIĆ AUGUSTIN POK. BOŽE ZA 2/6"`` gives
        ``{"num": 2, "den": 6, "decimal": 0.333...}``, the same shape as a
        Sheet B share's ``share_fraction``. Sheet B owners carry their share on
        the ``LRShare`` instead, so this is None for them.
        """
        fraction = split_name_share(self.name)[1]
        if fraction is None:
            return None
        num, den = fraction
        return {"num": num, "den": den, "decimal": num / den}


class SheetType(str, Enum):
    """Land registry sheet type (List u zemljišnoj knjizi)."""

    A = "A"  # Parcel list (List čestica)
    B = "B"  # Ownership (Vlasnički list)
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

    # ``extra="allow"``: anything else the server nests under an entry is kept
    # verbatim in ``model_extra`` instead of being dropped (``source_fields``),
    # and ``get_parties()`` also picks person records out of it.
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    description: str = Field(description="Full text description of the entry")
    order_number: str = Field(
        alias="orderNumber", description="Entry order number (e.g., '1.1', '3.2')"
    )

    # Persons the entry is registered in favour of (the "u korist:" the
    # description ends with). Same shape as the owners of a Sheet B share.
    owners: list[Party] = Field(
        default_factory=list,
        alias="lrOwners",
        description="Beneficiaries of the entry (u korist), e.g. usufructuary, creditor",
    )

    lr_entry_id: int | None = Field(None, alias="lrEntryId", description="Entry ID")

    # Structured fields. The server sends only the text; these are parsed from
    # it (``parse_lr_entry``) unless supplied explicitly.
    action_type: ActionType | None = Field(
        None, description="Type of action (upis, predbilježba, zabilježba, brisanje)"
    )
    diary_number: str | None = Field(
        None, description="Diary number, normalised (e.g. 'Z-487/49', 'Z-9139/2016')"
    )
    entry_date: date | None = Field(
        None, description="Receipt date of the entry (the first date in the text)"
    )
    basis_document: str | None = Field(
        None,
        description="Legal basis: the phrase after 'Na temelju' (judgment, decision, contract)",
    )
    basis_date: date | None = Field(
        None, description="Date of the basis document (first date inside basis_document)"
    )

    @model_validator(mode="after")
    def _parse_description(self) -> "LREntry":
        parsed = parse_lr_entry(self.description)
        if self.action_type is None and parsed["action_type"]:
            self.action_type = ActionType(parsed["action_type"])
        if self.diary_number is None:
            self.diary_number = parsed["diary_number"]  # type: ignore[assignment]
        if self.entry_date is None:
            self.entry_date = parsed["entry_date"]  # type: ignore[assignment]
        if self.basis_document is None:
            self.basis_document = parsed["basis_document"]  # type: ignore[assignment]
        if self.basis_date is None and self.basis_document:
            self.basis_date = first_date(self.basis_document)
        return self

    @property
    def source_fields(self) -> dict[str, Any]:
        """Fields the server sent that the model does not declare, verbatim."""
        return dict(self.model_extra or {})

    def get_parties(self) -> list[Party]:
        """Persons the entry is registered in favour of (the "u korist:").

        ``owners`` (the server's ``lrOwners``) first; then, as a safety net,
        every undeclared field holding an object (or list of objects) with a
        ``name`` is treated as a party record too.
        """
        return list(self.owners) + _collect_parties(self.model_extra or {})


def _collect_parties(fields: dict[str, Any]) -> list[Party]:
    """Build ``Party`` objects from every name-bearing object in ``fields``."""
    parties: list[Party] = []
    for value in fields.values():
        candidates = value if isinstance(value, list) else [value]
        for item in candidates:
            if isinstance(item, dict) and isinstance(item.get("name"), str) and item["name"]:
                parties.append(Party.model_validate(item))
    return parties


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

    For condominiums (etažno vlasništvo), each share represents an apartment/unit
    with additional fields for apartment identifier and descriptions.

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

    # Sub-shares (if any) - for co-ownership within a condominium unit
    sub_shares_and_entries: list[dict] = Field(
        default_factory=list,
        alias="subSharesAndEntries",
        description="Sub-shares if this share is divided (nested co-owners)",
    )

    # Condominium-specific fields
    condominium_number: str | None = Field(
        default=None,
        alias="condominiumNumber",
        description="Apartment identifier (e.g., 'E-16', 'E-35')",
    )
    condominium_descriptions: list[str] = Field(
        default_factory=list,
        alias="condominiums",
        description="Apartment descriptions (floor, rooms, area)",
    )

    @model_validator(mode="after")
    def _populate_fraction_from_description(self) -> "LRShare":
        """Fill numerator/denominator from the description string.

        The API leaves these structured fields empty and embeds the fraction in
        the description (e.g. "127. Suvlasnički dio: 1/4"). Parsing it here
        revives ``fraction_decimal`` and ``total_ownership_accounted``.
        """
        if self.numerator is None or self.denominator is None:
            parsed = parse_fraction(self.description)
            if parsed is not None:
                self.numerator, self.denominator = parsed
        return self

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

    @computed_field  # type: ignore[misc]
    @property
    def share_fraction(self) -> dict | None:
        """Structured ownership fraction ``{num, den, decimal}`` or None."""
        if self.numerator is not None and self.denominator:
            return {
                "num": self.numerator,
                "den": self.denominator,
                "decimal": self.fraction_decimal,
            }
        return None

    def is_condominium_share(self) -> bool:
        """Check if this share represents a condominium unit (apartment)."""
        return self.condominium_number is not None

    def get_apartment_description(self) -> str | None:
        """Get the first apartment description if available."""
        return self.condominium_descriptions[0] if self.condominium_descriptions else None

    def has_sub_owners(self) -> bool:
        """Check if this share has nested co-owners (subSharesAndEntries)."""
        return len(self.sub_shares_and_entries) > 0

    def _sub_shares(self) -> "list[LRShare]":
        """Parse sub-shares (raw dicts) into LRShare objects, skipping invalid ones."""
        subs: list[LRShare] = []
        for sub in self.sub_shares_and_entries:
            try:
                subs.append(LRShare.model_validate(sub))
            except Exception:
                pass  # Skip malformed sub-share data
        return subs

    def get_all_owners(self) -> list[Party]:
        """
        Get all owners, including co-owners nested in sub-shares.

        For simple ownership, returns the direct owners. For co-owned apartments
        (etažno vlasništvo), recurses into subSharesAndEntries.
        """
        all_owners = list(self.owners)
        for sub in self._sub_shares():
            all_owners.extend(sub.get_all_owners())
        return all_owners

    def owner_rows(self, condominium_number: str | None = None) -> list[dict]:
        """Flatten this share (and its sub-shares) into per-owner dicts.

        Direct owners carry this share's fraction; co-owners of a sub-share carry
        that sub-share's own fraction. The condominium number propagates from the
        parent apartment share.
        """
        cn = self.condominium_number or condominium_number
        rows = [
            {
                "name": owner.name,
                "name_normalized": owner.name_normalized,
                "tax_number": owner.tax_number,
                "address": owner.address,
                "register": owner.register,
                "share": self.share_fraction,
                "share_description": self.description,
                "condominium_number": cn,
            }
            for owner in self.owners
        ]
        for sub in self._sub_shares():
            rows.extend(sub.owner_rows(condominium_number=cn))
        return rows


class OwnershipSheetB(BaseModel):
    """
    Ownership sheet (List B - Vlasnički list).

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
        """Get all parties with active ownership shares, including sub-share co-owners."""
        owners = []
        for share in self.lr_unit_shares:
            if share.is_active:
                owners.extend(share.get_all_owners())
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

    def owner_rows(self) -> list[dict]:
        """Flatten active shares (and their sub-share co-owners) into per-owner dicts.

        A single canonical owner shape shared by the MCP response shaper and the
        CLI output builders, so they cannot drift apart.
        """
        rows: list[dict] = []
        for share in self.lr_unit_shares:
            if share.is_active:
                rows.extend(share.owner_rows())
        return rows


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

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    description: str = Field(description="Description of the encumbrance group")
    share_order_number: str | None = Field(
        default=None,
        alias="shareOrderNumber",
        description="Order number (e.g., '1', '2') - optional as API sometimes omits this field"
    )
    lr_entries: list[LREntry] = Field(
        default_factory=list,
        alias="lrEntries",
        description="List of entries for this encumbrance",
    )

    # Derived from the entries when the server does not send them (it never
    # does today): the right named in the entry text and the first person the
    # entry is registered in favour of.
    right_type: RightType | None = Field(
        None,
        description="Type of right/encumbrance, parsed from the entry text when not supplied",
    )
    beneficiary: Party | None = Field(
        None,
        description="First beneficiary (creditor, usufructuary, ...); all via get_parties()",
    )

    @model_validator(mode="after")
    def _derive_from_entries(self) -> "EncumbranceGroup":
        if self.beneficiary is None:
            nested = self._nested_parties()
            if nested:
                self.beneficiary = nested[0]
        if self.right_type is None and self.lr_entries:
            # Entry text names the right; the group label ("1. ", "Na
            # suvlasnički dio ...") never does, so it is not consulted.
            parsed = parse_right_type(" ".join(entry.description for entry in self.lr_entries))
            if parsed is not None:
                self.right_type = RightType(parsed)
        return self

    def _nested_parties(self) -> list[Party]:
        parties = _collect_parties(self.model_extra or {})
        for entry in self.lr_entries:
            parties.extend(entry.get_parties())
        return parties

    def get_parties(self) -> list[Party]:
        """Everyone this encumbrance is registered in favour of, in entry order.

        ``beneficiary`` is included once (it is normally the first of these).
        """
        parties = self._nested_parties()
        if self.beneficiary is not None and self.beneficiary not in parties:
            parties.insert(0, self.beneficiary)
        return parties


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

    model_config = ConfigDict(populate_by_name=True, extra="allow")

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
    # These fields are present on the standalone cadastral-parcel shape but are
    # omitted from the leaner Sheet A1 (lrParcels) shape returned by the LR-unit
    # endpoint, so they must be optional.
    cad_municipality_id: int | None = Field(
        None, alias="cadMunicipalityId", description="Municipality internal ID"
    )
    cad_municipality_reg_num: str | None = Field(
        None, alias="cadMunicipalityRegNum", description="Municipality registration number"
    )
    cad_municipality_name: str | None = Field(
        None, alias="cadMunicipalityName", description="Municipality name"
    )
    institution_id: int | None = Field(
        None, alias="institutionId", description="Cadastral institution ID"
    )

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
    alpha_numeric: bool = Field(
        True, alias="alphaNumeric", description="Alphanumeric data available"
    )
    status: int = Field(0, description="Parcel status code")
    # Sheet A1 (lrParcels) reports the parcel's status within the LR unit under
    # this distinct key; without an explicit field it is silently dropped.
    status_in_lr_unit: int | None = Field(
        None, alias="statusInLrUnit", description="Status of the parcel within the LR unit"
    )
    resource_code: int = Field(0, alias="resourceCode", description="Resource code")
    is_harmonized: bool = Field(
        False, alias="isHarmonized", description="Data harmonization status"
    )

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

    # The live API returns the parcel list under "lrParcels". Some hand-authored
    # mock fixtures use the legacy "cadParcels" key, so accept both. Mismatching
    # this alias silently yields an empty list (and total_parcels == 0).
    cad_parcels: list[LRUnitParcel] = Field(
        default_factory=list,
        validation_alias=AliasChoices("lrParcels", "cadParcels"),
        serialization_alias="lrParcels",
        description="List of cadastral parcels",
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


class Plumb(BaseModel):
    """A pending land-registry entry (plomba).

    A plomba marks an unresolved/in-progress request on the unit (e.g. an
    ownership transfer or mortgage being processed). Its presence means the
    current ownership/encumbrance picture may be about to change.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    file_number: str = Field(
        alias="fileNumber", description="Diary/file number, e.g. 'Z-12564/2026'"
    )
    cad_plumb: bool = Field(
        False, alias="cadPlumb", description="True if a cadastre plomba (else land registry)"
    )


class FileStatusInstitution(BaseModel):
    """Land-registry office that owns a file (spis)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    institution_id: int | None = Field(None, alias="institutionId")
    institution_name: str | None = Field(None, alias="institutionName")


class FileStatus(BaseModel):
    """Processing status of a single land-registry file (plomba / spis).

    Returned by ``POST /lr/file-status``. A :class:`Plumb` on a unit only
    carries the bare file number; this is the detail behind it - what the
    request is, where it is in processing, and the key dates. While the file is
    unresolved the matching plomba stays active on the unit, so this is how you
    tell *what* a pending change actually is (e.g. an ownership transfer vs an
    inheritance vs a mortgage).

    ⚠️ DEMO/EDUCATIONAL USE ONLY - For mock server testing only.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    file_id: int | None = Field(None, alias="fileId", description="Internal file ID")
    lr_file_number: str = Field(
        alias="lrFileNumber", description="File reference number, e.g. 'Z-12564/2026'"
    )
    institution: FileStatusInstitution | None = Field(
        None, description="Owning land-registry office"
    )

    status_description: str | None = Field(
        None,
        alias="statusDescription",
        description="Processing stage, e.g. 'IZRADA NACRTA RJEŠENJA', 'OTPREMA'",
    )
    application_content: str | None = Field(
        None,
        alias="applicationContent",
        description="What the request is, e.g. 'Uknjižba prava vlasništva'",
    )
    registration_number: str | None = Field(
        None,
        alias="registrationNumber",
        description="External reference (court/notary), e.g. 'OV-4021/2026'",
    )
    resolution_type_name: str | None = Field(
        None,
        alias="resolutionTypeName",
        description="Outcome once resolved, e.g. 'Udovoljeno'",
    )

    # Key timestamps (timezone-aware ISO 8601 in the API)
    info_date: datetime | None = Field(None, alias="infoDate")
    receiving_date: datetime | None = Field(None, alias="receivingDate")
    solving_date: datetime | None = Field(None, alias="solvingDate")
    execution_date: datetime | None = Field(None, alias="executionDate")
    file_shipment_date: datetime | None = Field(None, alias="fileShipmentDate")

    @computed_field  # type: ignore[misc]
    @property
    def is_resolved(self) -> bool:
        """Whether the file has been decided (executed), i.e. the change is no longer pending."""
        return self.execution_date is not None

    @property
    def institution_id(self) -> int | None:
        """Owning office ID, if present."""
        return self.institution.institution_id if self.institution else None


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
        alias="institutionName",
        description="Institution name (e.g., 'Zemljišnoknjižni odjel Zadar')",
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

    # Active plombe - pending/unresolved entries on the unit
    active_plumbs: list[Plumb] = Field(
        default_factory=list, alias="activePlumbs", description="Pending entries (plombe)"
    )

    # Sheet B: Ownership
    ownership_sheet_b: OwnershipSheetB = Field(
        alias="ownershipSheetB", description="Ownership sheet (List B)"
    )

    # Sheet A: Parcels (Possessory sheet / Popis čestica)
    possessory_sheet_a1: SheetAParcelList = Field(
        alias="possessionSheetA1", description="Parcel list (Possessory Sheet A1)"
    )
    possessory_sheet_a2: SheetAAdditionalInfo = Field(
        alias="possessionSheetA2", description="Additional info (Possessory Sheet A2)"
    )

    # Sheet C: Encumbrances
    encumbrance_sheet_c: EncumbranceSheetC = Field(
        alias="encumbranceSheetC", description="Encumbrance sheet (List C)"
    )

    # Resolution provenance (not from the API): set by get_lr_unit_from_parcel
    # when the unit was reached via parcel links because the parcel had no
    # direct lr_unit.
    lr_unit_derived_from_links: bool = Field(
        False, description="True if resolved via parcel links rather than a direct lr_unit"
    )
    # Cadastre/LR harmonization of the source parcel (set by get_lr_unit_from_parcel);
    # None when fetched directly by unit number (no parcel context).
    cadastre_harmonized: bool | None = Field(
        None, description="Source parcel's cadastre/LR harmonization status, if known"
    )

    # Convenience methods
    def get_all_owners(self) -> list[Party]:
        """Get all current owners."""
        return self.ownership_sheet_b.get_current_owners()

    def get_all_parcels(self) -> list[LRUnitParcel]:
        """Get all parcels in this unit."""
        return self.possessory_sheet_a1.cad_parcels

    def has_encumbrances(self) -> bool:
        """Check if unit has any encumbrances."""
        return self.encumbrance_sheet_c.has_encumbrances()

    def has_pending_plombe(self) -> bool:
        """Whether the unit has any pending entries (plombe) - changes in progress."""
        return len(self.active_plumbs) > 0

    def is_condominium(self) -> bool:
        """
        Check if this is a condominium (etažno vlasništvo) unit.

        Note: The `condominiums` boolean flag from API is often unreliable (returns False
        even for condominium units). This method checks both the flag and the type name.

        Returns:
            True if unit is a condominium (apartment building), False otherwise
        """
        return self.condominiums or "ETAŽN" in self.lr_unit_type_name.upper()

    def get_condominium_units_count(self) -> int:
        """
        Get the number of individual units (apartments) in this condominium.

        Returns:
            Number of shares that have a condominium number, or 0 if not a condominium
        """
        if not self.is_condominium():
            return 0
        return sum(
            1 for share in self.ownership_sheet_b.lr_unit_shares
            if share.is_condominium_share()
        )

    def summary(self) -> dict:
        """
        Get summary statistics for this land registry unit.

        Returns:
            Dictionary with key statistics
        """
        result = {
            "unit_number": self.lr_unit_number,
            "main_book": self.main_book_name,
            "total_parcels": len(self.possessory_sheet_a1.cad_parcels),
            "total_area_m2": self.possessory_sheet_a1.total_area(),
            "num_owners": len(self.get_all_owners()),
            "has_encumbrances": self.has_encumbrances(),
            "has_pending_plombe": self.has_pending_plombe(),
            "pending_plombe": [p.file_number for p in self.active_plumbs],
            "is_condominium": self.is_condominium(),
        }
        if self.is_condominium():
            result["condominium_units"] = self.get_condominium_units_count()
        return result
