"""Regression tests for land-registry unit (Sheet A1) parsing.

Guards against a silent alias-drift bug: the live API returns the parcel list
under ``possessionSheetA1.lrParcels`` with a lean parcel shape, while the model
previously expected ``cadParcels`` with a richer shape. The mismatch made
``cad_parcels`` fall back to an empty list, so ``summary()`` reported
``total_parcels == 0`` / ``total_area_m2 == 0`` despite the unit having parcels.

The fixture ``fixtures/lr_unit_449_21277.json`` is a real response for k.o. SAVAR
LR unit 449 (book 21277), with all Sheet B personal data (names, addresses, tax
numbers) redacted. The Sheet A1 parcel data is preserved as returned by the API.
"""

import json
from pathlib import Path

import pytest

from cadastral_api.models.entities import LandRegistryUnitDetailed, SheetAParcelList

FIXTURE = Path(__file__).parent / "fixtures" / "lr_unit_449_21277.json"


@pytest.fixture
def unit_449() -> LandRegistryUnitDetailed:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    payload = raw[0] if isinstance(raw, list) else raw
    return LandRegistryUnitDetailed.model_validate(payload)


def test_sheet_a1_parcels_are_parsed(unit_449: LandRegistryUnitDetailed) -> None:
    """The live ``lrParcels`` key must populate cad_parcels (not fall back to [])."""
    parcels = unit_449.possessory_sheet_a1.cad_parcels
    assert len(parcels) == 1
    assert parcels[0].parcel_number == "1122/1"


def test_summary_reports_real_totals(unit_449: LandRegistryUnitDetailed) -> None:
    """The original bug: these came back as 0 because Sheet A1 parsed empty."""
    summary = unit_449.summary()
    assert summary["total_parcels"] == 1
    assert summary["total_area_m2"] == 3291


def test_lean_a1_parcel_shape_validates() -> None:
    """The Sheet A1 parcel shape omits municipality/institution fields entirely."""
    lean = {
        "parcelId": 36370854,
        "parcelNumber": "1122/1",
        "address": "OVČJA",
        "area": "3291",
        "statusInLrUnit": 0,
        "parcelParts": [],
    }
    sheet = SheetAParcelList.model_validate({"lrParcels": [lean]})
    assert sheet.total_area() == 3291
    assert sheet.cad_parcels[0].cad_municipality_id is None


def test_legacy_cadparcels_alias_still_accepted() -> None:
    """Hand-authored mock fixtures use the legacy ``cadParcels`` key."""
    legacy = {"parcelId": 1, "parcelNumber": "1/1", "area": "100"}
    sheet = SheetAParcelList.model_validate({"cadParcels": [legacy]})
    assert len(sheet.cad_parcels) == 1
    assert sheet.total_area() == 100
