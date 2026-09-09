"""List C output shows the persons an entry is registered in favour of."""

from __future__ import annotations

import json

from cadastral_api.i18n import set_language
from cadastral_api.models.entities import LandRegistryUnitDetailed

from cadastral_cli.commands.registry import _format_structured_data
from cadastral_cli.lr_unit_output import console, print_lr_unit_encumbrance_sheet

UNIT = {
    "lrUnitId": 13122441,
    "lrUnitNumber": "657",
    "mainBookId": 21277,
    "mainBookName": "SAVAR",
    "institutionId": 1,
    "institutionName": "Zemljišnoknjižni odjel Zadar",
    "status": "0",
    "statusName": "Aktivan",
    "condominiums": False,
    "lrUnitTypeId": 1,
    "lrUnitTypeName": "VLASNIČKI",
    "cadastreMunicipalityId": 334979,
    "verificated": True,
    "lastDiaryNumber": "Z-1/2026",
    "ownershipSheetB": {"lrUnitShares": [], "lrEntries": []},
    "possessionSheetA1": {"cadParcels": []},
    "possessionSheetA2": {"lrEntries": []},
    "encumbranceSheetC": {
        "lrEntryGroups": [
            {
                "description": "Na cijelo",
                "shareOrderNumber": None,
                "lrEntries": [
                    {
                        "description": (
                            "Pr. 20. srpnja 1979. Z 2444/79<br>uknjižuje se pravo "
                            "ploduživanja u korist:"
                        ),
                        "lrEntryId": 93357927,
                        "orderNumber": "2.1",
                        "lrOwners": [
                            {"lrOwnerId": 7, "name": "TEST OSOBA", "address": "SAVAR"}
                        ],
                    }
                ],
            }
        ]
    },
}


def test_json_entries_carry_beneficiaries_and_source_fields() -> None:
    set_language("en")
    unit = LandRegistryUnitDetailed.model_validate(UNIT)
    data = _format_structured_data(unit, False, False, True, False)
    group = data["encumbrances"][0]
    assert group["share_order_number"] is None
    assert group["right_type"] == "usufruct"
    entry = group["entries"][0]
    assert entry["order_number"] == "2.1"
    assert entry["action_type"] == "upis"
    assert entry["diary_number"] == "Z-2444/79"
    assert entry["entry_date"] == "1979-07-20"
    assert entry["basis_document"] is None  # fixture text has no "Na temelju"
    assert entry["basis_date"] is None
    assert entry["beneficiaries"] == [
        {
            "name": "TEST OSOBA",
            "name_normalized": "Test Osoba",
            "share": None,
            "address": "SAVAR",
            "tax_number": None,
        }
    ]
    assert "source_fields" not in entry  # lrOwners is a declared field now
    json.dumps(data)  # serializable


def test_table_prints_in_favour_of_block() -> None:
    set_language("en")
    unit = LandRegistryUnitDetailed.model_validate(UNIT)
    with console.capture() as capture:
        print_lr_unit_encumbrance_sheet(unit)
    text = capture.get()
    assert "2.1" in text
    assert "In favour of" in text
    assert "TEST OSOBA, SAVAR" in text


def test_table_in_croatian() -> None:
    set_language("hr")
    try:
        unit = LandRegistryUnitDetailed.model_validate(UNIT)
        with console.capture() as capture:
            print_lr_unit_encumbrance_sheet(unit)
        assert "U korist" in capture.get()
    finally:
        set_language("en")
