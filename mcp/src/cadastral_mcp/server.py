"""Main MCP server implementation using FastMCP."""

import logging
import sys
from typing import Any

from cadastral_api import CadastralAPIClient
from mcp.server.fastmcp import FastMCP

from .config import config
from .prompts import CadastralPrompts
from .resources import CadastralResources
from .tools import CadastralTools

# Configure logging to stderr (CRITICAL: never log to stdout in MCP servers)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


def create_mcp_server() -> FastMCP:
    """
    Create and configure the Cadastral MCP server.

    Returns:
        Configured FastMCP server instance
    """
    # Initialize FastMCP server
    mcp = FastMCP(
        name=config.server_name,
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

            The search matches on the prefix, so a number that does not exist
            can still come back as a longer one ("973" -> 973/1). Check
            ``exact_match``: when it is False the parcel returned is NOT the one
            asked for, and ``match_note`` plus ``other_matches`` say what was
            found. Report that to the user instead of treating it as a hit.
        """
        logger.info(f"Tool invoked: find_parcel({parcel_number}, {municipality})")
        return await tools_handler.search_parcel(parcel_number, municipality)

    @mcp.tool()
    async def batch_fetch_parcels(
        parcels: list[dict[str, str]],
        source: str = "cadastre",
    ) -> dict[str, Any]:
        """
        Fetch multiple parcels (čestice) in a single operation.

        Use this tool when the user requests information about multiple parcels,
        especially when they are in the same cadastral municipality (katastarska
        općina, K.O.). More efficient than calling find_parcel repeatedly.

        Ideal for:
        - Multiple parcel numbers mentioned in one query (e.g., "parcels 103/2, 45, and 396/1")
        - Comparing parcels in the same area or municipality
        - Analyzing property portfolios or multiple properties owned by same entity
        - Land consolidation research involving adjacent or related parcels

        ⚠️ Register matters: cadastre POSSESSORS (posjedovni list) are often NOT
        the registered land-registry OWNERS (vlasnici / vlastovnica / B-list).
        Choose the register explicitly via ``source``:
        - source="cadastre" (default): include possession-sheet possessors.
        - source="land_registry": omit possessors; return the land-registry unit
          reference + a hint to fetch true owners via get_lr_unit_from_parcel /
          batch_lr_units (use this for "vlasnik", "prema zemljišnim knjigama").
        - source="none": parcel metadata only.

        Every person record carries a ``register`` field ("cadastre" |
        "land_registry") so the two can never be confused.

        Each successful entry also carries ``map_url``, the interactive map
        (karta) centred on the parcel, when the municipality's GIS data is
        available (downloaded once, then cached).

        Args:
            parcels: List of parcel specifications with parcel_number + municipality OR parcel_id
            source: Register to return ownership data from: "cadastre" | "land_registry" | "none"

        Returns:
            Dictionary with results array and summary statistics, including the
            resolved ``source``. Each successful result is tagged with its
            ``register`` and includes the lr_unit reference, which can be passed
            to batch_lr_units for detailed ownership shares and encumbrances.
        """
        logger.info(f"Tool invoked: batch_fetch_parcels({len(parcels)} parcels, source={source})")
        return await tools_handler.batch_fetch_parcels(parcels, source=source)

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
        unit_number: str,
        main_book_id: int | None = None,
        detail: str = "ownership",
        owners_limit: int | None = None,
        include_plombe_detail: bool = False,
        main_book_name: str | None = None,
    ) -> dict[str, Any]:
        """
        Get land registry unit (zemljišnoknjižni uložak) information.

        A land registry unit contains:
        - Sheet A (Popis čestica): All parcels in the unit
        - Sheet B (Vlasnički list): Ownership (vlasnici) with shares
        - Sheet C (Teretni list): Encumbrances (mortgages, liens, easements)

        Each owner row carries ``entry``, the registration entry (upis) that put
        the owner on the share: order number, receipt date, diary number (Z-broj),
        action type. ``share_entries`` lists the annotations (zabilježbe) on
        individual shares.

        Args:
            unit_number: LR unit number (e.g., "769")
            main_book_id: Main book ID (e.g., 21277). Omit it and give
                ``main_book_name`` (e.g., "SAVAR", the glavna knjiga name) to
                resolve the id through the main-book search.
            main_book_name: Main book name, used when ``main_book_id`` is not given.
            detail: "summary" | "ownership" | "full". Default "ownership" returns
                B-list owners with structured shares + summary (no geometry/C-sheet),
                which fits in context; "full" returns every sheet.
            owners_limit: Cap owner records ("ownership" and "full" alike);
                total_owners and owners_truncated report the full count. A full
                dump too large to return is refused with the smaller options
                named, so pass this whenever a unit may have many co-owners.
            include_plombe_detail: Resolve what each pending plomba (zaprimljena
                neriješena prijava) actually is - the request type, processing
                status, and dates. Adds a ``plombe_detail`` map (file_number ->
                detail). Costs one extra request per plomba; off by default.

        Returns:
            Dictionary shaped per ``detail``; owners carry a structured ``share``
            ({num, den, decimal}) and a ``register`` tag.
        """
        logger.info(
            f"Tool invoked: get_lr_unit({unit_number}, {main_book_id or main_book_name}, "
            f"detail={detail})"
        )
        return await tools_handler.get_lr_unit(
            unit_number, main_book_id, detail, owners_limit, include_plombe_detail, main_book_name
        )

    @mcp.tool()
    async def get_lr_unit_from_parcel(
        parcel_number: str,
        municipality: str,
        detail: str = "ownership",
        owners_limit: int | None = None,
        include_plombe_detail: bool = False,
    ) -> dict[str, Any]:
        """
        Get the land registry unit (and registered owners) for a parcel.

        Searches the parcel and resolves its LR unit - falling back to parcel
        links when the parcel has no direct lr_unit - then returns the unit.
        Reports ``lr_unit_derived_from_links`` so callers know how it resolved.
        Use this for "vlasnik" / "prema zemljišnim knjigama" questions: it returns
        registered owners (vlastovnica / B-list), not cadastre possessors.

        Args:
            parcel_number: Cadastral parcel number (e.g., "279/6")
            municipality: Municipality name or code
            detail: "summary" | "ownership" | "full" (default "ownership").
            owners_limit: Cap owner records ("ownership" and "full" alike).
            include_plombe_detail: Resolve what each pending plomba actually is
                (request type, status, dates). Adds a ``plombe_detail`` map
                (file_number -> detail). One extra request per plomba; off by
                default.

        Returns:
            Dictionary shaped per ``detail``; owners carry a structured ``share``
            and a ``register`` tag.
        """
        logger.info(
            "Tool invoked: get_lr_unit_from_parcel(%s, %s, detail=%s)",
            parcel_number, municipality, detail,
        )
        return await tools_handler.get_lr_unit_from_parcel(
            parcel_number, municipality, detail, owners_limit, include_plombe_detail
        )

    @mcp.tool()
    async def batch_lr_units(
        lr_units: list[dict[str, Any]],
        detail: str = "ownership",
        owners_limit: int | None = None,
    ) -> dict[str, Any]:
        """
        Fetch multiple land registry units in a single operation.

        Use this after batch_fetch_parcels to get detailed LR unit information
        for multiple parcels. Each parcel result from batch_fetch_parcels includes
        lr_unit.lr_unit_number and lr_unit.main_book_id which can be passed here.

        This tool automatically deduplicates LR units - if multiple parcels belong
        to the same LR unit, it will only be fetched once.

        Ideal for:
        - Getting detailed ownership info after batch parcel fetch
        - Comparing ownership structures across multiple properties
        - Analyzing encumbrances (mortgages, liens) for property portfolios

        Args:
            lr_units: List of LR unit specs with lr_unit_number and main_book_id
            detail: "summary" | "ownership" | "full" (default "ownership"), applied
                to every unit.
            owners_limit: Cap owner records per unit ("ownership" and "full").

        Returns:
            Dictionary with results array and summary statistics:
            - results: List with status, data (shaped per detail), lr_unit_number, main_book_id
            - total: Total input count
            - unique: Unique LR units (after deduplication)
            - successful / failed: counts
        """
        logger.info(f"Tool invoked: batch_lr_units({len(lr_units)} units, detail={detail})")
        return await tools_handler.batch_lr_units(lr_units, detail, owners_limit)

    @mcp.tool()
    async def find_main_book(
        search: str | None = None,
        office_id: str | None = None,
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
        office_id: str | None = None,
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
        one of its parcels with find_parcel / batch_fetch_parcels.

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
        "Available tools: find_parcel, batch_fetch_parcels, resolve_municipality, "
        "get_parcel_geometry, list_cadastral_offices, get_lr_unit, "
        "get_lr_unit_from_parcel, batch_lr_units, find_main_book, find_book_of_dc, "
        "find_possession_sheet"
    )
    logger.info("Available prompts: explain_ownership_structure, property_report, "
                "compare_parcels, land_use_summary")
    logger.info("Available resources: cadastral://parcel/{id}, cadastral://municipality/{code}, "
                "cadastral://office/{code}")

    return mcp
