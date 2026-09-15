"""Person identity across the registers.

The registers write a person as free text: surname first, in capitals, often
with a relative's name after a marker ("ŠARUNIĆ AUGUSTIN POK. BOŽE": Augustin
Šarunić, son of the late Božo; "TEST OSOBA UD. BOŽE": widow of Božo), and on
sheet C sometimes with the share of the right ("... ZA 2/6"). The cadastre
writes the same person without the relative. Two records are compared here
by a key that ignores case, diacritics, spacing and punctuation, with the
share suffix removed, and a second, looser key that also drops the relative:
a match on the looser key alone is reported as fuzzy, never merged silently.
The tax number (OIB) is the only identifier the registers carry; when both
records have one it decides.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from ..utils import fold_text, split_name_share

#: Words (folded) that introduce a relative's name: the late father ("pok."),
#: the late husband ("ud.", udova), the maiden name ("rođ."), "sin"/"kći" of.
_RELATION_MARKERS = frozenset(
    {
        "pok",
        "pokojnog",
        "pokojnoga",
        "pokojne",
        "ud",
        "udov",
        "udova",
        "rod",
        "rodj",
        "rodena",
        "rodjena",
        "sin",
        "kci",
        "kcer",
        "kceri",
    }
)


@dataclass(frozen=True)
class PersonKey:
    """The comparable form of one person record.

    ``strict`` is the folded name (share suffix removed, punctuation dropped);
    ``fuzzy`` is the same with any relative's name removed; ``tax_number`` is
    the OIB when the register gives one.
    """

    strict: str
    fuzzy: str
    tax_number: str | None = None


def _tokens(name: str) -> list[str]:
    bare = split_name_share(name)[0]
    return fold_text(bare.replace(".", " ").replace(",", " ")).split()


def _without_relatives(tokens: list[str]) -> list[str]:
    kept: list[str] = []
    skip = False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token in _RELATION_MARKERS:
            skip = True
            continue
        kept.append(token)
    return kept or tokens


def person_key(name: str | None, tax_number: str | None = None) -> PersonKey:
    """The key of one person record (see the module docstring)."""
    tokens = _tokens(name or "")
    tax = (tax_number or "").strip() or None
    return PersonKey(" ".join(tokens), " ".join(_without_relatives(tokens)), tax)


def same_person(a: PersonKey, b: PersonKey) -> tuple[bool, bool]:
    """Whether two keys name the same person, and whether only loosely.

    Returns ``(match, fuzzy)``. Two tax numbers decide outright. Otherwise
    equal strict keys are a match; equal fuzzy keys alone (one record names
    a relative, the other does not, or names a different one) are a match
    reported as fuzzy; anything else is not a match.
    """
    if a.tax_number and b.tax_number:
        return a.tax_number == b.tax_number, False
    if a.strict and a.strict == b.strict:
        return True, False
    if a.fuzzy and a.fuzzy == b.fuzzy:
        return True, True
    return False, False


def count_distinct_persons(records: Iterable[tuple[str | None, str | None]]) -> int:
    """How many different people a list of ``(name, tax_number)`` records names.

    Records are grouped by strict key (case, diacritics, spacing, punctuation
    and a share suffix ignored); within a group, records with different tax
    numbers are different people, and records without one join the group.
    The loose key is not used: a count of owners should not merge two people
    on a guess. Two different people with the same name and no tax number
    count once; that is the register's limitation, not the count's.
    """
    tax_numbers_by_name: dict[str, set[str]] = {}
    for name, tax_number in records:
        key = person_key(name, tax_number)
        if not key.strict:
            continue
        group = tax_numbers_by_name.setdefault(key.strict, set())
        if key.tax_number:
            group.add(key.tax_number)
    return sum(max(1, len(group)) for group in tax_numbers_by_name.values())
