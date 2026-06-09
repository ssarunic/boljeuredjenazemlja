# Cadastral MCP Server

Model Context Protocol (MCP) server for AI agent integration with the Croatian Cadastral System API.

## Features

- MCP-compliant server for AI agent integration
- Tools for parcel search and information retrieval
- Resources for cadastral offices and municipalities
- Prompts for common cadastral queries
- HTTP transport support

## Installation

```bash
cd mcp
pip install -e .
```

## Quick Start

```bash
# Start the MCP server
cadastral-mcp

# Or with HTTP transport
cadastral-mcp --http --port 8080
```

## Command-Line Interface

Prefer working from a terminal instead of an AI agent? The project also ships a
full-featured CLI (`cadastral`) for parcel search, detailed parcel and land
registry lookups, batch processing, and GIS data export:

```bash
# Search for a parcel
cadastral search 103/2 --municipality SAVAR

# Get detailed information with owners
cadastral get-parcel 103/2 -m 334979 --show-owners

# Get a land registry unit
cadastral get-lr-unit --from-parcel 279/6 -m SAVAR --all
```

See [CLI Reference](../docs/cli-reference.md) for the complete command reference.

## Documentation

- [MCP Server Documentation](docs/mcp-server.md)
- [CLI Reference](../docs/cli-reference.md)

## License

MIT
