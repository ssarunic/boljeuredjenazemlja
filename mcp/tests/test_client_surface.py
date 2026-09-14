"""Every SDK method the MCP server calls must exist on CadastralAPIClient.

The resources and prompts once called ``get_parcel_by_id`` and
``search_municipalities``, which the SDK never had; nothing exercised them, so
every parcel resource and every prompt failed at runtime. This reads the MCP
sources and checks each ``self.client.<name>(`` against the real client.
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api import CadastralAPIClient  # noqa: E402

MCP_SRC = REPO / "mcp" / "src" / "cadastral_mcp"
CALL = re.compile(r"self\.client\.([a-zA-Z_][a-zA-Z0-9_]*)\b")


def test_every_client_call_names_a_real_client_member() -> None:
    missing: set[str] = set()
    for source in MCP_SRC.glob("*.py"):
        for name in CALL.findall(source.read_text(encoding="utf-8")):
            if not hasattr(CadastralAPIClient, name) and name not in _instance_attributes():
                missing.add(f"{source.name}: {name}")
    assert not missing, f"MCP calls members CadastralAPIClient does not have: {sorted(missing)}"


def _instance_attributes() -> set[str]:
    """Attributes set in __init__ (``gis_cache`` ...), invisible on the class."""
    init_source = Path(CadastralAPIClient.__init__.__code__.co_filename).read_text(
        encoding="utf-8"
    )
    return set(re.findall(r"self\.([a-zA-Z_][a-zA-Z0-9_]*)\s*=", init_source))
