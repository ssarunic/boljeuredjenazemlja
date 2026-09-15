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

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from ..models.entities import LandRegistryUnitDetailed, ParcelInfo
from ..models.planning_entities import ParcelZoning
from ..models.provenance import now_utc_iso
from .persons import PartyTypeInference, count_distinct_persons, person_key
from .registers import PersonRecord, RegisterComparison

#: Default weights of the ease-of-acquisition factors (they sum to 1).
DEFAULT_WEIGHTS: dict[str, float] = {
    "single_owner": 0.25,
    "owner_is_possessor": 0.25,
    "no_encumbrances": 0.20,
    "no_pending_plombe": 0.15,
    "in_building_area": 0.15,
}

Role = Literal["owner", "possessor", "both"]


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
    owner_share: dict | None = None
    possessor_share: dict | None = None
    fuzzy: bool = Field(default=False, description="The owner/possessor match was fuzzy")


class PersonHolding(BaseModel):
    """One person across the set, with the area they own or possess."""

    key: str
    name: str
    surname: str = Field(description="First word of the folded name (the registers write it first)")
    tax_number: str | None
    party_type_inferred: PartyTypeInference
    parcels: list[str]
    owner_of: list[str]
    possessor_of: list[str]
    owned_area_m2: float = Field(
        description="Sum of share x cadastre area over the parcels the person owns"
    )
    possessed_area_m2: float = Field(
        description="Cadastre area of the parcels the person possesses (shares not applied)"
    )
    controlled_area_m2: float = Field(
        description="Owned area plus the area of the parcels the person only possesses"
    )
    shares_unknown: int = Field(description="Owner roles without a share; counted as the whole")
    fuzzy_matches: int


class SurnameGroup(BaseModel):
    """Persons sharing a surname (a family, most of the time)."""

    surname: str
    persons: list[str] = Field(description="Person keys")
    person_count: int
    parcel_count: int
    controlled_area_m2: float


class ParcelSummary(BaseModel):
    """One parcel of the set, with the facts the ranking rests on."""

    parcel_number: str
    municipality_code: str
    area_m2: int | None
    land_use: dict[str, int]
    lr_unit: dict | None
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
    score: float | None
    map_url: str | None
    provenance: dict[str, dict | None]


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
    factors: dict[str, bool | None] = {
        "single_owner": comparison.distinct_owners == 1 if unit is not None else None,
        "owner_is_possessor": (
            comparison.relationship == "same"
            if unit is not None and comparison.possessors and comparison.owners
            else None
        ),
        "no_encumbrances": not unit.has_sheet_c_entries() if unit is not None else None,
        "no_pending_plombe": not unit.has_pending_plombe() if unit is not None else None,
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


def _person_keys(records: list[PersonRecord]) -> dict[int, str]:
    """A key per record that tells people apart the way ``count_distinct_persons`` does."""
    taxes_by_name: dict[str, set[str]] = {}
    keys = [person_key(r.name, r.tax_number) for r in records]
    for key in keys:
        taxes_by_name.setdefault(key.strict, set())
        if key.tax_number:
            taxes_by_name[key.strict].add(key.tax_number)
    result: dict[int, str] = {}
    for index, key in enumerate(keys):
        taxes = taxes_by_name[key.strict]
        if key.tax_number:
            result[index] = f"{key.strict}#{key.tax_number}"
        elif len(taxes) == 1:
            result[index] = f"{key.strict}#{next(iter(taxes))}"
        else:
            result[index] = key.strict
    return result


def build_assembly(
    items: list[AssemblyInput], weights: dict[str, float] | None = None
) -> AssemblyAnalysis:
    """The matrix, the ranking and the scores for a set of parcels (pure; nothing is fetched)."""
    used = resolve_weights(weights)
    scores = [acquisition_score(item, used) for item in items]
    summaries = [_summary(item, score) for item, score in zip(items, scores, strict=True)]

    # Every (person, parcel, role) occurrence, then one key per person.
    occurrences: list[tuple[PersonRecord, str, Role, bool, dict | None, dict | None]] = []
    for item in items:
        number = item.parcel.parcel_number
        for match in item.comparison.matched:
            occurrences.append(
                (match.owner, number, "both", match.fuzzy, match.owner.share, match.possessor.share)
            )
        for owner in item.comparison.owners_only:
            occurrences.append((owner, number, "owner", False, owner.share, None))
        for possessor in item.comparison.possessors_only:
            occurrences.append((possessor, number, "possessor", False, None, possessor.share))
    keys = _person_keys([occ[0] for occ in occurrences])
    areas = {item.parcel.parcel_number: float(item.parcel.area_numeric or 0) for item in items}

    holdings: dict[str, _Holding] = {}
    matrix: list[MatrixCell] = []
    for index, occurrence in enumerate(occurrences):
        record, number, role, fuzzy, owner_share, possessor_share = occurrence
        key = keys[index]
        holding = holdings.setdefault(key, _Holding(record, {}))
        holding.parcels[number] = role
        holding.fuzzy += int(fuzzy)
        if role in ("owner", "both"):
            if owner_share and owner_share.get("decimal") is not None:
                holding.owned += float(owner_share["decimal"]) * areas[number]
            else:
                holding.owned += areas[number]
                holding.shares_unknown += 1
        if role in ("possessor", "both"):
            holding.possessed += areas[number]
        if role == "possessor":
            holding.possessed_only += areas[number]
        matrix.append(
            MatrixCell(
                person_key=key,
                parcel_number=number,
                role=role,
                owner_share=owner_share,
                possessor_share=possessor_share,
                fuzzy=fuzzy,
            )
        )

    persons = [
        PersonHolding(
            key=key,
            name=h.record.name,
            surname=(person_key(h.record.name).strict.split() or [""])[0],
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
    if any(p.fuzzy_matches for p in persons):
        notes.append(
            "some owner/possessor pairs were matched on the name without a relative's name"
        )
    if all(item.zoning is None for item in items):
        notes.append("zoning was not read: the building-area factor is left out of every score")
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
    )
