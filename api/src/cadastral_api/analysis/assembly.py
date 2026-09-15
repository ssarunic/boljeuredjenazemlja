"""Land assembly over a set of parcels: who holds what, how much, and where to start.

An investor assembling land from many small parcels needs three tables before
talking to anyone: the persons and the parcels each one owns or possesses
(the matrix), the persons ranked by the area they control and grouped by
family, and the parcels ranked by how easy they look to acquire. This module
builds them from records already fetched (a parcel, its unit, the register
comparison and, optionally, its zoning); nothing here makes a request.

The ease-of-acquisition score is a weighted sum of yes/no factors with the
weights returned next to it, so that a reader can see and change them; a
factor that could not be evaluated (no unit, no zoning asked for) is left out
of both the numerator and the denominator rather than counted against the
parcel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..models.entities import LandRegistryUnitDetailed, ParcelInfo
from ..models.planning_entities import ParcelZoning
from ..models.provenance import now_utc_iso
from .persons import (
    PartyTypeInference,
    count_distinct_persons,
    group_by_person,
    person_group_key,
    person_key,
    surname_of,
)
from .registers import PersonRecord, RegisterComparison
from .sale_blockers import ENCUMBRANCE_KINDS

#: Default weights of the ease-of-acquisition factors (they sum to 1).
DEFAULT_WEIGHTS: dict[str, float] = {
    "single_owner": 0.25,
    "owner_is_possessor": 0.25,
    "no_encumbrances": 0.20,
    "no_pending_plombe": 0.15,
    "in_building_area": 0.15,
}

Role = Literal["owner", "possessor", "both"]
#: A share as the registers give it, ``{num, den, decimal}``, or None.
Share = dict[str, Any] | None
#: One person on one parcel: record, parcel number, role, fuzzy match, owner
#: share, possessor share, and the id of the possessor record the share is from.
_Occurrence = tuple[PersonRecord, str, Role, bool, Share, Share, int | None]


@dataclass
class AssemblyInput:
    """Everything known about one parcel of the set."""

    parcel: ParcelInfo
    lr_unit: LandRegistryUnitDetailed | None
    comparison: RegisterComparison
    zoning: ParcelZoning | None = None
    map_url: str | None = None


class AcquisitionScore(BaseModel):
    """How easy one parcel looks to acquire, and why."""

    parcel_number: str
    score: float | None = Field(
        description="0 to 1 over the factors that could be evaluated; None when none could"
    )
    factors: dict[str, bool | None] = Field(
        description="Each factor: true, false, or None when it could not be evaluated"
    )
    weights: dict[str, float]
    weight_evaluated: float = Field(description="Sum of the weights of the evaluated factors")
    notes: list[str]


class MatrixCell(BaseModel):
    """One person on one parcel."""

    person_key: str
    parcel_number: str
    role: Role
    owner_share: dict[str, Any] | None = Field(
        default=None, description="The person's registered shares of the parcel, added up"
    )
    possessor_share: dict[str, Any] | None = Field(
        default=None, description="The person's possession shares of the parcel, added up"
    )
    fuzzy: bool = Field(default=False, description="An owner/possessor match was fuzzy")
    records: int = Field(default=1, description="Register records merged into this cell")


class PersonHolding(BaseModel):
    """One person across the set, with the area they own or possess."""

    key: str
    name: str
    surname: str = Field(
        description="First word of the folded name that is no marker (the registers write it first)"
    )
    tax_number: str | None
    party_type_inferred: PartyTypeInference
    parcels: list[str]
    owner_of: list[str]
    possessor_of: list[str]
    owned_area_m2: float = Field(
        description="Sum of (the person's shares added up) x cadastre area over the parcels owned"
    )
    possessed_area_m2: float = Field(
        description="Cadastre area of the parcels the person possesses (shares not applied)"
    )
    controlled_area_m2: float = Field(
        description="Owned area plus the area of the parcels the person only possesses"
    )
    shares_unknown: int = Field(description="Owner roles without a share; counted as the whole")
    fuzzy_matches: int
    likely_deceased: bool | None = Field(
        default=None,
        description="Inferred from any of the person's owner records; None for a possessor only",
    )
    address_abroad: bool | None = Field(
        default=None, description="Inferred from any owner record's address; None when unknown"
    )


class SurnameGroup(BaseModel):
    """Persons sharing a surname (a family, most of the time)."""

    surname: str
    persons: list[str] = Field(description="Person keys")
    person_count: int
    parcel_count: int
    controlled_area_m2: float
    likely_deceased_count: int = Field(
        default=0, description="Persons flagged likely deceased (inferred): estates to expect"
    )
    address_abroad_count: int = Field(
        default=0, description="Persons with an address abroad (inferred)"
    )


class ParcelSummary(BaseModel):
    """One parcel of the set, with the facts the ranking rests on."""

    parcel_number: str
    municipality_code: str
    area_m2: int | None
    land_use: dict[str, int]
    lr_unit: dict[str, Any] | None
    relationship: str
    distinct_owners: int
    distinct_possessors: int
    has_encumbrances: bool | None
    has_pending_plombe: bool | None
    pending_plombe: list[str]
    public_body_owner_share: float | None
    zoning_status: str | None
    in_building_area: bool | None
    designation_code: str | None
    plan_name: str | None
    area_mismatch: bool
    sale_verdict: str | None = Field(
        default=None, description="clear | conditional | blocked from the unit's sale blockers"
    )
    blocker_counts: dict[str, int] | None = Field(
        default=None, description="Counted blockers per severity"
    )
    blocker_kinds: list[str] = Field(
        default_factory=list, description="The kinds of blocker present, each once"
    )
    score: float | None
    map_url: str | None
    provenance: dict[str, dict[str, str] | None]


class AssemblyTotals(BaseModel):
    parcel_count: int
    total_area_m2: int
    area_by_land_use: dict[str, int]
    area_by_relationship: dict[str, int]
    area_by_zoning_status: dict[str, int] | None
    distinct_people: int
    distinct_owners: int
    distinct_possessors: int
    party_types: dict[str, int]
    public_body_parcels: int
    fuzzy_matches: int
    parcels_with_encumbrances: int | None
    parcels_with_pending_plombe: int | None
    parcels_in_building_area: int | None
    parcels_by_verdict: dict[str, int] | None = Field(
        default=None, description="Parcels per sale verdict; None when no unit was read"
    )
    persons_likely_deceased: int = Field(
        default=0, description="Persons flagged likely deceased (inferred)"
    )
    persons_address_abroad: int = Field(
        default=0, description="Persons with an address abroad (inferred)"
    )


class AssemblyAnalysis(BaseModel):
    """The three tables and the totals for a set of parcels."""

    generated_at: str
    weights: dict[str, float]
    parcels: list[ParcelSummary] = Field(description="Easiest to acquire first")
    persons: list[PersonHolding] = Field(description="Largest controlled area first")
    surname_groups: list[SurnameGroup]
    matrix: list[MatrixCell]
    scores: list[AcquisitionScore]
    totals: AssemblyTotals
    notes: list[str]


def resolve_weights(weights: dict[str, float] | None) -> dict[str, float]:
    """The weights to use: the defaults, overridden by ``weights``.

    Raises:
        ValueError: an unknown factor, a negative weight, or all weights zero
    """
    resolved = dict(DEFAULT_WEIGHTS)
    for name, value in (weights or {}).items():
        if name not in DEFAULT_WEIGHTS:
            raise ValueError(
                f"unknown factor {name!r}; the factors are {', '.join(DEFAULT_WEIGHTS)}"
            )
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
            raise ValueError(f"the weight of {name!r} must be a non-negative number")
        resolved[name] = float(value)
    if not any(resolved.values()):
        raise ValueError("at least one weight must be above zero")
    return resolved


def acquisition_score(
    item: AssemblyInput, weights: dict[str, float] | None = None
) -> AcquisitionScore:
    """Score one parcel (see the module docstring)."""
    used = resolve_weights(weights)
    comparison, unit, zoning = item.comparison, item.lr_unit, item.zoning
    notes: list[str] = []
    blockers = comparison.sale_blockers.blockers if comparison.sale_blockers else []
    # A charge is what the register holds against the unit (sheet C, share
    # and sheet notes) at blocking or conditional severity: an informational
    # note (a rejected request, an unrecognised annotation) does not count
    # against the parcel, and a cancelled entry is not in the list at all.
    charges = [
        b for b in blockers if b.kind in ENCUMBRANCE_KINDS and b.severity != "informational"
    ]
    factors: dict[str, bool | None] = {
        "single_owner": comparison.distinct_owners == 1 if unit is not None else None,
        "owner_is_possessor": (
            comparison.relationship == "same"
            if unit is not None and comparison.possessors and comparison.owners
            else None
        ),
        "no_encumbrances": not charges if unit is not None else None,
        "no_pending_plombe": (
            not any(b.kind == "pending_entry" for b in blockers) if unit is not None else None
        ),
        "in_building_area": zoning.in_building_area if zoning is not None else None,
    }
    if unit is None:
        notes.append("no land-registry unit: owner, encumbrance and plomba factors not evaluated")
    elif factors["owner_is_possessor"] is None:
        notes.append("one register lists nobody: the owner-is-possessor factor not evaluated")
    if zoning is None:
        notes.append("zoning not read: the building-area factor not evaluated")
    if comparison.fuzzy_matches:
        notes.append("the owner-is-possessor factor rests on a fuzzy name match")
    evaluated = {name: value for name, value in factors.items() if value is not None}
    weight_evaluated = round(sum(used[name] for name in evaluated), 6)
    score: float | None = None
    if weight_evaluated > 0:
        achieved = sum(used[name] for name, ok in evaluated.items() if ok)
        score = round(achieved / weight_evaluated, 3)
    return AcquisitionScore(
        parcel_number=item.parcel.parcel_number,
        score=score,
        factors=factors,
        weights=used,
        weight_evaluated=weight_evaluated,
        notes=notes,
    )


def _zoning_facts(
    zoning: ParcelZoning | None,
) -> tuple[str | None, bool | None, str | None, str | None]:
    if zoning is None:
        return None, None, None, None
    best = zoning.matches[0].zone if zoning.matches else None
    return (
        zoning.status.value,
        zoning.in_building_area,
        best.designation_code if best else None,
        best.plan_name if best else None,
    )


def _summary(item: AssemblyInput, score: AcquisitionScore) -> ParcelSummary:
    parcel, unit, comparison = item.parcel, item.lr_unit, item.comparison
    status, in_area, code, plan = _zoning_facts(item.zoning)
    return ParcelSummary(
        parcel_number=parcel.parcel_number,
        municipality_code=parcel.cad_municipality_reg_num,
        area_m2=parcel.area_numeric or None,
        land_use=parcel.land_use_summary,
        lr_unit=comparison.lr_unit,
        relationship=comparison.relationship,
        distinct_owners=comparison.distinct_owners,
        distinct_possessors=comparison.distinct_possessors,
        has_encumbrances=unit.has_sheet_c_entries() if unit is not None else None,
        has_pending_plombe=unit.has_pending_plombe() if unit is not None else None,
        pending_plombe=[p.file_number for p in unit.active_plumbs] if unit is not None else [],
        public_body_owner_share=comparison.public_body_owner_share,
        zoning_status=status,
        in_building_area=in_area,
        designation_code=code,
        plan_name=plan,
        area_mismatch=comparison.area_check.mismatch,
        sale_verdict=comparison.sale_blockers.verdict if comparison.sale_blockers else None,
        blocker_counts=comparison.sale_blockers.counts if comparison.sale_blockers else None,
        blocker_kinds=(
            sorted({b.kind for b in comparison.sale_blockers.blockers})
            if comparison.sale_blockers
            else []
        ),
        score=score.score,
        map_url=item.map_url,
        provenance={
            "cadastre": parcel.provenance.as_dict() if parcel.provenance else None,
            "land_registry": (
                unit.provenance.as_dict() if unit is not None and unit.provenance else None
            ),
        },
    )


@dataclass
class _Holding:
    record: PersonRecord
    parcels: dict[str, Role]
    owned: float = 0.0
    possessed_only: float = 0.0
    possessed: float = 0.0
    shares_unknown: int = 0
    fuzzy: int = 0
    likely_deceased: bool | None = None
    address_abroad: bool | None = None

    def add_flags(self, record: PersonRecord) -> None:
        """Fold one owner record's flags in: any flagged record flags the person."""
        flags = record.flags
        if flags is None:
            return
        if flags.likely_deceased is not None:
            self.likely_deceased = (
                bool(self.likely_deceased) or flags.likely_deceased.likely_deceased
            )
        if flags.address_abroad.abroad is not None:
            self.address_abroad = bool(self.address_abroad) or flags.address_abroad.abroad


