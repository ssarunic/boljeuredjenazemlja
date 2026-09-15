"""Person identity across the registers.

The registers write a person as free text: surname first, in capitals, often
with a relative's name after a marker ("ŠARUNIĆ AUGUSTIN POK. BOŽE": Augustin
Šarunić, son of the late Božo; "TEST OSOBA UD. BOŽE": widow of Božo), and on
sheet C sometimes with the share of the right ("... ZA 2/6"). The cadastre
writes the same person without the relative, or with the father's name after
a comma ("ŠARUNIĆ AUGUSTIN, BOŽO", "ŠARUNIĆ ANTE, P. BOŽE") and sometimes
with the given name first ("AUGUSTIN ŠARUNIĆ"). Two records are compared here
by a key that ignores case, diacritics, spacing and punctuation, with the
share suffix removed, and a second, looser key that also drops the relative
(after a marker, or after the first comma); the loose keys are also compared
with the words in any order. A match on the looser key alone, or on the
words out of order, is reported as fuzzy, never merged silently; the
register comparison lifts the flag on a reordered name when the shares or
the addresses corroborate it. The tax number (OIB) is the only identifier
the registers carry; when both records have one it decides.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from ..utils import LEGAL_FORMS, fold_text, split_name_share

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


def name_tokens(name: str) -> list[str]:
    """The folded words of a register name, the share suffix and punctuation removed."""
    bare = split_name_share(name)[0]
    return fold_text(bare.replace(".", " ").replace(",", " ")).split()


def _own_name(name: str) -> str:
    """The part of a name before the first comma: what follows names a relative.

    The cadastre writes "ŠARUNIĆ AUGUSTIN, BOŽO" (Augustin, son of Božo) and
    "IVIĆ MARKO, SIN PETRA"; the part after the comma is dropped from the
    loose key. A comma inside a legal person's name ("X d.o.o., Zagreb") is
    cut the same way, which loses only the seat.
    """
    bare = split_name_share(name)[0]
    return bare.split(",", 1)[0] if "," in bare else bare


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


#: Nominative death markers: they describe the person named, wherever they
#: stand ("POKOJNI HORVAT MARKO"), and are no part of the name.
DECEASED_NOMINATIVE = frozenset({"pokojni", "pokojna", "pokojnik", "pokojnica"})


def surname_of(name: str | None) -> str:
    """The surname as the registers write it: the first word that is not a marker."""
    for token in name_tokens(name or ""):
        if token not in _RELATION_MARKERS and token not in DECEASED_NOMINATIVE:
            return token
    return ""


def person_key(name: str | None, tax_number: str | None = None) -> PersonKey:
    """The key of one person record (see the module docstring)."""
    tokens = name_tokens(name or "")
    loose = _without_relatives(name_tokens(_own_name(name or "")))
    tax = (tax_number or "").strip() or None
    return PersonKey(" ".join(tokens), " ".join(loose or tokens), tax)


def same_person(a: PersonKey, b: PersonKey) -> tuple[bool, bool]:
    """Whether two keys name the same person, and whether only loosely.

    Returns ``(match, fuzzy)``. Two tax numbers decide outright. Otherwise
    equal strict keys are a match; equal fuzzy keys alone (one record names
    a relative, the other does not, or names a different one), or fuzzy keys
    of the same words in another order ("AUGUSTIN ŠARUNIĆ" against "ŠARUNIĆ
    AUGUSTIN"), are a match reported as fuzzy; anything else is not a match.
    """
    if a.tax_number and b.tax_number:
        return a.tax_number == b.tax_number, False
    if a.strict and a.strict == b.strict:
        return True, False
    if a.fuzzy and a.fuzzy == b.fuzzy:
        return True, True
    if plain_reorder(a, b):
        return True, True
    return False, False


def plain_reorder(a: PersonKey, b: PersonKey) -> bool:
    """Whether two keys are the same words in another order, with no relative on either side.

    "AUGUSTIN ŠARUNIĆ" against "ŠARUNIĆ AUGUSTIN": the names agree in full
    and only the order differs, which is how the cadastre writes people. A
    namesake (a grandson written like the grandfather) looks the same, so a
    caller treats it as fuzzy unless something else corroborates it (the
    shares agree, or the addresses do).
    """
    words_a, words_b = sorted(a.fuzzy.split()), sorted(b.fuzzy.split())
    plain = a.strict == a.fuzzy and b.strict == b.fuzzy
    return len(words_a) > 1 and words_a == words_b and plain


def group_by_person(records: Iterable[tuple[str | None, str | None]]) -> dict[str, set[str]]:
    """Strict key -> tax numbers seen: the grouping every distinct-person count shares.

    Records are grouped by strict key (case, diacritics, spacing, punctuation
    and a share suffix ignored); within a group, records with different tax
    numbers are different people, and records without one join the group.
    The loose key is not used: a count of owners should not merge two people
    on a guess. Two different people with the same name and no tax number
    fall in one group; that is the register's limitation, not the rule's.
    A record without a name is skipped.
    """
    groups: dict[str, set[str]] = {}
    for name, tax_number in records:
        key = person_key(name, tax_number)
        if not key.strict:
            continue
        group = groups.setdefault(key.strict, set())
        if key.tax_number:
            group.add(key.tax_number)
    return groups


def group_size(tax_numbers: set[str]) -> int:
    """How many people a group of ``group_by_person`` holds: one, or one per tax number."""
    return max(1, len(tax_numbers))


def person_group_key(strict: str, tax_number: str | None, groups: dict[str, set[str]]) -> str:
    """The key of one record within its group: ``strict#tax`` when a tax number applies.

    A record without a tax number joins the group's (first) tax number, so
    that it is the same person as the record that carries one; a group with
    no tax number at all keeps the bare strict key.
    """
    taxes = groups.get(strict) or set()
    tax = tax_number or (min(taxes) if taxes else None)
    return f"{strict}#{tax}" if tax else strict


def count_distinct_persons(records: Iterable[tuple[str | None, str | None]]) -> int:
    """How many different people ``(name, tax_number)`` records name (see ``group_by_person``)."""
    return sum(group_size(taxes) for taxes in group_by_person(records).values())


# ---------------------------------------------------------------------------
# Party type, inferred from the name
# ---------------------------------------------------------------------------

#: Inferred kinds of owner. The values are those of ``PartyType`` in the
#: entities; the register itself never says (``Party.party_type`` is unknown).
InferredPartyType = Literal["individual", "company", "state", "municipality", "unknown"]

#: Words (folded, dots removed) that mark a legal person besides the legal forms.
_COMPANY_WORDS = frozenset(
    {"zadruga", "udruga", "banka", "ustanova", "zaklada", "fond", "drustvo", "poduzece", "tvrtka"}
)
#: Local self-government: a town (grad), a municipality (općina), a county (županija).
_MUNICIPALITY_WORDS = frozenset({"grad", "opcina", "zupanija"})


class PartyTypeInference(BaseModel):
    """What kind of person a register name most likely denotes, and why.

    Always marked ``inferred``: the registers do not record it, and a rule on
    the spelling of a name can be wrong (a person surnamed Grad, a company
    written without its legal form). Use it to estimate how many public bodies
    and companies sit at the table, not to state a fact about one of them.
    """

    party_type: InferredPartyType = Field(
        description="individual | company | state | municipality | unknown"
    )
    inferred: Literal[True] = Field(default=True, description="Always true: read from the name")
    basis: str = Field(description="The spelling the inference rests on")


def infer_party_type(name: str | None) -> PartyTypeInference:
    """Infer a party type from a register name (see ``PartyTypeInference``)."""
    bare = split_name_share(name or "")[0]
    tokens = fold_text(bare.replace(".", "").replace(",", " ")).split()
    if not tokens:
        return PartyTypeInference(party_type="unknown", basis="no name")
    folded = " ".join(tokens)
    if "republika hrvatska" in folded or "republike hrvatske" in folded or "rh" in tokens:
        return PartyTypeInference(party_type="state", basis="the name says Republika Hrvatska")
    for token in tokens:
        if token in _MUNICIPALITY_WORDS:
            return PartyTypeInference(
                party_type="municipality",
                basis=f"the name contains {token!r} (local self-government)",
            )
    for token in tokens:
        if token in LEGAL_FORMS or token in _COMPANY_WORDS:
            return PartyTypeInference(
                party_type="company", basis=f"the name contains the legal form or word {token!r}"
            )
    return PartyTypeInference(
        party_type="individual", basis="no legal form or public body in the name"
    )
