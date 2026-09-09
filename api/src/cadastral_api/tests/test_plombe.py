"""#7: pending entries (plombe) are typed, summarized, and surfaced.

The server returns activePlumbs; the model must type them and summary() must
expose them so a pending change on the unit is visible. Unit 449 (parcel
1122/1) has one real active plomba.
"""

import json
from pathlib import Path

from cadastral_api.models.entities import LandRegistryUnitDetailed, Plumb

FIXTURE = Path(__file__).parent / "fixtures" / "lr_unit_lrparcels.json"


def _unit() -> LandRegistryUnitDetailed:
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    return LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)


def test_active_plumbs_are_typed() -> None:
    unit = _unit()
    assert unit.active_plumbs
    assert all(isinstance(p, Plumb) for p in unit.active_plumbs)
    assert {p.file_number for p in unit.active_plumbs} == set(['Z-12564/2026'])


def test_has_pending_plombe() -> None:
    assert _unit().has_pending_plombe() is True


def test_summary_surfaces_pending_plombe() -> None:
    summary = _unit().summary()
    assert summary["has_pending_plombe"] is True
    assert summary["pending_plombe"] == ['Z-12564/2026']


def test_no_plombe_when_absent() -> None:
    unit = _unit()
    unit.active_plumbs = []
    s = unit.summary()
    assert s["has_pending_plombe"] is False
    assert s["pending_plombe"] == []