@dataclass
class _Cell:
    """One person on one parcel, merged over every register record that names them there."""

    record: PersonRecord
    role: Role
    owner_share: Fraction | None = None
    owner_share_unknown: bool = False
    possessor_share: Fraction | None = None
    possessor_share_unknown: bool = False
    fuzzy: bool = False
    records: int = 0
    flagged: list[PersonRecord] = field(default_factory=list)
    possessors_seen: set[int] = field(default_factory=set)

    def add(
        self,
        role: Role,
        fuzzy: bool,
        owner_share: Share,
        possessor_share: Share,
        record: PersonRecord | None = None,
        possessor_id: int | None = None,
    ) -> None:
        self.records += 1
        if record is not None and record.flags is not None:
            self.flagged.append(record)
        self.fuzzy = self.fuzzy or fuzzy
        if self.records > 1 and self.role != role:
            self.role = "both"
        if role in ("owner", "both"):
            self.owner_share, self.owner_share_unknown = _add_share(
                self.owner_share, self.owner_share_unknown, owner_share
            )
        # One possessor record matched by two owner records (a person on two
        # shares) is one possession share, added once.
        if role in ("possessor", "both") and possessor_id not in self.possessors_seen:
            if possessor_id is not None:
                self.possessors_seen.add(possessor_id)
            self.possessor_share, self.possessor_share_unknown = _add_share(
                self.possessor_share, self.possessor_share_unknown, possessor_share
            )


