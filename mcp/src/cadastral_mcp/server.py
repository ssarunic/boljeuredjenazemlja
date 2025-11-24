"""Main MCP server implementation using FastMCP."""

import logging
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from cadastral_api import CadastralAPIClient

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
    client = CadastralAPIClient(
        base_url=config.api_base_url,
        timeout=config.api_timeout,
        rate_limit=config.api_rate_limit,
        cache_dir=str(config.cache_dir),
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
        Find a parcel and return basic information.

        Aggregates the 3-step API workflow: resolve municipality, find parcel, return info.

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name (e.g., "SAVAR") or registration code

        Returns:
            Dictionary with parcel search results including parcel_id
        """
        logger.info(f"Tool invoked: find_parcel({parcel_number}, {municipality})")
        return await tools_handler.search_parcel(parcel_number, municipality)

    @mcp.tool()
    async def batch_fetch_parcels(
        parcels: list[dict[str, str]], include_owners: bool = False
    ) -> dict[str, Any]:
        """
        Fetch multiple parcels in a single operation.

        Use this tool when the user requests information about multiple parcels,
        especially when they are in the same cadastral municipality (K.O.).
        This is more efficient than calling find_parcel multiple times as it
        handles rate limiting and returns aggregated statistics.

        Ideal for:
        - Multiple parcel numbers mentioned in one query (e.g., "parcels 103/2, 45, and 396/1")
        - Comparing parcels in the same area or municipality
        - Analyzing property portfolios or multiple properties owned by same entity
        - Land consolidation research involving adjacent or related parcels

        Args:
            parcels: List of parcel specifications with parcel_number + municipality OR parcel_id
            include_owners: Whether to include ownership information (default: False)

        Returns:
            Dictionary with results array and summary statistics.
            Each successful result includes:
            - parcel_number, municipality, area, etc.
            - lr_unit (land registry reference with lr_unit_number and main_book_id)

            The lr_unit reference can be used with batch_lr_units to get detailed
            land registry information including ownership shares and encumbrances.
        """
        logger.info(f"Tool invoked: batch_fetch_parcels({len(parcels)} parcels)")
        return await tools_handler.batch_fetch_parcels(parcels, include_owners)

    @mcp.tool()
    async def resolve_municipality(name_or_code: str) -> dict[str, Any]:
        """
        Resolve municipality name to registration code.

        Args:
            name_or_code: Municipality name (e.g., "SAVAR") or code (e.g., "334979")

        Returns:
            Dictionary with municipality code, name, and full name
        """
        logger.info(f"Tool invoked: resolve_municipality({name_or_code})")
        return await tools_handler.resolve_municipality(name_or_code)

    @mcp.tool()
    async def get_parcel_geometry(
        parcel_number: str, municipality: str, format: str = "geojson"
    ) -> dict[str, Any] | str:
        """
        Get parcel boundary geometry.

        Downloads and caches GML data if needed, then extracts geometry.

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name or registration code
            format: Output format - "geojson" (default), "wkt", or "dict"

        Returns:
            Geometry data in requested format
        """
        logger.info(f"Tool invoked: get_parcel_geometry({parcel_number}, {municipality}, {format})")
        return await tools_handler.get_parcel_geometry(parcel_number, municipality, format)

    @mcp.tool()
    async def list_cadastral_offices(filter_name: str | None = None) -> dict[str, Any]:
        """
        List all cadastral offices, optionally filtered by name.

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
        main_book_id: int,
        include_full_details: bool = True
    ) -> dict[str, Any]:
        """
        Get detailed land registry unit (zemljišnoknjižni uložak) information.

        A land registry unit contains:
        - Sheet A (Popis čestica): All parcels in the unit
        - Sheet B (Vlasnički list): Ownership information with shares
        - Sheet C (Teretni list): Encumbrances (mortgages, liens, easements)

        Args:
            unit_number: LR unit number (e.g., "769")
            main_book_id: Main book ID (e.g., 21277)
            include_full_details: Include all sheets (default: True)

        Returns:
            Dictionary with LR unit data including all sheets and summary
        """
        logger.info(f"Tool invoked: get_lr_unit({unit_number}, {main_book_id})")
        return await tools_handler.get_lr_unit(unit_number, main_book_id, include_full_details)

    @mcp.tool()
    async def get_lr_unit_from_parcel(
        parcel_number: str,
        municipality: str,
        include_full_details: bool = True
    ) -> dict[str, Any]:
        """
        Get land registry unit information from a parcel number.

        This is a convenience method that searches for the parcel and retrieves
        its complete land registry unit data.

        Args:
            parcel_number: Cadastral parcel number (e.g., "279/6")
            municipality: Municipality name or code
            include_full_details: Include all sheets (default: True)

        Returns:
            Dictionary with LR unit data including all sheets and summary
        """
        logger.info(f"Tool invoked: get_lr_unit_from_parcel({parcel_number}, {municipality})")
        return await tools_handler.get_lr_unit_from_parcel(parcel_number, municipality, include_full_details)

    @mcp.tool()
    async def batch_lr_units(
        lr_units: list[dict[str, Any]],
        include_full_details: bool = True
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
            include_full_details: Include all sheets (default: True)

        Returns:
            Dictionary with results array and summary statistics:
            - results: List with status, data (or error), lr_unit_number, main_book_id
            - total: Total input count
            - unique: Unique LR units (after deduplication)
            - successful: Successful fetches
            - failed: Failed fetches
        """
        logger.info(f"Tool invoked: batch_lr_units({len(lr_units)} units)")
        return await tools_handler.batch_lr_units(lr_units, include_full_details)

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
    logger.info("Available tools: find_parcel, batch_fetch_parcels, resolve_municipality, "
                "get_parcel_geometry, list_cadastral_offices, get_lr_unit, get_lr_unit_from_parcel, "
                "batch_lr_units")
    logger.info("Available prompts: explain_ownership_structure, property_report, "
                "compare_parcels, land_use_summary")
    logger.info("Available resources: cadastral://parcel/{id}, cadastral://municipality/{code}, "
                "cadastral://office/{code}")

    return mcp
