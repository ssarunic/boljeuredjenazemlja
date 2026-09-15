"""Are the cadastre possessors of a parcel its registered owners?

The cadastre (posjedovni list) records who holds and uses a parcel; the land
registry (vlastovnica, sheet B) records who owns it. The two are kept by
different bodies and frequently disagree: an heir farms land still registered
to a grandparent, a buyer is registered but the seller stays on the possession
sheet. Anyone buying land needs to know whether the person using it is the
person to sign with. This module matches the two lists of names with the
shared person identity (``persons``) and says which is which.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..models.entities import LandRegistryUnitDetailed, ParcelInfo
from ..models.provenance import Register
from .area_check import AreaCheck, check_area
from .persons import (
    PartyTypeInference,
    count_distinct_persons,
    infer_party_type,
    person_key,
    same_person,
)

Relationship = Literal[
    "same",
    "overlapping",
    "disjoint",
    "cadastre_only",
    "no_possessors",
    "no_owners",
    "land_registry_unavailable",
]


class PersonRecord(BaseModel):
    """One person as one register records them on this parcel.

    The register is stored as ``register_`` and read and written as
    ``register`` (pydantic 2.12's ``BaseModel`` owns that attribute name).
    """

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    name: str
    register_: Register = Field(alias="register", description="cadastre | land_registry")
    share: dict | None = Field(
        default=None, description="{num, den, decimal} when the register gives one"
    )
    tax_number: str | None = None
    address: str | None = None
    condominium_number: str | None = None
    party_type_inferred: PartyTypeInference
    key: str = Field(description="Strict person key (see persons.person_key)")

    @property
    def register(self) -> Register:
        return self.register_


class MatchedPerson(BaseModel):
    """A person found in both registers."""

    possessor: PersonRecord
    owner: PersonRecord
    fuzzy: bool = Field(description="Matched on the loose key only (a relative's name differs)")
    by_tax_number: bool = Field(description="Matched on the tax number (OIB)")
    shares_agree: bool | None = Field(
        default=None,
        description="Whether both registers give the same share; None when one gives none",
    )


class RegisterComparison(BaseModel):
    """Cadastre possessors against land-registry owners for one parcel."""

    parcel_number: str
    municipality_code: str
    lr_unit: dict | None = Field(
        default=None, description="{lr_unit_number, main_book_id} compared against"
    )
    relationship: Relationship
    possessors: list[PersonRecord]
    owners: list[PersonRecord]
    matched: list[MatchedPerson]
    possessors_only: list[PersonRecord]
    owners_only: list[PersonRecord]
    fuzzy_matches: int
    distinct_possessors: int
    distinct_owners: int
    distinct_people: int = Field(description="Different people across both registers")
    party_types: dict[str, int] = Field(description="Inferred party types of the distinct people")
    public_body_owner_share: float | None = Field(
        default=None,
        description=(
            "Share of the parcel registered to the state or a municipality (inferred), "
            "when shares are given"
        ),
    )
    area_check: AreaCheck
    summary: str
    notes: list[str]


def _record(
    name: str,
    register: Register,
    share: dict | None,
    tax_number: str | None,
    address: str | None,
    condominium_number: str | None = None,
) -> PersonRecord:
    return PersonRecord(
        name=name,
        register=register,
        share=share,
        tax_number=tax_number,
        address=address,
        condominium_number=condominium_number,
        party_type_inferred=infer_party_type(name),
        key=person_key(name, tax_number).strict,
    )


def possessor_records(parcel: ParcelInfo) -> list[PersonRecord]:
    """The possessors of a parcel's possession sheets as person records."""
    return [
        _record(
            p.name,
            "cadastre",
            p.ownership_fraction,
            None,
            p.address,
            p.condominium_share_number,
        )
        for sheet in parcel.possession_sheets
        for p in sheet.possessors
    ]


def owner_records(lr_unit: LandRegistryUnitDetailed) -> list[PersonRecord]:
    """The current owners of a unit (sheet B rows) as person records."""
    return [
        _record(
            row["name"],
            "land_registry",
            row.get("share"),
            row.get("tax_number"),
            row.get("address"),
            row.get("condominium_number"),
        )
        for row in lr_unit.ownership_sheet_b.owner_rows()
    ]


def _shares_agree(a: dict | None, b: dict | None) -> bool | None:
    if not a or not b:
        return None
    return abs(float(a["decimal"]) - float(b["decimal"])) < 1e-9


def _match(
    possessors: list[PersonRecord], owners: list[PersonRecord]
) -> tuple[list[MatchedPerson], list[PersonRecord], list[PersonRecord]]:
    """Pair possessors with owners one to one: exact matches first, then fuzzy."""
    keys_p = [person_key(p.name, p.tax_number) for p in possessors]
    keys_o = [person_key(o.name, o.tax_number) for o in owners]
    taken: set[int] = set()
    matched: list[MatchedPerson] = []
    unmatched_p: list[PersonRecord] = []
    pending: list[tuple[int, PersonRecord]] = []
    for i, possessor in enumerate(possessors):
        hit = next(
            (
                j
                for j in range(len(owners))
                if j not in taken and same_person(keys_p[i], keys_o[j]) == (True, False)
            ),
            None,
        )
        if hit is None:
            pending.append((i, possessor))
            continue
        taken.add(hit)
        matched.append(_pair(possessor, owners[hit], keys_p[i], keys_o[hit], fuzzy=False))
    for i, possessor in pending:
        hit = next(
            (
                j
                for j in range(len(owners))
                if j not in taken and same_person(keys_p[i], keys_o[j])[0]
            ),
            None,
        )
        if hit is None:
            unmatched_p.append(possessor)
            continue
        taken.add(hit)
        matched.append(_pair(possessor, owners[hit], keys_p[i], keys_o[hit], fuzzy=True))
    unmatched_o = [o for j, o in enumerate(owners) if j not in taken]
    return matched, unmatched_p, unmatched_o


def _pair(possessor, owner, key_p, key_o, fuzzy: bool) -> MatchedPerson:  # type: ignore[no-untyped-def]
    return MatchedPerson(
        possessor=possessor,
        owner=owner,
        fuzzy=fuzzy,
        by_tax_number=bool(key_p.tax_number and key_o.tax_number),
        shares_agree=_shares_agree(possessor.share, owner.share),
    )


def _sheet_a_area(
    parcel: ParcelInfo, lr_unit: LandRegistryUnitDetailed
) -> tuple[int | None, str | None]:
    """The land register's area of this parcel from sheet A (a note when matched by LR number)."""
    numbers = {parcel.parcel_number}
    linked = {link.parcel_number for link in parcel.parcel_links or []}
    for record in lr_unit.possessory_sheet_a1.cad_parcels:
        if record.parcel_number == parcel.parcel_number and record.area_numeric:
            return record.area_numeric, None
    for record in lr_unit.possessory_sheet_a1.cad_parcels:
        if record.parcel_number in linked - numbers and record.area_numeric:
            return record.area_numeric, (
                f"land-register area is that of land-register parcel {record.parcel_number}, "
                f"linked to this cadastre parcel"
            )
    return None, "the unit's sheet A does not list this parcel number"


def _party_type_counts(people: list[PersonRecord]) -> dict[str, int]:
    """Inferred party types of the distinct people (grouped as ``count_distinct_persons`` does)."""
    groups: dict[str, tuple[str, set[str]]] = {}
    for record in people:
        key = person_key(record.name, record.tax_number)
        if not key.strict:
            continue
        kind, taxes = groups.setdefault(
            key.strict, (record.party_type_inferred.party_type, set())
        )
        if key.tax_number:
            taxes.add(key.tax_number)
    counts: dict[str, int] = {}
    for kind, taxes in groups.values():
        counts[kind] = counts.get(kind, 0) + max(1, len(taxes))
    return counts


def _summary(relationship: Relationship, matched: int, only_p: int, only_o: int) -> str:
    if relationship == "same":
        return f"Cadastre and land registry name the same {matched} person(s)."
    if relationship == "overlapping":
        return (
            f"{matched} person(s) appear in both registers; {only_p} possessor(s) are not "
            f"registered owners and {only_o} registered owner(s) are not possessors."
        )
    if relationship == "disjoint":
        return "The cadastre possessors and the registered owners are different people."
    if relationship == "cadastre_only":
        return "The parcel is not in the land registry: cadastre possessors only."
    if relationship == "no_owners":
        return "The land-registry unit lists no current owner."
    if relationship == "no_possessors":
        return "The cadastre lists no possessor for the parcel."
    return "The land-registry unit could not be read; cadastre possessors only."


def compare_registers(
    parcel: ParcelInfo,
    lr_unit: LandRegistryUnitDetailed | None,
    gis_area_m2: float | None = None,
    lr_unit_error: str | None = None,
) -> RegisterComparison:
    """Match a parcel's possessors against its unit's owners (pure; nothing is fetched).

    ``lr_unit`` is the unit the parcel belongs to, or None when the parcel is
    not in the land registry; ``lr_unit_error`` says why a unit that should
    exist could not be read. ``gis_area_m2`` (the graphical area of the
    outline) joins the area check when known.
    """
    possessors = possessor_records(parcel)
    owners = owner_records(lr_unit) if lr_unit is not None else []
    notes: list[str] = []
    matched: list[MatchedPerson] = []
    only_p, only_o = list(possessors), list(owners)
    lr_ref = None
    lr_area: int | None = None
    if lr_unit is not None:
        lr_ref = {"lr_unit_number": lr_unit.lr_unit_number, "main_book_id": lr_unit.main_book_id}
        lr_area, area_note = _sheet_a_area(parcel, lr_unit)
        if area_note:
            notes.append(area_note)
    elif lr_unit_error:
        notes.append(f"land-registry unit not read: {lr_unit_error}")

    relationship: Relationship
    if lr_unit is None:
        relationship = "land_registry_unavailable" if lr_unit_error else "cadastre_only"
    elif not owners:
        relationship = "no_owners"
    elif not possessors:
        relationship = "no_possessors"
    else:
        matched, only_p, only_o = _match(possessors, owners)
        if matched and not only_p and not only_o:
            relationship = "same"
        elif matched:
            relationship = "overlapping"
        else:
            relationship = "disjoint"
    if any(m.fuzzy for m in matched):
        notes.append(
            "a fuzzy match rests on the name without the relative's name (POK./UD.); confirm it"
        )

    # Distinct people across both registers: a matched pair is one person.
    people: list[PersonRecord] = [m.owner for m in matched] + only_p + only_o
    party_types = _party_type_counts(people)
    public_share: float | None = None
    if owners and all(o.share for o in owners):
        public_share = round(
            sum(
                float(o.share["decimal"])  # type: ignore[index]
                for o in owners
                if o.party_type_inferred.party_type in ("state", "municipality")
            ),
            6,
        )

    area_check = check_area(
        cadastre_m2=parcel.area_numeric or None,
        land_registry_m2=lr_area,
        gis_m2=gis_area_m2,
    )
    return RegisterComparison(
        parcel_number=parcel.parcel_number,
        municipality_code=parcel.cad_municipality_reg_num,
        lr_unit=lr_ref,
        relationship=relationship,
        possessors=possessors,
        owners=owners,
        matched=matched,
        possessors_only=only_p,
        owners_only=only_o,
        fuzzy_matches=sum(1 for m in matched if m.fuzzy),
        distinct_possessors=count_distinct_persons((p.name, None) for p in possessors),
        distinct_owners=count_distinct_persons((o.name, o.tax_number) for o in owners),
        distinct_people=count_distinct_persons((r.name, r.tax_number) for r in people),
        party_types=party_types,
        public_body_owner_share=public_share,
        area_check=area_check,
        summary=_summary(relationship, len(matched), len(only_p), len(only_o)),
        notes=notes,
    )
