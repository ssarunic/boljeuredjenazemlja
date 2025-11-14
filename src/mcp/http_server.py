"""FastAPI HTTP transport for the MCP server."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from mcp.server.fastmcp import FastMCP

from .config import config

logger = logging.getLogger(__name__)


def create_http_app(mcp_server: FastMCP) -> FastAPI:
    """
    Create a FastAPI application with MCP SSE endpoints.

    Args:
        mcp_server: The configured FastMCP server instance

    Returns:
        FastAPI application with MCP transport
    """
    app = FastAPI(
        title="Cadastral MCP Server",
        description="Model Context Protocol server for Croatian Cadastral API queries",
        version=config.server_version,
    )

    # Configure CORS
    cors_origins = config.http_cors_origins or [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://claude.ai",
    ]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger.info(f"FastAPI app created with CORS origins: {cors_origins}")

    # Health check endpoint
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "server": config.server_name,
            "version": config.server_version,
            "api_base_url": config.api_base_url,
        }

    # MCP capabilities endpoint
    @app.get("/mcp/capabilities")
    async def capabilities() -> dict[str, Any]:
        """Return MCP server capabilities."""
        return {
            "name": config.server_name,
            "version": config.server_version,
            "capabilities": {
                "resources": True,
                "tools": True,
                "prompts": True,
            },
            "resources": [
                "cadastral://parcel/{parcel_id}",
                "cadastral://municipality/{code}",
                "cadastral://office/{code}",
            ],
            "tools": [
                "search_parcel",
                "batch_fetch_parcels",
                "resolve_municipality",
                "get_parcel_geometry",
                "list_cadastral_offices",
            ],
            "prompts": [
                "explain_ownership_structure",
                "property_report",
                "compare_parcels",
                "land_use_summary",
            ],
        }

    # MCP SSE endpoint
    @app.post("/mcp/sse")
    async def mcp_sse(request: Request) -> StreamingResponse:
        """
        MCP Server-Sent Events endpoint.

        This endpoint handles MCP protocol communication via SSE,
        allowing web clients to interact with the MCP server.
        """
        logger.info("SSE connection established")

        # Get request body
        body = await request.json()
        logger.debug(f"SSE request: {body}")

        # Process MCP request through FastMCP
        # Note: FastMCP's SSE handling will be implemented here
        # This is a placeholder for the actual SSE stream handling

        async def event_stream():
            """Generate SSE events."""
            # TODO: Implement actual MCP SSE protocol handling
            # This requires deeper integration with FastMCP's transport layer
            yield "data: {}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    logger.info("FastAPI HTTP transport configured")

    return app


def run_http_server(mcp_server: FastMCP) -> None:
    """
    Run the MCP server with HTTP transport using Uvicorn.

    Args:
        mcp_server: The configured FastMCP server instance
    """
    import uvicorn

    app = create_http_app(mcp_server)

    logger.info(f"Starting HTTP server on {config.http_host}:{config.http_port}")

    uvicorn.run(
        app,
        host=config.http_host,
        port=config.http_port,
        log_level="info",
    )
