"""MCP Tools - AI-invoked actions that perform operations."""

import json
import logging
from typing import Any

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError
from cadastral_api.models.gis_entities import DEFAULT_MAP_ZOOM
from cadastral_api.utils import is_building_parcel_number, normalize_parcel_number
from pydantic import BaseModel, ConfigDict, model_validator

logger = logging.getLogger(__name__)


#: The six generic keys every ``/search-*`` record carries. The typed models
#: expose them under meaningful names (``main_book_id``, ``sheet_number`` ...),
#: so the raw keys are dropped from tool results to avoid two spellings of
#: one value.
RAW_SEARCH_KEYS = frozenset({"key1", "value1", "key2", "value2", "value3", "display_value1"})


def search_record(model: Any) -> dict[str, Any]:
    """A search-result model as the agent should see it: named fields only."""
    record = model.model_dump(mode="json", exclude=RAW_SEARCH_KEYS)
    if not record.get("source_fields"):
        record.pop("source_fields", None)
    return record


class ParcelRef(BaseModel):
    """One parcel to fetch: by ``parcel_id``, or by ``parcel_number`` + ``municipality``."""

    model_config = ConfigDict(extra="forbid")

    # Parcel ids are integers everywhere in the SDK; a numeric string is accepted too.
    parcel_id: int | None = None
    parcel_number: str | None = None
    municipality: str | None = None

    @model_validator(mode="after")
    def _complete(self) -> "ParcelRef":
        if self.parcel_id is None and not (self.parcel_number and self.municipality):
            raise ValueError(
                "a parcel reference needs parcel_id, or parcel_number and municipality"
            )
        return self


