"""find_main_book / find_book_of_dc / find_possession_sheet return named fields only.

The server's ``/search-*`` records carry six generic keys (key1, value1, ...);
the typed models name them (main_book_id, sheet_number, ...). A tool result
must carry one spelling of each value, the named one, and numeric ids are
integers as they are everywhere else in the SDK.
"""

import asyncio
import importlib.util
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api.models.entities import (  # noqa: E402
    BookOfDCSearchResult,
    MainBookSearchResult,
    PossessionSheetSearchResult,
)

_TOOLS_PATH = REPO / "mcp" / "src" / "cadastral_mcp" / "tools.py"
_spec = importlib.util.spec_from_file_location("cadastral_mcp_tools_records", _TOOLS_PATH)
_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools)
CadastralTools = _tools.CadastralTools
RAW = _tools.RAW_SEARCH_KEYS


class _FakeClient:
    def find_main_book(self, search, office_id, institution_name):
        return [
            MainBookSearchResult.model_validate(
                {"key1": "21277", "value1": "SAVAR", "key2": "284", "value2": "ZADAR",
                 "value3": None, "displayValue1": "SAVAR, ZADAR"}
            )
        ]

    def find_book_of_dc(self, search, office_id, institution_name):
        return [
            BookOfDCSearchResult.model_validate(
                {"key1": "31", "value1": "ZADAR", "key2": "284", "value2": "ZK odjel Zadar",
                 "value3": None, "displayValue1": "ZADAR"}
            )
        ]

    def find_possession_sheet(self, sheet_number, municipality_reg_num):
        return [PossessionSheetSearchResult.model_validate({"key1": "14823725", "value1": "657"})]


def _run(coro):
    return asyncio.run(coro)


def test_main_books_carry_named_fields_only() -> None:
    res = _run(CadastralTools(_FakeClient()).find_main_book("SAVAR"))
    book = res["main_books"][0]
    assert book["main_book_id"] == 21277 and book["main_book_name"] == "SAVAR"
    assert book["institution_id"] == 284 and book["court_name"] == "ZADAR"
    assert not RAW & book.keys() and "source_fields" not in book


def test_books_of_dc_carry_named_fields_only() -> None:
    res = _run(CadastralTools(_FakeClient()).find_book_of_dc("ZADAR"))
    book = res["books_of_dc"][0]
    assert book["book_id"] == 31 and book["office_id"] == 284
    assert book["office_name"] == "ZK odjel Zadar"
    assert not RAW & book.keys()


def test_possession_sheets_carry_named_fields_only() -> None:
    res = _run(CadastralTools(_FakeClient()).find_possession_sheet("657", "334979"))
    sheet = res["possession_sheets"][0]
    assert sheet == {"possession_sheet_id": 14823725, "sheet_number": "657"}
