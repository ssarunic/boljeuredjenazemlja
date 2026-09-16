"""What an MCP client receives from ``tools/list``, ``prompts/list`` and ``initialize``.

The model chooses and calls tools from this data alone, so every parameter
needs a description in the schema, every choice parameter an enum, the server
an ``instructions`` text, and every prompt a description that says what it is
for. The docstrings must not repeat the parameters in an ``Args:`` block: that
text lives in the schema now, and repeating it costs context on every call.
"""

import asyncio
import logging
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))
sys.path.insert(0, str(REPO / "mcp" / "src"))

logging.disable(logging.CRITICAL)

from cadastral_mcp.server import SERVER_INSTRUCTIONS, create_mcp_server  # noqa: E402

CHOICES = {
    ("get_parcel", "source"): {"cadastre", "land_registry", "none"},
    ("get_lr_unit", "detail"): {
        "summary", "ownership", "shares", "parcels", "encumbrances", "full"
    },
    ("get_parcel_geometry", "format"): {"geojson", "wkt", "dict"},
    ("find_parcels_in_area", "relation"): {"intersects", "within"},
    ("build_assembly", "export"): {
        "parcels_csv", "persons_csv", "matrix_csv", "blockers_csv", "geojson"
    },
}


@pytest.fixture(scope="module")
def surface():
    mcp = create_mcp_server()

    async def collect():
        return await mcp.list_tools(), await mcp.list_prompts()

    tools, prompts = asyncio.run(collect())
    return mcp, {t.name: t for t in tools}, {p.name: p for p in prompts}


def _enum_of(prop: dict) -> set[str] | None:
    if "enum" in prop:
        return set(prop["enum"])
    for option in prop.get("anyOf", []):
        if "enum" in option:
            return set(option["enum"])
    return None


def test_server_sends_instructions(surface) -> None:
    mcp, _, _ = surface
    assert mcp.instructions == SERVER_INSTRUCTIONS
    assert "get_lr_unit" in SERVER_INSTRUCTIONS and "posjednik" in SERVER_INSTRUCTIONS.lower()


def test_every_parameter_has_a_schema_description(surface) -> None:
    _, tools, _ = surface
    missing = [
        f"{name}.{param}"
        for name, tool in tools.items()
        for param, prop in tool.input_schema["properties"].items()
        if not prop.get("description")
    ]
    assert not missing, missing


def test_reference_models_describe_their_fields(surface) -> None:
    _, tools, _ = surface
    missing = []
    for name, tool in tools.items():
        for model, definition in tool.input_schema.get("$defs", {}).items():
            for field, prop in definition["properties"].items():
                if not prop.get("description"):
                    missing.append(f"{name}.{model}.{field}")
    assert not missing, missing


def test_choice_parameters_are_enums(surface) -> None:
    _, tools, _ = surface
    for (name, param), expected in CHOICES.items():
        prop = tools[name].input_schema["properties"][param]
        assert _enum_of(prop) == expected, f"{name}.{param}: {prop}"


def test_tool_descriptions_do_not_repeat_the_parameters(surface) -> None:
    _, tools, _ = surface
    repeated = [name for name, tool in tools.items() if "Args:" in (tool.description or "")]
    assert not repeated, repeated


def test_prompts_say_what_they_are_for(surface) -> None:
    _, _, prompts = surface
    for name, prompt in prompts.items():
        text = " ".join((prompt.description or "").split())
        assert len(text) > 120, f"{name}: {text!r}"
        assert not text.startswith("Generate a"), f"{name}: {text!r}"
        assert "parcel_id" in text, f"{name}: does not say where the argument comes from"


def test_tool_surface_stays_within_budget(surface) -> None:
    """The whole tool list is read on every conversation; keep it under ~12k tokens."""
    import json

    _, tools, _ = surface
    chars = sum(
        len(t.description or "") + len(json.dumps(t.input_schema)) for t in tools.values()
    )
    assert chars < 48_000, chars
