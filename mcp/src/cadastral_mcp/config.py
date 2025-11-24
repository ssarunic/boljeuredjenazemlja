"""Configuration for the MCP server."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MCPConfig:
    """Configuration for the Cadastral MCP server."""

    # API Configuration
    api_base_url: str = os.getenv("CADASTRAL_API_BASE_URL", "http://localhost:8000")
    api_timeout: float = float(os.getenv("CADASTRAL_API_TIMEOUT", "10.0"))
    api_rate_limit: float = float(os.getenv("CADASTRAL_API_RATE_LIMIT", "0.375"))

    # Language Configuration
    language: str = os.getenv("CADASTRAL_LANG", "hr")

    # Cache Configuration
    cache_dir: Path = Path(os.getenv("CADASTRAL_CACHE_DIR",
                                     str(Path.home() / ".cadastral_api_cache")))

    # MCP Server Configuration
    server_name: str = "cadastral-mcp-server"
    server_version: str = "0.1.0"

    # HTTP Server Configuration (when running in HTTP mode)
    http_host: str = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
    http_port: int = int(os.getenv("MCP_HTTP_PORT", "8080"))
    http_cors_origins: list[str] | None = None  # Set to ["*"] for dev, specific origins for prod

    def __post_init__(self) -> None:
        """Ensure cache directory exists."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)


# Global config instance
config = MCPConfig()
