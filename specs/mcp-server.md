# Cadastral MCP Server

Model Context Protocol (MCP) server for querying Croatian cadastral and land registry data.

## ⚠️ Important Notice

**This MCP server is an educational demonstration.**

- ✅ **Default Configuration**: Connects to `http://localhost:8000` (mock test server)
- ⚠️ **Other servers**: Before configuring any other server, including the Croatian government APIs, verify that you have the rights to use it and its data (terms of service, data protection). You do so at your own risk; see `docs/legal.md`

## 📖 For Claude Desktop Users

**If you're using this with Claude Desktop, read the [MCP usage guide](../docs/mcp-usage-guide.md) first!**

It includes:
- ✅ Which tools work and how to use them
- ⚠️ Known issues and workarounds
- 💡 Usage tips and common patterns
- 🔧 Troubleshooting guide

## What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open standard that enables AI applications to securely access external data sources and tools. Think of it as "USB-C for AI" - a universal way to connect AI models to various services.

### MCP Architecture

MCP servers expose three types of primitives:

- **Resources** 📄 - Read-only contextual data (like REST GET endpoints)
- **Tools** 🔧 - Executable functions that perform actions
- **Prompts** 💬 - Reusable templates for common workflows

## Features

This MCP server wraps the Croatian Cadastral API SDK and provides:

### Resources (Read-only data)

AI agents can auto-fetch contextual information:

- `cadastral://parcel/{parcel_id}` - Full parcel details with ownership
- `cadastral://municipality/{code}` - Municipality information
- `cadastral://office/{code}` - Cadastral office details

### Tools (AI-invoked actions)

The AI decides when to invoke these based on user queries:

**Parcel Operations:**
- **`find_parcel`** - Find one parcel by number and municipality (parcel id, exact-match check, map link)
- **`get_parcel`** - Detailed cadastre record of one or more parcels. Takes a list of references (`parcel_id`, or `parcel_number` + `municipality`) and returns one entry per reference; `source` selects the register (cadastre possessors, land-registry hint, or none). Each entry carries the land registry unit reference.
- **`get_parcel_geometry`** - Download and return parcel boundaries

**Land Registry Operations:**
- **`get_lr_unit`** - One or more land registry units. Takes a list of references, each by `lr_unit_number` + `main_book_id`, by `lr_unit_number` + `main_book_name`, or by `parcel_number` + `municipality` (resolved through parcel links when needed). Returns one entry per reference; units shared by several references are fetched once. `detail`, `owners_limit` and `include_plombe_detail` shape every entry.

**Lookup Operations:**
- **`resolve_municipality`** - Convert municipality names to codes
- **`list_cadastral_offices`** - List available cadastral offices
- **`find_main_book`** - Find land registry main books (glavne knjige) by name, office or institution; gives the `main_book_id` for `get_lr_unit`
- **`find_book_of_dc`** - Find books of deposited contracts (knjige položenih ugovora, KPU)
- **`find_possession_sheet`** - Find cadastre possession sheets (posjedovni listovi) by number

#### One tool, one or many items

There are no separate batch tools. `get_parcel` and `get_lr_unit` take a list
of references; a single item is a list of one. The result shape is the same in
both cases: `results` with one entry per reference (in order, each with a
`status`), plus counts. A failed reference is an `error` entry and does not stop
the others. This keeps the agent's decision simple ("which register?") and the
result shape predictable.

#### Pipeline: From Parcels to Land Registry Units

```text
User: "Get detailed ownership info for parcels 103/2, 45, and 396/1 in SAVAR"

Step 1 (optional, cadastre facts): get_parcel(
  parcels=[{"parcel_number": "103/2", "municipality": "SAVAR"},
           {"parcel_number": "45", "municipality": "SAVAR"},
           {"parcel_number": "396/1", "municipality": "SAVAR"}],
  source="land_registry")
-> one entry per parcel with data.lr_unit = {lr_unit_number, main_book_id}

Step 2 (owners): get_lr_unit(
  units=[{"parcel_number": "103/2", "municipality": "SAVAR"},
         {"parcel_number": "45", "municipality": "SAVAR"},
         {"parcel_number": "396/1", "municipality": "SAVAR"}])
-> one entry per parcel; parcels of the same unit share one fetch
```

Step 2 works on its own for an ownership question; step 1 is only needed for
the cadastre side (area, land use, possessors, harmonisation).

### Prompts (User-selected templates)

Users can explicitly invoke these via slash commands:

- **`explain_ownership_structure`** - Analyze parcel ownership
- **`property_report`** - Generate comprehensive property report
- **`compare_parcels`** - Compare multiple parcels
- **`land_use_summary`** - Analyze land use distribution

## Installation

### 1. Install Dependencies

```bash
# From project root
pip install -e .
```

This installs:
- `mcp>=2,<3` - MCP Python SDK v2 (`MCPServer`, formerly `FastMCP`)
- `fastapi>=0.115.0` - For HTTP transport
- `uvicorn[standard]>=0.32.0` - ASGI server
- All existing cadastral API dependencies

