"""get_possession_sheet: possessors (paged) and the parcels of one sheet."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from cadastral_api.client.api_client import PossessionSheetParcels
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.models.entities import PossessionSheet, SearchedParcel
from cadastral_api.models.provenance import Provenance

from cadastral_mcp.tools import CadastralTools

REPO = Path(__file__).resolve().parents[2]
FIXTURES = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures"


class _FakeClient:
    SEARCH_PARCELS_OBSERVED_MAX = 30

    def __init__(self, parcels: int = 2, missing: bool = False) -> None:
        raw = json.loads((FIXTURES / "parcel_info_linked.json").read_text())
        sheet_raw = dict(raw["possessionSheets"][0])
        sheet_raw.update(cadMunicipalityRegNum="334979", cadMunicipalityName="SAVAR")
        self.sheet = PossessionSheet.model_validate(sheet_raw)
        self.sheet.provenance = Provenance("cadastre", "http://mock/cad/possession-sheet", "t")
        dropped = ("possessionSheets", "lrUnitsFromParcelLinks")
        record = {k: v for k, v in raw.items() if k not in dropped}
        record["possessionSheet"] = sheet_raw
        self.parcels = [SearchedParcel.model_validate(record) for _ in range(parcels)]
        self.missing = missing

    def get_possession_sheet_parcels(self, sheet_number, municipality):
        if self.missing:
            raise CadastralAPIError(
                ErrorType.POSSESSION_SHEET_NOT_FOUND, details={"sheet_number": sheet_number}
            )
        return PossessionSheetParcels(
            sheet=self.sheet,
            parcels=self.parcels,
            parcels_provenance=Provenance("cadastre", "http://mock/cad/search-parcels", "t"),
            maybe_truncated=len(self.parcels) >= 30,
        )


def _run(coro):
    return asyncio.run(coro)


def test_sheet_with_possessors_and_parcels() -> None:
    res = _run(CadastralTools(_FakeClient()).get_possession_sheet("363", "SAVAR", limit=2))
    assert res["sheet"]["possession_sheet_number"] and "possessors" not in res["sheet"]
    assert res["sheet"]["cad_municipality_reg_num"] == "334979"
    assert len(res["possessors"]) == 2 and res["page"]["truncated"] is True
    assert res["total_possessors"] == res["page"]["total"] > 2
    assert res["distinct_possessors"] <= res["total_possessors"]
    assert res["parcel_count"] == 2
    row = res["parcels"][0]
    assert row["parcel_number"] == "1122/1" and row["area_m2"] == 1618
    assert row["lr_unit"] == {"lr_unit_number": "449", "main_book_id": 21277}
    assert row["is_harmonized"] is False and row["inline_owners"] is None
    assert res["total_area_m2"] == 2 * 1618
    assert res["parcels_complete"] is True and "note" not in res
    assert res["provenance"]["sheet"]["register"] == "cadastre"
    assert res["provenance"]["parcels"]["source_url"].endswith("/cad/search-parcels")


def test_possessor_name_filter_and_long_sheet_note() -> None:
    client = _FakeClient(parcels=30)
    first = client.sheet.possessors[0].name
    res = _run(CadastralTools(client).get_possession_sheet("363", "SAVAR", possessor_name=first))
    assert res["matching_possessors"] >= 1 and res["possessor_filter"] == {"possessor_name": first}
    assert res["parcels_complete"] is False and "cap" in res["note"]


def test_missing_sheet_is_a_clear_error() -> None:
    with pytest.raises(ValueError) as excinfo:
        _run(CadastralTools(_FakeClient(missing=True)).get_possession_sheet("999", "SAVAR"))
    assert "999" in str(excinfo.value) and "find_possession_sheet" in str(excinfo.value)
    with pytest.raises(ValueError):
        _run(CadastralTools(_FakeClient()).get_possession_sheet(" ", "SAVAR"))
