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

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from ..models.entities import FileStatus, LandRegistryUnitDetailed, ParcelInfo
from ..models.provenance import Register
from ..utils import fold_text
from .area_check import AreaCheck, check_area
from .owner_flags import OwnerFlags, count_owner_flags, owner_flags
from .persons import (
    PartyTypeInference,
    count_distinct_persons,
    group_by_person,
    group_size,
    infer_party_type,
    person_key,
    plain_reorder,
    same_person,
)
from .sale_blockers import Blocker, SaleBlockers, detect_blockers, merge_blockers

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
    share: dict[str, Any] | None = Field(
        default=None, description="{num, den, decimal} when the register gives one"
    )
    tax_number: str | None = None
    address: str | None = None
    condominium_number: str | None = None
    share_order_number: str | None = Field(
        default=None, description="The top-level share an owner sits on (land registry only)"
    )
    party_type_inferred: PartyTypeInference
    flags: OwnerFlags | None = Field(
        default=None,
        description="likely_deceased, address_abroad, public_body (owners only; inferred)",
    )
    key: str = Field(description="Strict person key (see persons.person_key)")

    @property
    def register(self) -> Register:
        return self.register_


MatchVia = Literal["tax_number", "name", "name_reordered", "name_loose", "tax_number_extension"]


class MatchedPerson(BaseModel):
    """A person found in both registers."""

    possessor: PersonRecord
    owner: PersonRecord
    fuzzy: bool = Field(
        description="Matched on the name alone: a relative written differently, or another order"
    )
    via: MatchVia = Field(
        default="name",
        description=(
            "How the pair was found: tax_number, name (the same words in the same order), "
            "name_reordered (the same words in another order), name_loose (a relative's "
            "name differs or is missing on one side), tax_number_extension (another share "
            "of an owner already matched, with the same OIB)"
        ),
    )
    extended_from: str | None = Field(
        default=None,
        description="The share order number the match was extended from (tax_number_extension)",
    )
    shares_agree: bool | None = Field(
        default=None,
        description="Whether both registers give the same share; None when one gives none",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def by_tax_number(self) -> bool:
        """Possessor and owner matched on the tax number (OIB): derived from ``via``.

        An extension to another share of an owner already matched rests on
        the two owner records' OIB, not on the possessor's, so it is not one.
        """
        return self.via == "tax_number"


class RegisterComparison(BaseModel):
    """Cadastre possessors against land-registry owners for one parcel."""

    parcel_number: str
    municipality_code: str
    lr_unit: dict[str, Any] | None = Field(
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
    sale_blockers: SaleBlockers | None = Field(
        default=None,
        description=(
            "What is registered against the unit that bears on a sale, plus owner_not_possessor "
            "and fuzzy_owner_match from this comparison; None without a unit"
        ),
    )
    owner_flag_counts: dict[str, int] | None = Field(
        default=None,
        description="Owner records flagged likely_deceased, address_abroad, public_body (inferred)",
    )
    summary: str
    notes: list[str]


def _record(
    name: str,
    register: Register,
    share: dict[str, Any] | None,
    tax_number: str | None,
    address: str | None,
    condominium_number: str | None = None,
    share_order_number: str | None = None,
    flags: OwnerFlags | None = None,
) -> PersonRecord:
    return PersonRecord(
        name=name,
        register=register,
        share=share,
        tax_number=tax_number,
        address=address,
        condominium_number=condominium_number,
        share_order_number=share_order_number,
        party_type_inferred=flags.party_type_inferred if flags else infer_party_type(name),
        flags=flags,
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
    """The current owners of a unit (sheet B rows) as person records, with their flags."""
    return [
        _record(
            row["name"],
            "land_registry",
            row.get("share"),
            row.get("tax_number"),
            row.get("address"),
            row.get("condominium_number"),
            row.get("share_order_number"),
            owner_flags(
                row["name"], row.get("address"), row.get("entry"), tax_number=row.get("tax_number")
            ),
        )
        for row in lr_unit.ownership_sheet_b.owner_rows()
    ]


def _owner_not_possessor(owner: PersonRecord) -> Blocker:
    """An owner the cadastre does not list.

    Across Dalmatia the cadastre lags the register by years, so an owner
    whose entry is recent and carries an OIB is the normal state and only
    informational; an owner with an old or legacy record, or without an
    OIB, may face a possessor who is a genuine third party: conditional.
    """
    deceased = owner.flags.likely_deceased if owner.flags is not None else None
    recent = bool(owner.tax_number) and deceased is not None and not deceased.likely_deceased
    return Blocker(
        kind="owner_not_possessor",
        severity="informational" if recent else "conditional",
        scope="share" if owner.share_order_number else "unit",
        share_order_number=owner.share_order_number,
        condominium_unit=owner.condominium_number,
        source="register_comparison",
        description=f"registered owner {owner.name} is not a cadastre possessor of the parcel",
        basis=(
            "the name is on sheet B and on no possession sheet; the entry is recent and "
            "carries an OIB, so the cadastre has not caught up with the register"
            if recent
            else "the name is on sheet B and on no possession sheet; the record is old or "
            "carries no OIB, so the possessor may be a genuine third party"
        ),
        beneficiary=owner.name,
    )


def _comparison_blockers(
    matched: list[MatchedPerson],
    owners_only: list[PersonRecord],
    area_check: AreaCheck,
    estate_shares: set[str | None],
) -> list[Blocker]:
    """The blockers only a comparison of the two registers can see.

    An owner whose share is already a ``likely_estate`` blocker gets no
    ``owner_not_possessor`` row: a deceased owner not appearing as possessor
    is expected, not a second risk.
    """
    blockers = [
        _owner_not_possessor(owner)
        for owner in owners_only
        if owner.share_order_number not in estate_shares
    ]
    blockers.extend(
        Blocker(
            kind="fuzzy_owner_match",
            severity="informational",
            scope="share" if pair.owner.share_order_number else "unit",
            share_order_number=pair.owner.share_order_number,
            condominium_unit=pair.owner.condominium_number,
            source="register_comparison",
            description=(
                f"owner {pair.owner.name} matched possessor {pair.possessor.name} on the name "
                f"alone: "
                + (
                    "the name is written in another order and nothing corroborates it"
                    if pair.via == "name_reordered"
                    else "the relative's name is written differently or missing on one side"
                )
                + "; confirm it is one person"
            ),
            basis=f"matched via {pair.via}; the strict person key did not match",
            beneficiary=pair.owner.name,
        )
        for pair in matched
        if pair.fuzzy
    )
    if area_check.mismatch:
        figures = ", ".join(
            f"{label} {value:,.0f} m²"
            for label, value in (
                ("cadastre", area_check.cadastre_m2),
                ("land register", area_check.land_registry_m2),
                ("map", area_check.gis_m2),
            )
            if value is not None
        )
        fraction = area_check.max_difference_fraction or 0.0
        blockers.append(
            Blocker(
                kind="area_mismatch",
                severity="conditional",
                scope="unit",
                source="register_comparison",
                description=(
                    f"the areas the registers give the parcel differ by {fraction:.0%}: "
                    f"{figures}; a sale or a mortgage needs the area settled by a survey"
                ),
                basis=(
                    f"area_check: the largest difference is {fraction:.0%}, above the "
                    f"{area_check.tolerance_fraction:.0%} tolerance"
                ),
            )
        )
    return blockers




def _shares_agree(a: dict[str, Any] | None, b: dict[str, Any] | None) -> bool | None:
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
    # A person on several shares is several owner records. Once one of them
    # matched a possessor, the others with the same tax number are the same
    # person and match the same possessor, so that the person is never both
    # matched and "owner only". Only the OIB extends a match: the same name
    # on another share may be a namesake (a grandson written like the
    # grandfather), and that record stays owner only.
    unmatched_o: list[PersonRecord] = []
    for j, owner in enumerate(owners):
        if j in taken:
            continue
        pair = next(
            (
                m
                for m in matched
                if keys_o[j].tax_number and m.owner.tax_number == keys_o[j].tax_number
            ),
            None,
        )
        if pair is None:
            unmatched_o.append(owner)
            continue
        matched.append(
            MatchedPerson(
                possessor=pair.possessor,
                owner=owner,
                fuzzy=pair.fuzzy,
                shares_agree=None,
                via="tax_number_extension",
                extended_from=pair.owner.share_order_number,
            )
        )
    return matched, unmatched_p, unmatched_o


def _pair(possessor, owner, key_p, key_o, fuzzy: bool) -> MatchedPerson:  # type: ignore[no-untyped-def]
    shares_agree = _shares_agree(possessor.share, owner.share)
    via: MatchVia = "tax_number" if key_p.tax_number and key_o.tax_number else "name"
    if fuzzy:
        via = "name_reordered" if plain_reorder(key_p, key_o) else "name_loose"
    # A name written in another order with no relative on either side agrees
    # in full; when the shares or the addresses agree too it is not a guess.
    if via == "name_reordered":
        addresses = fold_text(possessor.address or ""), fold_text(owner.address or "")
        if shares_agree or (all(addresses) and addresses[0] == addresses[1]):
            fuzzy = False
    return MatchedPerson(
        possessor=possessor,
        owner=owner,
        fuzzy=fuzzy,
        shares_agree=shares_agree,
        via=via,
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
    groups = group_by_person((r.name, r.tax_number) for r in people)
    kind_of = {r.key: r.party_type_inferred.party_type for r in people}
    counts: dict[str, int] = {}
    for strict, taxes in groups.items():
        kind = kind_of.get(strict, "unknown")
        counts[kind] = counts.get(kind, 0) + group_size(taxes)
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
    plombe_detail: dict[str, FileStatus] | None = None,
) -> RegisterComparison:
    """Match a parcel's possessors against its unit's owners (pure; nothing is fetched).

    ``lr_unit`` is the unit the parcel belongs to, or None when the parcel is
    not in the land registry; ``lr_unit_error`` says why a unit that should
    exist could not be read. ``gis_area_m2`` (the graphical area of the
    outline) joins the area check when known. ``plombe_detail`` (file number
    -> ``FileStatus``) names the pending requests among the sale blockers.
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
            "a fuzzy match rests on the name alone (a relative's name written differently or "
            "missing on one side, or the words in another order); confirm it"
        )

    # Distinct people across both registers: a matched pair is one person.
    people: list[PersonRecord] = [m.owner for m in matched] + only_p + only_o
    party_types = _party_type_counts(people)
    public_share: float | None = None
    if owners and all(o.share for o in owners):
        public_share = round(
            sum(
                float(o.share["decimal"])
                for o in owners
                if o.share and o.party_type_inferred.party_type in ("state", "municipality")
            ),
            6,
        )

    area_check = check_area(
        cadastre_m2=parcel.area_numeric or None,
        land_registry_m2=lr_area,
        gis_m2=gis_area_m2,
    )
    sale_blockers: SaleBlockers | None = None
    flag_counts: dict[str, int] | None = None
    if lr_unit is not None:
        unit_blockers = detect_blockers(lr_unit, plombe_detail=plombe_detail)
        estate_shares = {
            b.share_order_number for b in unit_blockers.blockers if b.kind == "likely_estate"
        }
        sale_blockers = merge_blockers(
            unit_blockers, _comparison_blockers(matched, only_o, area_check, estate_shares)
        )
        flag_counts = count_owner_flags(o.flags for o in owners)
        if flag_counts["likely_deceased"] or flag_counts["address_abroad"]:
            notes.append(
                "owner flags (likely deceased, address abroad) are inferred from the entry age, "
                "the name and the address; confirm them before relying on a count"
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
        sale_blockers=sale_blockers,
        owner_flag_counts=flag_counts,
        summary=_summary(
            relationship,
            count_distinct_persons((m.owner.name, m.owner.tax_number) for m in matched),
            len(only_p),
            len(only_o),
        ),
        notes=notes,
    )
