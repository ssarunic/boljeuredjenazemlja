"""Indicative flags on a registered owner: likely deceased, address abroad, public body.

An investor sizing up a set of parcels wants to know how many estates and how
many foreign counterparties are behind the names on sheet B before reading
them one by one. The register does not say; it gives a name, sometimes an
address, and the registration entry that put the owner on the share. Three
rules read those and each result is marked ``inferred`` with the ``basis``
it rests on, in the same way ``persons.infer_party_type`` does:

- ``likely_deceased``: the owner's registration entry is older than a
  threshold (40 years by default), or the owner was carried over from an
  earlier unit ("IZ ZK ULOŠKA PRENESENI VLASNICI", so the original date is
  unknown and older still), or the record carries neither a tax number nor
  a registration entry (a legacy record from the paper register, decades
  old), or the owner's own name carries a death marker ("POKOJNI", or "POK."
  with no relative's name after it; "HORVAT IVAN POK. MARKA" names Ivan's
  late father, not Ivan, and is not a marker).
- ``address_abroad``: the address names a country other than Croatia
  (Croatian addresses name none), or carries a letter-prefixed foreign
  postcode as a weak signal. Unknown when the register gives no address.
- ``public_body``: the name reads as the state or a local self-government
  (``persons.infer_party_type``).

The flags decorate ``OwnershipSheetB.owner_rows()``, the one owner shape the
CLI and the MCP share; nothing here makes a request.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..models.entities import LandRegistryUnitDetailed, LREntry
from ..utils import fold_text
from .persons import DECEASED_NOMINATIVE, PartyTypeInference, infer_party_type, name_tokens

#: Years after the registration entry from which an individual owner is likely
#: an estate rather than a living counterparty.
DEFAULT_DECEASED_THRESHOLD_YEARS = 40

#: Genitive and abbreviated forms: they introduce a relative's name ("POK.
#: BOŽE") unless nothing follows them or they open the name.
_DECEASED_GENITIVE = frozenset({"pok", "pokojnog", "pokojnoga", "pokojne", "pokojnoj"})

#: Country names (folded) an address abroad may carry, endonym and exonym.
#: The label is what the flag reports. Croatia itself is listed separately.
_COUNTRY_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("njemacka", "Germany"),
    ("deutschland", "Germany"),
    ("germany", "Germany"),
    ("austrija", "Austria"),
    ("osterreich", "Austria"),
    ("oesterreich", "Austria"),
    ("austria", "Austria"),
    ("svicarska", "Switzerland"),
    ("schweiz", "Switzerland"),
    ("suisse", "Switzerland"),
    ("switzerland", "Switzerland"),
    ("italija", "Italy"),
    ("italia", "Italy"),
    ("italy", "Italy"),
    ("francuska", "France"),
    ("france", "France"),
    ("slovenija", "Slovenia"),
    ("slovenia", "Slovenia"),
    ("bosna i hercegovina", "Bosnia and Herzegovina"),
    ("bosnia", "Bosnia and Herzegovina"),
    ("bih", "Bosnia and Herzegovina"),
    ("srbija", "Serbia"),
    ("serbia", "Serbia"),
    ("crna gora", "Montenegro"),
    ("montenegro", "Montenegro"),
    ("madarska", "Hungary"),
    ("magyarorszag", "Hungary"),
    ("hungary", "Hungary"),
    ("australija", "Australia"),
    ("australia", "Australia"),
    ("novi zeland", "New Zealand"),
    ("new zealand", "New Zealand"),
    ("sjedinjene americke drzave", "United States"),
    ("united states", "United States"),
    ("usa", "United States"),
    ("kanada", "Canada"),
    ("canada", "Canada"),
    ("velika britanija", "United Kingdom"),
    ("united kingdom", "United Kingdom"),
    ("england", "United Kingdom"),
    ("irska", "Ireland"),
    ("ireland", "Ireland"),
    ("nizozemska", "Netherlands"),
    ("nederland", "Netherlands"),
    ("netherlands", "Netherlands"),
    ("belgija", "Belgium"),
    ("belgium", "Belgium"),
    ("svedska", "Sweden"),
    ("sverige", "Sweden"),
    ("sweden", "Sweden"),
    ("norveska", "Norway"),
    ("norway", "Norway"),
    ("danska", "Denmark"),
    ("denmark", "Denmark"),
    ("spanjolska", "Spain"),
    ("espana", "Spain"),
    ("spain", "Spain"),
    ("portugal", "Portugal"),
    ("ceska", "Czechia"),
    ("czech", "Czechia"),
    ("slovacka", "Slovakia"),
    ("slovakia", "Slovakia"),
    ("poljska", "Poland"),
    ("poland", "Poland"),
    ("makedonija", "North Macedonia"),
    ("macedonia", "North Macedonia"),
    ("kosovo", "Kosovo"),
    ("argentina", "Argentina"),
    ("cile", "Chile"),
    ("chile", "Chile"),
    ("brazil", "Brazil"),
    ("juzna afrika", "South Africa"),
    ("south africa", "South Africa"),
)
_CROATIA = ("hrvatska", "croatia", "kroatien")
#: A letter-prefixed postcode ("A-1010", "D-80331", "CH-8001"); Croatian
#: postcodes are five bare digits, and "HR-10000" is Croatian.
_FOREIGN_POSTCODE_RE = re.compile(r"\b(?!HR-)([A-Z]{1,2})-(\d{4,5})\b")


class DeceasedInference(BaseModel):
    """Whether an owner is likely deceased, and why."""

    likely_deceased: bool
    inferred: Literal[True] = Field(default=True, description="Always true: a rule, not a record")
    basis: str = Field(description="What the inference rests on")
    signals: list[str] = Field(
        default_factory=list,
        description=(
            "Rules that fired: name_marker, transferred_from_unit, entry_age, legacy_record"
        ),
    )
    marker: str | None = Field(default=None, description="The death marker found in the name")
    entry_date: str | None = Field(default=None, description="The registration entry's date")
    entry_age_years: int | None = Field(default=None, description="Age of that entry in years")


class AddressAbroadInference(BaseModel):
    """Whether an owner's address is abroad, and why."""

    abroad: bool | None = Field(description="None when the register gives no address")
    inferred: Literal[True] = Field(default=True, description="Always true: a rule, not a record")
    basis: str = Field(description="What the inference rests on")
    country: str | None = Field(default=None, description="The country named, when one is")
    confidence: Literal["keyword", "postcode_pattern"] | None = Field(
        default=None, description="keyword (a country is named) or postcode_pattern (weak)"
    )
    matched: str | None = Field(
        default=None, description="The country word or postcode found in the address"
    )


