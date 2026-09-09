"""F5: structured share fractions parsed from LR-unit descriptions."""

import json
from pathlib import Path

from cadastral_api.models.entities import LandRegistryUnitDetailed, LRShare

FIXTURES = Path(__file__).parent / "fixtures"


def _share(description: str, **kw) -> LRShare:
    return LRShare.model_validate(
        {"lrUnitShareId": 1, "description": description, "orderNumber": "1", "status": 0, **kw}
    )


def test_fraction_parsed_from_description_revives_decimal() -> None:
    share = _share("127. Suvlasnički dio: 1/4")
    assert share.numerator == 1
    assert share.denominator == 4
    assert share.fraction_decimal == 0.25
    assert share.share_fraction == {"num": 1, "den": 4, "decimal": 0.25}


def test_explicit_numerator_denominator_not_overwritten() -> None:
    share = _share("ignored: 9/9", numerator=1, denominator=2)
    assert share.share_fraction == {"num": 1, "den": 2, "decimal": 0.5}


def test_share_fraction_none_when_unparseable() -> None:
    assert _share("no fraction").share_fraction is None


def test_real_lr_unit_shares_have_structured_fractions() -> None:
    raw = json.loads((FIXTURES / "lr_unit_lrparcels.json").read_text(encoding="utf-8"))
    payload = raw[0] if isinstance(raw, list) else raw
    unit = LandRegistryUnitDetailed.model_validate(payload)
    shares = unit.ownership_sheet_b.lr_unit_shares
    assert shares
    # Every active share on unit 449 carries a "Suvlasnički dio: X/Y" description.
    assert all(s.share_fraction is not None for s in shares if s.is_active)
    # Fractions sum to 1 (3x 1/4 + 3x 1/12).
    total = sum(s.fraction_decimal for s in shares if s.is_active)
    assert round(total, 6) == 1.0
