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

## Documentation

- [MCP Server Documentation](docs/mcp-server.md)

## License

MIT