class OwnerFlags(BaseModel):
    """The three flags of one owner."""

    likely_deceased: DeceasedInference | None = Field(
        description="None for a company or a public body"
    )
    address_abroad: AddressAbroadInference
    public_body: bool = Field(description="The state or a local self-government (inferred)")
    party_type_inferred: PartyTypeInference


class OwnerFlagsRow(BaseModel):
    """One owner row of a unit with its flags."""

    name: str
    tax_number: str | None = None
    share_order_number: str | None = None
    condominium_number: str | None = None
    flags: OwnerFlags


def _entry_facts(entry: LREntry | dict[str, Any] | None) -> tuple[date | None, bool]:
    """The receipt date and the transfer marker of an entry, model or ``entry_row`` dict."""
    if entry is None:
        return None, False
    if isinstance(entry, LREntry):
        return entry.entry_date, entry.transferred_from_unit
    raw = entry.get("entry_date")
    when = date.fromisoformat(raw) if isinstance(raw, str) and raw else None
    return when, bool(entry.get("transferred_from_unit"))


def name_marks_deceased(name: str | None) -> str | None:
    """The token that marks the named person as deceased, or None.

    A nominative form anywhere ("POKOJNI IVAN HORVAT"); an abbreviated or
    genitive form only when it opens the name or nothing follows it ("HORVAT
    IVAN POK."). "HORVAT IVAN POK. MARKA" marks Marko, not Ivan.
    """
    tokens = name_tokens(name or "")
    for index, token in enumerate(tokens):
        if token in DECEASED_NOMINATIVE:
            return token
        if token in _DECEASED_GENITIVE and (index == 0 or index == len(tokens) - 1):
            return token
    return None


