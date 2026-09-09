"""
Pydantic models for Croatian Cadastral API responses.

⚠️ DEMO/EDUCATIONAL PROJECT

This is a demonstration project showing how cadastral and land registry systems
could be connected to AI systems via modern APIs. The defaults and examples use
the included mock server (http://localhost:8000). Before using any other server,
verify that you have the rights to use it and its data; use at your own risk
(docs/legal.md). Do not bypass authorization or terms of service.

Purpose: Demonstrating how LLMs could be connected to land books in a safe,
educational context using a mock server that closely mimics production behavior.
"""

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from typing import Annotated, Any, Literal

from pydantic import (
    AliasChoices,
    BaseModel,
    ConfigDict,
    Discriminator,
    Field,
    Tag,
    computed_field,
    field_validator,
    model_validator,
)

from ..utils import (
    display_parcel_number,
    first_date,
    is_building_parcel_number,
    normalize_name,
    parse_amount,
    parse_fraction,
    parse_lr_entry,
    parse_right_type,
    parse_style_class,
    split_name_share,
    strip_html,
)


class SourceModel(BaseModel):
    """Base of every model that receives server JSON.

    Coverage rule R2 (specs/api-coverage-specification.md): unknown keys are
    never dropped. They are kept in ``model_extra`` and exposed through
    ``source_fields`` so that a key the server starts sending after the last
    capture is visible (and the client can warn about it) instead of vanishing.
    Every key observed in a capture is a declared field; ``source_fields`` is
    the safety net, never a place to leave known keys.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    @property
    def source_fields(self) -> dict[str, Any]:
        """Fields the server sent that the model does not declare, verbatim."""
        return dict(self.model_extra or {})


# ============================================================================
# Search endpoints (E2 to E6): one six-key record shape
# ============================================================================


class KeyValueSearchResult(SourceModel):
    """The six-key record every ``/search-*`` endpoint returns.

    ``key1``/``value1`` are the primary id and its display value; the meaning
    of the other four keys depends on the endpoint (see the subclasses). On the
    parcel and possession-sheet searches they are always null (reserved).
    """

    key1: str = Field(description="Primary id (meaning depends on the endpoint)")
    value1: str = Field(description="Display value of the primary id")
    key2: str | None = Field(None, description="Secondary id; reserved (null) on E3/E4")
    value2: str | None = Field(None, description="Secondary display value; reserved on E3/E4")
    value3: str | None = Field(None, description="Tertiary value; reserved except on E2")
    display_value1: str | None = Field(
        None, alias="displayValue1", description="Full display label; reserved on E3/E4"
    )

    def _require(self, field: str) -> str:
        value = getattr(self, field)
        if value is None:
            raise ValueError(f"{type(self).__name__}: server record has no {field}")
        return str(value)


class MunicipalitySearchResult(KeyValueSearchResult):
    """
    Municipality information from search endpoint.

    Response from /search-cad-parcels/municipalities endpoint.
    Can be filtered by cadastral office and department using optional parameters.
    ``key1`` municipality id, ``value1`` "334979 SAVAR", ``key2`` registration
    number, ``value2`` cadastral office id, ``value3`` department id,
    ``displayValue1`` "334979 SAVAR, ZADAR, PUK ZADAR".
    """

    @model_validator(mode="after")
    def _require_registration_number(self) -> "MunicipalitySearchResult":
        # The registration number is what every parcel search needs; a record
        # without it is unusable, so fail loudly rather than return "".
        self._require("key2")
        return self

    @computed_field  # type: ignore[misc]
    @property
    def municipality_id(self) -> str:
        """Municipality internal ID (cadMunicipalityId)."""
        return self.key1

    @computed_field  # type: ignore[misc]
    @property
    def code_and_name(self) -> str:
        """Municipality code and name combined ("334979 SAVAR")."""
        return self.value1

    @computed_field  # type: ignore[misc]
    @property
    def municipality_reg_num(self) -> str:
        """Municipality registration number for parcel searches."""
        return self._require("key2")

    @computed_field  # type: ignore[misc]
    @property
    def institution_id(self) -> str | None:
        """Cadastral office ID (matches the officeId parameter)."""
        return self.value2

    @computed_field  # type: ignore[misc]
    @property
    def department_id(self) -> str | None:
        """Department ID (matches the departmentId parameter)."""
        return self.value3

    @computed_field  # type: ignore[misc]
    @property
    def display_value(self) -> str:
        """Full display name with court information."""
        return self.display_value1 or self.value1

    @computed_field  # type: ignore[misc]
    @property
    def municipality_name(self) -> str:
        """Extract municipality name from code_and_name field."""
        # Format: "334979 SAVAR" -> "SAVAR"
        parts = self.code_and_name.split(" ", 1)
        return parts[1] if len(parts) > 1 else self.code_and_name


class CadastralOffice(SourceModel):
    """
    Cadastral office (Područni ured za katastar) information.

    Response from /search-cad-parcels/offices endpoint.
    Lists all cadastral offices in Croatia.
    """

    id: str = Field(description="Cadastral office ID (matches institutionId in other responses)")
    name: str = Field(description="Full name of cadastral office")


class ParcelSearchResult(KeyValueSearchResult):
    """
    Minimal parcel information from search endpoint (E3).

    ``key1`` is the parcel id, ``value1`` the parcel number in the API
    spelling (building parcels carry a leading asterisk, ``"*35/1"``). The
    other four keys are reserved and null in every observed response.
    """

    @computed_field  # type: ignore[misc]
    @property
    def parcel_id(self) -> str:
        """Unique parcel identifier."""
        return self.key1

    @computed_field  # type: ignore[misc]
    @property
    def parcel_number(self) -> str:
        """Cadastral parcel number (API spelling)."""
        return self.value1

    @computed_field  # type: ignore[misc]
    @property
    def is_building_parcel(self) -> bool:
        """True for a building parcel (``"*35/1"``)."""
        return is_building_parcel_number(self.value1)


class PossessionSheetSearchResult(KeyValueSearchResult):
    """Possession sheet search (E4, ``/search-cad-parcels/possession-sheet-numbers``).

    ``key1`` is the ``possessionSheetId`` the parcel-info ``possessionSheets[]``
    carry, ``value1`` the sheet number. No endpoint returns a sheet by id
    (open question OQ4), so the search records are all there is.
    """

    @computed_field  # type: ignore[misc]
    @property
    def possession_sheet_id(self) -> str:
        """Possession sheet id (matches ``possessionSheets[].possessionSheetId``)."""
        return self.key1

    @computed_field  # type: ignore[misc]
    @property
    def sheet_number(self) -> str:
        """Possession sheet number."""
        return self.value1


class MainBookSearchResult(KeyValueSearchResult):
    """Land-registry main book search (E5, ``/search-lr-parcels/main-books``).

    ``key1`` is the ``mainBookId`` the ``/lr/lr-unit`` endpoint takes,
    ``value1`` the book name ("SAVAR"), ``key2`` the land-registry office
    (``institutionId``), ``value2`` the court name ("ZADAR"),
    ``displayValue1`` "SAVAR, ZADAR".
    """

    @computed_field  # type: ignore[misc]
    @property
    def main_book_id(self) -> int:
        """Main book ID (``mainBookId`` of the lr-unit endpoint)."""
        return int(self.key1)

    @computed_field  # type: ignore[misc]
    @property
    def main_book_name(self) -> str:
        """Main book name (usually the cadastral municipality name)."""
        return self.value1

    @computed_field  # type: ignore[misc]
    @property
    def institution_id(self) -> str | None:
        """Land-registry office id (``institutionId`` of the unit)."""
        return self.key2

    @computed_field  # type: ignore[misc]
    @property
    def court_name(self) -> str | None:
        """Court the main book belongs to ("ZADAR")."""
        return self.value2


class BookOfDCSearchResult(KeyValueSearchResult):
    """Book of deposited contracts search (E6, ``/search-lr-parcels/books-of-dc``).

    "DC" stands for deposited contracts (knjiga položenih ugovora, KPU): the
    register kept for buildings whose flats were sold before the land registry
    unit existed. ``key1`` book id, ``value1`` book name, ``key2`` land-registry
    office id, ``value2`` office name ("Zemljišnoknjižni odjel Zadar"),
    ``displayValue1`` "ZADAR, Zemljišnoknjižni odjel Zadar". Whether ``key1``
    can be passed as ``mainBookId`` to ``/lr/lr-unit`` is unverified (OQ5).
    """

    @computed_field  # type: ignore[misc]
    @property
    def book_id(self) -> int:
        """Book id."""
        return int(self.key1)

    @computed_field  # type: ignore[misc]
    @property
    def book_name(self) -> str:
        """Book name."""
        return self.value1

    @computed_field  # type: ignore[misc]
    @property
    def office_id(self) -> str | None:
        """Land-registry office id."""
        return self.key2

    @computed_field  # type: ignore[misc]
    @property
    def office_name(self) -> str | None:
        """Land-registry office name."""
        return self.value2


class Possessor(SourceModel):
    """
    Possessor (posjednik): a person recorded on a cadastre possession sheet.

    The cadastre records possession, not title; the registered owners (vlasnici)
    are on sheet B of the land registry unit (see ``Party``).

    IMPORTANT: The 'ownership' and 'address' fields are frequently missing in API
    responses. Many parcels do not include the possessors' shares or addresses.

    For condominiums (etažno vlasništvo), additional fields indicate the apartment/unit
    number and the share of common areas.
    """

    name: str = Field(description="Possessor's full name")
    ownership: str | None = Field(
        default=None,
        description="Possessor's share as a fraction (server key 'ownership'), e.g. '1/1', '1/4'",
    )
    address: str | None = Field(
        default=None, description="Possessor's address"
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
        """The possessor's share as ``{num, den, decimal}``, or None."""
        parsed = parse_fraction(self.ownership)
        if parsed is None:
            return None
        num, den = parsed
        return {"num": num, "den": den, "decimal": num / den}

    @computed_field  # type: ignore[misc]
    @property
    def ownership_decimal(self) -> float | None:
        """
        Parse the possessor's share to a decimal.

        Returns:
            Float between 0.0 and 1.0, or None if the share is not specified

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


class PossessionSheet(SourceModel):
    """
    Possession sheet (posjedovni list): a cadastre record with its possessors.

    A parcel can have multiple possession sheets, each with multiple possessors.
    """

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
        default_factory=list, description="Possessors recorded on the sheet"
    )

    @computed_field  # type: ignore[misc]
    @property
    def total_ownership(self) -> float | None:
        """
        Sum of the possessors' shares on this sheet.

        Summed exactly as fractions, then converted once, so thirds and sixths
        add up to 1.0. None when no possessor carries a share.
        """
        pairs = [parse_fraction(p.ownership) for p in self.possessors]
        fractions = [Fraction(num, den) for pair in pairs if pair for num, den in [pair]]
        return float(sum(fractions)) if fractions else None


class ParcelPart(SourceModel):
    """
    Land use classification for a part of the parcel.

    Each parcel can have multiple parts with different land use types. Two
    shapes occur: the cadastre shape (parcel-info ``parcelParts[]`` and sheet A1
    ``cadParcels[].parcelParts[]``) carries the ids and the possession sheet;
    the lean land-registry shape (sheet A1 ``lrParcels[].parcelParts[]``) has
    only ``name``, ``area``, ``building`` plus ``parcelPartId``, ``type`` and
    ``buildingRight`` on building parts. On building parcels the name is
    "KUĆA, SELO".
    """

    parcel_part_id: int | None = Field(
        default=None, alias="parcelPartId", description="Unique parcel part identifier"
    )
    name: str = Field(description="Land use type (e.g., 'PAŠNJAK', 'MASLINJAK', 'ŠUMA')")
    area: str = Field(description="Area in square meters (string format)")
    possession_sheet_id: int | None = Field(
        default=None, alias="possessionSheetId", description="Link to possession sheet"
    )
    possession_sheet_number: str | None = Field(
        default=None, alias="possessionSheetNumber", description="Possession sheet reference"
    )
    last_change_log_number: str | None = Field(
        default=None,
        alias="lastChangeLogNumber",
        description="Last change log entry, e.g. '18/2025'",
    )
    last_change_log_file_num: str | None = Field(
        default=None,
        alias="lastChangeLogFileNum",
        description=(
            "Administrative file of the last change ('UP/I 932-07/2026-02/1217') or the "
            "literal 'Automatska OIB promjena'"
        ),
    )
    building: bool = Field(description="Whether this part contains buildings")
    part_type: str | None = Field(
        default=None, alias="type", description="Part type, 'Zgrada' on building parts"
    )
    building_right: int | None = Field(
        default=None,
        alias="buildingRight",
        description="Building right code on building parts (0 observed)",
    )

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


class LandRegistryUnit(SourceModel):
    """
    Land registry unit reference (zemljišnoknjižni uložak) as carried by parcel-info.

    Three shapes occur, told apart by ``reference_shape``:

    - ``minimal`` (parcel-info ``lrUnit``): ``lrUnitId``, ``lrUnitNumber``,
      ``mainBookId``, ``status``, ``verificated``, ``condominiums``;
    - ``link`` (``parcelLinks[].lrUnit``): minimal plus ``cadastreMunicipalityId``
      and ``mainBookName``;
    - ``full`` (``lrUnitsFromParcelLinks[]``): link plus ``institutionId``,
      ``institutionName``, ``lrUnitTypeId``, ``lrUnitTypeName``, ``statusName``.
    """

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

    @computed_field  # type: ignore[misc]
    @property
    def reference_shape(self) -> Literal["minimal", "link", "full"]:
        """Which of the three reference shapes the server sent (see the class docstring)."""
        provided = self.model_fields_set
        if provided & {"institution_id", "lr_unit_type_id", "status_name", "institution_name"}:
            return "full"
        if provided & {"main_book_name", "cadastre_municipality_id"}:
            return "link"
        return "minimal"

    @computed_field  # type: ignore[misc]
    @property
    def lr_unit_type(self) -> "LRUnitType | None":
        """Unit type as an enum (None when the shape has no ``lrUnitTypeId``)."""
        if self.lr_unit_type_id is None:
            return None
        return LRUnitType.from_id(self.lr_unit_type_id)


class ParcelLink(SourceModel):
    """
    Land-register side of a cadastre parcel (parcel-info ``parcelLinks[]``).

    Present on the "linked" parcel-info shape: the parcel has no direct
    ``lrUnit``; its unit is reachable through this link (``lr_unit`` here is the
    "link" shape, ``lrUnitsFromParcelLinks[]`` the "full" one). ``address`` is
    NOT a location: it is the culture or toponym as recorded in the land
    register ("ORANICA", "VINOGRAD", "ŠUMA"). ``parcelParts`` is always empty.
    """

    parcel_id: int = Field(alias="parcelId", description="Linked parcel ID")
    parcel_number: str = Field(alias="parcelNumber", description="Linked parcel number")
    address: str | None = Field(
        None, description="Culture or toponym as recorded in the land register, not a location"
    )
    area: str = Field(description="Linked parcel area")
    lr_unit: LandRegistryUnit | None = Field(
        default=None, alias="lrUnit", description="Land registry unit information"
    )
    parcel_parts: list[ParcelPart] = Field(
        default_factory=list,
        alias="parcelParts",
        description="Parcel parts (usually empty)",
    )


class ParcelInfo(SourceModel):
    """
    Complete parcel information including its possession sheets (cadastre).

    This is the main entity returned by the /cad/parcel-info endpoint. The
    response has three shapes (``lr_reference_shape``): ``direct`` (an
    ``lrUnit`` object, no links), ``linked`` (no ``lrUnit`` key; one
    ``parcelLinks[]`` element and one ``lrUnitsFromParcelLinks[]`` element) and
    ``none`` (``parcelLinks: []`` and nothing else; every building parcel).
    """

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
    building_remark: int = Field(
        alias="buildingRemark",
        description="Building remark: 1 on every building parcel, 0 otherwise",
    )
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
        description="Possession sheets (cadastre possessors)",
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
    def total_possessors(self) -> int:
        """Number of possessors across all possession sheets (cadastre, not owners)."""
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

    @computed_field  # type: ignore[misc]
    @property
    def is_building_parcel(self) -> bool:
        """Building parcel: ``parcelNumber`` starts with ``*`` or ``buildingRemark`` is 1.

        Building parcels have no land-registry reference of any shape; the
        building is registered on its land parcel.
        """
        return is_building_parcel_number(self.parcel_number) or self.building_remark == 1

    @computed_field  # type: ignore[misc]
    @property
    def parcel_number_display(self) -> str:
        """Croatian display form: ``"*35/1"`` renders as ``"zgr. 35/1"``; land parcels unchanged."""
        return display_parcel_number(self.parcel_number)

    @computed_field  # type: ignore[misc]
    @property
    def lr_reference_shape(self) -> Literal["direct", "linked", "none"]:
        """How the parcel refers to its land-registry unit (see the class docstring)."""
        if self.lr_unit is not None:
            return "direct"
        if self.resolved_lr_unit() is not None:
            return "linked"
        return "none"

    def lr_unit_candidates(self) -> "list[LandRegistryUnit]":
        """Every land-registry unit reference the parcel carries, in resolution order.

        The direct ``lr_unit`` first, then ``lr_units_from_parcel_links``, then the
        units of ``parcel_links``; references to the same unit (number and main
        book) are listed once. The client refuses to pick silently when no direct
        unit exists and the links disagree.
        """
        candidates: list[LandRegistryUnit] = []
        seen: set[tuple[str, int]] = set()
        units = [self.lr_unit] if self.lr_unit is not None else []
        units += list(self.lr_units_from_parcel_links or [])
        units += [link.lr_unit for link in (self.parcel_links or []) if link.lr_unit]
        for unit in units:
            key = (unit.lr_unit_number, unit.main_book_id)
            if key not in seen:
                seen.add(key)
                candidates.append(unit)
        return candidates

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


class Party(SourceModel):
    """
    Legal person (individual or entity) that can own property or be a beneficiary.

    Represents the entity itself, separate from how they're registered in the
    land registry. The same party can have multiple ownership entries across
    different properties. On sheet B the server attaches ``lrEntry``, the
    registration entry that put the owner on the share (``entry``); sheet C
    beneficiaries have no entry of their own.

    Design principle: Separate "who" (Party) from "how they own" (``entry``).
    """

    model_config = ConfigDict(use_enum_values=True)

    lr_owner_id: int | None = Field(None, alias="lrOwnerId", description="Owner ID from API")
    name: str = Field(description="Full name of the party")
    address: str | None = Field(None, description="Address of the party")
    tax_number: str | None = Field(
        None, alias="taxNumber", description="Tax identification number (OIB in Croatia)"
    )
    party_type: PartyType = Field(
        PartyType.UNKNOWN, description="Type of legal person"
    )
    entry: "LREntry | None" = Field(
        None,
        alias="lrEntry",
        description=(
            "Registration entry that put this owner on the share (sheet B). Null on older "
            "shares, absent on sheet C beneficiaries."
        ),
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
    """Kind of land registry entry (vrsta upisa).

    The Land Registry Act knows three kinds: uknjižba, predbilježba and
    zabilježba. ``upis`` is the generic fallback when the text only says
    "upisuje se"; ``brisanje`` is used only when a deletion names no kind
    (a deletion is otherwise reported by ``LREntry.deletes_prior_entry``).
    """

    UKNJIŽBA = "uknjižba"  # Unconditional registration
    PREDBILJEŽBA = "predbilježba"  # Conditional (preliminary) registration
    ZABILJEŽBA = "zabilježba"  # Note / annotation
    UPIS = "upis"  # Generic registration ("upisuje se")
    BRISANJE = "brisanje"  # Deletion that names no kind


class LREntry(SourceModel):
    """
    Generic land registry entry (događaj u zemljišnoj knjizi).

    Represents a single event/action in the land registry. Every change to
    Sheet A, B, or C is caused by an entry. This is the audit trail backbone.
    The same shape appears as an owner's ``lrEntry`` (sheet B), as a sheet-level
    entry (sheet B ``lrEntries``, sheet A2), as a share entry inside
    ``subSharesAndEntries`` and as a sheet C entry (with ``lrOwners`` and
    ``amount``).

    Examples:
    - "Upis prava vlasništva temeljem rješenja o nasljeđivanju"
    - "Zabilježba tražbine socijalne pomoći"
    - "Uknjižba založnog prava"

    ``description`` is the raw HTML fragment the server sends; ``description_text``
    is the stripped text. ``get_parties()`` also picks person records out of any
    undeclared field (``source_fields``).
    """

    description: str = Field(description="Full text description of the entry (raw HTML)")
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

    # Sheet C only: the secured amount of a mortgage or lien, in the Croatian
    # number format with the currency ("134.000,00 EUR", "43.000,00 KN",
    # "10.092.021,00 HRD").
    amount: str | None = Field(
        None, description="Secured amount as sent ('134.000,00 EUR'); mortgages and liens"
    )

    # Structured fields. The server sends only the text; these are parsed from
    # it (``parse_lr_entry``) unless supplied explicitly.
    action_type: ActionType | None = Field(
        None, description="Kind of entry (uknjižba, predbilježba, zabilježba, upis, brisanje)"
    )
    deletes_prior_entry: bool = Field(
        False, description="True when the text deletes an earlier entry ('briše se')"
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
    priority_diary_number: str | None = Field(
        None,
        description=(
            "Diary number whose rank this entry inherits ('Prvenstveni red upisa: Z-8920/2012')"
        ),
    )
    transferred_from_unit: bool = Field(
        False,
        description="True when the owners were carried over from another unit "
        "('IZ ZK ULOŠKA PRENESENI VLASNICI')",
    )
    style_class: str | None = Field(
        None,
        description="CSS class of the span the description opens with ('lr-entry-black')",
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
        if self.priority_diary_number is None:
            self.priority_diary_number = parsed["priority_diary_number"]  # type: ignore[assignment]
        if "transferred_from_unit" not in self.model_fields_set:
            self.transferred_from_unit = bool(parsed["transferred_from_unit"])
        if "deletes_prior_entry" not in self.model_fields_set:
            self.deletes_prior_entry = bool(parsed["deletes_prior_entry"])
        if self.style_class is None:
            self.style_class = parse_style_class(self.description)
        return self

    @computed_field  # type: ignore[misc]
    @property
    def description_text(self) -> str:
        """The description with HTML tags removed and entities decoded."""
        return strip_html(self.description)

    @computed_field  # type: ignore[misc]
    @property
    def amount_value(self) -> Decimal | None:
        """``amount`` as a number (``Decimal('134000.00')``), or None."""
        parsed = parse_amount(self.amount)
        return parsed[0] if parsed else None

    @computed_field  # type: ignore[misc]
    @property
    def amount_currency(self) -> str | None:
        """Currency of ``amount`` ('EUR', 'KN', 'HRD'), or None."""
        parsed = parse_amount(self.amount)
        return parsed[1] if parsed else None

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
    """Status of an ownership share, derived from the server's ``status`` code.

    0 is active; every other value is treated as historical until a
    historical-overview capture shows what the codes mean (OQ1).
    """

    ACTIVE = "active"  # status 0
    HISTORICAL = "historical"  # any other status


def _share_or_entry(value: Any) -> str:
    """Route a ``subSharesAndEntries`` element: a sub-share has ``lrUnitShareId``."""
    if isinstance(value, dict):
        return "share" if "lrUnitShareId" in value or "lr_unit_share_id" in value else "entry"
    return "share" if isinstance(value, LRShare) else "entry"


SubShareOrEntry = Annotated[
    Annotated["LRShare", Tag("share")] | Annotated[LREntry, Tag("entry")],
    Discriminator(_share_or_entry),
]


class LRShare(SourceModel):
    """
    Single ownership share in a land registry unit.

    Represents one co-ownership share (e.g., "4/8 share") with its owners.
    ``subSharesAndEntries`` holds two different things, told apart by the
    presence of ``lrUnitShareId``: sub-shares (co-owners of a condominium
    apartment, ``sub_shares``) and share entries (ZABILJEŽBA on that share:
    lifetime-maintenance contracts, disputes, rejected inheritance decisions,
    cross-references to sheet C; ``share_entries``).

    For condominiums (etažno vlasništvo), each share represents an apartment/unit
    with additional fields for apartment identifier and descriptions.
    """

    lr_unit_share_id: int = Field(
        alias="lrUnitShareId", description="Unique share identifier"
    )
    description: str = Field(description="Share description (e.g., '1. Suvlasnički dio: 4/8')")
    order_number: str = Field(alias="orderNumber", description="Order number (e.g., '1', '3')")
    status: int = Field(description="Status code (0 = active)")

    # Ownership details. The server sends a list, null (unit 870 share 192 in
    # the capture) or omits the key (condominium shares owned through
    # sub-shares); null is normalised to [].
    owners: list[Party] = Field(
        default_factory=list, alias="lrOwners", description="List of owners for this share"
    )

    # Fraction (could be parsed from description)
    numerator: int | None = Field(None, description="Numerator of ownership fraction")
    denominator: int | None = Field(None, description="Denominator of ownership fraction")

    # Sub-shares (co-owners of a divided share) and share entries (annotations
    # on this share), routed by ``_share_or_entry``. Nesting deeper than one
    # level was not observed; the union is recursive anyway.
    sub_shares_and_entries: list[SubShareOrEntry] = Field(
        default_factory=list,
        alias="subSharesAndEntries",
        description="Sub-shares (nested co-owners) and entries (annotations) of this share",
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

    @field_validator("owners", mode="before")
    @classmethod
    def _null_owners_to_empty(cls, value: Any) -> Any:
        return [] if value is None else value

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
    def share_status(self) -> ShareStatus:
        """``ACTIVE`` for status 0, ``HISTORICAL`` for any other code."""
        return ShareStatus.ACTIVE if self.status == 0 else ShareStatus.HISTORICAL

    @computed_field  # type: ignore[misc]
    @property
    def has_direct_owners(self) -> bool:
        """True when the share lists owners itself (not only through sub-shares)."""
        return bool(self.owners)

    @property
    def sub_shares(self) -> "list[LRShare]":
        """The sub-shares (co-owners of a divided share) among ``sub_shares_and_entries``."""
        return [item for item in self.sub_shares_and_entries if isinstance(item, LRShare)]

    @property
    def share_entries(self) -> list[LREntry]:
        """The entries (annotations on this share) among ``sub_shares_and_entries``."""
        return [item for item in self.sub_shares_and_entries if isinstance(item, LREntry)]

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
        """Check if this share has nested co-owners (sub-shares)."""
        return len(self.sub_shares) > 0

    def get_all_owners(self) -> list[Party]:
        """
        Get all owners, including co-owners nested in sub-shares.

        For simple ownership, returns the direct owners. For co-owned apartments
        (etažno vlasništvo), recurses into the sub-shares (entries are skipped).
        """
        all_owners = list(self.owners)
        for sub in self.sub_shares:
            all_owners.extend(sub.get_all_owners())
        return all_owners

    def owner_rows(self, condominium_number: str | None = None) -> list[dict]:
        """Flatten this share (and its sub-shares) into per-owner dicts.

        Direct owners carry this share's fraction; co-owners of a sub-share carry
        that sub-share's own fraction. The condominium number propagates from the
        parent apartment share. ``entry`` is the owner's registration entry
        (``entry_row``), or None on older shares.
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
                "entry": entry_row(owner.entry),
            }
            for owner in self.owners
        ]
        for sub in self.sub_shares:
            rows.extend(sub.owner_rows(condominium_number=cn))
        return rows

    def share_entry_rows(self) -> list[dict]:
        """The annotations on this share (and its sub-shares) as per-entry dicts."""
        rows = [
            {
                "share_order_number": self.order_number,
                "share_description": self.description,
                **(entry_row(entry) or {}),
            }
            for entry in self.share_entries
        ]
        for sub in self.sub_shares:
            rows.extend(sub.share_entry_rows())
        return rows


