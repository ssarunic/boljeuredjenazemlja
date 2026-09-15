# Sale blockers and owner flags

Status: implemented (2026-09-15)
Code: `api/src/cadastral_api/analysis/sale_blockers.py`,
`api/src/cadastral_api/analysis/owner_flags.py`; surfaces in
`mcp/src/cadastral_mcp/tools.py` (`get_lr_unit`, `compare_registers`,
`build_assembly`) and `cli/src/cadastral_cli/commands/registry.py`
(`get-lr-unit --blockers`).
Related: [terminology.md](terminology.md) section 2,
[mcp-server.md](mcp-server.md), [api-coverage-specification.md](api-coverage-specification.md) (OQ1).

## 1. Purpose

A land-registry unit holds everything that can stop or condition a sale, but
it holds it as Croatian prose spread over sheet C, the annotations on the
shares, the sheet-level entries and the pending plombe. The requirement (the
console layer's story "is anything blocking a sale of this parcel right now")
asks for a plain list of those things, each linked to its entry, and for
three indicative flags on every owner (likely deceased, address abroad,
public body) so that an investor can count the estates and the foreign
counterparties in a set of parcels before reading names.

The rule is deliberately a screening, not a legal judgement: it classifies
text by a table, shows the table's basis for every item, keeps what it could
not classify, and returns the rule it applied next to the verdict. The
reader, or the agent, applies judgement on top.

## 2. Blockers

`detect_blockers(unit, owner_name=None, condominium_unit=None,
plombe_detail=None, severities=None)` reads one `LandRegistryUnitDetailed`
and returns `SaleBlockers`:

| Field | Meaning |
|---|---|
| `verdict` | `clear`, `conditional` or `blocked` |
| `rule` | The sentence the verdict follows (see section 4) |
| `counts` | Counted blockers per severity |
| `blockers` | The counted blockers, in source order |
| `blockers_cancelled` | Entries a later entry deleted; listed, not counted |
| `scope_filter` | `{owner_name}` or `{condominium_unit}` when narrowed |
| `plombe_detail_included` | Whether the pending requests were resolved |
| `notes` | What was left out, what was not recognised |

Each `Blocker` carries `kind`, `severity`, `scope` (`unit` or `share`),
`share_order_number` (the top-level share, as sheet C refers to it with "Na
suvlasnički dio: 88"), `condominium_unit` ("E-80"), `source` (plomba,
sheet_c, share_entry, sheet_b_entry, sheet_a2_entry, ownership,
register_comparison), `description` (the entry text, shortened), `basis`
(the pattern or rule matched), `entry` (order number, date, diary number,
action type), `amount` with `amount_value` and `amount_currency`,
`beneficiary`, and for a plomba `file_number` and, with the detail,
`request_kind`, `status_description` and `dates`.

### 2.1 Sources

| Source | What is read | Scope |
|---|---|---|
| `active_plumbs` | Every pending plomba; `plumb_mark` "(E-80)" names the flat | share when marked, else unit |
| `encumbrance_sheet_c.lr_entry_groups` | Every entry of every group | share when the group has `share_order_number`, else unit |
| `ownership_sheet_b.lr_unit_shares[].share_entries` | The annotations on each share and its sub-shares | share |
| `ownership_sheet_b.lr_entries` | Sheet-level entries of sheet B (a rejected request, for instance) | unit |
| `possessory_sheet_a2.lr_entries` | Notes about the parcels (a cultural good) | unit |
| `owner_rows()` | Owners whose name reads as the state or a local self-government | share |

### 2.2 Classification

A first pass takes the group's `right_type` (`parse_right_type` in
`utils.py`) when the group holds exactly one entry: mortgage, prohibition,
preemption and usufruct map straight to a kind. Everything else goes through
the finer table, applied to the folded text (no diacritics, lower case),
most specific first:

