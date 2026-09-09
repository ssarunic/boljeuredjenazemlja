"""Tests for the shared fraction/name helpers (F5)."""

import pytest

from cadastral_api.utils import normalize_name, parse_beneficiary_name, parse_fraction


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


@pytest.mark.parametrize(
    "text,expected",
    [
        # A legal person named inline, with the body acting for it after a comma.
        (
            "ZABILJEŽBA, TRAŽBINA SOCIJALNE POMOĆI, uknjiženog prava vlasništva "
            "na ime N.N., za korist REPUBLIKE HRVATSKE, Centar za socijalnu skrb Zadar.",
            "REPUBLIKE HRVATSKE",
        ),
        # The name ends where the sentence continues in lower case.
        (
            "Na 1/1560 dijela čest. 1138 uknjižene u korist Letinić Jakov "
            "postojanja ugovora o doživotnom uzdržavanju",
            "Letinić Jakov",
        ),
        # A company keeps its legal form, and the seat after it is left out.
        ("u korist Zagrebačke banke d.d. iz Zagreba", "Zagrebačke banke d.d."),
        ("u korist ERSTE&STEIERMÄRKISCHE BANK d.d. Rijeka", "ERSTE&STEIERMÄRKISCHE BANK d.d."),
        ("<span class='lr-entry-black' >u korist REPUBLIKE HRVATSKE.</span>", "REPUBLIKE HRVATSKE"),
        # Nothing after the colon: the name is in lrOwners, not in the text.
        ("uknjižuje se pravo ploduživanja u korist:", None),
        ("zabilježuje se zabrana opterećenja stana.", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_beneficiary_name(text, expected) -> None:
    assert parse_beneficiary_name(text) == expected