def entry_row(entry: LREntry | None) -> dict | None:
    """The structured parts of an entry as a plain dict (shared by CLI and MCP output)."""
    if entry is None:
        return None
    return {
        "order_number": entry.order_number,
        "entry_date": entry.entry_date.isoformat() if entry.entry_date else None,
        "diary_number": entry.diary_number,
        "priority_diary_number": entry.priority_diary_number,
        "action_type": entry.action_type.value if entry.action_type else None,
        "basis_document": entry.basis_document,
        "transferred_from_unit": entry.transferred_from_unit,
        "description_text": entry.description_text,
    }


class OwnershipSheetB(SourceModel):
    """
    Ownership sheet (List B - Vlasnički list).

    This is a DTO/view that aggregates all ownership shares and entries
    for a land registry unit. It represents the current state of ownership.

    Design principle: Sheet B is a logical view/DTO, not a separate table.
    """

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

    def total_ownership_fraction(self) -> Fraction | None:
        """Exact sum of the active shares' fractions, or None when none has one."""
        fractions = [
            Fraction(share.numerator, share.denominator)
            for share in self.lr_unit_shares
            if share.is_active and share.numerator is not None and share.denominator
        ]
        return sum(fractions, Fraction(0)) if fractions else None

    def total_ownership_accounted(self) -> float | None:
        """
        Total ownership across the active shares as a decimal.

        Summed exactly as fractions (``total_ownership_fraction``) and converted
        once, so 1/3 + 1/3 + 1/3 is 1.0. None if no share carries a fraction.
        """
        total = self.total_ownership_fraction()
        return float(total) if total is not None else None

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

    def share_entry_rows(self) -> list[dict]:
        """Annotations registered on individual shares (ZABILJEŽBA), flattened."""
        rows: list[dict] = []
        for share in self.lr_unit_shares:
            rows.extend(share.share_entry_rows())
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