| Kind | Pattern (folded) | Default severity |
|---|---|---|
| `social_claim` | `trazbin* socijaln` | blocking |
| `fiduciary_transfer` | `prijenos* ... radi osiguranja`, `fiducijar` | blocking |
| `transfer_prohibition` | `zabran* (otudenja / opterecenja / raspolaganja)` | blocking |
| `mortgage` | `zalozn* prav`, `hipotek` | blocking |
| `enforcement` | `ovr-`, `ovrsivost`, `ovrha`, `ovrsn*`, `ovrsi` | blocking |
| `dispute` | `spor`, `spora`, `sporu`, `tuzb*`, `parnic*` | blocking |
| `rejected_request` | `odbij* [se] prijedlog`, `odbijen* provedb` | informational |
| `preemption` | `prvokup`, `kulturno dobro` | conditional |
| `personal_servitude` | `pravo stanovanja`, `plodouzivanj`, `dozivotn* uzdrzavanj`, `dosmrtn* uzdrzavanj`, `osobn* sluznost` | conditional |
| `easement` | `sluznost`, `pravo uporabe`, `pravo puta`, `pravo prolaz` | conditional |
| `lien` | `trazbin` | blocking |
| `other_annotation` | anything else | informational |
| `pending_entry` | a plomba | blocking |
| `public_body_share` | an owner inferred state or municipality | conditional |
| `likely_estate` | a share whose owner is flagged `likely_deceased` (section 3): an unprobated estate, whether or not the cadastre lists the same person | conditional |
| `owner_not_possessor` | a registered owner on no possession sheet (comparison only) | informational when the owner's entry is recent and carries an OIB (the cadastre lags), conditional otherwise (an old or legacy record: the possessor may be a genuine third party) |
| `fuzzy_owner_match` | an owner matched to a possessor on the loose key only (comparison only) | informational |
| `area_mismatch` | the cadastre, land-register and map areas differ by more than the 5 % tolerance and more than 20 m² (comparison only) | conditional |

A judicial mortgage names its enforcement file (OVR-...) and is still a
mortgage, which is why `mortgage` precedes `enforcement`; a bare
"OVRŠIVOST TRAŽBINE" note or an enforcement order is `enforcement`.
`severities` overrides any default.

A `personal_servitude` registered 40 years ago or more
(`DEFAULT_DECEASED_THRESHOLD_YEARS`) is marked `likely_lapsed`: the right
ends with the holder's death, so an entry from 1949 or 1979 is almost
certainly spent and only needs deleting, on the holder's death certificate.
It stays conditional and counted until it is deleted; the basis says why. A
`pending_entry` whose resolved file carries a UP/I 932 reference is a
cadastre administrative case (survey and cadastre), most often a survey being
implemented, and its basis says so: a parcel's number or area may change.

### 2.3 Deletions

An entry whose text deletes an earlier one (`deletes_prior_entry`) names the
entry it deletes ("pod st. 2.1", "pod brojem 3.1"). When that order number is
a sibling in the same group or share, the sibling is moved to
`blockers_cancelled` with `cancelled_by`, and the deleting entry stays in the
list as informational with the basis "deletes entry 2.1". A deletion that
names no sibling is left as it is, its basis saying so: nothing is cancelled
on a guess. Whether the register still returns discharged charges at all is
the open question OQ1 of the coverage specification.

### 2.4 Scope