class LRUnitRef(BaseModel):
    """One land registry unit to fetch, named in one of three ways.

    - ``lr_unit_number`` + ``main_book_id`` (the direct reference);
    - ``lr_unit_number`` + ``main_book_name`` (the glavna knjiga name, resolved
      through the main-book search);
    - ``parcel_number`` + ``municipality`` (the unit the parcel belongs to,
      resolved through parcel links when the parcel has no direct unit).
    """

    model_config = ConfigDict(extra="forbid")

    # Unit numbers are strings ("769", "374/A") but are often typed as numbers.
    lr_unit_number: str | int | None = None
    main_book_id: int | None = None
    main_book_name: str | None = None
    parcel_number: str | None = None
    municipality: str | None = None

    @model_validator(mode="after")
    def _complete(self) -> "LRUnitRef":
        if self.lr_unit_number is not None:
            self.lr_unit_number = str(self.lr_unit_number)
        by_unit = bool(self.lr_unit_number) and (
            self.main_book_id is not None or bool(self.main_book_name)
        )
        by_parcel = bool(self.parcel_number) and bool(self.municipality)
        if by_unit == by_parcel:
            raise ValueError(
                "a unit reference is lr_unit_number with main_book_id or main_book_name, "
                "or parcel_number with municipality (not both, not neither)"
            )
        return self

    @property
    def by_parcel(self) -> bool:
        return bool(self.parcel_number)

    def describe(self) -> str:
        if self.by_parcel:
            return f"parcel {self.parcel_number} in {self.municipality}"
        return f"unit {self.lr_unit_number} in main book {self.main_book_id or self.main_book_name}"


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

            The server matches on a substring, so a number that does not exist
            can still return a longer one ("973" -> 973/1). ``exact_match``
            says whether the returned ``parcel_number`` is the requested
            ``requested_parcel_number``; when it is not, ``match_note`` and
            ``other_matches`` describe what was found instead, and say whether
            the fallback begins with the requested number or merely contains
            it. A building parcel never falls back to a land parcel, or the
            other way round.

        Example:
            >>> await search_parcel("103/2", "SAVAR")
            {
                "parcel_id": "...",
                "parcel_number": "103/2",
                "requested_parcel_number": "103/2",
                "exact_match": True,
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

            # Step 2: Find parcel. The server matches on a substring, so prefer
            # the exact number (in the API spelling: "35/1.ZGR" -> "*35/1").
            wanted = normalize_parcel_number(parcel_number)
            results = self.client.find_parcel(wanted, muni_code)

            if not results:
                raise ValueError(
                    f"No parcels found matching '{parcel_number}' in {municipality}"
                )

            result, kind, siblings = self._pick_parcel_match(results, wanted, municipality)
            exact_match = kind == "exact"
            response: dict[str, Any] = {
                "parcel_id": result.parcel_id,
                "parcel_number": result.parcel_number,
                "requested_parcel_number": wanted,
                "exact_match": exact_match,
                "is_building_parcel": result.is_building_parcel,
                "municipality": municipality,
                "municipality_code": muni_code,
                "success": True,
            }
            if not exact_match:
                # The server matches on a substring, so "973" can come back as
                # 973/1 only. Say so instead of passing a different parcel off
                # as the one that was asked for.
                response["match_note"] = self._match_note(wanted, result.parcel_number, kind)
                response["other_matches"] = [
                    r.parcel_number for r in siblings
                ][: self.MAX_OTHER_MATCHES]
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

    #: How many further matches to name when the match is not exact.
    MAX_OTHER_MATCHES = 10

    @staticmethod
    def _match_note(wanted: str, found: str, kind: str) -> str:
        """Explain, in the response, why a different parcel came back."""
        if kind == "prefix":
            how = f"'{found}' is the first parcel number that begins with it"
        else:
            how = (
                f"'{found}' merely contains it: no parcel number in this cadastral "
                f"municipality begins with '{wanted}'"
            )
        return (
            f"No parcel numbered '{wanted}' exists in this cadastral municipality. "
            f"{how}; confirm it is the parcel you meant."
        )

    @classmethod
    def _pick_parcel_match(
        cls, results: list[Any], wanted: str, municipality: str
    ) -> tuple[Any, str, list[Any]]:
        """Choose which search result answers ``wanted``, and say how it matched.

        The server matches on a substring, so "*56/" (before it was normalised)
        returned 56/1, 56/2, 256/1, 656/1 ... Two rules keep a fallback from
        answering with a parcel that cannot be the one meant:

        - a building parcel ("*56") never falls back to a land parcel, nor the
          other way round: the two are separate numbering series;
        - a prefix match is preferred over a mere substring match, and the
          response says which of the two happened.

        Returns (result, kind, other candidates of the same kind), where kind is
        "exact", "prefix" or "contains".
        """
        wants_building = is_building_parcel_number(wanted)
        candidates = [
            r for r in results
            if is_building_parcel_number(r.parcel_number) == wants_building
        ]
        if not candidates:
            numbers = [r.parcel_number for r in results]
            if not wants_building and f"*{wanted}" in numbers:
                # The everyday confusion: the number belongs to the building
                # parcel alone. Name the spelling that asks for it.
                raise ValueError(
                    f"There is no land parcel {wanted} in {municipality}, only the "
                    f"building parcel zgr. {wanted}. Ask for it as '{wanted} ZGR'."
                )
            asked, other = (
                ("building parcel", "land") if wants_building else ("land parcel", "building")
            )
            found = ", ".join(numbers[: cls.MAX_OTHER_MATCHES])
            raise ValueError(
                f"No {asked} matching '{wanted}' in {municipality}; the search returned "
                f"only {other} parcels ({found}), which are a separate numbering series."
            )

        exact = next((r for r in candidates if r.parcel_number == wanted), None)
        if exact is not None:
            return exact, "exact", []

        prefixed = [r for r in candidates if r.parcel_number.startswith(wanted)]
        pool = prefixed or candidates
        kind = "prefix" if prefixed else "contains"
        return pool[0], kind, pool[1:]

    @staticmethod
    def _lr_unit_hint(parcel: Any) -> dict[str, Any]:
        """Build a routing hint to the land-registry owners for a parcel.

        The direct ``lr_unit`` may be null while the unit is still reachable via
        parcel links; surface whichever is available so the caller can chain to
        get_lr_unit for the true owners.
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
                "(vlasnici / vlastovnica B-list), call get_lr_unit with this "
                "reference (or with the parcel_number and municipality)."
            ),
            "lr_unit_ref": ref,
            "in_land_registry": ref is not None,
            "lr_unit_derived_from_links": derived_from_links,
        }

    async def get_parcel(
        self,
        parcels: list[ParcelRef | dict[str, Any]],
        source: str = "cadastre",
    ) -> dict[str, Any]:
        """
        Fetch the detailed cadastre record of one or more parcels.

        ⚠️ Cadastre possessors (posjedovni list) and land-registry owners
        (vlasnici / vlastovnica / B-list) are DIFFERENT registers and frequently
        list different people. Every person record is tagged with a ``register``
        field so the two can never be confused.

        Register selection (``source``):
        - "cadastre" (default): include the possession sheet (posjedovni list),
          i.e. cadastre POSSESSORS - NOT necessarily the registered owners.
        - "land_registry": omit possessors and instead return, per parcel, the
          land-registry unit reference plus a hint to fetch the true owners via
          get_lr_unit.
        - "none": parcel metadata only.

        Args:
            parcels: One or more parcel references (``ParcelRef``): parcel_id, or
                parcel_number + municipality.
            source: One of "cadastre", "land_registry", "none".

        Returns:
            Dictionary with ``results`` (one entry per reference, in order),
            counts, and the resolved ``source``. Each successful entry also
            carries ``map_url`` (the interactive map centred on the parcel)
            when the municipality's GIS data is available; it is omitted
            otherwise. An entry resolved from a fallback match rather than the
            exact number carries ``exact_match`` False with
            ``requested_parcel_number`` and ``match_note``.
        """
        if source not in self.VALID_SOURCES:
            raise ValueError(
                f"Invalid source '{source}'. Expected one of {self.VALID_SOURCES}."
            )
        if not parcels:
            raise ValueError("Give at least one parcel reference.")

        logger.info(f"Fetching {len(parcels)} parcel(s) (source={source})")
        results: list[dict[str, Any]] = []
        for spec in parcels:
            try:
                ref = spec if isinstance(spec, ParcelRef) else ParcelRef.model_validate(spec)
            except ValueError as e:
                results.append({"status": "error", "error": str(e), "ref": spec})
                continue
            try:
                results.append(await self._get_one_parcel(ref, source))
            except Exception as e:  # noqa: BLE001 - recorded per item on purpose
                logger.error(f"Failed to fetch parcel {ref}: {e}")
                results.append({
                    "status": "error",
                    "error": str(e),
                    "ref": ref.model_dump(exclude_none=True),
                })

        successful = sum(1 for r in results if r["status"] == "success")
        return {
            "results": results,
            "total": len(parcels),
            "successful": successful,
            "failed": len(results) - successful,
            "source": source,
        }

    async def _get_one_parcel(self, ref: ParcelRef, source: str) -> dict[str, Any]:
        """The ``results`` entry of one parcel reference (raises on failure)."""
        search_result: dict[str, Any] | None = None
        if ref.parcel_id is not None:
            parcel_id = ref.parcel_id
        else:
            assert ref.parcel_number is not None and ref.municipality is not None
            search_result = await self.search_parcel(ref.parcel_number, ref.municipality)
            parcel_id = search_result["parcel_id"]

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
            "ref": ref.model_dump(exclude_none=True),
            "register": source,
            "cadastre_lr_harmonized": parcel.is_harmonized,
            "data": result_data,
        }
        # A fallback match is not the parcel that was asked for; carry the
        # warning out of search_parcel rather than losing it here.
        if search_result is not None and not search_result["exact_match"]:
            entry["exact_match"] = False
            entry["requested_parcel_number"] = search_result["requested_parcel_number"]
            entry["match_note"] = search_result["match_note"]
        # Best-effort map link from the cached municipality GIS data
        map_url = self._map_url_for(parcel.parcel_number, parcel.cad_municipality_reg_num)
        if map_url:
            entry["map_url"] = map_url
        return entry

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

    #: Characters of JSON a full dump may reach before it is refused. A large
    #: condominium runs to hundreds of shares, each with its own registration
    #: entry, and overruns an agent's context long before it is read; refusing
    #: with a way forward beats returning something unusable. The ceiling is
    #: well under a typical MCP client's per-response limit, since a response
    #: the client truncates is worse than one it never asked for.
    MAX_FULL_RESPONSE_CHARS = 50_000

    @staticmethod
    def _sub_shares(share: dict[str, Any]) -> list[dict[str, Any]]:
        """The nested share dicts of a share (an apartment's co-owners)."""
        nested = share.get("sub_shares_and_entries") or []
        return [item for item in nested if isinstance(item, dict) and "owners" in item]

    @classmethod
    def _count_owner_records(cls, shares: list[dict[str, Any]]) -> int:
        """Owner records held by these shares and their sub-shares."""
        total = 0
        for share in shares:
            total += len(share.get("owners") or [])
            total += cls._count_owner_records(cls._sub_shares(share))
        return total

    @classmethod
    def _cap_dumped_owners(
        cls, dump: dict[str, Any], limit: int | None
    ) -> tuple[int, bool, int]:
        """Cap sheet B inside a full dump; return (total, truncated, shares_omitted).

        Walks the shares of sheet B in document order (recursing into the
        sub-shares that hold an apartment's co-owners) and keeps them until
        ``limit`` owner records have been taken; the shares after that are
        dropped whole. Dropping the owners alone is not enough: a condominium
        keeps its weight in the shares themselves, each with its own
        description and registration entry, so a 85-share unit still serialises
        to 135,000 characters with every owner removed.

        Unlike the "ownership" view, which lists active shares only, ``total``
        counts every owner record in the dump. ``limit`` of None only counts.
        """
        sheet = dump.get("ownership_sheet_b") or {}
        shares = sheet.get("lr_unit_shares") or []
        total = cls._count_owner_records(shares)
        if limit is None:
            return total, False, 0

        omitted = 0

        def take(shares: list[dict[str, Any]], budget: int) -> tuple[list[dict[str, Any]], int]:
            nonlocal omitted
            kept: list[dict[str, Any]] = []
            for index, share in enumerate(shares):
                if budget <= 0:
                    rest = shares[index:]
                    omitted += len(rest) + sum(
                        cls._count_shares(cls._sub_shares(item)) for item in rest
                    )
                    break
                owners = share.get("owners") or []
                share["owners"] = owners[:budget]
                budget -= len(share["owners"])
                nested = cls._sub_shares(share)
                if nested:
                    kept_nested, budget = take(nested, budget)
                    keep = set(id(item) for item in kept_nested)
                    share["sub_shares_and_entries"] = [
                        item
                        for item in share["sub_shares_and_entries"]
                        if not (isinstance(item, dict) and "owners" in item) or id(item) in keep
                    ]
                kept.append(share)
            return kept, budget

        sheet["lr_unit_shares"], _ = take(shares, limit)
        return total, total > limit, omitted

    @classmethod
    def _count_shares(cls, shares: list[dict[str, Any]]) -> int:
        """Number of share dicts here and below (for the omitted-share count)."""
        return sum(1 + cls._count_shares(cls._sub_shares(share)) for share in shares)

    @classmethod
    def _shape_lr_unit(
        cls, lr_unit: Any, detail: str, owners_limit: int | None
    ) -> dict[str, Any]:
        """Shape an LR unit for output at the requested detail level.

        - "summary": identity + summary statistics only.
        - "ownership" (default): B-list owners (with structured shares) + summary;
          drops geometry, Sheet A2, the C-sheet, and raw internal IDs.
        - "full": every sheet (raw model dump) + summary, with sheet B cut off
          at ``owners_limit`` owner records: the shares past it are dropped
          whole (counted in ``shares_omitted``), since a condominium's weight
          is in the shares themselves, not only in their owners.
        """
        if detail not in cls.VALID_DETAIL:
            raise ValueError(
                f"Invalid detail '{detail}'. Expected one of {cls.VALID_DETAIL}."
            )
        summary = lr_unit.summary()
        is_condo = lr_unit.is_condominium()

        if detail == "full":
            result = lr_unit.model_dump(mode="json")
            total, truncated, omitted = cls._cap_dumped_owners(result, owners_limit)
            result["total_owners"] = total
            result["owners_truncated"] = truncated
            if omitted:
                # The shares past the owner budget were dropped whole, not
                # merely emptied; say how many so the count is not read as the
                # unit's full sheet B.
                result["shares_omitted"] = omitted
            result["summary"] = summary
            if is_condo:
                result["is_condominium"] = True
                result["condominium_units_count"] = lr_unit.get_condominium_units_count()
            cls._check_full_size(result, lr_unit, total, owners_limit)
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

        # detail == "ownership". Each owner row carries ``entry`` (the
        # registration entry that put the owner on the share: order number,
        # receipt date, diary number, action type); ``share_entries`` are the
        # annotations (ZABILJEŽBA) registered on individual shares.
        owners, total, truncated = cls._ownership_rows(lr_unit, owners_limit)
        return {
            "lr_unit_number": lr_unit.lr_unit_number,
            "main_book_id": lr_unit.main_book_id,
            "main_book_name": lr_unit.main_book_name,
            "institution_name": lr_unit.institution_name,
            "in_land_registry": True,
            "lr_unit_derived_from_links": lr_unit.lr_unit_derived_from_links,
            "sheet_a1_source_key": lr_unit.sheet_a1_source_key,
            "is_condominium": is_condo,
            "owners": owners,
            "total_owners": total,
            "owners_truncated": truncated,
            "share_entries": lr_unit.ownership_sheet_b.share_entry_rows(),
            "summary": summary,
        }

    @classmethod
    def _check_full_size(
        cls, result: dict[str, Any], lr_unit: Any, total_owners: int, owners_limit: int | None
    ) -> None:
        """Refuse a full dump that is too large to be read, with a way forward.

        A unit with hundreds of shares serialises to hundreds of kilobytes even
        after the owners are capped, because every share keeps its own
        description and registration entry. Returning it silently overruns the
        caller's context; this says so and names the smaller options.
        """
        size = len(json.dumps(result, ensure_ascii=False))
        if size <= cls.MAX_FULL_RESPONSE_CHARS:
            return
        sheet, sheet_size = cls._largest_sheet(result)
        options = [
            'detail="ownership" for the owners without the other sheets',
            'detail="summary" for the totals alone',
        ]
        # owners_limit only helps while sheet B is what makes the dump large;
        # on a unit whose weight is in the encumbrances it changes nothing.
        if owners_limit is None and total_owners > 0 and sheet == "ownership_sheet_b":
            options.insert(0, "owners_limit (e.g. owners_limit=10) to cap the owner records")
        raise ValueError(
            f"A full dump of land-registry unit {lr_unit.lr_unit_number} is "
            f"{size:,} characters ({total_owners} owner records; the largest part is "
            f"{sheet} at {sheet_size:,} characters), too large to return in one "
            f"response. Use {', or '.join(options)}."
        )

    @staticmethod
    def _largest_sheet(result: dict[str, Any]) -> tuple[str, int]:
        """The sheet that makes a full dump large, and its size in characters."""
        sizes = {
            key: len(json.dumps(value, ensure_ascii=False))
            for key, value in result.items()
            if key.startswith(("ownership_sheet", "encumbrance_sheet", "possessory_sheet"))
        }
        if not sizes:
            return "the unit", 0
        return max(sizes.items(), key=lambda item: item[1])

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
        units: list[LRUnitRef | dict[str, Any]],
        detail: str = "ownership",
        owners_limit: int | None = None,
        include_plombe_detail: bool = False,
    ) -> dict[str, Any]:
        """
        Get one or more land registry units (zemljišnoknjižni uložak).

        Each reference (``LRUnitRef``) names a unit directly (lr_unit_number +
        main_book_id, or + main_book_name) or through a parcel (parcel_number +
        municipality; the unit is resolved through parcel links when the parcel
        has no direct unit, and the entry reports ``lr_unit_derived_from_links``).

        A unit that several references resolve to is fetched and returned once;
        the later references get ``status`` "duplicate" and ``same_unit_as``,
        the index of the entry that carries the data.

        Args:
            units: One or more unit references.
            detail: "summary" | "ownership" | "full" (default "ownership"),
                applied to every unit.
            owners_limit: Cap owner records per unit ("ownership" and "full");
                total_owners and owners_truncated report the full count.
            include_plombe_detail: Resolve what each pending plomba is (request
                type, status, dates) into a ``plombe_detail`` map per unit; one
                extra request per plomba.

        Returns:
            Dictionary with ``results`` (one entry per reference, in order:
            status, ref, lr_unit_number, main_book_id, data | error), ``total``,
            ``unique`` (units actually fetched), ``successful``, ``failed``,
            ``duplicates`` and ``condominiums_found``. Every reference has
            exactly one of the three statuses, so
            ``successful + failed + duplicates == total``; ``successful`` counts
            fetched units, i.e. equals ``unique``.
        """
        if detail not in self.VALID_DETAIL:
            raise ValueError(
                f"Invalid detail '{detail}'. Expected one of {self.VALID_DETAIL}."
            )
        if not units:
            raise ValueError("Give at least one land registry unit reference.")

        logger.info(f"Fetching {len(units)} land registry unit reference(s) (detail={detail})")
        results: list[dict[str, Any]] = []
        fetched: dict[tuple[str, int], int] = {}  # (unit number, main book id) -> index
        by_name: dict[tuple[str, str], int] = {}  # (unit number, MAIN BOOK NAME) -> index
        condominiums_found = 0

        for spec in units:
            try:
                ref = spec if isinstance(spec, LRUnitRef) else LRUnitRef.model_validate(spec)
            except ValueError as e:
                results.append({"status": "error", "error": str(e), "ref": spec})
                continue
            entry: dict[str, Any] = {"ref": ref.model_dump(exclude_none=True)}

            # A direct reference that was already fetched needs no request.
            known = None
            if not ref.by_parcel:
                assert ref.lr_unit_number is not None
                if ref.main_book_id is not None:
                    known = fetched.get((ref.lr_unit_number, ref.main_book_id))
                elif ref.main_book_name:
                    known = by_name.get((ref.lr_unit_number, ref.main_book_name.upper()))
            if known is not None:
                entry.update(
                    status="duplicate",
                    same_unit_as=known,
                    lr_unit_number=results[known]["lr_unit_number"],
                    main_book_id=results[known]["main_book_id"],
                )
                results.append(entry)
                continue

            try:
                lr_unit = self._fetch_lr_unit(ref)
            except Exception as e:  # noqa: BLE001 - recorded per item on purpose
                logger.error(f"Failed to fetch {ref.describe()}: {e}")
                entry.update(status="error", error=str(e))
                results.append(entry)
                continue

            key = (str(lr_unit.lr_unit_number), int(lr_unit.main_book_id))
            entry["lr_unit_number"], entry["main_book_id"] = key
            if ref.by_parcel:
                entry["lr_unit_derived_from_links"] = lr_unit.lr_unit_derived_from_links
            if key in fetched:
                entry.update(status="duplicate", same_unit_as=fetched[key])
                results.append(entry)
                continue

            try:
                data = self._shape_lr_unit(lr_unit, detail, owners_limit)
                if include_plombe_detail and lr_unit.has_pending_plombe():
                    data["plombe_detail"] = self._plombe_detail(lr_unit)
            except Exception as e:  # noqa: BLE001 - e.g. a full dump too large to return
                entry.update(status="error", error=str(e))
                results.append(entry)
                continue

            fetched[key] = len(results)
            if ref.main_book_name:
                by_name[(key[0], ref.main_book_name.upper())] = len(results)
            entry.update(status="success", data=data)
            if lr_unit.is_condominium():
                entry["is_condominium"] = True
                condominiums_found += 1
            results.append(entry)

        successful = sum(1 for r in results if r["status"] == "success")
        failed = sum(1 for r in results if r["status"] == "error")
        duplicates = sum(1 for r in results if r["status"] == "duplicate")
        # Every reference lands in exactly one of the three; clients can check
        # successful + failed + duplicates == total.
        return {
            "results": results,
            "total": len(units),
            "unique": len(fetched),
            "successful": successful,
            "failed": failed,
            "duplicates": duplicates,
            "condominiums_found": condominiums_found,
        }

    def _fetch_lr_unit(self, ref: LRUnitRef) -> Any:
        """Fetch the unit a reference names; errors carry a message for the agent."""
        try:
            if ref.by_parcel:
                assert ref.parcel_number is not None and ref.municipality is not None
                muni_code = self._resolve_municipality_sync(ref.municipality)
                return self.client.get_lr_unit_from_parcel(ref.parcel_number, muni_code)
            assert ref.lr_unit_number is not None
            return self.client.get_lr_unit_detailed(
                ref.lr_unit_number, ref.main_book_id, main_book_name=ref.main_book_name
            )
        except CadastralAPIError as e:
            raise ValueError(
                f"Could not retrieve the land registry unit for {ref.describe()}: {e}"
            ) from e

    async def find_main_book(
        self,
        search: str | None = None,
        office_id: str | int | None = None,
        institution_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Find land-registry main books (glavne knjige) by name, office or institution.

        The main book id is what ``get_lr_unit`` needs; searching a cadastral
        municipality name ("SAVAR") returns the book that holds its units.

        Returns:
            {"main_books": [{main_book_id, main_book_name, institution_id,
            court_name, ...}], "count": n}
        """
        try:
            logger.info(f"Finding main books (search={search}, office={office_id})")
            books = self.client.find_main_book(search, office_id, institution_name)
            return {
                "main_books": [search_record(book) for book in books],
                "count": len(books),
            }
        except CadastralAPIError as e:
            logger.error(f"Main book search failed: {e}", exc_info=True)
            raise ValueError("Could not search land-registry main books.") from e

    async def find_book_of_dc(
        self,
        search: str | None = None,
        office_id: str | int | None = None,
        institution_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Find books of deposited contracts (knjige položenih ugovora, KPU).

        Returns:
            {"books_of_dc": [{book_id, book_name, office_id, office_name, ...}], "count": n}
        """
        try:
            logger.info(f"Finding books of deposited contracts (search={search})")
            books = self.client.find_book_of_dc(search, office_id, institution_name)
            return {
                "books_of_dc": [search_record(book) for book in books],
                "count": len(books),
            }
        except CadastralAPIError as e:
            logger.error(f"Books-of-DC search failed: {e}", exc_info=True)
            raise ValueError("Could not search books of deposited contracts.") from e

    async def find_possession_sheet(self, sheet_number: str, municipality: str) -> dict[str, Any]:
        """
        Find cadastre possession sheets (posjedovni listovi) by sheet number.

        Returns:
            {"possession_sheets": [{possession_sheet_id, sheet_number, ...}],
            "municipality_code": code, "count": n}
        """
        try:
            logger.info(f"Finding possession sheet {sheet_number} in {municipality}")
            muni_code = await self._resolve_municipality(municipality)
            sheets = self.client.find_possession_sheet(sheet_number, muni_code)
            return {
                "possession_sheets": [search_record(sheet) for sheet in sheets],
                "municipality_code": muni_code,
                "count": len(sheets),
            }
        except CadastralAPIError as e:
            logger.error(f"Possession sheet search failed: {e}", exc_info=True)
            raise ValueError(
                f"Could not search possession sheets for '{sheet_number}' in {municipality}."
            ) from e

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
        """Resolve a municipality name to its registration code (see the sync twin)."""
        return self._resolve_municipality_sync(name_or_code)

    def _resolve_municipality_sync(self, name_or_code: str) -> str:
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
