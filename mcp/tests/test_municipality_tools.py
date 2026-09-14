"""resolve_municipality returns the complete record; list_municipalities filters and pages."""

import asyncio
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api.models.entities import MunicipalitySearchResult  # noqa: E402

_TOOLS_PATH = REPO / "mcp" / "src" / "cadastral_mcp" / "tools.py"
_spec = importlib.util.spec_from_file_location("cadastral_mcp_tools_muni", _TOOLS_PATH)
_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools)
CadastralTools = _tools.CadastralTools

RECORDS = [
    {"key1": "2387", "value1": "334979 SAVAR", "key2": "334979", "value2": "114",
     "value3": "116", "displayValue1": "334979 SAVAR, ZADAR, PUK ZADAR"},
    {"key1": "2388", "value1": "334731 LUKA", "key2": "334731", "value2": "114",
     "value3": "116", "displayValue1": "334731 LUKA, ZADAR, PUK ZADAR"},
    {"key1": "2389", "value1": "300001 LUKA VRBOVEČKA", "key2": "300001", "value2": "120",
     "value3": "121", "displayValue1": "300001 LUKA VRBOVEČKA, VRBOVEC, PUK ZAGREB"},
]


class _FakeClient:
    """Filters the three records the way the server does (substring, office, department)."""

    def __init__(self) -> None:
        self.all = [MunicipalitySearchResult.model_validate(r) for r in RECORDS]
        self.calls: list[tuple] = []

    def find_municipality(self, search_term=None, office_id=None, department_id=None):
        self.calls.append((search_term, office_id, department_id))
        rows = self.all
        if office_id is not None:
            rows = [m for m in rows if m.institution_id == int(office_id)]
        if department_id is not None:
            rows = [m for m in rows if m.department_id == int(department_id)]
        if search_term:
            rows = [m for m in rows if search_term.lower() in m.code_and_name.lower()]
        return rows


@pytest.fixture
def client() -> _FakeClient:
    return _FakeClient()


@pytest.fixture
def tools(client) -> "CadastralTools":
    return CadastralTools(client)


def test_resolve_returns_the_complete_record(tools, client) -> None:
    record = asyncio.run(tools.resolve_municipality("SAVAR"))
    assert record == {
        "code": "334979",
        "name": "SAVAR",
        "full_name": "334979 SAVAR, ZADAR, PUK ZADAR",
        "municipality_id": 2387,
        "office_id": 114,
        "department_id": 116,
    }
    # One request, by the name given; no full listing to find the code.
    assert client.calls == [("SAVAR", None, None)]


def test_resolve_by_code_picks_the_exact_code(tools) -> None:
    record = asyncio.run(tools.resolve_municipality("334731"))
    assert record["name"] == "LUKA"
    assert "other_matches" not in record


def test_resolve_names_the_other_matches(tools) -> None:
    record = asyncio.run(tools.resolve_municipality("LUKA"))
    assert record["code"] == "334731"
    assert record["matches_total"] == 2
    assert [m["name"] for m in record["other_matches"]] == ["LUKA VRBOVEČKA"]


def test_resolve_unknown_is_an_error(tools) -> None:
    with pytest.raises(ValueError):
        asyncio.run(tools.resolve_municipality("NOWHERE"))


def test_list_filters_by_office_and_department(tools, client) -> None:
    result = asyncio.run(tools.list_municipalities(office_id=114, department_id="116"))
    assert [m["code"] for m in result["municipalities"]] == ["334979", "334731"]
    assert result["total"] == 2
    assert result["page"]["truncated"] is False
    assert client.calls[-1] == (None, 114, "116")


def test_list_pages(tools) -> None:
    first = asyncio.run(tools.list_municipalities(limit=2))
    assert first["total"] == 3
    assert first["page"] == {
        "offset": 0, "limit": 2, "total": 3, "returned": 2, "truncated": True, "next_offset": 2
    }
    rest = asyncio.run(tools.list_municipalities(offset=first["page"]["next_offset"], limit=2))
    assert [m["code"] for m in rest["municipalities"]] == ["300001"]
    assert rest["page"]["truncated"] is False
    everything = asyncio.run(tools.list_municipalities(limit=None))
    assert everything["page"]["returned"] == 3


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"offset": -1}])
def test_list_rejects_bad_paging(tools, kwargs) -> None:
    with pytest.raises(ValueError):
        asyncio.run(tools.list_municipalities(**kwargs))