### 2. Configure Environment

Create or update your `.env` file:

```bash
# Use local test server (default - RECOMMENDED)
CADASTRAL_API_BASE_URL=http://localhost:8000

# Optional: Language setting
CADASTRAL_LANG=hr

# Optional: HTTP server configuration
MCP_HTTP_HOST=127.0.0.1
MCP_HTTP_PORT=8080
```

**⚠️ Configure another API URL only after verifying your rights to use that server (see `docs/legal.md`); use at your own risk.**

## Usage

The MCP server supports two transport modes:

### STDIO Mode (Claude Desktop Integration)

For local integration with Claude Desktop or other MCP clients:

```bash
# Run MCP server with STDIO transport
cadastral-mcp --transport stdio

# Or with Python module
python -m mcp.main --transport stdio
```

#### Claude Desktop Configuration

Add to your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cadastral": {
      "command": "cadastral-mcp",
      "args": ["--transport", "stdio"],
      "env": {
        "CADASTRAL_API_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

Or with full Python path:

```json
{
  "mcpServers": {
    "cadastral": {
      "command": "/path/to/your/venv/bin/python",
      "args": ["-m", "mcp.main", "--transport", "stdio"],
      "env": {
        "CADASTRAL_API_BASE_URL": "http://localhost:8000"
      }
    }
  }
}
```

Restart Claude Desktop to load the server.

### HTTP Mode (Web/Remote Access)

For web applications or remote access via FastAPI:

```bash
# Run on default host and port (127.0.0.1:8080)
cadastral-mcp --transport http

# Custom host and port
cadastral-mcp --transport http --host 0.0.0.0 --port 8080

# With debug logging
cadastral-mcp --transport http --log-level DEBUG
```

#### HTTP Endpoints

Once running, the server provides:

- **Health Check**: `GET http://localhost:8080/health`
- **Capabilities**: `GET http://localhost:8080/mcp/capabilities`
- **MCP SSE**: `POST http://localhost:8080/mcp/sse` (for MCP clients)

Test the health endpoint:

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "server": "cadastral-mcp-server",
  "version": "0.1.0",
  "api_base_url": "http://localhost:8000"
}
```

## Example Interactions

### Using Tools

When integrated with Claude Desktop, you can interact naturally:

**User**: "Find parcel 103/2 in SAVAR"

**Claude** (invokes `find_parcel` tool):
```json
{
  "parcel_id": "...",
  "parcel_number": "103/2",
  "municipality": "SAVAR",
  "address": "...",
  "area": "1234 m²",
  "success": true
}
```

**User**: "Get detailed information about this parcel including owners"

**Claude** (uses `cadastral://parcel/{id}` resource):
Returns full parcel details with ownership records.

**User**: "Show me the parcel boundaries"

**Claude** (invokes `get_parcel_geometry` tool):
Returns GeoJSON or WKT geometry data.

**User**: "Get information about parcels 103/2, 45, and 396/1 in SAVAR"

**Claude** (invokes `get_parcel` tool):
```json
{
  "results": [
    {
      "status": "success",
      "data": {
        "parcel_number": "103/2",
        "municipality": "SAVAR",
        "area": "1234",
        "...": "..."
      }
    },
    {
      "status": "success",
      "data": {
        "parcel_number": "45",
        "...": "..."
      }
    },
    {
      "status": "success",
      "data": {
        "parcel_number": "396/1",
        "...": "..."
      }
    }
  ],
  "total": 3,
  "successful": 3,
  "failed": 0
}
```

Claude then presents all three parcels in a formatted response, comparing their areas, land use, and ownership information.

### Using Prompts

**User**: "/explain_ownership_structure {parcel_id}"

Claude receives a structured prompt with ownership data and analyzes:
- Who owns the parcel
- Ownership percentages
- Co-ownership situations
- Unusual ownership patterns

**User**: "/property_report {parcel_id}"

Claude generates a comprehensive report including:
- Executive summary
- Land use breakdown
- Ownership structure
- Development potential
- Notable features

**User**: "/compare_parcels {parcel_id_1} {parcel_id_2}"

Claude compares multiple parcels across:
- Size and total area
- Land use differences
- Development potential
- Ownership complexity
- Market value considerations

## Architecture

### Design Principles

1. **Stateless by Default**: Each request is self-contained
   - Enables horizontal scaling
   - Perfect for serverless deployment
   - No session affinity required

2. **Capability Aggregation**: Higher-level abstractions
   - `find_parcel` aggregates: municipality lookup → parcel search → basic info
   - Reduces context window usage
   - Simplifies AI reasoning

3. **Reuse Existing SDK**: No code duplication
   - Imports from `cadastral_api` package
   - Leverages Pydantic V2 models for automatic schema generation
   - Uses existing rate limiting and caching

