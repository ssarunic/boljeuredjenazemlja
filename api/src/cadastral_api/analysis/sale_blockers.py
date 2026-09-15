"""What is registered against a unit that a buyer must know before signing.

Sheet C, the share annotations, the pending plombe and the owners of a
land-registry unit hold everything that can stop or condition a sale, but
they hold it as Croatian prose. This module reads that prose into a list of
blockers, each with a kind (mortgage, dispute, enforcement, pre-emption, a
pending request ...), a severity, the share it attaches to and the entry it
comes from, and sums them into a verdict. The verdict is a screening of the
register's text with its rule shown, not a legal opinion: an unusual entry the
table does not recognise stays in the list as ``other_annotation`` for a
reader to judge, and a cancelled entry is listed apart rather than dropped.

Scope matters in a condominium: a mortgage on flat 88 does not block the sale
of flat 40. Every blocker therefore carries ``scope`` (``unit`` or ``share``)
with the share order number and the condominium unit it hits; a verdict for
one owner or one flat counts the unit-wide blockers and only that share's own.

Pure: nothing here makes a request. The plomba detail (what each pending
request is) is passed in when the caller has fetched it.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..models.entities import (
    EncumbranceGroup,
    FileStatus,
    LandRegistryUnitDetailed,
    LREntry,
    LRShare,
    RightType,
)
from ..utils import fold_text, split_name_share
from .owner_flags import DEFAULT_DECEASED_THRESHOLD_YEARS, owner_flags

BlockerKind = Literal[
    "pending_entry",
    "mortgage",
    "lien",
    "enforcement",
    "dispute",
    "transfer_prohibition",
    "preemption",
    "social_claim",
    "personal_servitude",
    "easement",
    "fiduciary_transfer",
    "rejected_request",
    "public_body_share",
    "likely_estate",
    "owner_not_possessor",
    "fuzzy_owner_match",
    "area_mismatch",
    "other_annotation",
]
Severity = Literal["blocking", "conditional", "informational"]
Scope = Literal["unit", "share"]
Verdict = Literal["clear", "conditional", "blocked"]
BlockerSource = Literal[
    "plomba",
    "sheet_c",
    "share_entry",
    "sheet_b_entry",
    "sheet_a2_entry",
    "ownership",
    "register_comparison",
]

#: Default severity of each kind, overridable through ``resolve_severities``.
#: Blocking: the sale cannot close as the register stands (a charge or a
#: pending request must be cleared first). Conditional: it can close, but the
#: buyer takes something with it or must satisfy a holder of a right first.
#: Informational: worth reading, changes nothing by itself.
DEFAULT_SEVERITY: dict[str, Severity] = {
    "pending_entry": "blocking",
    "mortgage": "blocking",
    "lien": "blocking",
    "enforcement": "blocking",
    "dispute": "blocking",
    "transfer_prohibition": "blocking",
    "fiduciary_transfer": "blocking",
    "social_claim": "blocking",
    "preemption": "conditional",
    "personal_servitude": "conditional",
    "easement": "conditional",
    "public_body_share": "conditional",
    "likely_estate": "conditional",
    "owner_not_possessor": "conditional",
    "fuzzy_owner_match": "informational",
    "area_mismatch": "conditional",
    "rejected_request": "informational",
    "other_annotation": "informational",
}

VERDICT_RULE = (
    "blocked when any counted blocker is blocking; conditional when any is conditional; "
    "clear otherwise. Cancelled entries are listed apart and not counted. A screening of the "
    "register's text with the severities shown, not a legal opinion; read other_annotation "
    "entries yourself."
)

#: The kinds that are charges or notes on the register (sheet C, share and
#: sheet entries), as opposed to a pending request or a fact about the people.
ENCUMBRANCE_KINDS = frozenset(
    {
        "mortgage",
        "lien",
        "enforcement",
        "dispute",
        "transfer_prohibition",
        "fiduciary_transfer",
        "social_claim",
        "preemption",
        "personal_servitude",
        "easement",
        "rejected_request",
        "other_annotation",
    }
)

#: Coarse first pass: the right ``parse_right_type`` already reads from an
#: entry. Easements, annotations and liens fall through to the finer table.
_RIGHT_TYPE_TO_KIND: dict[RightType, str] = {
    RightType.MORTGAGE: "mortgage",
    RightType.PROHIBITION: "transfer_prohibition",
    RightType.PREEMPTION: "preemption",
    RightType.USUFRUCT: "personal_servitude",
}

#: Finer classification of an entry's folded text, most specific first. The
#: patterns are folded (no diacritics, lower case) like the text they match.
_KIND_PATTERNS: tuple[tuple[str, str], ...] = (
    ("social_claim", r"trazbin\w*\s+socijaln"),
    ("fiduciary_transfer", r"prijenos\w*[\s\S]{0,200}?radi\s+osiguranja|fiducijar"),
    ("transfer_prohibition", r"zabran\w*\s+(?:otudenja|opterecenja|raspolaganja)"),
    # A judicial mortgage names its enforcement file (OVR-...) and is still a
    # mortgage; a bare enforceability note or an enforcement order is not.
    ("mortgage", r"zalozn\w*\s+prav|hipotek"),
    ("enforcement", r"\bovr-|\bovrsivost\b|\bovrh[aeiu]\b|\bovrsn\w*\b|\bovrsi\b"),
    ("dispute", r"\bspor\b|\bspora\b|\bsporu\b|\btuzb\w*|\bparnic\w*"),
    ("rejected_request", r"odbij\w*\s+(?:se\s+)?prijedlog|odbijen\w*\s+provedb"),
    ("preemption", r"prvokup|kulturno\s+dobro"),
    (
        "personal_servitude",
        r"pravo\s+stanovanja|plodo?uzivanj|dozivotn\w*\s+uzdrzavanj|"
        r"dosmrtn\w*\s+uzdrzavanj|osobn\w*\s+sluznost",
    ),
    ("easement", r"sluznost|pravo\s+uporabe|pravo\s+puta|pravo\s+prolaz"),
    ("lien", r"trazbin"),
)
#: A deleting entry names the entry it deletes: "briše se ... pod st. 49.1",
#: "upisano pod brojem 3.1", "pod red. br. 2.1".
_DELETED_REF_RE = re.compile(
    r"(?:st\.?|red\.?\s*br\.?|broj(?:em)?|r\.?\s*br\.?)\s*(\d+(?:\.\d+)+)", re.IGNORECASE
)
_PLUMB_MARK_RE = re.compile(r"[()\s]")
#: A cadastre administrative case behind a land-registry plomba: the file's
#: reference is classed UP/I 932 (survey and cadastre), most often the
#: implementation of a survey (geodetski elaborat) that changes a parcel.
_CADASTRE_CASE_RE = re.compile(r"UP/I\s*-?\s*932", re.IGNORECASE)


class Blocker(BaseModel):
    """One thing registered against the unit that bears on a sale."""

    kind: str = Field(description="pending_entry | mortgage | dispute | ... | other_annotation")
    severity: Severity
    scope: Scope = Field(description="unit: the whole unit; share: one share or condominium unit")
    share_order_number: str | None = Field(
        default=None, description="The top-level share it attaches to, when scope is share"
    )
    condominium_unit: str | None = Field(
        default=None, description="The condominium unit ('E-80') it attaches to, when known"
    )
    source: BlockerSource
    description: str = Field(description="The entry text, shortened, or a note")
    basis: str = Field(description="The pattern or rule the classification rests on")
    entry: dict[str, Any] | None = Field(
        default=None,
        description="order_number, entry_date, diary_number, action_type of the source entry",
    )
    amount: str | None = None
    amount_value: float | None = None
    amount_currency: str | None = None
    beneficiary: str | None = Field(default=None, description="Creditor, holder of the right")
    file_number: str | None = Field(default=None, description="Plomba file number (Z-broj)")
    request_kind: str | None = Field(
        default=None, description="What the pending request is, with the plomba detail"
    )
    status_description: str | None = Field(
        default=None, description="Processing stage, with the plomba detail"
    )
    dates: dict[str, str | None] | None = Field(
        default=None, description="received, solved, executed, with the plomba detail"
    )
    cancelled_by: str | None = Field(
        default=None, description="Order number of the entry that deleted this one"
    )
    likely_lapsed: bool = Field(
        default=False,
        description=(
            "A personal servitude whose entry is decades old: it ends with the holder's "
            "death, so it is probably spent and only needs deleting (inferred)"
        ),
    )


class SaleBlockers(BaseModel):
    """The blockers of one unit, or of one owner's or one flat's part of it."""

    lr_unit_number: str
    main_book_id: int
    verdict: Verdict
    rule: str = Field(default=VERDICT_RULE, description="How the verdict is derived")
    counts: dict[str, int] = Field(description="Counted blockers per severity")
    blockers: list[Blocker]
    blockers_cancelled: list[Blocker] = Field(
        default_factory=list, description="Entries a later entry deleted; not counted"
    )
    scope_filter: dict[str, str] | None = Field(
        default=None, description="{owner_name} or {condominium_unit} when narrowed"
    )
    plombe_detail_included: bool = False
    notes: list[str] = Field(default_factory=list)


def resolve_severities(overrides: dict[str, str] | None) -> dict[str, Severity]:
    """The severities to use: the defaults, overridden by ``overrides``.

    Raises:
        ValueError: an unknown kind or an unknown severity
    """
    resolved: dict[str, Severity] = dict(DEFAULT_SEVERITY)
    for kind, severity in (overrides or {}).items():
        if kind not in DEFAULT_SEVERITY:
            raise ValueError(
                f"unknown blocker kind {kind!r}; the kinds are {', '.join(DEFAULT_SEVERITY)}"
            )
        if severity not in ("blocking", "conditional", "informational"):
            raise ValueError(
                f"the severity of {kind!r} must be blocking, conditional or informational"
            )
        resolved[kind] = severity  # type: ignore[assignment]
    return resolved


def classify_entry_text(text: str | None, right_type: RightType | None = None) -> tuple[str, str]:
    """The blocker kind of an entry, and the basis: the right type or the pattern matched."""
    if right_type is not None and right_type in _RIGHT_TYPE_TO_KIND:
        return _RIGHT_TYPE_TO_KIND[right_type], f"right type {right_type.value}"
    folded = fold_text(text or "")
    for kind, pattern in _KIND_PATTERNS:
        match = re.search(pattern, folded)
        if match:
            return kind, f"the text says {match.group(0)!r}"
    return "other_annotation", "no known right or note in the text"


def unit_key(unit: str | None) -> str:
    """A condominium unit number for comparison: "E-16", "(E-16)", "E16" and "16" agree."""
    key = fold_text(_PLUMB_MARK_RE.sub("", unit or ""))
    if key.startswith("e-"):
        key = key[2:]
    elif key.startswith("e") and key[1:2].isdigit():
        key = key[1:]
    return key


def verdict_for(blockers: list[Blocker]) -> Verdict:
    """blocked > conditional > clear over the counted blockers."""
    severities = {b.severity for b in blockers}
    if "blocking" in severities:
        return "blocked"
    if "conditional" in severities:
        return "conditional"
    return "clear"


def counts_for(blockers: list[Blocker]) -> dict[str, int]:
    """Counted blockers per severity, every severity present."""
    counts = {"blocking": 0, "conditional": 0, "informational": 0}
    for blocker in blockers:
        counts[blocker.severity] += 1
    return counts


def blocker_identity(blocker: Blocker) -> tuple[str, str, str | None, str | None, str | None]:
    """A stable key for matching a blocker across two readings of the unit."""
    return (
        blocker.kind,
        blocker.scope,
        blocker.share_order_number,
        blocker.condominium_unit,
        blocker.file_number or (blocker.entry or {}).get("order_number"),
    )


def merge_blockers(base: SaleBlockers, extra: list[Blocker]) -> SaleBlockers:
    """``base`` with ``extra`` appended and the verdict and counts recomputed."""
    blockers = base.blockers + extra
    return base.model_copy(
        update={
            "blockers": blockers,
            "verdict": verdict_for(blockers),
            "counts": counts_for(blockers),
        }
    )


def _shorten(text: str, limit: int = 160) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _entry_facts(entry: LREntry) -> dict[str, Any]:
    return {
        "order_number": entry.order_number,
        "entry_date": entry.entry_date.isoformat() if entry.entry_date else None,
        "diary_number": entry.diary_number,
        "action_type": entry.action_type.value if entry.action_type else None,
    }


def _pair_deletions(entries: list[LREntry]) -> dict[int, int]:
    """Index of each deleting entry -> index of the sibling it deletes, when named.

    A deletion that names no sibling, or names one that is not here, is left
    unpaired: the deleting entry is then reported like any other rather than
    guessed at.
    """
    by_order = {entry.order_number: index for index, entry in enumerate(entries)}
    pairs: dict[int, int] = {}
    for index, entry in enumerate(entries):
        if not entry.deletes_prior_entry:
            continue
        for reference in _DELETED_REF_RE.findall(entry.description_text):
            target = by_order.get(reference)
            if target is not None and target != index:
                pairs[index] = target
                break
    return pairs


def _share_maps(lr_unit: LandRegistryUnitDetailed) -> tuple[dict[str, str | None], dict[str, str]]:
    """Top-level share order number -> condominium unit, and unit key -> share order number."""
    by_order: dict[str, str | None] = {}
    by_unit: dict[str, str] = {}
    for share in lr_unit.ownership_sheet_b.lr_unit_shares:
        by_order[share.order_number] = share.condominium_number
        if share.condominium_number:
            by_unit[unit_key(share.condominium_number)] = share.order_number
    return by_order, by_unit


class _Builder:
    """Collects the blockers of one unit."""

    def __init__(
        self,
        lr_unit: LandRegistryUnitDetailed,
        severities: dict[str, Severity],
        plombe_detail: dict[str, FileStatus] | None,
        today: date,
    ) -> None:
        self.unit = lr_unit
        self.severities = severities
        self.plombe_detail = plombe_detail or {}
        self.today = today
        self.by_order, self.by_unit = _share_maps(lr_unit)
        self.blockers: list[Blocker] = []
        self.cancelled: list[Blocker] = []
        self.notes: list[str] = []

    def _blocker(self, kind: str, **fields: Any) -> Blocker:
        return Blocker(kind=kind, severity=self.severities[kind], **fields)

    def plombe(self) -> None:
        for plumb in self.unit.active_plumbs:
            condominium = unit_key(plumb.plumb_mark) if plumb.plumb_mark else ""
            share_order = self.by_unit.get(condominium) if condominium else None
            status = self.plombe_detail.get(plumb.file_number)
            fields: dict[str, Any] = {
                "scope": "share" if plumb.plumb_mark else "unit",
                "share_order_number": share_order,
                "condominium_unit": (
                    _PLUMB_MARK_RE.sub("", plumb.plumb_mark) if plumb.plumb_mark else None
                ),
                "source": "plomba",
                "file_number": plumb.file_number,
                "basis": (
                    "a cadastre plomba is pending on the unit"
                    if plumb.cad_plumb
                    else "a request for registration is pending on the unit"
                ),
            }
            if status is not None:
                reference = " ".join(
                    filter(None, [status.registration_number, status.application_content])
                )
                if _CADASTRE_CASE_RE.search(reference):
                    fields["basis"] = (
                        "the file is a cadastre administrative case (UP/I 932: survey and "
                        "cadastre), most often a survey being implemented; a parcel's number "
                        "or area may be about to change"
                    )
                fields.update(
                    description=(
                        f"pending request {plumb.file_number}: "
                        f"{status.application_content or 'kind unknown'}"
                    ),
                    request_kind=status.application_content,
                    status_description=status.status_description,
                    dates={
                        "received": _iso(status.receiving_date),
                        "solved": _iso(status.solving_date),
                        "executed": _iso(status.execution_date),
                    },
                )
            else:
                fields["description"] = (
                    f"pending request {plumb.file_number}"
                    + (" (cadastre plomba)" if plumb.cad_plumb else "")
                    + "; kind unknown without the plomba detail"
                )
            self.blockers.append(self._blocker("pending_entry", **fields))

    def sheet_c(self) -> None:
        for group in self.unit.encumbrance_sheet_c.lr_entry_groups:
            share_order = group.share_order_number
            scope: Scope = "share" if share_order else "unit"
            condominium = self.by_order.get(share_order) if share_order else None
            self._entries(
                group.lr_entries,
                source="sheet_c",
                scope=scope,
                share_order_number=share_order,
                condominium_unit=condominium,
                group=group,
            )

    def share_entries(self) -> None:
        for share in self.unit.ownership_sheet_b.lr_unit_shares:
            self._share_entries(share, share.order_number, share.condominium_number)

    def _share_entries(
        self, share: LRShare, share_order: str, condominium: str | None
    ) -> None:
        self._entries(
            share.share_entries,
            source="share_entry",
            scope="share",
            share_order_number=share_order,
            condominium_unit=condominium,
            group=None,
        )
        for sub in share.sub_shares:
            self._share_entries(sub, share_order, condominium or sub.condominium_number)

    def sheet_entries(self) -> None:
        self._entries(
            self.unit.ownership_sheet_b.lr_entries,
            source="sheet_b_entry",
            scope="unit",
            share_order_number=None,
            condominium_unit=None,
            group=None,
        )
        self._entries(
            self.unit.possessory_sheet_a2.lr_entries,
            source="sheet_a2_entry",
            scope="unit",
            share_order_number=None,
            condominium_unit=None,
            group=None,
        )

    def _entries(
        self,
        entries: list[LREntry],
        *,
        source: BlockerSource,
        scope: Scope,
        share_order_number: str | None,
        condominium_unit: str | None,
        group: EncumbranceGroup | None,
    ) -> None:
        pairs = _pair_deletions(entries)
        deleted = {target: entries[index].order_number for index, target in pairs.items()}
        for index, entry in enumerate(entries):
            if index in pairs:
                # The deleting entry itself: recorded so the deletion is
                # visible (and itself cancelled when a later entry deletes it).
                deleting = self._blocker(
                    "other_annotation",
                    scope=scope,
                    share_order_number=share_order_number,
                    condominium_unit=condominium_unit,
                    source=source,
                    description=_shorten(entry.description_text),
                    basis=f"deletes entry {entries[pairs[index]].order_number}",
                    entry=_entry_facts(entry),
                )
                if index in deleted:
                    deleting.cancelled_by = deleted[index]
                    self.cancelled.append(deleting)
                else:
                    self.blockers.append(deleting)
                continue
            # The group's right type describes its joined text; it stands for
            # an entry only when the entry is the group's only one.
            right_type = (
                group.right_type if group is not None and len(group.lr_entries) == 1 else None
            )
            kind, basis = classify_entry_text(entry.description_text, right_type)
            if entry.deletes_prior_entry and index not in pairs:
                basis += "; the text deletes an earlier entry it does not name here"
            if source == "sheet_a2_entry" and kind == "preemption":
                basis += (
                    " (a cultural good: the state and the local government hold a "
                    "pre-emption right)"
                )
            # A personal servitude (habitation, usufruct, maintenance) ends
            # with the holder's death; one registered decades ago is probably
            # spent and only needs deleting, on the holder's death certificate.
            lapsed = False
            if kind == "personal_servitude" and entry.entry_date is not None:
                age = (self.today - entry.entry_date).days / 365.25
                if age >= DEFAULT_DECEASED_THRESHOLD_YEARS:
                    lapsed = True
                    basis += (
                        f"; a personal right that ends with the holder's death, registered "
                        f"{age:.0f} years ago: likely lapsed, deletion needs the holder's "
                        f"death certificate (inferred)"
                    )
            beneficiary = _beneficiary(entry, group)
            blocker = self._blocker(
                kind,
                scope=scope,
                share_order_number=share_order_number,
                condominium_unit=condominium_unit,
                source=source,
                description=_shorten(entry.description_text),
                basis=basis,
                entry=_entry_facts(entry),
                amount=entry.amount,
                amount_value=float(entry.amount_value) if entry.amount_value is not None else None,
                amount_currency=entry.amount_currency,
                beneficiary=beneficiary,
                likely_lapsed=lapsed,
            )
            if index in deleted:
                blocker.cancelled_by = deleted[index]
                self.cancelled.append(blocker)
            else:
                self.blockers.append(blocker)

    def owners(self) -> None:
        """Owners that are a public body, and owners likely deceased (an estate).

        A share registered to someone probably dead sits in an unprobated
        estate: nothing can be bought from it until the heirs are registered.
        That is a blocker of the share whether or not the cadastre lists the
        same person as possessor, so it is added here, per owner row.
        """
        seen: set[tuple[str, str | None, str]] = set()
        for row in self.unit.ownership_sheet_b.owner_rows():
            flags = owner_flags(
                row["name"],
                row.get("address"),
                row.get("entry"),
                tax_number=row.get("tax_number"),
                today=self.today,
            )
            party = flags.party_type_inferred
            share_order = row.get("share_order_number")
            share = row.get("share") or {}
            fraction = f"{share['num']}/{share['den']}" if share.get("den") else "an unknown share"
            common: dict[str, Any] = {
                "scope": "share",
                "share_order_number": share_order,
                "condominium_unit": row.get("condominium_number"),
                "source": "ownership",
                "beneficiary": row["name"],
            }
            if flags.public_body and (row["name"], share_order, "public") not in seen:
                seen.add((row["name"], share_order, "public"))
                self.blockers.append(
                    self._blocker(
                        "public_body_share",
                        description=(
                            f"{row['name']} holds {fraction}: a {party.party_type} as co-owner "
                            f"(a public body sells only by its own procedure)"
                        ),
                        basis=party.basis + " (inferred)",
                        **common,
                    )
                )
            deceased = flags.likely_deceased
            if (
                deceased is not None
                and deceased.likely_deceased
                and (row["name"], share_order, "estate") not in seen
            ):
                seen.add((row["name"], share_order, "estate"))
                self.blockers.append(
                    self._blocker(
                        "likely_estate",
                        description=(
                            f"{row['name']} holds {fraction} and is likely deceased: the share "
                            f"sits in an estate until the heirs are registered (ostavina)"
                        ),
                        basis=deceased.basis + " (inferred)",
                        **common,
                    )
                )


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _beneficiary(entry: LREntry, group: EncumbranceGroup | None) -> str | None:
    parties = entry.get_parties()
    if parties:
        return split_name_share(parties[0].name)[0]
    if group is not None and group.beneficiary is not None:
        return split_name_share(group.beneficiary.name)[0]
    return None


def _name_matches(name: str | None, wanted: str) -> bool:
    haystack = fold_text(name or "")
    return all(word in haystack for word in fold_text(wanted).split())


def _matching_shares(
    lr_unit: LandRegistryUnitDetailed, owner_name: str | None, condominium_unit: str | None
) -> tuple[set[str], set[str]]:
    """Share order numbers and condominium unit keys the filter keeps."""
    orders: set[str] = set()
    units: set[str] = set()
    if owner_name is not None:
        for row in lr_unit.ownership_sheet_b.owner_rows():
            if _name_matches(row.get("name"), owner_name) and row.get("share_order_number"):
                orders.add(row["share_order_number"])
    if condominium_unit is not None:
        wanted = unit_key(condominium_unit)
        units.add(wanted)
        for share in lr_unit.ownership_sheet_b.lr_unit_shares:
            if share.condominium_number and unit_key(share.condominium_number) == wanted:
                orders.add(share.order_number)
    for order in orders:
        for share in lr_unit.ownership_sheet_b.lr_unit_shares:
            if share.order_number == order and share.condominium_number:
                units.add(unit_key(share.condominium_number))
    return orders, units


def _in_scope(blocker: Blocker, orders: set[str], units: set[str]) -> bool:
    if blocker.scope == "unit":
        return True
    if blocker.share_order_number and blocker.share_order_number in orders:
        return True
    return bool(blocker.condominium_unit) and unit_key(blocker.condominium_unit) in units


def detect_blockers(
    lr_unit: LandRegistryUnitDetailed,
    *,
    owner_name: str | None = None,
    condominium_unit: str | None = None,
    plombe_detail: dict[str, FileStatus] | None = None,
    severities: dict[str, str] | None = None,
    today: date | None = None,
) -> SaleBlockers:
    """The blockers of a unit (pure; nothing is fetched).

    Reads the pending plombe, sheet C, the annotations on the shares, the
    sheet-level entries of sheets B and A2, and the owners that are public
    bodies. ``plombe_detail`` (file number -> ``FileStatus``, as
    ``CadastralAPIClient.get_plombe_details`` returns) turns a bare plomba
    into the request it is. ``owner_name`` or ``condominium_unit`` narrow the
    answer to one owner's shares or one flat: unit-wide blockers always
    count, share-scoped ones only on the matching shares. ``severities``
    overrides the default severity of any kind; ``today`` dates the age of
    a personal servitude (for tests).
    """
    resolved = resolve_severities(severities)
    builder = _Builder(lr_unit, resolved, plombe_detail, today or date.today())
    builder.plombe()
    builder.sheet_c()
    builder.share_entries()
    builder.sheet_entries()
    builder.owners()

    blockers = builder.blockers
    notes = builder.notes
    scope_filter: dict[str, str] | None = None
    if owner_name is not None or condominium_unit is not None:
        if owner_name is not None and not fold_text(owner_name):
            raise ValueError("owner_name must not be blank")
        if condominium_unit is not None and not unit_key(condominium_unit):
            raise ValueError("condominium_unit must not be blank")
        scope_filter = {}
        if owner_name is not None:
            scope_filter["owner_name"] = owner_name
        if condominium_unit is not None:
            scope_filter["condominium_unit"] = condominium_unit
        orders, units = _matching_shares(lr_unit, owner_name, condominium_unit)
        kept = [b for b in blockers if _in_scope(b, orders, units)]
        dropped = len(blockers) - len(kept)
        if not orders:
            notes.append("the filter matches no share of the unit; unit-wide blockers only")
        elif dropped:
            notes.append(
                f"{dropped} share-scoped blocker(s) on other shares left out; unit-wide "
                f"blockers are counted"
            )
        blockers = kept
    if builder.cancelled:
        notes.append(
            f"{len(builder.cancelled)} entr{'y' if len(builder.cancelled) == 1 else 'ies'} "
            f"deleted by a later entry: listed under blockers_cancelled, not counted"
        )
    if any(b.kind == "pending_entry" and b.request_kind is None for b in blockers):
        notes.append(
            "a pending request counts as blocking until it is resolved; the plomba detail says "
            "what it is"
        )
    estates = sum(1 for b in blockers if b.kind == "likely_estate")
    if estates:
        notes.append(
            f"{estates} share(s) registered to an owner likely deceased (inferred from the "
            f"entry, the record or the name): an estate to probate before that share can be "
            f"bought"
        )
    lapsed = sum(1 for b in blockers if b.likely_lapsed)
    if lapsed:
        notes.append(
            f"{lapsed} personal servitude(s) registered decades ago are likely lapsed "
            f"(the holder's death ends them) and only need deleting; still counted until "
            f"they are"
        )
    if any(b.kind == "other_annotation" for b in blockers):
        notes.append("other_annotation entries were not recognised; read their text")
    return SaleBlockers(
        lr_unit_number=lr_unit.lr_unit_number,
        main_book_id=lr_unit.main_book_id,
        verdict=verdict_for(blockers),
        counts=counts_for(blockers),
        blockers=blockers,
        blockers_cancelled=builder.cancelled,
        scope_filter=scope_filter,
        plombe_detail_included=plombe_detail is not None,
        notes=notes,
    )
