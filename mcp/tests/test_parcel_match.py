"""find_parcel must not pass a prefix match off as the parcel that was asked for.

The server matches on the prefix, so a number that does not exist ("973") comes
back as a longer one (973/1). The response says which happened, and every
spelling of a building parcel ("35/1.ZGR") still resolves to "*35/1" exactly.
"""

import asyncio
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api.models.entities import ParcelSearchResult  # noqa: E402

_TOOLS_PATH = REPO / "mcp" / "src" / "cadastral_mcp" / "tools.py"
_spec = importlib.util.spec_from_file_location("cadastral_mcp_tools_match", _TOOLS_PATH)
_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools)
CadastralTools = _tools.CadastralTools

FIXTURES = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures"


class _FakeClient:
    """Serves a search fixture and records what number was actually searched."""

    def __init__(self, fixture: str) -> None:
        raw = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
        self.results = [ParcelSearchResult.model_validate(item) for item in raw]
        self.searched: str | None = None

    def find_parcel(self, parcel_number: str, municipality_reg_num: str):
        self.searched = parcel_number
        return self.results

    def get_parcel_geometry(self, *args, **kwargs):  # no GIS cache in tests
        raise RuntimeError("no geometry")


def _search(fixture: str, number: str) -> tuple[dict, _FakeClient]:
    client = _FakeClient(fixture)
    result = asyncio.run(CadastralTools(client).search_parcel(number, "334979"))
    return result, client


def test_prefix_match_is_reported_not_hidden() -> None:
    # "1072" does not exist; the fixture returns 1072/1, 1072/10, ...
    result, _ = _search("parcel_search_prefix.json", "1072")
    assert result["exact_match"] is False
    assert result["requested_parcel_number"] == "1072"
    assert result["parcel_number"] == "1072/1"
    assert "1072" in result["match_note"]
    assert "1072/1" in result["match_note"]
    assert "1072/10" in result["other_matches"]
    assert len(result["other_matches"]) <= CadastralTools.MAX_OTHER_MATCHES


def test_exact_match_carries_no_warning() -> None:
    result, _ = _search("parcel_search_prefix.json", "1072/1")
    assert result["exact_match"] is True
    assert result["requested_parcel_number"] == "1072/1"
    assert "match_note" not in result
    assert "other_matches" not in result


@pytest.mark.parametrize("spelling", ["35/1.ZGR", "35/1 ZGR", "zgr. 35/1", "*35/1"])
def test_building_parcel_spellings_resolve_exactly(spelling: str) -> None:
    # The fixture also holds 135/1, which the asterisk wildcard drags in.
    result, client = _search("parcel_search_building.json", spelling)
    assert client.searched == "*35/1"  # the API spelling was sent
    assert result["parcel_number"] == "*35/1"
    assert result["requested_parcel_number"] == "*35/1"
    assert result["exact_match"] is True
    assert result["is_building_parcel"] is True
