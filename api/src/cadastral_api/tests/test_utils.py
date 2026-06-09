"""Tests for the shared fraction/name helpers (F5)."""

import pytest

from cadastral_api.utils import normalize_name, parse_fraction


@pytest.mark.parametrize(
    "text,expected",
    [
        ("1. Suvlasnički dio: 4/8", (4, 8)),
        ("1. Na suvlasnički dio: 1 (4/8)", (4, 8)),
        ("16. Suvlasnički dio: 61/4651 ETAŽNO VLASNIŠTVO (E-16)", (61, 4651)),
        ("22.3. Suvlasnički dio etaže: 1/2", (1, 2)),
        ("1/4", (1, 4)),
        ("Suvlasnički dio: 0/0", None),  # zero denominator
        ("no fraction here", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_fraction(text, expected) -> None:
    assert parse_fraction(text) == expected


def test_parse_fraction_ignores_leading_order_number() -> None:
    # "127." must not be read as 127/<something>; the share is after the colon.
    assert parse_fraction("127. Suvlasnički dio: 1/4") == (1, 4)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("KOLAR RAJKA", "Kolar Rajka"),
        ("  Šarunić   Augustin ", "Šarunić Augustin"),
        ("BORČIĆ SUNČICA", "Borčić Sunčica"),
    ],
)
def test_normalize_name(raw, expected) -> None:
    assert normalize_name(raw) == expected