def _add_share(
    total: Fraction | None, unknown: bool, share: Share
) -> tuple[Fraction | None, bool]:
    """Add one register record's share to a running total; a missing share taints the total."""
    if not share or share.get("den") in (None, 0) or share.get("num") is None:
        return total, True
    part = Fraction(int(share["num"]), int(share["den"]))
    return (total or Fraction(0)) + part, unknown


def _share_dict(total: Fraction | None, unknown: bool) -> Share:
    """A summed share as ``{num, den, decimal}``; None when a record gave no share."""
    if total is None or unknown:
        return None
    return {"num": total.numerator, "den": total.denominator, "decimal": float(total)}


def _person_keys(records: list[PersonRecord]) -> dict[int, str]:
    """A key per record that tells people apart the way ``count_distinct_persons`` does."""
    groups = group_by_person((r.name, r.tax_number) for r in records)
    return {
        index: person_group_key(person_key(r.name, r.tax_number).strict, r.tax_number, groups)
        for index, r in enumerate(records)
    }


def build_assembly(
    items: list[AssemblyInput], weights: dict[str, float] | None = None
) -> AssemblyAnalysis:
    """The matrix, the ranking and the scores for a set of parcels (pure; nothing is fetched)."""
    used = resolve_weights(weights)
    scores = [acquisition_score(item, used) for item in items]
    summaries = [_summary(item, score) for item, score in zip(items, scores, strict=True)]

    # Every (person, parcel, role) occurrence, then one key per person.
    occurrences: list[_Occurrence] = []
    for item in items:
        number = item.parcel.parcel_number
        for match in item.comparison.matched:
            occurrences.append(
                (
                    match.owner,
                    number,
                    "both",
                    match.fuzzy,
                    match.owner.share,
                    match.possessor.share,
                    id(match.possessor),
                )
            )
        for owner in item.comparison.owners_only:
            occurrences.append((owner, number, "owner", False, owner.share, None, None))
        for possessor in item.comparison.possessors_only:
            occurrences.append(
                (possessor, number, "possessor", False, None, possessor.share, None)
            )
    keys = _person_keys([occ[0] for occ in occurrences])
    areas = {item.parcel.parcel_number: float(item.parcel.area_numeric or 0) for item in items}

    # One cell per person and parcel: a person with two shares of one parcel
    # (an inherited quarter and a bought quarter) is two register records,
    # one cell with the shares added; a person matched as owner on one record
    # and left as owner only on another is still both on that parcel.
    cells: dict[tuple[str, str], _Cell] = {}
    for index, occurrence in enumerate(occurrences):
        record, number, role, fuzzy, owner_share, possessor_share, possessor_id = occurrence
        cell = cells.setdefault((keys[index], number), _Cell(record, role))
        cell.add(role, fuzzy, owner_share, possessor_share, record, possessor_id)

    holdings: dict[str, _Holding] = {}
    matrix: list[MatrixCell] = []
    for (key, number), cell in cells.items():
        holding = holdings.setdefault(key, _Holding(cell.record, {}))
        holding.parcels[number] = cell.role
        holding.fuzzy += int(cell.fuzzy)
        for flagged in cell.flagged:
            holding.add_flags(flagged)
        if cell.role in ("owner", "both"):
            if cell.owner_share is not None and not cell.owner_share_unknown:
                holding.owned += float(cell.owner_share) * areas[number]
            else:
                holding.owned += areas[number]
                holding.shares_unknown += 1
        if cell.role in ("possessor", "both"):
            holding.possessed += areas[number]
        if cell.role == "possessor":
            holding.possessed_only += areas[number]
        matrix.append(
            MatrixCell(
                person_key=key,
                parcel_number=number,
                role=cell.role,
                owner_share=_share_dict(cell.owner_share, cell.owner_share_unknown),
                possessor_share=_share_dict(cell.possessor_share, cell.possessor_share_unknown),
                fuzzy=cell.fuzzy,
                records=cell.records,
            )
        )

    persons = [
        PersonHolding(
            key=key,
            name=h.record.name,
            surname=surname_of(h.record.name),
            tax_number=h.record.tax_number,
            party_type_inferred=h.record.party_type_inferred,
            parcels=sorted(h.parcels),
            owner_of=sorted(n for n, r in h.parcels.items() if r in ("owner", "both")),
            possessor_of=sorted(n for n, r in h.parcels.items() if r in ("possessor", "both")),
            owned_area_m2=round(h.owned, 1),
            possessed_area_m2=round(h.possessed, 1),
            controlled_area_m2=round(h.owned + h.possessed_only, 1),
            shares_unknown=h.shares_unknown,
            fuzzy_matches=h.fuzzy,
            likely_deceased=h.likely_deceased,
            address_abroad=h.address_abroad,
        )
        for key, h in holdings.items()
    ]
    persons.sort(key=lambda p: (-p.controlled_area_m2, p.name))

    groups: dict[str, list[PersonHolding]] = {}
    for person in persons:
        groups.setdefault(person.surname, []).append(person)
    surname_groups = [
        SurnameGroup(
            surname=surname,
            persons=[p.key for p in members],
            person_count=len(members),
            parcel_count=len({n for p in members for n in p.parcels}),
            controlled_area_m2=round(sum(p.controlled_area_m2 for p in members), 1),
            likely_deceased_count=sum(1 for p in members if p.likely_deceased),
            address_abroad_count=sum(1 for p in members if p.address_abroad),
        )
        for surname, members in groups.items()
    ]
    surname_groups.sort(key=lambda g: (-g.controlled_area_m2, g.surname))

    totals = _totals(items, summaries, persons)
    order = sorted(
        range(len(items)),
        key=lambda i: (
            scores[i].score is None,
            -(scores[i].score or 0),
            summaries[i].parcel_number,
        ),
    )
    notes: list[str] = []
    if any(p.shares_unknown for p in persons):
        notes.append("an owner role without a registered share counts the whole parcel as owned")
    if any(cell.records > 1 for cell in matrix):
        notes.append(
            "a person named by several records of one register on one parcel is one cell, "
            "shares added"
        )
    if any(p.fuzzy_matches for p in persons):
        notes.append(
            "some owner/possessor pairs were matched on the name without a relative's name"
        )
    if all(item.zoning is None for item in items):
        notes.append("zoning was not read: the building-area factor is left out of every score")
    if any(p.likely_deceased or p.address_abroad for p in persons):
        notes.append(
            "likely_deceased and address_abroad are inferred from the entry age, the name and "
            "the address; confirm before counting estates or foreign counterparties"
        )
    notes.append("party types are inferred from names; the controlled area uses cadastre areas")
    return AssemblyAnalysis(
        generated_at=now_utc_iso(),
        weights=used,
        parcels=[summaries[i] for i in order],
        persons=persons,
        surname_groups=surname_groups,
        matrix=matrix,
        scores=[scores[i] for i in order],
        totals=totals,
        notes=notes,
    )


