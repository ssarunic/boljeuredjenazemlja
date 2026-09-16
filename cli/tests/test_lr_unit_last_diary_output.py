"""The basic-info table and the JSON cope with a unit that has no last diary number."""

from __future__ import annotations

import json
from pathlib import Path

from cadastral_api.i18n import set_language
from cadastral_api.models.entities import LandRegistryUnitDetailed

from cadastral_cli.commands.registry import _format_structured_data
from cadastral_cli.lr_unit_output import console, print_lr_unit_basic_info

FIXTURES = (
    Path(__file__).resolve().parents[2] / "api" / "src" / "cadastral_api" / "tests" / "fixtures"
)


def _unit() -> LandRegistryUnitDetailed:
    data = json.loads((FIXTURES / "lr_unit_cadparcels.json").read_text())
    unit = data[0] if isinstance(data, list) else data
    del unit["lastDiaryNumber"]
    return LandRegistryUnitDetailed.model_validate(unit)


def test_table_prints_empty_last_diary_row() -> None:
    set_language("en")
    with console.capture() as capture:
        print_lr_unit_basic_info(_unit())
    assert "Last Diary Number" in capture.get()


def test_json_has_null_last_diary_number() -> None:
    set_language("en")
    payload = _format_structured_data(_unit(), show_owners=False, show_parcels=False,
                                      show_encumbrances=False, show_all=False)
    assert payload["last_diary_number"] is None
