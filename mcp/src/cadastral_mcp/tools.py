"""MCP Tools - AI-invoked actions that perform operations."""

import logging
from typing import Any

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError

logger = logging.getLogger(__name__)


class CadastralTools:
    """
    MCP Tools for cadastral operations.

    Tools are executable functions that the AI can invoke to perform
    actions like searching, fetching data, or resolving identifiers.
    """

    def __init__(self, client: CadastralAPIClient) -> None:
        """Initialize tools with a cadastral API client."""
        self.client = client

    async def search_parcel(
        self, parcel_number: str, municipality: str
    ) -> dict[str, Any]:
        """
        Search for a parcel and return basic information.

        This tool aggregates the 3-step API workflow:
        1. Resolve municipality name to code (if needed)
        2. Search for parcel by number
        3. Return parcel ID and basic info

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name or registration code

        Returns:
            Dictionary with parcel search results including parcel_id

        Example:
            >>> await search_parcel("103/2", "SAVAR")
            {
                "parcel_id": "...",
                "parcel_number": "103/2",
                "municipality": "SAVAR",
                "address": "...",
                "area": "..."
            }
        """
        try:
            logger.info(f"Searching for parcel {parcel_number} in {municipality}")

            # Step 1: Resolve municipality if needed
            muni_code = await self._resolve_municipality(municipality)

            # Step 2: Find parcel
            results = self.client.find_parcel(parcel_number, muni_code)

            if not results:
                raise ValueError(
                    f"No parcels found matching '{parcel_number}' in {municipality}"
                )

            # Return first match
            result = results[0]
            return {
                "parcel_id": result.parcel_id,
                "parcel_number": result.parcel_number,
                "municipality": municipality,
                "municipality_code": muni_code,
                "success": True,
            }

        except CadastralAPIError as e:
            logger.error(f"Search failed for {parcel_number} in {municipality}: {e}", exc_info=True)
            raise ValueError(
                f"Could not search for parcel '{parcel_number}'. Please verify the parcel number "
                f"and municipality."
            ) from e

    async def batch_fetch_parcels(
        self, parcels: list[dict[str, str]], include_owners: bool = False
    ) -> dict[str, Any]:
        """
        Fetch multiple parcels in a single operation.

        Args:
            parcels: List of parcel specifications, each with:
                - parcel_number: Cadastral number (e.g., "103/2")
                - municipality: Municipality name or code
                OR
                - parcel_id: Direct parcel ID if already known
            include_owners: Whether to include ownership information

        Returns:
            Dictionary with results array and summary statistics

        Example:
            >>> await batch_fetch_parcels([
            ...     {"parcel_number": "103/2", "municipality": "SAVAR"},
            ...     {"parcel_number": "45", "municipality": "LUKA"}
            ... ])
            {
                "results": [...],
                "total": 2,
                "successful": 2,
                "failed": 0
            }
        """
        try:
            logger.info(f"Batch fetching {len(parcels)} parcels (include_owners={include_owners})")

            results: list[dict[str, Any]] = []
            successful = 0
            failed = 0

            for spec in parcels:
                try:
                    # Check if parcel_id is directly provided
                    if "parcel_id" in spec:
                        parcel_id = spec["parcel_id"]
                    else:
                        # Search for parcel first
                        parcel_number = spec.get("parcel_number")
                        municipality = spec.get("municipality")

                        if not parcel_number or not municipality:
                            raise ValueError("Each parcel must have either parcel_id or both parcel_number and municipality")

                        search_result = await self.search_parcel(parcel_number, municipality)
                        parcel_id = search_result["parcel_id"]

                    # Fetch detailed info
                    parcel = self.client.get_parcel_info(parcel_id)

                    result_data = parcel.model_dump(mode="json")

                    # Optionally filter out ownership data
                    if not include_owners:
                        result_data.pop("possession_sheets", None)

                    results.append({
                        "status": "success",
                        "data": result_data,
                    })
                    successful += 1

                except Exception as e:
                    logger.error(f"Failed to fetch parcel {spec}: {e}")
                    results.append({
                        "status": "error",
                        "error": str(e),
                        "spec": spec,
                    })
                    failed += 1

            return {
                "results": results,
                "total": len(parcels),
                "successful": successful,
                "failed": failed,
            }

        except Exception as e:
            logger.error(f"Batch fetch operation failed: {e}", exc_info=True)
            raise ValueError(f"Batch fetch operation failed: {e}") from e

    async def resolve_municipality(self, name_or_code: str) -> dict[str, Any]:
        """
        Resolve municipality name to registration code.

        Args:
            name_or_code: Municipality name (e.g., "SAVAR") or code (e.g., "334979")

        Returns:
            Dictionary with municipality code and name

        Example:
            >>> await resolve_municipality("SAVAR")
            {"code": "334979", "name": "SAVAR", "full_name": "..."}
        """
        try:
            logger.info(f"Resolving municipality: {name_or_code}")
            code = await self._resolve_municipality(name_or_code)

            # Fetch full municipality info
            municipalities = self.client.find_municipality("")
            for muni in municipalities:
                if muni.municipality_reg_num == code:
                    return {
                        "code": muni.municipality_reg_num,
                        "name": muni.municipality_name,
                        "full_name": muni.display_value,
                    }

            raise ValueError(f"Municipality {name_or_code} not found")

        except CadastralAPIError as e:
            logger.error(f"Failed to resolve municipality {name_or_code}: {e}", exc_info=True)
            raise ValueError(f"Could not resolve municipality '{name_or_code}'.") from e

    async def get_parcel_geometry(
        self, parcel_number: str, municipality: str, format: str = "geojson"
    ) -> dict[str, Any] | str:
        """
        Get parcel boundary geometry.

        Downloads and caches GML data if needed, then extracts geometry.

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name or registration code
            format: Output format - "geojson", "wkt", or "dict"

        Returns:
            Geometry data in requested format

        Example:
            >>> await get_parcel_geometry("103/2", "SAVAR", format="geojson")
            {
                "type": "Feature",
                "geometry": {...},
                "properties": {...}
            }
        """
        try:
            logger.info(f"Fetching geometry for {parcel_number} in {municipality} (format: {format})")

            # Resolve municipality
            muni_code = await self._resolve_municipality(municipality)

            # Fetch geometry using SDK
            geometry = self.client.get_parcel_geometry(parcel_number, muni_code)

            # Return in requested format
            if format.lower() == "geojson":
                return geometry.to_geojson()
            elif format.lower() == "wkt":
                return geometry.to_wkt()
            else:  # dict
                return geometry.model_dump(mode="json")

        except CadastralAPIError as e:
            logger.error(f"Failed to fetch geometry for {parcel_number}: {e}", exc_info=True)
            raise ValueError(
                f"Could not retrieve geometry for parcel '{parcel_number}'. "
                f"GIS data may not be available."
            ) from e

    async def list_cadastral_offices(self, filter_name: str | None = None) -> dict[str, Any]:
        """
        List all cadastral offices, optionally filtered by name.

        Args:
            filter_name: Optional filter string to match office names

        Returns:
            Dictionary with list of offices and count

        Example:
            >>> await list_cadastral_offices()
            {
                "offices": [...],
                "count": 15
            }
        """
        try:
            logger.info(f"Listing cadastral offices (filter: {filter_name})")

            offices = self.client.list_cadastral_offices()

            # Apply filter if provided
            if filter_name:
                filter_lower = filter_name.lower()
                offices = [
                    office for office in offices
                    if filter_lower in office.name.lower()
                ]

            return {
                "offices": [office.model_dump(mode="json") for office in offices],
                "count": len(offices),
            }

        except CadastralAPIError as e:
            logger.error(f"Failed to list cadastral offices: {e}", exc_info=True)
            raise ValueError("Could not retrieve cadastral offices.") from e

    async def get_lr_unit(
        self,
        unit_number: str,
        main_book_id: int,
        include_full_details: bool = True,
    ) -> dict[str, Any]:
        """
        Get detailed land registry unit (zemljišnoknjižni uložak) information.

        A land registry unit contains:
        - Sheet A (Popis čestica): All parcels in the unit
        - Sheet B (Vlasnički list): Ownership information with shares
        - Sheet C (Teretni list): Encumbrances (mortgages, liens, easements)

        For condominiums (etažno vlasništvo), each share represents an individual
        apartment/unit with additional fields:
        - condominium_number: Apartment identifier (e.g., "E-16")
        - condominium_descriptions: Detailed descriptions (floor, rooms, area)

        Args:
            unit_number: LR unit number (e.g., "769")
            main_book_id: Main book ID (e.g., 21277)
            include_full_details: Include all sheets (default: True)

        Returns:
            Dictionary with LR unit data including all sheets

        Example:
            >>> await get_lr_unit("769", 21277)
            {
                "lr_unit_number": "769",
                "main_book_name": "SAVAR",
                "ownership_sheet_b": {...},
                "possessory_sheet_a1": {...},
                "encumbrance_sheet_c": {...},
                "summary": {
                    "total_parcels": 3,
                    "total_area_m2": 2621,
                    "num_owners": 5,
                    "has_encumbrances": True,
                    "is_condominium": False
                }
            }
        """
        try:
            logger.info(f"Fetching LR unit {unit_number} from main book {main_book_id}")

            # Fetch LR unit
            lr_unit = self.client.get_lr_unit_detailed(unit_number, main_book_id)

            # Convert to dict
            result = lr_unit.model_dump(mode="json")

            # Add summary (includes is_condominium and condominium_units)
            result["summary"] = lr_unit.summary()

            # Add condominium-specific info if applicable
            if lr_unit.is_condominium():
                result["is_condominium"] = True
                result["condominium_units_count"] = lr_unit.get_condominium_units_count()

            # Optionally simplify if not full details
            if not include_full_details:
                # Keep only summary and basic info
                simple_result = {
                    "lr_unit_number": lr_unit.lr_unit_number,
                    "main_book_name": lr_unit.main_book_name,
                    "institution_name": lr_unit.institution_name,
                    "summary": result["summary"],
                }
                if lr_unit.is_condominium():
                    simple_result["is_condominium"] = True
                    simple_result["condominium_units_count"] = lr_unit.get_condominium_units_count()
                return simple_result

            return result

        except CadastralAPIError as e:
            logger.error(f"Failed to fetch LR unit {unit_number}: {e}", exc_info=True)
            raise ValueError(
                f"Could not retrieve land registry unit '{unit_number}' from main book {main_book_id}. "
                f"Please verify the unit number and main book ID."
            ) from e

    async def get_lr_unit_from_parcel(
        self,
        parcel_number: str,
        municipality: str,
        include_full_details: bool = True,
    ) -> dict[str, Any]:
        """
        Get land registry unit information from a parcel number.

        This is a convenience method that:
        1. Searches for the parcel
        2. Extracts the LR unit reference
        3. Fetches the complete LR unit data

        For condominiums (etažno vlasništvo), the response includes additional
        fields for each ownership share:
        - condominium_number: Apartment identifier (e.g., "E-16")
        - condominium_descriptions: Detailed descriptions (floor, rooms, area)

        Args:
            parcel_number: Cadastral parcel number (e.g., "279/6")
            municipality: Municipality name or code
            include_full_details: Include all sheets (default: True)

        Returns:
            Dictionary with LR unit data including all sheets.
            For condominiums, includes is_condominium and condominium_units_count.

        Example:
            >>> await get_lr_unit_from_parcel("279/6", "SAVAR")
            {
                "lr_unit_number": "769",
                "main_book_name": "SAVAR",
                "ownership_sheet_b": {...},
                "summary": {
                    "is_condominium": False,
                    ...
                },
                ...
            }
        """
        try:
            logger.info(f"Fetching LR unit for parcel {parcel_number} in {municipality}")

            # Resolve municipality
            muni_code = await self._resolve_municipality(municipality)

            # Use API client's convenience method
            lr_unit = self.client.get_lr_unit_from_parcel(parcel_number, muni_code)

            # Convert to dict
            result = lr_unit.model_dump(mode="json")

            # Add summary (includes is_condominium and condominium_units)
            result["summary"] = lr_unit.summary()

            # Add condominium-specific info if applicable
            if lr_unit.is_condominium():
                result["is_condominium"] = True
                result["condominium_units_count"] = lr_unit.get_condominium_units_count()

            # Optionally simplify if not full details
            if not include_full_details:
                simple_result = {
                    "lr_unit_number": lr_unit.lr_unit_number,
                    "main_book_name": lr_unit.main_book_name,
                    "institution_name": lr_unit.institution_name,
                    "summary": result["summary"],
                }
                if lr_unit.is_condominium():
                    simple_result["is_condominium"] = True
                    simple_result["condominium_units_count"] = lr_unit.get_condominium_units_count()
                return simple_result

            return result

        except CadastralAPIError as e:
            logger.error(f"Failed to fetch LR unit from parcel {parcel_number}: {e}", exc_info=True)
            raise ValueError(
                f"Could not retrieve land registry unit for parcel '{parcel_number}'. "
                f"Please verify the parcel number and municipality."
            ) from e

    async def batch_lr_units(
        self,
        lr_units: list[dict[str, Any]],
        include_full_details: bool = True,
    ) -> dict[str, Any]:
        """
        Fetch multiple land registry units in a single operation.

        This is useful for:
        - Processing LR unit references from batch_fetch_parcels output
        - Comparing multiple LR units side by side
        - Analyzing property portfolios with complete ownership info
        - Batch processing of condominium buildings

        For condominiums (etažno vlasništvo), each result includes:
        - is_condominium: True if this is a condominium unit
        - condominium_units_count: Number of individual apartments/units
        - Each ownership share has condominium_number and condominium_descriptions

        Args:
            lr_units: List of LR unit specifications, each with:
                - lr_unit_number: LR unit number (e.g., "769")
                - main_book_id: Main book ID (e.g., 21277)
            include_full_details: Include all sheets (default: True)

        Returns:
            Dictionary with results array and summary statistics:
            - results: List of {status, data/error, lr_unit_number, main_book_id, is_condominium}
            - total: Total LR units processed
            - successful: Number of successful fetches
            - failed: Number of failed fetches
            - condominiums_found: Number of condominium units found

        Example:
            >>> await batch_lr_units([
            ...     {"lr_unit_number": "769", "main_book_id": 21277},
            ...     {"lr_unit_number": "13998", "main_book_id": 30783}
            ... ])
            {
                "results": [...],
                "total": 2,
                "successful": 2,
                "failed": 0,
                "condominiums_found": 1
            }
        """
        try:
            logger.info(f"Batch fetching {len(lr_units)} LR units")

            results: list[dict[str, Any]] = []
            successful = 0
            failed = 0
            condominiums_found = 0

            # Deduplicate LR units by (unit_number, main_book_id)
            seen: set[tuple[str, int]] = set()
            unique_lr_units: list[dict[str, Any]] = []

            for spec in lr_units:
                lr_unit_number = str(spec.get("lr_unit_number", ""))
                main_book_id = spec.get("main_book_id")

                if not lr_unit_number or main_book_id is None:
                    results.append({
                        "status": "error",
                        "error": "lr_unit_number and main_book_id are required",
                        "spec": spec,
                    })
                    failed += 1
                    continue

                key = (lr_unit_number, main_book_id)
                if key in seen:
                    continue  # Skip duplicates
                seen.add(key)
                unique_lr_units.append(spec)

            for spec in unique_lr_units:
                try:
                    lr_unit_number = str(spec["lr_unit_number"])
                    main_book_id = int(spec["main_book_id"])

                    # Fetch LR unit
                    lr_unit = self.client.get_lr_unit_detailed(lr_unit_number, main_book_id)

                    # Convert to dict
                    result_data = lr_unit.model_dump(mode="json")
                    result_data["summary"] = lr_unit.summary()

                    # Check if condominium
                    is_condo = lr_unit.is_condominium()
                    if is_condo:
                        condominiums_found += 1
                        result_data["is_condominium"] = True
                        result_data["condominium_units_count"] = lr_unit.get_condominium_units_count()

                    # Optionally simplify
                    if not include_full_details:
                        result_data = {
                            "lr_unit_number": lr_unit.lr_unit_number,
                            "main_book_name": lr_unit.main_book_name,
                            "institution_name": lr_unit.institution_name,
                            "summary": result_data["summary"],
                        }
                        if is_condo:
                            result_data["is_condominium"] = True
                            result_data["condominium_units_count"] = lr_unit.get_condominium_units_count()

                    result_entry = {
                        "status": "success",
                        "lr_unit_number": lr_unit_number,
                        "main_book_id": main_book_id,
                        "data": result_data,
                    }
                    if is_condo:
                        result_entry["is_condominium"] = True

                    results.append(result_entry)
                    successful += 1

                except Exception as e:
                    logger.error(f"Failed to fetch LR unit {spec}: {e}")
                    results.append({
                        "status": "error",
                        "lr_unit_number": spec.get("lr_unit_number"),
                        "main_book_id": spec.get("main_book_id"),
                        "error": str(e),
                    })
                    failed += 1

            return {
                "results": results,
                "total": len(lr_units),
                "unique": len(unique_lr_units),
                "successful": successful,
                "failed": failed,
                "condominiums_found": condominiums_found,
            }

        except Exception as e:
            logger.error(f"Batch LR unit operation failed: {e}", exc_info=True)
            raise ValueError(f"Batch LR unit operation failed: {e}") from e

    async def _resolve_municipality(self, name_or_code: str) -> str:
        """
        Internal helper to resolve municipality name to code.

        Args:
            name_or_code: Municipality name or code

        Returns:
            Municipality registration code

        Raises:
            ValueError: If municipality cannot be resolved
        """
        # If it looks like a code (all digits), return as-is
        if name_or_code.isdigit():
            return name_or_code

        # Find municipality by name
        municipalities = self.client.find_municipality(name_or_code)

        if not municipalities:
            raise ValueError(f"Municipality '{name_or_code}' not found")

        # Return first match registration number (used for parcel searches)
        return municipalities[0].municipality_reg_num
