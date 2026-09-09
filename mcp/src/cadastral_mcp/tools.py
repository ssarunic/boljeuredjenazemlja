"""MCP Tools - AI-invoked actions that perform operations."""

import logging
from typing import Any

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError
from cadastral_api.models.gis_entities import DEFAULT_MAP_ZOOM

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
            Dictionary with parcel search results including parcel_id and,
            when the municipality's GIS data is available, ``map_url`` (the
            interactive map centred on the parcel). The GIS data is downloaded
            on the first request for a municipality and cached afterwards; if
            it cannot be fetched or the parcel is not in it, ``map_url`` is
            simply omitted and the search still succeeds.

        Example:
            >>> await search_parcel("103/2", "SAVAR")
            {
                "parcel_id": "...",
                "parcel_number": "103/2",
                "municipality": "SAVAR",
                "municipality_code": "334979",
                "map_url": "https://oss.uredjenazemlja.hr/map?center=...",
                "success": True
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
            response: dict[str, Any] = {
                "parcel_id": result.parcel_id,
                "parcel_number": result.parcel_number,
                "municipality": municipality,
                "municipality_code": muni_code,
                "success": True,
            }
            map_url = self._map_url_for(result.parcel_number, muni_code)
            if map_url:
                response["map_url"] = map_url
            return response

        except CadastralAPIError as e:
            logger.error(f"Search failed for {parcel_number} in {municipality}: {e}", exc_info=True)
            raise ValueError(
                f"Could not search for parcel '{parcel_number}'. Please verify the parcel number "
                f"and municipality."
            ) from e

    #: Valid register sources for parcel-level ownership data.
    VALID_SOURCES = ("cadastre", "land_registry", "none")

    @staticmethod
    def _lr_unit_hint(parcel: Any) -> dict[str, Any]:
        """Build a routing hint to the land-registry owners for a parcel.

        The direct ``lr_unit`` may be null while the unit is still reachable via
        parcel links; surface whichever is available so the caller can chain to
        get_lr_unit_from_parcel / batch_lr_units for the true owners.
        """
        ref = None
        derived_from_links = False
        lr_unit = getattr(parcel, "lr_unit", None)
        if lr_unit is not None:
            ref = {
                "lr_unit_number": lr_unit.lr_unit_number,
                "main_book_id": lr_unit.main_book_id,
            }
        else:
            links = getattr(parcel, "lr_units_from_parcel_links", None) or []
            if links:
                ref = {
                    "lr_unit_number": links[0].lr_unit_number,
                    "main_book_id": links[0].main_book_id,
                }
                derived_from_links = True
        return {
            "message": (
                "Cadastre possessors omitted. For registered owners "
                "(vlasnici / vlastovnica B-list), call get_lr_unit_from_parcel "
                "or batch_lr_units with this reference."
            ),
            "lr_unit_ref": ref,
            "in_land_registry": ref is not None,
            "lr_unit_derived_from_links": derived_from_links,
        }

    async def batch_fetch_parcels(
        self,
        parcels: list[dict[str, str]],
        source: str = "cadastre",
    ) -> dict[str, Any]:
        """
        Fetch multiple parcels in a single operation.

        ⚠️ Cadastre possessors (posjedovni list) and land-registry owners
        (vlasnici / vlastovnica / B-list) are DIFFERENT registers and frequently
        list different people. Every person record is tagged with a ``register``
        field so the two can never be confused.

        Register selection (``source``):
        - "cadastre" (default): include the possession sheet (posjedovni list),
          i.e. cadastre POSSESSORS - NOT necessarily the registered owners.
        - "land_registry": omit possessors and instead return, per parcel, the
          land-registry unit reference plus a hint to fetch the true owners via
          get_lr_unit_from_parcel / batch_lr_units.
        - "none": parcel metadata only.

        Args:
            parcels: List of parcel specs, each with parcel_number + municipality
                OR a direct parcel_id.
            source: One of "cadastre", "land_registry", "none".

        Returns:
            Dictionary with results array, summary statistics, and the resolved
            ``source``. Each successful entry also carries ``map_url`` (the
            interactive map centred on the parcel) when the municipality's GIS
            data is available; it is omitted otherwise.
        """
        if source not in self.VALID_SOURCES:
            raise ValueError(
                f"Invalid source '{source}'. Expected one of {self.VALID_SOURCES}."
            )

        try:
            logger.info(f"Batch fetching {len(parcels)} parcels (source={source})")

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
                            raise ValueError(
                                "Each parcel must have either parcel_id "
                                "or both parcel_number and municipality"
                            )

                        search_result = await self.search_parcel(parcel_number, municipality)
                        parcel_id = search_result["parcel_id"]

                    # Fetch detailed info
                    parcel = self.client.get_parcel_info(parcel_id)

                    result_data = parcel.model_dump(mode="json")

                    # Possession sheets are CADASTRE data; only include them when
                    # cadastre possessors were explicitly requested.
                    if source != "cadastre":
                        result_data.pop("possession_sheets", None)
                    if source == "land_registry":
                        result_data["land_registry_hint"] = self._lr_unit_hint(parcel)

                    entry: dict[str, Any] = {
                        "status": "success",
                        "register": source,
                        "cadastre_lr_harmonized": parcel.is_harmonized,
                        "data": result_data,
                    }
                    # Best-effort map link from the cached municipality GIS data
                    map_url = self._map_url_for(
                        parcel.parcel_number, parcel.cad_municipality_reg_num
                    )
                    if map_url:
                        entry["map_url"] = map_url
                    results.append(entry)
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
                "source": source,
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
        self,
        parcel_number: str,
        municipality: str,
        format: str = "geojson",
        zoom: int = DEFAULT_MAP_ZOOM,
    ) -> dict[str, Any] | str:
        """
        Get parcel boundary geometry.

        Downloads and caches GML data if needed, then extracts geometry.

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name or registration code
            format: Output format - "geojson", "wkt", or "dict"
            zoom: Zoom level of the ``map_url`` link (geojson and dict output)

        Returns:
            Geometry data in requested format. "geojson" and "dict" include a
            ``map_url`` pointing the interactive map at the parcel; "wkt" is
            the bare polygon.

        Example:
            >>> await get_parcel_geometry("103/2", "SAVAR", format="geojson")
            {
                "type": "Feature",
                "geometry": {...},
                "properties": {...}
            }
        """
        try:
            logger.info(
                f"Fetching geometry for {parcel_number} in {municipality} (format: {format})"
            )

            # Resolve municipality
            muni_code = await self._resolve_municipality(municipality)

            # Fetch geometry using SDK (None when the parcel is not in the GML)
            geometry = self.client.get_parcel_geometry(parcel_number, muni_code)
            if geometry is None:
                raise ValueError(
                    f"Parcel '{parcel_number}' has no geometry in the GIS data for "
                    f"municipality '{municipality}' ({muni_code}). Check the parcel "
                    f"number; if the cached GIS data may be stale, clear it for this "
                    f"municipality and try again."
                )

            # Return in requested format
            if format.lower() == "geojson":
                return geometry.to_geojson(zoom=zoom)
            elif format.lower() == "wkt":
                return geometry.to_wkt()
            else:  # dict
                data = geometry.model_dump(mode="json")
                data["map_url"] = geometry.map_url(zoom)
                return data

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

    #: Valid detail levels for land-registry unit output.
    VALID_DETAIL = ("summary", "ownership", "full")

    @staticmethod
    def _ownership_rows(
        lr_unit: Any, owners_limit: int | None
    ) -> tuple[list[dict[str, Any]], int, bool]:
        """Owner rows for an LR unit, capped at owners_limit.

        Returns (rows, total_owners, truncated). The canonical row shape comes
        from OwnershipSheetB.owner_rows() (shared with the CLI).
        """
        rows = lr_unit.ownership_sheet_b.owner_rows()
        total = len(rows)
        truncated = owners_limit is not None and total > owners_limit
        if truncated:
            rows = rows[:owners_limit]
        return rows, total, truncated

    @classmethod
    def _shape_lr_unit(
        cls, lr_unit: Any, detail: str, owners_limit: int | None
    ) -> dict[str, Any]:
        """Shape an LR unit for output at the requested detail level.

        - "summary": identity + summary statistics only.
        - "ownership" (default): B-list owners (with structured shares) + summary;
          drops geometry, Sheet A2, the C-sheet, and raw internal IDs.
        - "full": every sheet (raw model dump) + summary.
        """
        if detail not in cls.VALID_DETAIL:
            raise ValueError(
                f"Invalid detail '{detail}'. Expected one of {cls.VALID_DETAIL}."
            )
        summary = lr_unit.summary()
        is_condo = lr_unit.is_condominium()

        if detail == "full":
            result = lr_unit.model_dump(mode="json")
            result["summary"] = summary
            if is_condo:
                result["is_condominium"] = True
                result["condominium_units_count"] = lr_unit.get_condominium_units_count()
            return result

        if detail == "summary":
            result = {
                "lr_unit_number": lr_unit.lr_unit_number,
                "main_book_name": lr_unit.main_book_name,
                "institution_name": lr_unit.institution_name,
                "lr_unit_derived_from_links": lr_unit.lr_unit_derived_from_links,
                "summary": summary,
            }
            if is_condo:
                result["is_condominium"] = True
                result["condominium_units_count"] = lr_unit.get_condominium_units_count()
            return result

        # detail == "ownership"
        owners, total, truncated = cls._ownership_rows(lr_unit, owners_limit)
        return {
            "lr_unit_number": lr_unit.lr_unit_number,
            "main_book_id": lr_unit.main_book_id,
            "main_book_name": lr_unit.main_book_name,
            "institution_name": lr_unit.institution_name,
            "in_land_registry": True,
            "lr_unit_derived_from_links": lr_unit.lr_unit_derived_from_links,
            "is_condominium": is_condo,
            "owners": owners,
            "total_owners": total,
            "owners_truncated": truncated,
            "summary": summary,
        }

    def _plombe_detail(self, lr_unit: Any) -> dict[str, Any]:
        """Resolve pending-plomba detail for a unit, shaped for JSON output.

        Returns a map of file_number -> status detail for the land-registry
        plombe that resolved (cadastre/unresolvable plombe are omitted, but they
        remain visible in the unit's summary ``pending_plombe`` list).
        """
        details = self.client.get_plombe_details(lr_unit)
        return {
            file_number: status.model_dump(mode="json", by_alias=False)
            for file_number, status in details.items()
        }

    async def get_lr_unit(
        self,
        unit_number: str,
        main_book_id: int,
        detail: str = "ownership",
        owners_limit: int | None = None,
        include_plombe_detail: bool = False,
    ) -> dict[str, Any]:
        """
        Get land registry unit (zemljišnoknjižni uložak) information.

        A land registry unit contains:
        - Sheet A (Popis čestica): All parcels in the unit
        - Sheet B (Vlasnički list): Ownership (vlasnici) with shares
        - Sheet C (Teretni list): Encumbrances (mortgages, liens, easements)

        For condominiums (etažno vlasništvo), each share represents an individual
        apartment/unit (condominium_number, condominium_descriptions).

        Args:
            unit_number: LR unit number (e.g., "769")
            main_book_id: Main book ID (e.g., 21277)
            detail: "summary" | "ownership" | "full" (default "ownership" -
                B-list owners with structured shares + summary, no geometry/C-sheet).
            owners_limit: Cap the number of owner rows returned (ownership detail);
                total_owners and owners_truncated report the full count.

        Returns:
            Dictionary shaped per ``detail``; owners carry a structured
            ``share`` ({num, den, decimal}) and a ``register`` tag.
        """
        if detail not in self.VALID_DETAIL:
            raise ValueError(
                f"Invalid detail '{detail}'. Expected one of {self.VALID_DETAIL}."
            )

        try:
            logger.info(
                f"Fetching LR unit {unit_number} from main book {main_book_id} (detail={detail})"
            )
            lr_unit = self.client.get_lr_unit_detailed(unit_number, main_book_id)
            result = self._shape_lr_unit(lr_unit, detail, owners_limit)
            if include_plombe_detail and lr_unit.has_pending_plombe():
                result["plombe_detail"] = self._plombe_detail(lr_unit)
            return result

        except CadastralAPIError as e:
            logger.error(f"Failed to fetch LR unit {unit_number}: {e}", exc_info=True)
            raise ValueError(
                f"Could not retrieve land registry unit '{unit_number}' "
                f"from main book {main_book_id}. "
                f"Please verify the unit number and main book ID."
            ) from e

    async def get_lr_unit_from_parcel(
        self,
        parcel_number: str,
        municipality: str,
        detail: str = "ownership",
        owners_limit: int | None = None,
        include_plombe_detail: bool = False,
    ) -> dict[str, Any]:
        """
        Get the land registry unit (and registered owners) for a parcel.

        Convenience method that searches the parcel, resolves its LR unit
        reference - falling back to parcel links when the parcel has no direct
        lr_unit - and fetches the unit. The result reports
        ``lr_unit_derived_from_links`` so callers know how it was resolved.

        Use this for "vlasnik" / "prema zemljišnim knjigama" questions; it
        returns true land-registry owners (vlastovnica / B-list), not cadastre
        possessors.

        Args:
            parcel_number: Cadastral parcel number (e.g., "279/6")
            municipality: Municipality name or code
            detail: "summary" | "ownership" | "full" (default "ownership").
            owners_limit: Cap owner rows (ownership detail); total_owners and
                owners_truncated report the full count.

        Returns:
            Dictionary shaped per ``detail``; owners carry a structured
            ``share`` and a ``register`` tag.
        """
        if detail not in self.VALID_DETAIL:
            raise ValueError(
                f"Invalid detail '{detail}'. Expected one of {self.VALID_DETAIL}."
            )

        try:
            logger.info(
                f"Fetching LR unit for parcel {parcel_number} in {municipality} (detail={detail})"
            )
            muni_code = await self._resolve_municipality(municipality)
            lr_unit = self.client.get_lr_unit_from_parcel(parcel_number, muni_code)
            result = self._shape_lr_unit(lr_unit, detail, owners_limit)
            if include_plombe_detail and lr_unit.has_pending_plombe():
                result["plombe_detail"] = self._plombe_detail(lr_unit)
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
        detail: str = "ownership",
        owners_limit: int | None = None,
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
            detail: "summary" | "ownership" | "full" (default "ownership"),
                applied to every unit.
            owners_limit: Cap owner rows per unit (ownership detail).

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
        if detail not in self.VALID_DETAIL:
            raise ValueError(
                f"Invalid detail '{detail}'. Expected one of {self.VALID_DETAIL}."
            )

        try:
            logger.info(f"Batch fetching {len(lr_units)} LR units (detail={detail})")

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

                    # Shape per requested detail level
                    result_data = self._shape_lr_unit(lr_unit, detail, owners_limit)

                    is_condo = lr_unit.is_condominium()
                    if is_condo:
                        condominiums_found += 1

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

    def _map_url_for(self, parcel_number: str, muni_code: str) -> str | None:
        """
        Best-effort interactive map link for a parcel.

        Uses the cached municipality GIS data (downloaded on first use). Any
        failure (download, parse, parcel not in the GML) is logged and yields
        None so that the calling tool still returns its main result.
        """
        try:
            geometry = self.client.get_parcel_geometry(parcel_number, muni_code)
        except Exception as e:  # noqa: BLE001 - the link is optional
            logger.warning(f"No map link for {parcel_number} in {muni_code}: {e}")
            return None
        return geometry.map_url() if geometry is not None else None

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
