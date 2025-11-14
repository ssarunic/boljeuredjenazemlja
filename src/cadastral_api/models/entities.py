"""Pydantic models for Croatian Cadastral API responses."""

from fractions import Fraction

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
