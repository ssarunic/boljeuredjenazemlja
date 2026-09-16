"""Configuration for the MCP server."""

import os
from dataclasses import dataclass
from pathlib import Path

from cadastral_api import CadastralAPIClient
from cadastral_api.gis import GISCache


@dataclass
class MCPConfig:
    """Configuration for the Cadastral MCP server."""

    # API Configuration (the SDK reads the CADASTRAL_API_* variables and
    # owns the defaults; importing it loads the .env file first)
    api_base_url: str = CadastralAPIClient.BASE_URL
    api_timeout: float = CadastralAPIClient.DEFAULT_TIMEOUT
    api_rate_limit: float = CadastralAPIClient.DEFAULT_RATE_LIMIT

    # Language Configuration
    language: str = os.getenv("CADASTRAL_LANG", "hr")

    # Cache Configuration
    cache_dir: Path = Path(os.getenv("CADASTRAL_CACHE_DIR", str(GISCache.DEFAULT_CACHE_DIR)))

    # MCP Server Configuration
    server_name: str = "cadastral-mcp-server"
    server_version: str = "0.3.0"

    # HTTP Server Configuration (when running in HTTP mode)
    http_host: str = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
    http_port: int = int(os.getenv("MCP_HTTP_PORT", "8080"))
    http_cors_origins: list[str] | None = None  # Set to ["*"] for dev, specific origins for prod

    def __post_init__(self) -> None:
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
config = MCPConfig()
