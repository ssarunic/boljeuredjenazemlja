"""
MCP (Model Context Protocol) Server for Cadastral/Land Registry Queries.

This module provides an MCP server that wraps the Croatian Cadastral API,
enabling AI agents to query land registry and parcel information through
standardized MCP primitives: Resources, Tools, and Prompts.

IMPORTANT: This MCP server is an educational demonstration. It connects to
the localhost mock server by default. Before configuring any other server,
including the Croatian government systems, verify that you have the rights
to use it and its data (terms of service, data protection); you do so at
your own risk. See docs/legal.md.
"""

from .server import create_mcp_server

__all__ = ["create_mcp_server"]
