"""MCP Tools - AI-invoked actions that perform operations."""

import logging
from typing import Any

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError
from cadastral_api.models.entities import ParcelSearchResult

from .config import config

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

            # Step 2: Search for parcel
            results = self.client.search_parcels(parcel_number, muni_code)

            if not results:
                raise ValueError(
                    f"No parcels found matching '{parcel_number}' in {municipality}"
                )

            # Return first match
            result = results[0]
            return {
                "parcel_id": result.key1,
                "parcel_number": result.parcel_number,
                "municipality": result.municipality_name,
                "address": result.address or "N/A",
                "area": result.area or "N/A",
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
                    parcel = self.client.get_parcel_by_id(parcel_id)

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
            municipalities = self.client.search_municipalities("")
            for muni in municipalities:
                if muni.key1 == code:
                    return {
                        "code": muni.key1,
                        "name": muni.name,
                        "full_name": muni.full_name,
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
        - Sheet A (Posjedovni list): All parcels in the unit
        - Sheet B (Vlasnički list): Ownership information with shares
        - Sheet C (Teretni list): Encumbrances (mortgages, liens, easements)

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
                "possession_sheet_a1": {...},
                "encumbrance_sheet_c": {...},
                "summary": {
                    "total_parcels": 3,
                    "total_area_m2": 2621,
                    "num_owners": 5,
                    "has_encumbrances": True
                }
            }
        """
        try:
            logger.info(f"Fetching LR unit {unit_number} from main book {main_book_id}")

            # Fetch LR unit
            lr_unit = self.client.get_lr_unit_detailed(unit_number, main_book_id)

            # Convert to dict
            result = lr_unit.model_dump(mode="json")

            # Add summary
            result["summary"] = lr_unit.summary()

            # Optionally simplify if not full details
            if not include_full_details:
                # Keep only summary and basic info
                return {
                    "lr_unit_number": lr_unit.lr_unit_number,
                    "main_book_name": lr_unit.main_book_name,
                    "institution_name": lr_unit.institution_name,
                    "summary": result["summary"],
                }

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

        Args:
            parcel_number: Cadastral parcel number (e.g., "279/6")
            municipality: Municipality name or code
            include_full_details: Include all sheets (default: True)

        Returns:
            Dictionary with LR unit data including all sheets

        Example:
            >>> await get_lr_unit_from_parcel("279/6", "SAVAR")
            {
                "lr_unit_number": "769",
                "main_book_name": "SAVAR",
                "ownership_sheet_b": {...},
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

            # Add summary
            result["summary"] = lr_unit.summary()

            # Optionally simplify if not full details
            if not include_full_details:
                return {
                    "lr_unit_number": lr_unit.lr_unit_number,
                    "main_book_name": lr_unit.main_book_name,
                    "institution_name": lr_unit.institution_name,
                    "summary": result["summary"],
                }

            return result

        except CadastralAPIError as e:
            logger.error(f"Failed to fetch LR unit from parcel {parcel_number}: {e}", exc_info=True)
            raise ValueError(
                f"Could not retrieve land registry unit for parcel '{parcel_number}'. "
                f"Please verify the parcel number and municipality."
            ) from e

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

        # Search for municipality by name
        municipalities = self.client.search_municipalities(name_or_code)

        if not municipalities:
            raise ValueError(f"Municipality '{name_or_code}' not found")

        # Return first match code
        return municipalities[0].key1
