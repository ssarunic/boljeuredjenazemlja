"""A unit with no entry in the electronic diary has no ``lastDiaryNumber`` key."""

from __future__ import annotations

import json
from pathlib import Path

from cadastral_api.models.entities import LandRegistryUnitDetailed

FIXTURES = Path(__file__).resolve().parents[2] / "src" / "cadastral_api" / "tests" / "fixtures"


def _unit_without_diary_number() -> dict:
    data = json.loads((FIXTURES / "lr_unit_cadparcels.json").read_text())
    unit = data[0] if isinstance(data, list) else data
    del unit["lastDiaryNumber"]  # the server omits the key, it does not send null
    return unit


def test_unit_without_last_diary_number_validates() -> None:
    unit = LandRegistryUnitDetailed.model_validate(_unit_without_diary_number())

    assert unit.last_diary_number is None
    assert unit.ownership_sheet_b.lr_unit_shares  # the rest of the unit is intact


def test_last_diary_number_still_read_when_present() -> None:
    data = _unit_without_diary_number()
    data["lastDiaryNumber"] = "Z-32597/2025"

    assert LandRegistryUnitDetailed.model_validate(data).last_diary_number == "Z-32597/2025"
