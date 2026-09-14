"""Main MCP server implementation using the MCP Python SDK (MCPServer)."""

import functools
import json
import logging
import sys
from collections.abc import Callable
from typing import Any

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError, ToolError

from .config import config
from .prompts import CadastralPrompts
from .resources import CadastralResources
from .tools import CadastralTools, LRUnitRef, ParcelRef

# Configure logging to stderr (CRITICAL: never log to stdout in MCP servers)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


Handler = Callable[..., Any]


def _anticipated(error_class: type[Exception]) -> Callable[[Handler], Handler]:
    """Turn a handler's ``ValueError`` into the SDK's anticipated failure.

    The handlers raise ``ValueError`` with a message written for the agent
    ("No parcels found matching ...", "Could not match parcel ... against the
    building areas: ..."). The MCP SDK treats any exception other than
    ``ToolError`` / ``ResourceError`` as a crash and withholds its message from
    the client, so the agent saw only "Error executing tool <name>". Wrapping
    the handlers hands the message over as the SDK expects.
    """

    def decorate(func: Handler) -> Handler:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except (ValueError, CadastralAPIError) as e:
                raise error_class(str(e)) from e

        return wrapper

    return decorate


anticipated_tool = _anticipated(ToolError)
anticipated_resource = _anticipated(ResourceError)


