"""Main MCP server implementation using the MCP Python SDK (MCPServer)."""

import logging
import sys
from typing import Any

from cadastral_api import CadastralAPIClient
from mcp.server.mcpserver import MCPServer

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
    async def get_parcel_resource(parcel_id: str) -> str:
        """Get full parcel details by ID."""
        logger.info(f"Resource request: cadastral://parcel/{parcel_id}")

        result = await resources_handler.get_parcel_resource(parcel_id)
        import json
        return json.dumps(result, indent=2)

    @mcp.resource("cadastral://municipality/{code}")
    async def get_municipality_resource(code: str) -> str:
        """Get municipality information by code."""
        logger.info(f"Resource request: cadastral://municipality/{code}")

        result = await resources_handler.get_municipality_resource(code)
        import json
        return json.dumps(result, indent=2)

    @mcp.resource("cadastral://office/{office_code}")
    async def get_office_resource(office_code: str) -> str:
        """Get cadastral office information by code."""
        logger.info(f"Resource request: cadastral://office/{office_code}")

        result = await resources_handler.get_office_resource(office_code)
        import json
        return json.dumps(result, indent=2)

    # ========================================================================
    # TOOLS - AI-invoked actions
    # ========================================================================

    @mcp.tool()
    async def find_parcel(parcel_number: str, municipality: str) -> dict[str, Any]:
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
        return await tools_handler.search_parcel(parcel_number, municipality)

    @mcp.tool()
    async def get_parcel(
        parcels: list[ParcelRef],
        source: str = "cadastre",
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

        Args:
            parcels: One or more parcel references (parcel_id, or parcel_number + municipality)
            source: Register to return ownership data from: "cadastre" | "land_registry" | "none"

        Returns:
            Dictionary with ``results`` (status, ref, register, data, map_url
            per entry), ``total``, ``successful``, ``failed`` and the resolved
            ``source``. Each successful entry includes the lr_unit reference
            (``data.lr_unit``), which get_lr_unit accepts for ownership shares
            and encumbrances.
        """
        logger.info(f"Tool invoked: get_parcel({len(parcels)} parcels, source={source})")
        return await tools_handler.get_parcel(list(parcels), source=source)

    @mcp.tool()
    async def resolve_municipality(name_or_code: str) -> dict[str, Any]:
        """
        Resolve a cadastral municipality (katastarska općina, k.o.) name to its
        registration number.

        Args:
            name_or_code: Municipality name (e.g., "SAVAR") or code (e.g., "334979")

        Returns:
            Dictionary with municipality code, name, and full name
        """
        logger.info(f"Tool invoked: resolve_municipality({name_or_code})")
        return await tools_handler.resolve_municipality(name_or_code)

    @mcp.tool()
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
    async def get_lr_unit(
        units: list[LRUnitRef],
        detail: str = "ownership",
        owners_limit: int | None = None,
        include_plombe_detail: bool = False,
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

        Args:
            units: One or more unit references (see above).
            detail: "summary" | "ownership" | "full". Default "ownership" returns
                B-list owners with structured shares + summary (no geometry/C-sheet),
                which fits in context; "full" returns every sheet.
            owners_limit: Cap owner records per unit ("ownership" and "full"
                alike); total_owners and owners_truncated report the full count.
                In "full" it cuts sheet B off at that many owner records, dropping
                the shares past it whole (``shares_omitted``). A full dump too
                large to return is reported as that unit's error with the smaller
                options named, so pass this whenever a unit may have many co-owners.
            include_plombe_detail: Resolve what each pending plomba (zaprimljeni
                neriješeni prijedlog za upis) actually is - the request type,
                processing status, and dates. Adds a ``plombe_detail`` map
                (file_number -> detail) per unit. Costs one extra request per
                plomba; off by default.

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
        logger.info(f"Tool invoked: get_lr_unit({len(units)} refs, detail={detail})")
        return await tools_handler.get_lr_unit(
            list(units), detail, owners_limit, include_plombe_detail
        )

    @mcp.tool()
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
        "get_parcel_geometry, list_cadastral_offices, get_lr_unit, find_main_book, "
        "find_book_of_dc, find_possession_sheet"
    )
    logger.info("Available prompts: explain_ownership_structure, property_report, "
                "compare_parcels, land_use_summary")
    logger.info("Available resources: cadastral://parcel/{id}, cadastral://municipality/{code}, "
                "cadastral://office/{code}")

    return mcp