4. **Error Handling**: Defensive coding
   - All logs to stderr (never stdout in STDIO mode)
   - Sanitized, user-friendly error messages
   - Full error details logged for debugging

### Project Structure

```text
src/mcp/
├── __init__.py          # Package exports
├── config.py            # Configuration from environment
├── server.py            # Main MCPServer with all primitives
├── resources.py         # Resource implementations
├── tools.py             # Tool implementations
├── prompts.py           # Prompt templates
├── http_server.py       # FastAPI HTTP transport
└── main.py              # CLI entry point
```

### Data Flow

```text
User Query
    ↓
Claude Desktop (MCP Host)
    ↓
MCP Client (STDIO/HTTP)
    ↓
Cadastral MCP Server
    ↓
CadastralAPIClient (SDK)
    ↓
Mock Server / API (http://localhost:8000)
```

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=mcp
```

### Debugging

Enable debug logging:

```bash
cadastral-mcp --transport stdio --log-level DEBUG
```

**Important**: All logs go to stderr, not stdout. Check your terminal's error output.

### Adding New Tools

1. Add method to `CadastralTools` class in [tools.py](../src/mcp/tools.py)
2. Register in `create_mcp_server()` in [server.py](../src/mcp/server.py):

```python
@mcp.tool()
async def my_new_tool(param: str) -> dict[str, Any]:
    """Tool description for AI."""
    return await tools_handler.my_new_tool(param)
```

1. MCPServer automatically generates JSON schema from type annotations

### Adding New Prompts

1. Add method to `CadastralPrompts` class in [prompts.py](../src/mcp/prompts.py)
2. Register in `create_mcp_server()`:

```python
@mcp.prompt()
async def my_new_prompt(param: str) -> str:
    """Prompt description."""
    return await prompts_handler.my_new_prompt(param)
```

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CADASTRAL_API_BASE_URL` | `http://localhost:8000` | API base URL |
| `CADASTRAL_API_TIMEOUT` | `10.0` | Request timeout (seconds) |
| `CADASTRAL_API_RATE_LIMIT` | `0.75` | Rate limit between requests (seconds) |
| `CADASTRAL_LANG` | `hr` | Language: hr, en, de, it |
| `CADASTRAL_CACHE_DIR` | `~/.cadastral_api_cache` | GIS data cache directory |
| `MCP_HTTP_HOST` | `127.0.0.1` | HTTP server host |
| `MCP_HTTP_PORT` | `8080` | HTTP server port |

### CLI Arguments

```bash
cadastral-mcp --help
```

Options:
- `--transport {stdio,http}` - Transport mode (default: stdio)
- `--host HOST` - HTTP server host
- `--port PORT` - HTTP server port
- `--log-level {DEBUG,INFO,WARNING,ERROR}` - Logging level
- `--version` - Show version

## Troubleshooting

### Common Issues

**Issue**: MCP server won't start in Claude Desktop

**Solution**:
1. Check config file JSON syntax
2. Verify command path: `which cadastral-mcp`
3. Test STDIO mode manually: `cadastral-mcp --transport stdio`
4. Check Claude Desktop logs

**Issue**: "Connection refused" errors

**Solution**:
1. Ensure mock server is running: `curl http://localhost:8000/health`
2. Check `CADASTRAL_API_BASE_URL` in config
3. Verify network connectivity

**Issue**: Tools not appearing in Claude

**Solution**:
1. Restart Claude Desktop completely
2. Check server initialization logs (stderr)
3. Verify MCP server config is loaded

### Logging

The MCP server logs to **stderr only** (critical for STDIO mode):

```bash
# View logs when running STDIO mode
cadastral-mcp --transport stdio 2> mcp_server.log

# In HTTP mode, logs appear in terminal
cadastral-mcp --transport http --log-level DEBUG
```

## Security Considerations

### Rate Limiting

The server respects the configured rate limit (0.75s default) to prevent API abuse.

### CORS Configuration

In HTTP mode, CORS is configured for:
- `http://localhost:3000`
- `http://127.0.0.1:3000`
- `https://claude.ai`

Modify `config.http_cors_origins` for custom origins.

### Data Privacy

**Critical**: This server accesses land ownership data (personal information):
- Only use with mock/test servers
- Never expose to public internet without proper authorization
- Respect Croatian data protection laws (GDPR)

## Resources

- **MCP Specification**: <https://spec.modelcontextprotocol.io/>
- **MCP Python SDK**: <https://github.com/modelcontextprotocol/python-sdk>
- **Claude Desktop**: <https://claude.ai/download>
- **Project Documentation**: [../README.md](../README.md)
- **API Documentation**: [../specs/Croatian_Cadastral_API_Specification.md](../specs/Croatian_Cadastral_API_Specification.md)

## License

Same as parent project - for educational/demonstration purposes only.

## Support

For issues or questions:
1. Check existing documentation
2. Review error logs (stderr)
3. Verify configuration
4. Test with mock server first

Remember: This is a demonstration project. It should not be used with production cadastral systems.
