"""Regression tests for cadastral parcel-info (/cad/parcel-info) parsing.

The fixture ``fixtures/parcel_info_1122_1.json`` is a real response for parcel
1122/1, k.o. SAVAR (parcel id 6566195), with possessor personal data redacted.

This parcel is a useful contract case because it has ``lrUnit: null`` while its
land-registry unit is reachable only via ``lrUnitsFromParcelLinks`` — the exact
shape the F3 fallback work depends on.
"""

import json
from pathlib import Path

import pytest

from cadastral_api.models.entities import ParcelInfo

FIXTURE = Path(__file__).parent / "fixtures" / "parcel_info_1122_1.json"


@pytest.fixture
def parcel_1122_1() -> ParcelInfo:
    return ParcelInfo.model_validate(json.loads(FIXTURE.read_text(encoding="utf-8")))


def test_parcel_info_parses(parcel_1122_1: ParcelInfo) -> None:
    assert parcel_1122_1.parcel_number == "1122/1"


def test_cadastre_lr_harmonization_flag(parcel_1122_1: ParcelInfo) -> None:
    """1122/1 is NOT harmonized - the signal that cadastre and ZK may differ
    (and indeed its possessors differ from its registered owners)."""
    assert parcel_1122_1.is_harmonized is False


def test_lr_unit_null_but_resolvable_via_links(parcel_1122_1: ParcelInfo) -> None:
    """F3 scenario: no direct lr_unit, but parcel_links carry the LR unit."""
    assert parcel_1122_1.lr_unit is None
    assert parcel_1122_1.parcel_links, "expected parcel_links to be populated"
    assert parcel_1122_1.lr_units_from_parcel_links, "expected link-derived LR units"


def test_possession_sheet_possessors_parse(parcel_1122_1: ParcelInfo) -> None:
    """Cadastre possessors (posjedovni list) must parse, with their shares."""
    sheets = parcel_1122_1.possession_sheets
    assert sheets
    possessors = sheets[0].possessors
    assert possessors
    # ownership fraction is present on this parcel's possessors (as a raw string)
    assert any(p.ownership for p in possessors)
