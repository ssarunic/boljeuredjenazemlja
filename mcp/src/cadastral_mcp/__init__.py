"""
MCP (Model Context Protocol) Server for Cadastral/Land Registry Queries.

This module provides an MCP server that wraps the Croatian Cadastral API,
enabling AI agents to query land registry and parcel information through
standardized MCP primitives: Resources, Tools, and Prompts.

IMPORTANT: This MCP server is for educational/demonstration purposes only.
It connects to the localhost mock server by default. Do NOT configure it
to use Croatian government production systems - this violates terms of
service and involves sensitive personal data.
"""

from .server import create_mcp_server

__all__ = ["create_mcp_server"]
