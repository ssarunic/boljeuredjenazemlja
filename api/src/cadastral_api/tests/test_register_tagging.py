"""Tests for register tagging (Phase 1: cadastre vs. land-registry).

Cadastre possessors (posjedovni list) and land-registry owners (vlastovnica /
B-list) are different registers that frequently list different people. Every
person record must carry a ``register`` field so they can never be confused.
"""

import json
from pathlib import Path

from cadastral_api.models.entities import (
    LandRegistryUnitDetailed,
    ParcelInfo,
    Party,
    Possessor,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_possessor_tagged_cadastre() -> None:
    p = Possessor(name="Test Possessor", ownership="1/2")
    assert p.model_dump()["register"] == "cadastre"


def test_party_tagged_land_registry() -> None:
    party = Party(name="Test Owner")
    assert party.model_dump()["register"] == "land_registry"


def test_parcel_info_possessors_are_cadastre() -> None:
    """Possessors from a real parcel-info response are tagged cadastre."""
    raw = json.loads((FIXTURES / "parcel_info_linked.json").read_text(encoding="utf-8"))
    parcel = ParcelInfo.model_validate(raw)
    possessors = parcel.possession_sheets[0].possessors
    assert possessors
    assert all(p.model_dump()["register"] == "cadastre" for p in possessors)


def test_lr_unit_owners_are_land_registry() -> None:
    """B-list owners from a real LR-unit response are tagged land_registry."""
    raw = json.loads((FIXTURES / "lr_unit_lrparcels.json").read_text(encoding="utf-8"))
    payload = raw[0] if isinstance(raw, list) else raw
    unit = LandRegistryUnitDetailed.model_validate(payload)
    owners = unit.get_all_owners()
    assert owners
    assert all(o.model_dump()["register"] == "land_registry" for o in owners)