def create_mcp_server() -> MCPServer:
    """
    Create and configure the Cadastral MCP server.

    Returns:
        Configured MCPServer server instance
    """
    # Initialize the MCP server
    mcp = MCPServer(
        name=config.server_name,
        version=config.server_version,
    )

    # Initialize cadastral API client (shared across all requests)
    # Note: In production, consider using dependency injection or lifespan context
    # Unknown server fields are kept in ``source_fields`` and never reported
    # here: the MCP transport has no place for warnings (stdout is JSON-RPC).
    client = CadastralAPIClient(
        base_url=config.api_base_url,
        timeout=config.api_timeout,
        rate_limit=config.api_rate_limit,
        cache_dir=str(config.cache_dir),
        unknown_fields="ignore",
    )

    # Initialize handlers
    resources_handler = CadastralResources(client)
    tools_handler = CadastralTools(client)
    prompts_handler = CadastralPrompts(client)

    logger.info(f"Initializing {config.server_name} v{config.server_version}")
    logger.info(f"API Base URL: {config.api_base_url}")
    logger.info(f"Cache Directory: {config.cache_dir}")

    # ========================================================================
    # RESOURCES - Read-only contextual data
    # ========================================================================

    @mcp.resource("cadastral://parcel/{parcel_id}")
    @anticipated_resource
    async def get_parcel_resource(parcel_id: str) -> str:
        """Get full parcel details by ID."""
        logger.info(f"Resource request: cadastral://parcel/{parcel_id}")

        result = await resources_handler.get_parcel_resource(parcel_id)
        return json.dumps(result, indent=2)

    @mcp.resource("cadastral://municipality/{code}")
    @anticipated_resource
    async def get_municipality_resource(code: str) -> str:
        """Get municipality information by code."""
        logger.info(f"Resource request: cadastral://municipality/{code}")

        result = await resources_handler.get_municipality_resource(code)
        return json.dumps(result, indent=2)

    @mcp.resource("cadastral://office/{office_code}")
    @anticipated_resource
    async def get_office_resource(office_code: str) -> str:
        """Get cadastral office information by code."""
        logger.info(f"Resource request: cadastral://office/{office_code}")

        result = await resources_handler.get_office_resource(office_code)
        return json.dumps(result, indent=2)

    # ========================================================================
    # TOOLS - AI-invoked actions
    # ========================================================================

    @mcp.tool()
    @anticipated_tool
    async def find_parcel(
        parcel_number: str, municipality: str, max_matches: int = 0
    ) -> dict[str, Any]:
        """
        Find a cadastral parcel (čestica / katastarska čestica, k.č.) and return
        basic information.

        Use for a single parcel in the Croatian/Serbian cadastre (katastar) by
        parcel number within a cadastral municipality (katastarska općina, k.o.).
        Aggregates the 3-step API workflow: resolve municipality, find parcel, return info.

        Also returns ``map_url``, a link to the interactive map (karta) centred
        on the parcel, when the municipality's GIS data is available (downloaded
        once, then cached).

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name (e.g., "SAVAR") or registration code
            max_matches: Above 0, also return the complete search response:
                every record the server matched (parcel_id, parcel_number,
                is_building_parcel), up to this many, under ``matches`` with
                ``matches_total`` and ``matches_truncated``. Use it to list
                what exists ("which parcels start with 103"). With it, a
                search from which no single parcel can be chosen is not an
                error: ``success`` is False, ``parcel_id`` null, ``match_note``
                says why and ``matches`` still holds the records.

        Returns:
            Dictionary with parcel search results including parcel_id.

            The search matches on a substring, so a number that does not exist
            can still come back as a longer one ("973" -> 973/1). Check
            ``exact_match``: when it is False the parcel returned is NOT the one
            asked for, and ``match_note`` plus ``other_matches`` say what was
            found, and whether the number returned begins with the requested one
            or merely contains it. Report that to the user instead of treating
            it as a hit.
        """
        logger.info(f"Tool invoked: find_parcel({parcel_number}, {municipality})")
        return await tools_handler.search_parcel(parcel_number, municipality, max_matches)

    @mcp.tool()
    @anticipated_tool
    async def get_parcel(
        parcels: list[ParcelRef],
        source: str = "cadastre",
        offset: int = 0,
        limit: int | None = None,
        possessor_name: str | None = None,
        condominium_unit: str | None = None,
    ) -> dict[str, Any]:
        """
        Get the detailed cadastre (katastar) record of one or more parcels
        (čestice): area, land use, possession sheet, land-registry reference.

        Pass one reference for a single parcel and several for a list
        ("parcels 103/2, 45 and 396/1 in SAVAR"); the result has one entry per
        reference, in order, and a failed parcel does not stop the others.
        A reference is ``{"parcel_id": ...}`` (from find_parcel) or
        ``{"parcel_number": ..., "municipality": ...}`` (katastarska općina,
        K.O., by name or code).

        ⚠️ Register matters: cadastre POSSESSORS (posjedovni list) are often NOT
        the registered land-registry OWNERS (vlasnici / vlastovnica / B-list).
        Choose the register explicitly via ``source``:
        - source="cadastre" (default): include possession-sheet possessors.
        - source="land_registry": omit possessors; return the land-registry unit
          reference + a hint to fetch true owners via get_lr_unit (use this for
          "vlasnik", "prema zemljišnim knjigama").
        - source="none": parcel metadata only.

        Every person record carries a ``register`` field ("cadastre" |
        "land_registry") so the two can never be confused.

        Each successful entry also carries ``map_url``, the interactive map
        (karta) centred on the parcel, when the municipality's GIS data is
        available (downloaded once, then cached).

        A parcel under a large condominium (etažno vlasništvo) carries hundreds
        of possessors on one possession sheet. With source="cadastre" page
        through them with ``limit`` and ``offset``: each entry has a ``page``
        block and ``total_possessors``; when ``page.truncated`` is true call
        again with ``offset=page.next_offset``. An entry too large to return
        in one response is recorded as that parcel's error naming a smaller
        limit; do not retry it without one. On such a sheet each possessor's
        ``ownership`` is the share of their own unit and
        ``condominium_share_ownership`` the share of the parcel; the sheet's
        ``total_ownership`` sums the latter. A person holding two units is two
        records: ``total_possessors`` counts records, ``distinct_possessors``
        the different names. To find one person or one unit on such a sheet
        pass ``possessor_name`` (every word must occur in the name; case and
        diacritics ignored) or ``condominium_unit`` (the unit number, "E-16"
        or "16") instead of paging through it.

        Args:
            parcels: One or more parcel references (parcel_id, or parcel_number + municipality)
            source: Register to return ownership data from: "cadastre" | "land_registry" | "none"
            offset: Skip this many possessor records of each parcel (counted
                across its possession sheets, in sheet order); source="cadastre" only
            limit: Return at most this many possessor records per parcel
                (null for all); source="cadastre" only
            possessor_name: Keep only possessors whose name contains every word
                of this text (case and diacritics ignored); source="cadastre" only
            condominium_unit: Keep only the possessors of this condominium unit
                number ("E-16", "E16" and "16" agree); source="cadastre" only

        Returns:
            Dictionary with ``results`` (status, ref, register, data, map_url
            per entry; with source="cadastre" also total_possessors,
            possessors_truncated and a page block), ``total``, ``successful``,
            ``failed`` and the resolved ``source``. Each successful entry of
            a parcel that is in the land registry includes the unit reference
            under ``data.lr_unit``, which get_lr_unit accepts for ownership
            shares and encumbrances; ``data.lr_reference_shape`` says whether
            the cadastre linked it directly ("direct") or only through parcel
            links ("linked", the unit is then promoted from
            ``lr_units_from_parcel_links``), or not at all ("none").
        """
        logger.info(
            f"Tool invoked: get_parcel({len(parcels)} parcels, source={source}, "
            f"offset={offset}, limit={limit}, possessor_name={possessor_name!r}, "
            f"condominium_unit={condominium_unit!r})"
        )
        return await tools_handler.get_parcel(
            list(parcels),
            source=source,
            offset=offset,
            limit=limit,
            possessor_name=possessor_name,
            condominium_unit=condominium_unit,
        )

    @mcp.tool()
    @anticipated_tool
    async def resolve_municipality(name_or_code: str) -> dict[str, Any]:
        """
        Resolve a cadastral municipality (katastarska općina, k.o.) name to its
        registration number and complete search record.

        Args:
            name_or_code: Municipality name (e.g., "SAVAR") or code (e.g., "334979")

        Returns:
            Dictionary with ``code`` (registration number), ``name``,
            ``full_name`` (with the cadastral office), ``municipality_id``,
            ``office_id`` and ``department_id``. A name that matches several
            municipalities returns the first with the rest under
            ``other_matches``; use list_municipalities to see them all.
        """
        logger.info(f"Tool invoked: resolve_municipality({name_or_code})")
        return await tools_handler.resolve_municipality(name_or_code)

    @mcp.tool()
    @anticipated_tool
    async def list_municipalities(
        search: str | None = None,
        office_id: str | int | None = None,
        department_id: str | int | None = None,
        offset: int = 0,
        limit: int | None = 200,
    ) -> dict[str, Any]:
        """
        List cadastral municipalities (katastarske općine, k.o.), filtered by
        name, cadastral office (područni ured za katastar) or department.

        Use it for "which cadastral municipalities belong to the Zadar office"
        or to see every municipality a name matches. Without filters it lists
        all municipalities in the country, paged.

        Args:
            search: Name or code to match (substring)
            office_id: Cadastral office id (``id`` from list_cadastral_offices)
            department_id: Department id within the office
            offset: Skip this many records
            limit: Return at most this many (default 200; null for all)

        Returns:
            Dictionary with ``municipalities`` (code, name, full_name,
            municipality_id, office_id, department_id each), ``total`` and a
            ``page`` block (offset, limit, total, returned, truncated,
            next_offset).
        """
        logger.info(
            f"Tool invoked: list_municipalities({search}, office={office_id}, "
            f"department={department_id})"
        )
        return await tools_handler.list_municipalities(
            search, office_id, department_id, offset, limit
        )

    @mcp.tool()
    @anticipated_tool
    async def get_parcel_geometry(
        parcel_number: str, municipality: str, format: str = "geojson", zoom: int = 19
    ) -> dict[str, Any] | str:
        """
        Get a parcel's boundary geometry (granice čestice) as GeoJSON/WKT, with
        a link to the interactive map (karta) centred on the parcel.

        For mapping cadastral parcels (katastarska čestica) - coordinates,
        outline, area. Downloads and caches GML data if needed, then extracts geometry.

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name or registration code
            format: Output format - "geojson" (default), "wkt", or "dict"
            zoom: Zoom level for the map link (default 19 fits one parcel; 20 for
                very small parcels)

        Returns:
            Geometry data in requested format. "geojson" (in properties) and
            "dict" carry ``map_url``; "wkt" is the bare polygon.
        """
        logger.info(
            f"Tool invoked: get_parcel_geometry({parcel_number}, {municipality}, "
            f"{format}, zoom={zoom})"
        )
        return await tools_handler.get_parcel_geometry(parcel_number, municipality, format, zoom)

    @mcp.tool()
    @anticipated_tool
    async def get_parcel_zoning(
        parcel_number: str,
        municipality: str,
        include_geometry: bool = False,
        min_overlap: float = 0.02,
    ) -> dict[str, Any]:
        """
        Screening of a parcel against the spatial plans (prostorni planovi):
        is it inside a settlement building area (građevinsko područje
        naselja), in a detached zone outside a settlement (for example a T2
        tourist settlement or T3 camp), touching one below the threshold, or
        outside every building area (namjena prostora, građevinska područja,
        turistička zona).

        It does NOT answer "može li se graditi": ``buildability`` is always
        ``"unknown"``, because plan provisions, plot size, access,
        infrastructure and protection regimes are not evaluated. Matches the
        parcel boundary against the nationwide building-areas layer derived
        from the plans in force and reports every zone covering the parcel
        with the share it covers. The layer is an interpretation of the plans,
        not the plans themselves: always pass the ``disclaimer`` on.

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name or registration code
            include_geometry: Include the zone polygons (EPSG:3765), default False
            min_overlap: Drop zones covering a smaller share of the parcel (default 0.02)

        Returns:
            ``status``, ``buildability`` ("unknown"), ``matches`` (zone
            designation code and text, zone name, plan name and id, generation
            of the code list, overlap), ``below_threshold``, ``plans``,
            ``dataset`` with ``disclaimer``, ``source_url`` and ``retrieved_at``,
            ``summary``, ``generation_note``.
        """
        logger.info(
            f"Tool invoked: get_parcel_zoning({parcel_number}, {municipality}, "
            f"include_geometry={include_geometry}, min_overlap={min_overlap})"
        )
        return await tools_handler.get_parcel_zoning(
            parcel_number, municipality, include_geometry, min_overlap
        )

    @mcp.tool()
    @anticipated_tool
    async def list_cadastral_offices(filter_name: str | None = None) -> dict[str, Any]:
        """
        List cadastral offices (katastarski uredi / područni uredi), optionally
        filtered by name.

        Args:
            filter_name: Optional filter string to match office names

        Returns:
            Dictionary with list of offices and count
        """
        logger.info(f"Tool invoked: list_cadastral_offices(filter={filter_name})")
        return await tools_handler.list_cadastral_offices(filter_name)

    @mcp.tool()
    @anticipated_tool
    async def get_lr_unit(
        units: list[LRUnitRef],
        detail: str = "ownership",
        owners_limit: int | None = None,
        include_plombe_detail: bool = False,
        historical_overview: bool = False,
        offset: int = 0,
        limit: int | None = None,
        owner_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Get one or more land registry units (zemljišnoknjižni uložak, zemljišne
        knjige, ZK, gruntovnica): registered owners (vlasnici) and their shares.

        A land registry unit contains:
        - Sheet A (Posjedovnica): All parcels in the unit
        - Sheet B (Vlastovnica): Ownership (vlasnici) with shares
        - Sheet C (Teretovnica): Encumbrances (mortgages, liens, easements)

        Use this for "vlasnik" / "tko je vlasnik" / "prema zemljišnim knjigama"
        questions: it returns registered owners (vlastovnica / B-list), not
        cadastre possessors. Each reference names a unit in one of three ways:
        - ``{"parcel_number": "279/6", "municipality": "SAVAR"}``: the unit the
          parcel belongs to, resolved through parcel links when the parcel has
          no direct unit (the entry reports ``lr_unit_derived_from_links``);
        - ``{"lr_unit_number": "769", "main_book_id": 21277}``: the direct
          reference (as returned by get_parcel under ``data.lr_unit``);
        - ``{"lr_unit_number": "769", "main_book_name": "SAVAR"}``: with the
          main book (glavna knjiga) name instead of its id.

        Pass one reference for a single unit, several for a portfolio. The
        result has one entry per reference, in order; a unit that several
        references resolve to is fetched once (the later entries say
        ``duplicate`` and point at the entry with the data), and a failed
        reference does not stop the others.

        Each owner row carries ``entry``, the registration entry (upis) that put
        the owner on the share: order number, receipt date, diary number (Z-broj),
        action type. ``share_entries`` lists the annotations (zabilježbe) on
        individual shares.

        To find one person in a unit ("is X an owner", "which flat does X
        own") pass ``owner_name``: only the matching owners (or, in "shares"
        and "full", the shares holding one) come back, in one call, however
        many co-owners the unit has; ``matching_owners`` is 0 when the name is
        not on the sheet.

        Args:
            units: One or more unit references (see above).
            detail: "summary" | "ownership" | "shares" | "parcels" |
                "encumbrances" | "full". Default "ownership" returns B-list
                owners with structured shares + summary (no geometry/C-sheet),
                which fits in context. "shares" is sheet B as the register
                holds it (vlastovnica: raw shares with sub-shares, entries and
                status, historical ones included with historical_overview),
                "parcels" is sheet A (posjedovnica: the parcels of the unit,
                with sheet A2 entries), "encumbrances" is sheet C (teretovnica:
                the entry groups with amounts and beneficiaries), each paged on
                its own; "full" returns every sheet at once.
            owners_limit: Synonym of ``limit`` for "ownership" and "full"
                (kept for older callers; ``limit`` wins when both are given).
            include_plombe_detail: Resolve what each pending plomba (zaprimljeni
                neriješeni prijedlog za upis) actually is - the request type,
                processing status, and dates. Adds a ``plombe_detail`` map
                (file_number -> detail) per unit. Costs one extra request per
                plomba; off by default.
            historical_overview: Ask for the historical overview (povijesni
                pregled) as well: deleted entries and shares whose status is
                not active. Off by default; owners are then the current ones.
            offset: Skip this many items of the list the level is about
                (owner records for "ownership", top-level shares for "shares"
                and "full", parcels for "parcels", entry groups for
                "encumbrances").
            limit: Return at most this many of them. Every unit carries a
                ``page`` block (offset, limit, total, returned, truncated,
                next_offset); when ``truncated`` is true call again with
                ``offset=next_offset`` for the rest. In "shares" and "full"
                the shares outside the window are dropped whole
                (``shares_omitted``); a share without owners is a page item too.
                A response too large to return is reported as that unit's error
                with the smaller options named, so pass a limit whenever a unit
                may have many co-owners or encumbrances.
            owner_name: Keep only the owners whose name contains every word of
                this text (case and diacritics ignored, words in any order;
                "sarunic" finds "ŠARUNIĆ SAŠA"). Applies to "ownership"
                (owner rows), "shares" and "full" (the shares holding such an
                owner, kept whole with their co-owners); the other levels
                refuse it. The page walks the matches; ``matching_owners`` /
                ``matching_shares`` count them, ``total_owners`` /
                ``total_shares`` still describe the whole sheet.

        Returns:
            Dictionary with ``results`` (status, ref, lr_unit_number,
            main_book_id, data | error per entry) and the counts ``total``,
            ``unique``, ``successful``, ``failed``, ``duplicates`` and
            ``condominiums_found``. Each reference has exactly one status
            (success, error or duplicate), so successful + failed + duplicates
            = total; do not expect successful + failed alone to add up when
            references share a unit. ``data`` is shaped per ``detail``; owners
            carry a structured ``share`` ({num, den, decimal}) and a
            ``register`` tag.
        """
        logger.info(
            f"Tool invoked: get_lr_unit({len(units)} refs, detail={detail}, "
            f"owner_name={owner_name!r})"
        )
        return await tools_handler.get_lr_unit(
            list(units),
            detail,
            owners_limit,
            include_plombe_detail,
            historical_overview=historical_overview,
            offset=offset,
            limit=limit,
            owner_name=owner_name,
        )

    @mcp.tool()
    @anticipated_tool
    async def find_main_book(
        search: str | None = None,
        office_id: str | int | None = None,
        institution_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Find land-registry main books (glavna knjiga, glavne knjige zemljišne
        knjige) by name, land-registry office or institution.

        Use this to get the ``main_book_id`` that get_lr_unit needs when only
        the cadastral municipality (katastarska općina) name is known: searching
        "SAVAR" returns main book 21277 of the Zadar court (institution 284).

        Args:
            search: Book name to search (e.g., "SAVAR"); empty lists every book
            office_id: Land-registry office (zemljišnoknjižni odjel) id, e.g. "284"
            institution_name: Institution name filter

        Returns:
            Dictionary with ``main_books`` (main_book_id, main_book_name,
            institution_id, court_name) and ``count``
        """
        logger.info(f"Tool invoked: find_main_book({search}, office={office_id})")
        return await tools_handler.find_main_book(search, office_id, institution_name)

    @mcp.tool()
    @anticipated_tool
    async def find_book_of_dc(
        search: str | None = None,
        office_id: str | int | None = None,
        institution_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Find books of deposited contracts (knjiga položenih ugovora, KPU) of the
        land registry (zemljišne knjige), by name, office or institution.

        A KPU book holds flats sold before their building had a land-registry
        unit. Whether its id can be used as a main book id for get_lr_unit is
        not verified; the tool returns the search records only.

        Args:
            search: Book name to search (e.g., "ZADAR")
            office_id: Land-registry office id
            institution_name: Institution name filter

        Returns:
            Dictionary with ``books_of_dc`` (book_id, book_name, office_id,
            office_name) and ``count``
        """
        logger.info(f"Tool invoked: find_book_of_dc({search}, office={office_id})")
        return await tools_handler.find_book_of_dc(search, office_id, institution_name)

    @mcp.tool()
    @anticipated_tool
    async def find_possession_sheet(sheet_number: str, municipality: str) -> dict[str, Any]:
        """
        Find cadastre possession sheets (posjedovni list, posjedovni listovi) by
        sheet number in a cadastral municipality (katastar, katastarska općina).

        The records carry the possession sheet id that parcel possession sheets
        reference and the sheet number. The cadastre has no endpoint that
        returns a sheet by id; to see a sheet's possessors (posjednici) look up
        one of its parcels with get_parcel.

        Args:
            sheet_number: Possession sheet number (prefix match, e.g. "363")
            municipality: Municipality name (e.g., "SAVAR") or registration code

        Returns:
            Dictionary with ``possession_sheets`` (possession_sheet_id,
            sheet_number), ``municipality_code`` and ``count``
        """
        logger.info(f"Tool invoked: find_possession_sheet({sheet_number}, {municipality})")
        return await tools_handler.find_possession_sheet(sheet_number, municipality)

    @mcp.tool()
    @anticipated_tool
    async def get_file_status(file_number: str, institution_id: int) -> dict[str, Any]:
        """
        Processing status of one land-registry file (spis, plomba, zaprimljeni
        prijedlog) by its number, e.g. "Z-12564/2026": what the request is
        (uknjižba, nasljeđivanje, hipoteka ...), where it is in processing, and
        its dates.

        A unit's pending plombe carry only the file number; get_lr_unit with
        include_plombe_detail resolves them all at once. Use this tool when you
        already hold a file number and the office that processes it.

        Args:
            file_number: File number as written on the unit, e.g. "Z-12564/2026"
            institution_id: Land-registry office id (``institution_id`` of the
                unit from get_lr_unit, or of the book from find_main_book)

        Returns:
            Dictionary with ``found`` and, when found, ``status`` (file id,
            application content, status description, registration number,
            resolution type, dates); otherwise a ``message``.
        """
        logger.info(f"Tool invoked: get_file_status({file_number}, {institution_id})")
        return await tools_handler.get_file_status(file_number, institution_id)

    @mcp.tool()
    @anticipated_tool
    async def download_municipality_gis(
        municipality: str, force: bool = False
    ) -> dict[str, Any]:
        """
        Download the GIS data (parcel boundaries, GML) of a whole cadastral
        municipality (katastarska općina) into the local cache, or refresh it.

        get_parcel_geometry and get_parcel_zoning do this on demand for the
        parcel they need; call this to fetch a municipality ahead of many
        lookups, to refresh stale data (``force=true``), or to learn how many
        parcels the municipality has.

        Args:
            municipality: Municipality name (e.g., "SAVAR") or registration code
            force: Download again even when the municipality is already cached

        Returns:
            Dictionary with ``municipality_code``, ``download_url``,
            ``already_cached``, ``zip_path``, ``zip_size_bytes``, ``gml_path``,
            ``parcel_count`` and ``source`` (the server the cache came from).
        """
        logger.info(f"Tool invoked: download_municipality_gis({municipality}, force={force})")
        return await tools_handler.download_municipality_gis(municipality, force)

    # ========================================================================
    # PROMPTS - User-selected templates
    # ========================================================================

    @mcp.prompt()
    async def explain_ownership_structure(parcel_id: str) -> str:
        """
        Generate a prompt to explain parcel ownership structure.

        Args:
            parcel_id: The unique parcel identifier

        Returns:
            Formatted prompt text with ownership data for AI analysis
        """
        logger.info(f"Prompt invoked: explain_ownership_structure({parcel_id})")
        return await prompts_handler.explain_ownership_structure(parcel_id)

    @mcp.prompt()
    async def property_report(parcel_id: str) -> str:
        """
        Generate a comprehensive property report prompt.

        Args:
            parcel_id: The unique parcel identifier

        Returns:
            Formatted prompt for generating a detailed property report
        """
        logger.info(f"Prompt invoked: property_report({parcel_id})")
        return await prompts_handler.property_report(parcel_id)

    @mcp.prompt()
    async def compare_parcels(parcel_ids: list[str]) -> str:
        """
        Generate a prompt to compare multiple parcels.

        Args:
            parcel_ids: List of parcel identifiers to compare (at least 2)

        Returns:
            Formatted prompt with data for all parcels
        """
        logger.info(f"Prompt invoked: compare_parcels({len(parcel_ids)} parcels)")
        return await prompts_handler.compare_parcels(parcel_ids)

    @mcp.prompt()
    async def land_use_summary(parcel_id: str) -> str:
        """
        Generate a prompt to analyze land use distribution.

        Args:
            parcel_id: The unique parcel identifier

        Returns:
            Formatted prompt for land use analysis
        """
        logger.info(f"Prompt invoked: land_use_summary({parcel_id})")
        return await prompts_handler.land_use_summary(parcel_id)

    logger.info("MCP server initialized successfully")
    logger.info(
        "Available tools: find_parcel, get_parcel, resolve_municipality, "
        "list_municipalities, get_parcel_geometry, get_parcel_zoning, "
        "list_cadastral_offices, get_lr_unit, get_file_status, find_main_book, "
        "find_book_of_dc, find_possession_sheet, download_municipality_gis"
    )
    logger.info("Available prompts: explain_ownership_structure, property_report, "
                "compare_parcels, land_use_summary")
    logger.info("Available resources: cadastral://parcel/{id}, cadastral://municipality/{code}, "
                "cadastral://office/{code}")

    return mcp