class EncumbranceGroup(SourceModel):
    """
    Group of related encumbrance entries.

    Example: A single mortgage that affects multiple parcels in the unit
    will have one group with multiple individual encumbrance entries. The
    secured amount of a mortgage or lien is on the entry (``LREntry.amount``).
    """

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


class EncumbranceSheetC(SourceModel):
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
        default_factory=list,
        alias="lrEntryGroups",
        description="List of encumbrance groups",
    )

    def has_entries(self) -> bool:
        """Whether sheet C carries any entry group at all.

        Nothing in the observed shape says whether a group is still in force
        (OQ1), and a group may hold only notes (zabilježbe), so this is not
        "has active encumbrances".
        """
        return len(self.lr_entry_groups) > 0


class LRUnitParcel(SourceModel):
    """
    Cadastral parcel that is part of this land registry unit (sheet A1).

    Two shapes occur, never mixed within a unit (``SheetAParcelList.source_key``):

    - ``cadParcels[]``: full cadastre parcel records (every parcel-info root key
      except the land-registry references), with ``parcelParts`` in the
      cadastre shape and ``possessionSheets`` whose possessors are empty;
    - ``lrParcels[]``: lean land-register records (``parcelId``,
      ``parcelNumber``, ``address``, ``area``, ``statusInLrUnit``,
      ``parcelParts``), where ``address`` is the old land-register culture or
      toponym ("PAŠNJAK", "ORANICA", "VRT", "ZGRADA"), not a location.
    """

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
    # The lean lrParcels shape omits everything below except area; absent keys
    # stay None rather than becoming a false "0" / "not harmonized" fact.
    address: str | None = Field(
        None,
        description="Location (cadParcels shape) or land-register culture/toponym (lrParcels)",
    )
    area: str | None = Field(None, description="Total area in m²")
    building_remark: int | None = Field(
        None, alias="buildingRemark", description="Building remark code (cadParcels shape)"
    )
    detail_sheet_number: str | None = Field(
        None, alias="detailSheetNumber", description="Detail sheet number"
    )
    has_building_right: bool | None = Field(
        None, alias="hasBuildingRight", description="Whether building is permitted"
    )

    # Parcel parts (land use classification); lean shape on lrParcels
    parcel_parts: list[ParcelPart] = Field(
        default_factory=list, alias="parcelParts", description="Land use classifications"
    )

    # Possession sheets (cadParcels shape only; possessors observed empty)
    possession_sheets: list[PossessionSheet] = Field(
        default_factory=list,
        alias="possessionSheets",
        description="Possession sheets (cadParcels shape; possessors observed empty)",
    )

    # Status flags (cadParcels shape only; None when the server did not send them)
    is_additional_data_set: bool | None = Field(
        None, alias="isAdditionalDataSet", description="Additional data availability flag"
    )
    legal_regime: bool | None = Field(
        None, alias="legalRegime", description="Legal regime indicator"
    )
    graphic: bool | None = Field(None, description="Graphical data available")
    alpha_numeric: bool | None = Field(
        None, alias="alphaNumeric", description="Alphanumeric data available"
    )
    status: int | None = Field(None, description="Parcel status code")
    # Sheet A1 (lrParcels) reports the parcel's status within the LR unit under
    # this distinct key; without an explicit field it is silently dropped.
    status_in_lr_unit: int | None = Field(
        None, alias="statusInLrUnit", description="Status of the parcel within the LR unit"
    )
    resource_code: int | None = Field(None, alias="resourceCode", description="Resource code")
    is_harmonized: bool | None = Field(
        None, alias="isHarmonized", description="Data harmonization status"
    )

    @computed_field  # type: ignore[misc]
    @property
    def area_numeric(self) -> int | None:
        """Area as an integer; None when the server sent no usable area."""
        if self.area is None:
            return None
        try:
            return int(self.area)
        except ValueError:
            return None


