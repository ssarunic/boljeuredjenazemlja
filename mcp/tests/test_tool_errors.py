"""A handler's error message reaches the client instead of "Error executing tool".

The MCP SDK withholds the message of any exception that is not a ``ToolError``
(or ``ResourceError`` for resources). The handlers raise ``ValueError`` with a
message written for the agent, so every failure used to arrive as the bare
"Error executing tool <name>"; the server now converts them.
"""

import asyncio

import pytest
from mcp.server.mcpserver.exceptions import (
    ResourceError,
    ToolError,
    UnexpectedResourceError,
    UnexpectedToolError,
)

import cadastral_mcp.server as server_module


class _FakeClient:
    gis_cache = None

    def resolve_municipality_reg_num(self, name_or_code):
        raise ValueError("Municipality 'NOWHERE' not found")

    def list_cadastral_offices(self):
        return []


@pytest.fixture
def server(monkeypatch):
    monkeypatch.setattr(server_module, "CadastralAPIClient", lambda **kwargs: _FakeClient())
    return server_module.create_mcp_server()


def test_tool_failure_carries_the_handler_message(server) -> None:
    with pytest.raises(ToolError) as excinfo:
        args = {"parcel_number": "1", "municipality": "NOWHERE"}
        asyncio.run(server.call_tool("find_parcel", args))
    assert "Municipality 'NOWHERE' not found" in str(excinfo.value)
    assert not isinstance(excinfo.value, UnexpectedToolError)


def test_wrapping_keeps_the_tool_schema(server) -> None:
    tools = asyncio.run(server.list_tools())
    schema = next(t for t in tools if t.name == "find_parcel").input_schema
    assert set(schema["properties"]) == {"parcel_number", "municipality", "max_matches"}


def test_resource_failure_carries_the_handler_message(server) -> None:
    with pytest.raises(ResourceError) as excinfo:
        asyncio.run(server.read_resource("cadastral://office/999"))
    assert "999" in str(excinfo.value)
    assert not isinstance(excinfo.value, UnexpectedResourceError)


def test_get_parcel_schema_exposes_possessor_paging(server) -> None:
    tools = asyncio.run(server.list_tools())
    schema = next(t for t in tools if t.name == "get_parcel").input_schema
    assert {"parcels", "source", "offset", "limit", "possessor_name", "condominium_unit"} <= set(
        schema["properties"]
    )
    assert schema["properties"]["offset"]["default"] == 0
    assert schema["properties"]["limit"]["default"] is None


def test_get_lr_unit_schema_exposes_owner_name(server) -> None:
    tools = asyncio.run(server.list_tools())
    schema = next(t for t in tools if t.name == "get_lr_unit").input_schema
    assert {"units", "detail", "offset", "limit", "owner_name"} <= set(schema["properties"])
    assert schema["properties"]["owner_name"]["default"] is None


def test_tool_failure_names_the_kind_of_error(server) -> None:
    with pytest.raises(ToolError) as excinfo:
        args = {"parcel_number": "1", "municipality": "NOWHERE"}
        asyncio.run(server.call_tool("find_parcel", args))
    # The fake raises a plain ValueError; the SDK's typed errors keep their type.
    assert str(excinfo.value).endswith("[error_type=invalid_request]")


def test_error_kind_walks_the_chain_of_causes() -> None:
    from cadastral_api.exceptions import CadastralAPIError, ErrorType

    from cadastral_mcp.tools import ResponseTooLargeError, error_kind

    try:
        try:
            raise CadastralAPIError(ErrorType.RATE_LIMIT, details={"retry_count": 3, "x": None})
        except CadastralAPIError as e:
            raise ValueError("Could not search") from e
    except ValueError as wrapped:
        assert error_kind(wrapped) == ("rate_limit", {"retry_count": 3})
    assert error_kind(ResponseTooLargeError("big")) == ("response_too_large", {})
    assert error_kind(ValueError("bad ref")) == ("invalid_request", {})
    assert error_kind(RuntimeError("boom")) == ("internal_error", {})
