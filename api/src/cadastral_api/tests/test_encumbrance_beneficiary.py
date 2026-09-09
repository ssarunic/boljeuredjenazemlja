"""Sheet C beneficiaries, including the ones named only in the entry text.

A charge in favour of a legal person is often registered with an empty
``lrOwners``: the name lives in the prose ("... za korist REPUBLIKE HRVATSKE").
Reading only ``lrOwners`` left every such charge without a beneficiary.
"""

import json
from pathlib import Path

import pytest

from cadastral_api.models.entities import (
    EncumbranceGroup,
    LandRegistryUnitDetailed,
    RightType,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _unit(name: str) -> LandRegistryUnitDetailed:
    raw = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)


def test_beneficiary_read_from_entry_text_when_lr_owners_is_empty() -> None:
    unit = _unit("lr_unit_encumbrances.json")
    groups = unit.encumbrance_sheet_c.lr_entry_groups
    assert groups, "fixture must carry a sheet C group"
    group = groups[0]
    assert group.lr_entries[0].owners == []  # the server sent no person record
    assert group.right_type == RightType.LIEN
    assert group.beneficiary is not None
    assert group.beneficiary.name == "REPUBLIKE HRVATSKE"
    assert group.beneficiary_source == "description"
    assert group.get_parties()[0].name == "REPUBLIKE HRVATSKE"


def test_lr_owners_win_over_the_text_and_are_reported_as_such() -> None:
    unit = _unit("lr_unit_condominium.json")
    with_owners = [
        group
        for group in unit.encumbrance_sheet_c.lr_entry_groups
        if any(entry.owners for entry in group.lr_entries)
    ]
    assert with_owners, "fixture must carry a group with lrOwners"
    for group in with_owners:
        assert group.beneficiary_source == "lr_owners"
        assert group.beneficiary.name == group.lr_entries[0].owners[0].name


@pytest.mark.parametrize(
    "description",
    [
        "zabilježuje se zabrana opterećenja stana.",  # names nobody
        "uknjižuje se pravo ploduživanja u korist:",  # name would be in lrOwners
    ],
)
def test_no_beneficiary_is_invented(description: str) -> None:
    group = EncumbranceGroup.model_validate(
        {
            "description": "1. Na suvlasnički dio: 1/1",
            "lrEntries": [{"description": description, "orderNumber": "1.1"}],
        }
    )
    assert group.beneficiary is None
    assert group.beneficiary_source is None