class SheetAParcelList(SourceModel):
    """
    Sheet A1 - Parcel list (List čestica).

    Lists all cadastral parcels that are registered in this land registry unit.
    In Croatian ZK terminology: "List A - popis čestica".

    ⚠️ NOT "Possession Sheet" - that's posjedovni list, a different system.

    The server uses one of two keys, never both: ``cadParcels`` (full cadastre
    records) when the parcel-info of the unit's parcels has the direct shape,
    ``lrParcels`` (lean land-register records) when it has the linked shape.
    ``source_key`` records which one was present.
    """

    cad_parcels: list[LRUnitParcel] = Field(
        default_factory=list,
        validation_alias=AliasChoices("lrParcels", "cadParcels"),
        serialization_alias="lrParcels",
        description="List of cadastral parcels",
    )
    source_key: Literal["lrParcels", "cadParcels"] | None = Field(
        None,
        description="Which key the server used for the parcel list (set on validation)",
    )

    @model_validator(mode="before")
    @classmethod
    def _record_source_key(cls, data: Any) -> Any:
        if isinstance(data, dict) and "source_key" not in data:
            for key in ("lrParcels", "cadParcels"):
                if key in data:
                    return {**data, "source_key": key}
        return data

    def total_area(self) -> int:
        """Total area of the parcels in m² (parcels without a usable area count as 0)."""
        return sum(p.area_numeric or 0 for p in self.cad_parcels)

    def parcel_numbers(self) -> list[str]:
        """Get list of all parcel numbers."""
        return [p.parcel_number for p in self.cad_parcels]


