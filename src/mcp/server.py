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
        version=config.server_version,
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
    async def get_parcel_resource(uri: str) -> str:
        """Get full parcel details by ID."""
        # Extract parcel_id from URI
        parcel_id = uri.split("/")[-1]
        logger.info(f"Resource request: {uri}")

        result = await resources_handler.get_parcel_resource(parcel_id)
        import json
        return json.dumps(result, indent=2)

    @mcp.resource("cadastral://municipality/{code}")
    async def get_municipality_resource(uri: str) -> str:
        """Get municipality information by code."""
        code = uri.split("/")[-1]
        logger.info(f"Resource request: {uri}")

        result = await resources_handler.get_municipality_resource(code)
        import json
        return json.dumps(result, indent=2)

    @mcp.resource("cadastral://office/{code}")
    async def get_office_resource(uri: str) -> str:
        """Get cadastral office information by code."""
        code = uri.split("/")[-1]
        logger.info(f"Resource request: {uri}")

        result = await resources_handler.get_office_resource(code)
        import json
        return json.dumps(result, indent=2)

    # ========================================================================
    # TOOLS - AI-invoked actions
    # ========================================================================

    @mcp.tool()
    async def search_parcel(parcel_number: str, municipality: str) -> dict[str, Any]:
        """
        Search for a parcel and return basic information.

        Aggregates the 3-step API workflow: resolve municipality, search parcel, return info.

        Args:
            parcel_number: Cadastral parcel number (e.g., "103/2")
            municipality: Municipality name (e.g., "SAVAR") or registration code

        Returns:
            Dictionary with parcel search results including parcel_id
        """
        logger.info(f"Tool invoked: search_parcel({parcel_number}, {municipality})")
        return await tools_handler.search_parcel(parcel_number, municipality)

    @mcp.tool()
    async def batch_fetch_parcels(
        parcels: list[dict[str, str]], include_owners: bool = False
    ) -> dict[str, Any]:
        """
        Fetch multiple parcels in a single operation.

        Args:
            parcels: List of parcel specifications with parcel_number + municipality OR parcel_id
            include_owners: Whether to include ownership information (default: False)

        Returns:
            Dictionary with results array and summary statistics
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
    logger.info("Available tools: search_parcel, batch_fetch_parcels, resolve_municipality, "
                "get_parcel_geometry, list_cadastral_offices")
    logger.info("Available prompts: explain_ownership_structure, property_report, "
                "compare_parcels, land_use_summary")
    logger.info("Available resources: cadastral://parcel/{id}, cadastral://municipality/{code}, "
                "cadastral://office/{code}")

    return mcp
