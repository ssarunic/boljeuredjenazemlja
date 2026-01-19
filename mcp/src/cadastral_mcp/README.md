# Cadastral MCP Server

Model Context Protocol (MCP) server for querying Croatian cadastral and land registry data.

## Quick Start

### Installation

```bash
pip install -e .
```

### Run with STDIO (Claude Desktop)

```bash
cadastral-mcp --transport stdio
```

### Run with HTTP (Web/Remote)

```bash
cadastral-mcp --transport http --port 8080
```

## Documentation

See [docs/MCP_SERVER.md](../../docs/MCP_SERVER.md) for complete documentation including:

- Setup and configuration
- Claude Desktop integration
- HTTP deployment
- Available tools, resources, and prompts
- Example interactions
- Development guide

## ⚠️ Important

This MCP server is for **educational/demonstration purposes only**. It connects to `http://localhost:8000` (mock server) by default. Do NOT configure it to use Croatian government production systems.

## Architecture

The server exposes three MCP primitive types:

### Resources (Read-only data)
- `cadastral://parcel/{id}` - Parcel details
- `cadastral://municipality/{code}` - Municipality info
- `cadastral://office/{code}` - Office info

### Tools (AI-invoked actions)
- `search_parcel` - Search parcels
- `batch_fetch_parcels` - Fetch multiple parcels
- `resolve_municipality` - Name to code resolution
- `get_parcel_geometry` - Boundary coordinates
- `list_cadastral_offices` - List offices

### Prompts (User templates)
- `explain_ownership_structure` - Ownership analysis
- `property_report` - Comprehensive report
- `compare_parcels` - Multi-parcel comparison
- `land_use_summary` - Land use analysis

## Configuration

Via environment variables:

```bash
CADASTRAL_API_BASE_URL=http://localhost:8000  # API URL
CADASTRAL_LANG=hr                              # Language
MCP_HTTP_HOST=127.0.0.1                        # HTTP host
MCP_HTTP_PORT=8080                             # HTTP port
```

## Project Structure

```text
src/mcp/
├── config.py         # Configuration
├── server.py         # Main FastMCP server
├── resources.py      # Resource handlers
├── tools.py          # Tool handlers
├── prompts.py        # Prompt templates
├── http_server.py    # FastAPI transport
└── main.py           # CLI entry point
```

## License

Educational/demonstration purposes only.