def _totals(
    items: list[AssemblyInput], summaries: list[ParcelSummary], persons: list[PersonHolding]
) -> AssemblyTotals:
    by_use: dict[str, int] = {}
    by_relationship: dict[str, int] = {}
    by_zoning: dict[str, int] = {}
    any_zoning = any(item.zoning is not None for item in items)
    any_unit = any(item.lr_unit is not None for item in items)
    for item, summary in zip(items, summaries, strict=True):
        area = summary.area_m2 or 0
        for use, m2 in summary.land_use.items():
            by_use[use] = by_use.get(use, 0) + m2
        by_relationship[summary.relationship] = by_relationship.get(summary.relationship, 0) + area
        if summary.zoning_status is not None:
            by_zoning[summary.zoning_status] = by_zoning.get(summary.zoning_status, 0) + area
    possessors = [
        (p.name, p.tax_number) for item in items for p in item.comparison.possessors
    ]
    owners = [(o.name, o.tax_number) for item in items for o in item.comparison.owners]
    party_types: dict[str, int] = {}
    for person in persons:
        kind = person.party_type_inferred.party_type
        party_types[kind] = party_types.get(kind, 0) + 1
    by_verdict: dict[str, int] = {}
    for summary in summaries:
        if summary.sale_verdict is not None:
            by_verdict[summary.sale_verdict] = by_verdict.get(summary.sale_verdict, 0) + 1
    return AssemblyTotals(
        parcel_count=len(items),
        total_area_m2=sum(s.area_m2 or 0 for s in summaries),
        area_by_land_use=by_use,
        area_by_relationship=by_relationship,
        area_by_zoning_status=by_zoning if any_zoning else None,
        distinct_people=count_distinct_persons(possessors + owners),
        distinct_owners=count_distinct_persons(owners),
        distinct_possessors=count_distinct_persons(possessors),
        party_types=party_types,
        public_body_parcels=sum(1 for s in summaries if (s.public_body_owner_share or 0) > 0),
        fuzzy_matches=sum(item.comparison.fuzzy_matches for item in items),
        parcels_with_encumbrances=(
            sum(1 for s in summaries if s.has_encumbrances) if any_unit else None
        ),
        parcels_with_pending_plombe=(
            sum(1 for s in summaries if s.has_pending_plombe) if any_unit else None
        ),
        parcels_in_building_area=(
            sum(1 for s in summaries if s.in_building_area) if any_zoning else None
        ),
        parcels_by_verdict=by_verdict if any_unit else None,
        persons_likely_deceased=sum(1 for p in persons if p.likely_deceased),
        persons_address_abroad=sum(1 for p in persons if p.address_abroad),
    )
