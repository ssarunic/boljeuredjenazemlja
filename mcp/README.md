# cadastral_mcp: MCP server

Model Context Protocol server that lets Claude Desktop and other MCP clients look
up parcels, owners, land registry units, encumbrances, and geometry.

```bash
pip install -e ./api -e ./mcp
cadastral-mcp --transport stdio
```

Claude Desktop configuration and a tool-by-tool guide:
[docs/mcp-usage-guide.md](../docs/mcp-usage-guide.md). Architecture:
[specs/mcp-server.md](../specs/mcp-server.md).

The `--transport http` mode is a placeholder. A hosted REST and remote MCP service
is specified in [specs/gateway-service.md](../specs/gateway-service.md).

Runs against the included mock server only; see [docs/legal.md](../docs/legal.md).