class SheetAAdditionalInfo(SourceModel):
    """
    Sheet A2 - Additional information.

    Entries about the parcels themselves: building registration notes under
    the Building Act, cultural-heritage notes, use permits. Often empty.
    """

    lr_entries: list[LREntry] = Field(
        default_factory=list, alias="lrEntries", description="Additional entries"
    )


class Plumb(SourceModel):
    """A pending land-registry entry (plomba).

    A plomba marks an unresolved/in-progress request on the unit (e.g. an
    ownership transfer or mortgage being processed). Its presence means the
    current ownership/encumbrance picture may be about to change.
    """

    file_number: str = Field(
        alias="fileNumber", description="Diary/file number, e.g. 'Z-12564/2026'"
    )
    cad_plumb: bool = Field(
        False, alias="cadPlumb", description="True if a cadastre plomba (else land registry)"
    )
    plumb_mark: str | None = Field(
        None,
        alias="plumbMark",
        description="On condominiums: the unit the plomba concerns, e.g. '(E-80)'",
    )


class FileStatusInstitution(SourceModel):
    """Land-registry office that owns a file (spis)."""

    institution_id: int | None = Field(None, alias="institutionId")
    institution_name: str | None = Field(None, alias="institutionName")


class FileStatus(SourceModel):
    """Processing status of a single land-registry file (plomba / spis).

    Returned by ``POST /lr/file-status``. A :class:`Plumb` on a unit only
    carries the bare file number; this is the detail behind it - what the
    request is, where it is in processing, and the key dates. While the file is
    unresolved the matching plomba stays active on the unit, so this is how you
    tell *what* a pending change actually is (e.g. an ownership transfer vs an
    inheritance vs a mortgage).

    ⚠️ Demo project: verify your rights before using any server other than the mock.
    """

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