def infer_deceased(
    name: str | None,
    entry: LREntry | dict[str, Any] | None,
    *,
    tax_number: str | None = None,
    threshold_years: int = DEFAULT_DECEASED_THRESHOLD_YEARS,
    today: date | None = None,
) -> DeceasedInference:
    """Whether an individual owner is likely deceased (see the module docstring)."""
    today = today or date.today()
    entry_date, transferred = _entry_facts(entry)
    signals: list[str] = []
    reasons: list[str] = []
    marker = name_marks_deceased(name)
    if marker:
        signals.append("name_marker")
        reasons.append(f"the name marks the person as deceased ({marker!r})")
    if entry is None and not (tax_number or "").strip():
        # A record with neither an OIB nor a registration entry was carried
        # from the paper register as it stood: decades old, usually an estate.
        signals.append("legacy_record")
        reasons.append(
            "the record carries neither a tax number (OIB) nor a registration entry: a "
            "legacy record from the paper register, decades old"
        )
    if transferred:
        signals.append("transferred_from_unit")
        reasons.append(
            "the owner was carried over from an earlier unit (IZ ZK ULOŠKA PRENESENI "
            "VLASNICI): the entry date is the transfer's, the original registration is older"
        )
    age_years: int | None = None
    if entry_date is not None:
        age = (today - entry_date).days / 365.25
        age_years = int(age)
        if age >= threshold_years:
            signals.append("entry_age")
            reasons.append(
                f"the registration entry of {entry_date.isoformat()} is {age:.0f} years old "
                f"(threshold {threshold_years})"
            )
    when = entry_date.isoformat() if entry_date else None
    if signals:
        return DeceasedInference(
            likely_deceased=True,
            basis="; ".join(reasons),
            signals=signals,
            marker=marker,
            entry_date=when,
            entry_age_years=age_years,
        )
    if entry_date is None and not transferred:
        basis = (
            "no registration entry to date the owner by and no marker in the name (the "
            "record carries a tax number, so it is not a legacy record)"
        )
    else:
        basis = (
            f"the registration entry of {entry_date.isoformat()} is under {threshold_years} "
            f"years old and the name carries no marker"
            if entry_date is not None
            else "no marker in the name"
        )
    return DeceasedInference(
        likely_deceased=False,
        basis=basis,
        signals=[],
        marker=marker,
        entry_date=when,
        entry_age_years=age_years,
    )


def infer_address_abroad(address: str | None) -> AddressAbroadInference:
    """Whether an address is abroad (see the module docstring)."""
    if not address or not address.strip():
        return AddressAbroadInference(abroad=None, basis="no address on record")
    folded = fold_text(address)
    padded = f" {folded} "
    for keyword, country in _COUNTRY_KEYWORDS:
        if f" {keyword} " in padded or f" {keyword}," in padded:
            return AddressAbroadInference(
                abroad=True,
                basis=f"the address names {country} ({keyword!r})",
                country=country,
                confidence="keyword",
                matched=keyword,
            )
    if any(f" {word} " in padded for word in _CROATIA):
        return AddressAbroadInference(abroad=False, basis="the address names Croatia")
    match = _FOREIGN_POSTCODE_RE.search(address.upper())
    if match:
        return AddressAbroadInference(
            abroad=True,
            basis=f"the postcode {match.group(0)!r} has a foreign country prefix (weak signal)",
            confidence="postcode_pattern",
            matched=match.group(0),
        )
    return AddressAbroadInference(
        abroad=False,
        basis="no foreign country or postcode in the address (Croatian addresses name none)",
    )


def owner_flags(
    name: str | None,
    address: str | None,
    entry: LREntry | dict[str, Any] | None,
    *,
    tax_number: str | None = None,
    threshold_years: int = DEFAULT_DECEASED_THRESHOLD_YEARS,
    today: date | None = None,
) -> OwnerFlags:
    """The flags of one owner from the name, address, tax number and registration entry."""
    party = infer_party_type(name)
    deceased = (
        infer_deceased(
            name, entry, tax_number=tax_number, threshold_years=threshold_years, today=today
        )
        if party.party_type in ("individual", "unknown")
        else None
    )
    return OwnerFlags(
        likely_deceased=deceased,
        address_abroad=infer_address_abroad(address),
        public_body=party.party_type in ("state", "municipality"),
        party_type_inferred=party,
    )


def owner_flags_for_unit(
    lr_unit: LandRegistryUnitDetailed,
    *,
    threshold_years: int = DEFAULT_DECEASED_THRESHOLD_YEARS,
    today: date | None = None,
) -> list[OwnerFlagsRow]:
    """The flags of every current owner of a unit, in ``owner_rows()`` order."""
    return [
        OwnerFlagsRow(
            name=row["name"],
            tax_number=row.get("tax_number"),
            share_order_number=row.get("share_order_number"),
            condominium_number=row.get("condominium_number"),
            flags=owner_flags(
                row["name"],
                row.get("address"),
                row.get("entry"),
                tax_number=row.get("tax_number"),
                threshold_years=threshold_years,
                today=today,
            ),
        )
        for row in lr_unit.ownership_sheet_b.owner_rows()
    ]


def count_owner_flags(flags: Iterable[OwnerFlags | None]) -> dict[str, int]:
    """How many owner records carry each flag (records, not distinct people).

    Takes the flags of the records (``row.flags`` of an ``OwnerFlagsRow`` or
    of a ``PersonRecord``); a record without flags counts as an owner only.
    """
    rows = list(flags)
    known = [f for f in rows if f is not None]
    return {
        "owners": len(rows),
        "likely_deceased": sum(
            1 for f in known if f.likely_deceased is not None and f.likely_deceased.likely_deceased
        ),
        "address_abroad": sum(1 for f in known if f.address_abroad.abroad is True),
        "address_unknown": sum(1 for f in known if f.address_abroad.abroad is None),
        "public_body": sum(1 for f in known if f.public_body),
    }