Every blocker carries where it attaches. The whole unit's verdict counts them
all. With `owner_name` (every word of it in the owner's folded name) or
`condominium_unit` ("E-16", "E16" and "16" agree), the shares that match are
found, unit-wide blockers are kept, share-scoped blockers are kept only on
those shares, and a note says how many were left out. A filter that matches
no share keeps the unit-wide blockers alone and says so.

## 3. Owner flags

`owner_flags(name, address, entry)` and `owner_flags_for_unit(unit)`
decorate `owner_rows()` with:

| Flag | Rule | Basis reported |
|---|---|---|
| `likely_deceased` | The registration entry is 40 years old or more (`DEFAULT_DECEASED_THRESHOLD_YEARS`), or the owner was carried over from an earlier unit (`transferred_from_unit`: the entry date is the transfer's), or the record carries neither a tax number nor a registration entry (`legacy_record`: carried from the paper register as it stood, usually an estate), or the owner's own name carries a death marker: a nominative form anywhere ("POKOJNI HORVAT MARKO"), an abbreviated or genitive form only at the start or the end ("HORVAT IVAN POK." yes, "HORVAT IVAN POK. MARKA" no, that is Ivan's late father) | the date and the age, the transfer, or the marker |
| `address_abroad` | The address names a country other than Croatia (a folded keyword table, endonyms and exonyms), or carries a letter-prefixed postcode ("A-1010", not "HR-10000") as a weak `postcode_pattern` signal; `None` without an address | the country or the postcode |
| `public_body` | `infer_party_type` says state or municipality | the party-type basis |

A company or a public body gets no `likely_deceased` flag. Every inference
carries `inferred: true` and its `basis`, in the shape `PartyTypeInference`
set. `surname_of` skips the markers, so a person written "POKOJNI HORVAT
MARKO" groups under Horvat in the assembly ranking.

## 4. Verdict

`blocked` when any counted blocker is blocking; `conditional` when any is
conditional; `clear` otherwise. Cancelled entries are not counted. The rule
is returned as text next to every verdict, and the MCP instructions and the
CLI footer both say that it is a screening of the register's text, not a
legal opinion.

## 5. Where it shows

- `compare_registers` computes `detect_blockers(unit)` once, adds the two
  comparison-only kinds, and stores `RegisterComparison.sale_blockers` and
  `owner_flag_counts`; every owner `PersonRecord` carries `flags` and
  `share_order_number`.
- `acquisition_score` reads `no_pending_plombe` and `no_encumbrances` from
  the blockers: a charge is a blocker of an encumbrance kind at blocking or
  conditional severity, so an informational note or a cancelled entry no
  longer counts against a parcel. `ParcelSummary` gets `sale_verdict`,
  `blocker_counts`, `blocker_kinds`; `PersonHolding` gets `likely_deceased`
  and `address_abroad`; `SurnameGroup` and `AssemblyTotals` count them.
- MCP `get_lr_unit`: `sale_blockers` at every level, the list itself in
  "ownership" and "encumbrances" (a large condominium's list runs to tens of
  kilobytes, too much for every page of the raw sheets), the verdict, the
  counts and the rule elsewhere; `owner_flags_summary` on the owner levels;
  `flags` on every "ownership" row; `condominium_unit` narrows the blockers;
  `include_plombe_detail` is fetched once and feeds both `plombe_detail` and
  the pending blockers.
- CLI `get-lr-unit --blockers` (`uz uložak --zapreke`): the verdict line,
  the SALE BLOCKERS table, the cancelled count, the rule, the OWNER FLAGS
  table for the flagged owners; `sale_blockers` and `owner_flags` in JSON;
  `sale_verdict` and `blockers` columns in the list CSV.

## 5.1 Person matching behind `owner_not_possessor`

The comparison-only blockers rest on the person identity in `persons.py`.
The cadastre writes the father's name after a comma ("ŠARUNIĆ AUGUSTIN,
BOŽO", "ŠARUNIĆ ANTE, P. BOŽE") where the register writes a marker
("ŠARUNIĆ AUGUSTIN POK. BOŽE"), and sometimes the given name first
("AUGUSTIN ŠARUNIĆ"). The loose key drops everything after the first comma
as well as a marked relative, and two loose keys of the same words in
another order match. Both are fuzzy matches, flagged as such, with one
exception: a name in another order with no relative on either side is lifted
to an exact match when the shares agree or the addresses agree, since a
namesake (a grandson written like the grandfather) would otherwise pass on
the name alone. The strict key keeps the comma part, so distinct-person
counts never merge on a guess. Matching is per person: an owner on several
shares is several records, and once one of them matches a possessor the
others with the same OIB match the same possessor, so a person is never
both matched and owner only (the assembly counts the possessor's share
once); the same name without an OIB stays owner only. With `plombe_detail`
the comparison names the pending requests.

## 6. Limits

- The table reads register prose; an entry it does not know stays
  `other_annotation` and must be read. Add a pattern when a reviewer finds a
  kind that recurs.
- The checked-in fixtures are redacted ("Vlasnik N", "Adresa N"), so the name
  and address rules are tested on a synthetic unit
  (`lr_unit_sale_blockers.json`); their recall on real data is unmeasured.
- The deceased flag is a proxy: an old entry may belong to a living owner and
  a recent one to an estate. It is for counting, not for stating.
- Historical shares and discharged charges depend on what the server returns
  (OQ1); the rule never guesses at a cancellation it cannot pin to a sibling.