class LRUnitType(str, Enum):
    """Land-registry unit type (``lrUnitTypeId``), with a fallback for unseen ids."""

    OWNERSHIP = "ownership"  # 1, VLASNIČKI
    CONDOMINIUM_DEFINED_SHARES = "condominium_defined_shares"  # 3, ETAŽNO ... S ODREĐENIM OMJERIMA
    OTHER = "other"  # any other id (e.g. simple ETAŽNI units, OQ6)

    @classmethod
    def from_id(cls, type_id: int | None) -> "LRUnitType":
        return _LR_UNIT_TYPE_IDS.get(type_id, cls.OTHER)  # type: ignore[arg-type]


_LR_UNIT_TYPE_IDS: dict[int, LRUnitType] = {
    1: LRUnitType.OWNERSHIP,
    3: LRUnitType.CONDOMINIUM_DEFINED_SHARES,
}


class LandRegistryUnitDetailed(SourceModel):
    """
    Complete land registry unit with all sheets (A, B, C).

    This is the main DTO returned by the /lr/lr-unit endpoint.
    It aggregates:
    - Basic unit metadata
    - Sheet A: List of parcels
    - Sheet B: Ownership information
    - Sheet C: Encumbrances and burdens

    This is a read model / view - generated from API, not persisted.

    ⚠️ Demo project: verify your rights before using any server other than the mock.
    """

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

    # Unit type (1 = VLASNIČKI, 3 = ETAŽNO VLASNIŠTVO S ODREĐENIM OMJERIMA)
    lr_unit_type_id: int = Field(alias="lrUnitTypeId", description="Type ID (1, 3, ...)")
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

    @computed_field  # type: ignore[misc]
    @property
    def lr_unit_type(self) -> LRUnitType:
        """Unit type as an enum, ``LRUnitType.OTHER`` for ids not seen so far."""
        return LRUnitType.from_id(self.lr_unit_type_id)

    @property
    def sheet_a1_source_key(self) -> str | None:
        """Which key sheet A1 used for its parcel list (``lrParcels`` or ``cadParcels``)."""
        return self.possessory_sheet_a1.source_key

    # Convenience methods
    def get_all_owners(self) -> list[Party]:
        """Get all current owners."""
        return self.ownership_sheet_b.get_current_owners()

    def get_all_parcels(self) -> list[LRUnitParcel]:
        """Get all parcels in this unit."""
        return self.possessory_sheet_a1.cad_parcels

    def has_sheet_c_entries(self) -> bool:
        """Whether sheet C has any entry group (see ``EncumbranceSheetC.has_entries``)."""
        return self.encumbrance_sheet_c.has_entries()

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
            "has_sheet_c_entries": self.has_sheet_c_entries(),
            "has_pending_plombe": self.has_pending_plombe(),
            "pending_plombe": [p.file_number for p in self.active_plumbs],
            "is_condominium": self.is_condominium(),
        }
        if self.is_condominium():
            result["condominium_units"] = self.get_condominium_units_count()
        return result


# Party -> LREntry -> Party and LRShare -> SubShareOrEntry -> LRShare are
# mutually recursive; resolve the string annotations now that all are defined.
Party.model_rebuild()
LREntry.model_rebuild()
LRShare.model_rebuild()
LandRegistryUnit.model_rebuild()
