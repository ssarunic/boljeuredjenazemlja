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


def test_building_parcel_never_falls_back_to_a_land_parcel() -> None:
    # "56/.ZGR" is the building parcel *56; the search returns land parcels
    # only. Answering with 56/1 (another parcel, another LR unit) would be a
    # silent wrong answer, so the search fails instead.
    with pytest.raises(ValueError) as excinfo:
        _search("parcel_search_building_miss.json", "56/.ZGR")
    message = str(excinfo.value)
    assert "building parcel" in message
    assert "56/1" in message


def test_empty_sub_number_is_dropped_before_searching() -> None:
    # "56/" is not a parcel number; without the trailing slash the building
    # parcel *56 is found exactly.
    result, client = _search("parcel_search_building_56.json", "56/.ZGR")
    assert client.searched == "*56"
    assert result["parcel_number"] == "*56"
    assert result["exact_match"] is True
    assert result["is_building_parcel"] is True


def test_prefix_match_is_preferred_over_a_mere_substring() -> None:
    # The server matches on a substring: "973" also returns 1973, which is
    # first in the response. The parcels that begin with 973 come first.
    result, _ = _search("parcel_search_substring.json", "973")
    assert result["exact_match"] is False
    assert result["parcel_number"] == "973/2"
    assert result["other_matches"] == ["973/1"]  # 1973 only contains "973"
    assert "begins with" in result["match_note"]


def test_substring_match_says_it_is_not_a_prefix() -> None:
    # Nothing begins with "73"; the note must not claim a prefix match.
    result, _ = _search("parcel_search_substring.json", "73")
    assert result["exact_match"] is False
    assert result["parcel_number"] == "1973"
    assert "merely contains" in result["match_note"]
    assert result["other_matches"] == ["973/2", "973/1"]


def test_land_parcel_that_exists_only_as_a_building_parcel_names_the_zgr_spelling() -> None:
    with pytest.raises(ValueError) as excinfo:
        _search("parcel_search_bare_building.json", "35/1")
    assert "35/1 ZGR" in str(excinfo.value)
