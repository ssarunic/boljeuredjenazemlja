# API Coverage Specification

Complete coverage of every field, shape and endpoint the public OSS API returns,
in the SDK models, the client, the CLI, the MCP server and the mock server.

## Scope note

This project is a demonstration. The evidence below was captured once, with
the repository owner's explicit approval, so that the mock server can replicate
the real response shapes. Nothing in this document authorises running the code
against production systems; the default configuration stays on the mock server.

## 1. Purpose

Today the SDK parses the responses it was written against and quietly discards
or hides the rest. Several models have no `extra="allow"`, so unknown keys are
dropped without trace; other keys survive only as untyped leftovers in
`model_extra`; two lists are typed `list[dict]` and never interpreted. This
specification defines:

1. The full field inventory of every endpoint, as observed on 2026-09-09.
2. The rule that every observed key must be a declared, typed field.
3. The model, client, CLI, MCP and mock-server changes that achieve that.
4. A test gate that fails whenever a captured response contains a key the
   models do not declare, so coverage cannot silently regress.

It supersedes the field lists in
[croatian-cadastral-api-specification.md](croatian-cadastral-api-specification.md)
wherever the two disagree; that document keeps the endpoint narrative and
examples.

## 2. Evidence base

| Endpoint | Objects captured | Source |
|---|---|---|
| `/search-cad-parcels/municipalities` | 1 | search "SAVAR" |
| `/search-cad-parcels/offices` | 21 | full list |
| `/search-cad-parcels/parcel-numbers` | 79 hits from 76 searches | 59 parcels of k.o. Savar plus spelling probes |
| `/search-cad-parcels/possession-sheet-numbers` | 1 | sheet 363, k.o. Savar |
| `/search-lr-parcels/main-books` | 1 | search "SAVAR" |
| `/search-lr-parcels/books-of-dc` | 1 | search "ZADAR" |
| `/cad/parcel-info` | 59 | 53 land parcels, 6 building parcels |
| `/lr/lr-unit` | 19 | 17 units of main book 21277 (SAVAR), 1 historical-overview call, 1 condominium unit 13998/30783 (SPLIT) |
| `/lr/file-status` | 1 | Z-12564/2026, institution 284 |

All 17 Savar units are of type `VLASNIČKI`; the Split unit is
`ETAŽNO VLASNIŠTVO S ODREĐENIM OMJERIMA`. Every captured object validates
against the current models without error; the problem is what validation
throws away. Counts in the tables below are "non-null occurrences / objects
that could carry the key".

Raw captures contain personal data and are not committed. Section 9 defines
how redacted fixtures are produced from them.

## 3. Coverage rules

R1. Every key observed in a captured response is a declared field on the
    model that receives it, with the observed JSON type and nullability.
    "Declared" means a `Field` with the server's camelCase alias; no key may
    rely on `model_extra` for storage.

R2. Every model that receives server JSON sets `extra="allow"` and exposes the
    undeclared remainder through a common `source_fields` property. This is the
    safety net for keys that appear after this capture, never a place to leave
    known keys.

R3. No `list[dict]` or `dict` typed fields. Every nested object has a model.
    Heterogeneous lists use a discriminated union with an explicit rule.

R4. Every declared field is reachable from the CLI (`json` output at the
    highest detail level) and from the MCP server (`detail="full"`). Fields
    that are always null in the capture are still declared, typed
    `... | None`, and documented as "reserved, observed null".

R5. Every endpoint the public API exposes and this document lists has a client
    method, a typed model, a mock-server route with data, a CLI command or
    option, and an MCP tool or tool parameter. The ATOM download is covered
    by the GIS module and is out of scope here.

R6. The coverage gate (section 10) runs in CI over the redacted fixtures and
    fails on any key path that R1 does not cover.

R7. Parsing failures are never swallowed. Where the code today does
    `try: ... except Exception: pass`, the replacement either validates
    against a union that accepts every observed shape or raises
    `CadastralAPIError(INVALID_RESPONSE)`.

## 4. Endpoint inventory

| # | Method and path | Client method today | Status |
|---|---|---|---|
| E1 | `GET /search-cad-parcels/offices` | `list_cadastral_offices` | covered |
| E2 | `GET /search-cad-parcels/municipalities` | `find_municipality` | covered |
| E3 | `GET /search-cad-parcels/parcel-numbers` | `find_parcel` | covered; building-parcel spelling not handled (section 6.1) |
| E4 | `GET /search-cad-parcels/possession-sheet-numbers` | none | missing |
| E5 | `GET /search-lr-parcels/main-books` | none | missing |
| E6 | `GET /search-lr-parcels/books-of-dc` | none | missing |
| E7 | `GET /cad/parcel-info` | `get_parcel_info` | 3 keys untyped |
| E8 | `GET /lr/lr-unit` | `get_lr_unit_detailed` | 1 object dropped, 2 lists untyped, 2 keys untyped |
| E9 | `POST /lr/file-status` | `get_file_status` | covered |

### 4.1 Common shape of the search endpoints (E2 to E6)

E2 to E6 all return a list of the same six-key record:

| Key | Type | Meaning per endpoint |
|---|---|---|
| `key1` | string | primary id: municipality id (E2), parcel id (E3), possession sheet id (E4), main book id (E5), book id (E6) |
| `value1` | string | display value: "334979 SAVAR" (E2), parcel number (E3), sheet number (E4), book name (E5, E6) |
| `key2` | string or null | municipality registration number (E2), land-registry office id (E5, E6); null on E3, E4 |
| `value2` | string or null | cadastral office id (E2), court name "ZADAR" (E5), office name "Zemljišnoknjižni odjel Zadar" (E6); null on E3, E4 |
| `value3` | string or null | department id (E2); null elsewhere |
| `displayValue1` | string or null | "334979 SAVAR, ZADAR, PUK ZADAR" (E2), "SAVAR, ZADAR" (E5), "ZADAR, Zemljišnoknjižni odjel Zadar" (E6); null on E3, E4 |

Requirement: one base model `KeyValueSearchResult` declaring all six keys as
`str | None`, and one subclass per endpoint that adds the named properties
(`parcel_id`, `main_book_id`, `institution_id`, ...). `ParcelSearchResult`
and `MunicipalitySearchResult` become such subclasses; their existing
attribute names stay.

### 4.2 E3 search semantics (observed)

- Prefix match on the parcel number: "1072/1" returns 1072/1, 1072/10,
  1072/11, 1072/12; "35" returns 14 hits including 350 and 359.
- Building parcels are stored with a leading asterisk: `*35/1`, `*56`.
  Searching "35/1" returns `*35/1`; searching "*35/1" returns `*35/1` and
  `135/1` (the asterisk acts as a wildcard); "35/1 ZGR" returns `*35/1`;
  "35/1.ZGR", "35/1ZGR" and "ZGR" return nothing.
- A number that exists only as sub-parcels returns the sub-parcels: "973"
  returns 973/1 and 973/2 and no exact match.

### 4.3 E4 possession sheet search

`GET /search-cad-parcels/possession-sheet-numbers?search=363&municipalityRegNum=334979`
returns `key1` = `possessionSheetId` (11731543, the same id the parcel-info
`possessionSheets[]` carry) and `value1` = sheet number. No endpoint that
returns a possession sheet by id is known; the client method
`find_possession_sheet(sheet_number, municipality_reg_num)` returns the
search records only. Open question OQ4 in section 11.

### 4.4 E5 and E6 main books and books of deposit companies

`GET /search-lr-parcels/main-books?search=SAVAR&officeId=&institutionName=`
returns `key1` 21277 (the `mainBookId` used by E8), `value1` "SAVAR", `key2`
284 (the `institutionId` E8 reports), `value2` "ZADAR". This is the missing
link that lets a caller reach a land-registry unit from a municipality name
and unit number without knowing the main book id.

Required client methods: `find_main_book(search, office_id=None,
institution_name=None)` and `find_book_of_dc(...)`, both returning lists of
the typed subclass. `get_lr_unit_detailed` gains an overload that accepts a
main book name and resolves it through E5, raising `LR_UNIT_NOT_FOUND` with
reason `main_book_ambiguous` when the search returns more than one book.

Whether a book-of-DC id can be passed as `mainBookId` to E8 is unverified
(OQ5).

## 5. Field inventory and required changes

Legend for the "Now" column: typed = declared field; extra = kept only in
`model_extra`; raw = inside a `list[dict]`; dropped = discarded by a model
without `extra="allow"`.

### 5.1 E7 parcel-info root

The response has three shapes:

| Shape | Keys present | Observed |
|---|---|---|
| direct | `lrUnit` object; no `parcelLinks`, no `lrUnitsFromParcelLinks` | 16 of 59 |
| linked | `parcelLinks` (1 element), `lrUnitsFromParcelLinks` (1 element); no `lrUnit` key | 37 of 59 |
| cadastre-only | `parcelLinks: []`; no `lrUnit`, no `lrUnitsFromParcelLinks` | 6 of 59, all building parcels |

| Key | Type | Presence | Now | Change |
|---|---|---|---|---|
| `parcelId` | int | 59/59 | typed | none |
| `parcelNumber` | string | 59/59 | typed | add `is_building_parcel` (leading `*`) and `parcel_number_display` (section 6.1) |
| `cadMunicipalityId` | int | 59/59 | typed | none |
| `cadMunicipalityRegNum` | string | 59/59 | typed | none |
| `cadMunicipalityName` | string | 59/59 | typed | none |
| `institutionId` | int | 59/59 | typed | none |
| `address` | string | 59/59 | typed | none |
| `area` | string of int | 59/59 | typed | none |
| `buildingRemark` | int, 0 or 1 | 59/59 | typed | document: 1 on every building parcel, 0 otherwise |
| `detailSheetNumber` | string | 59/59 | typed | none |
| `hasBuildingRight` | bool | 59/59 | typed | none |
| `parcelParts[]` | list | 59/59 | typed | see 5.2 |
| `possessionSheets[]` | list | 59/59 | typed | see 5.3 |
| `lrUnit` | object | 16/16 when key present | typed | none; document the 6-key shape (5.4) |
| `parcelLinks[]` | list | 37 non-empty, 6 empty, 16 absent | typed | none; document the three shapes |
| `lrUnitsFromParcelLinks[]` | list | 37/37 when present | typed | none |
| `isAdditionalDataSet` | bool | 59/59 | typed | none |
| `legalRegime` | bool | 59/59 | typed | none |
| `graphic` | bool, both values seen | 59/59 | typed | none |
| `alphaNumeric` | bool | 59/59 | typed | none |
| `status` | int, 0 | 59/59 | typed | none |
| `resourceCode` | int, 0 or 2 | 59/59 | typed | none |
| `isHarmonized` | bool | 59/59 | typed | none |

### 5.2 E7 `parcelParts[]`

| Key | Type | Presence | Now | Change |
|---|---|---|---|---|
| `parcelPartId` | int | 153/153 | typed | none |
| `name` | string | 153/153 | typed | none; on building parcels the value is "KUĆA, SELO" |
| `area` | string of int | 153/153 | typed | none |
| `possessionSheetId` | int | 153/153 | typed | none |
| `possessionSheetNumber` | string | 153/153 | typed | none |
| `lastChangeLogNumber` | string, e.g. "18/2025" | 111/153 | typed | none |
| `lastChangeLogFileNum` | string | 17/153 | extra | declare `last_change_log_file_num: str \| None`. Values are the administrative file of the last change ("UP/I 932-07/2026-02/1217") or the literal "Automatska OIB promjena" |
| `building` | bool | 153/153 | typed | none |
| `type` | string, "Zgrada" | 21/153, building parts only | extra | declare `part_type: str \| None` (alias `type`) |
| `buildingRight` | int, 0 | 21/153, building parts only | extra | declare `building_right: int \| None` |

### 5.3 E7 `possessionSheets[]` and `possessors[]`

| Key | Type | Presence | Now | Change |
|---|---|---|---|---|
| `possessionSheetId` | int | 139/139 | typed | none |
| `possessionSheetNumber` | string | 139/139 | typed | none |
| `cadMunicipalityId` | int | 139/139 | typed | none |
| `cadMunicipalityRegNum` | string | 123/139, absent on sheets of direct-shape parcels | typed | none |
| `cadMunicipalityName` | string | 123/139, same | typed | none |
| `possessionSheetTypeId` | int, 1 | 102/139 | typed | none |
| `possessors[].name` | string | 2630/2630 | typed | none |
| `possessors[].address` | string | 1797/2630 | typed | none |
| `possessors[].ownership` | string fraction | 1380/2630 | typed | none |
| `possessors[].condominiumShareNumber` | string | 0 observed | typed | keep; comes from the earlier condominium capture |
| `possessors[].condominiumShareOwnership` | string | 0 observed | typed | keep |

Naming: `Possessor`, `PossessionSheet` and `ParcelInfo` still describe
these people as owners in field descriptions and docstrings ("Owner's full
name", "Ownership record", "Ownership information"), and
`ParcelInfo.total_owners` counts possessors. Change: reword every description
to possessor / possession sheet, rename `total_owners` to `total_possessors`
(keep `total_owners` as a deprecated alias for one release) and extend
`cli/tests/test_terminology.py` so the English pattern also rejects "owner"
inside the cadastre models. The JSON alias `ownership` on the possessor's
fraction stays, because it is the server's key.

### 5.4 E7 land-registry references

Three shapes of the unit reference occur:

| Shape | Keys | Where |
|---|---|---|
| minimal | `lrUnitId`, `lrUnitNumber`, `mainBookId`, `status`, `verificated`, `condominiums` | `lrUnit` (direct shape) |
| link | minimal plus `cadastreMunicipalityId`, `mainBookName` | `parcelLinks[].lrUnit` |
| full | link plus `institutionId`, `institutionName`, `lrUnitTypeId`, `lrUnitTypeName`, `statusName` | `lrUnitsFromParcelLinks[]` |

`LandRegistryUnit` already declares all 13 keys as optional. Change: none to
the fields; document the shapes and add a `reference_shape` computed field
("minimal", "link", "full") so consumers know which attributes they can
expect.

`parcelLinks[]`: `parcelId` int, `parcelNumber` string, `address` string
(36/37; here the value is the old land-register culture text such as
"ORANICA", "VINOGRAD", "ŠUMA", not a location), `area` string, `lrUnit`
(link shape), `parcelParts` always `[]`. Change: rename the model attribute
`address` semantics in the docstring to "culture or toponym as recorded in
the land register"; keep the alias.

### 5.5 E8 land-registry unit root

The response is a list with exactly one element.

| Key | Type | Presence | Now | Change |
|---|---|---|---|---|
| `lrUnitId` | int | 19/19 | typed | none |
| `lrUnitNumber` | string | 19/19 | typed | none |
| `mainBookId` | int | 19/19 | typed | none |
| `mainBookName` | string | 19/19 | typed | none |
| `cadastreMunicipalityId` | int | 19/19 | typed | none |
| `institutionId` | int | 19/19 | typed | none |
| `institutionName` | string | 19/19 | typed | none |
| `status` | string, "0" | 19/19 | typed | none |
| `statusName` | string, "Aktivan" | 19/19 | typed | none |
| `verificated` | bool | 19/19 | typed | none |
| `condominiums` | bool, false even on the condominium | 19/19 | typed | none; keep `is_condominium()` on the type name |
| `lrUnitTypeId` | int, 1 or 3 | 19/19 | typed | add enum `LRUnitType` (1 = VLASNIČKI, 3 = ETAŽNO VLASNIŠTVO S ODREĐENIM OMJERIMA) with an `OTHER` fallback |
| `lrUnitTypeName` | string | 19/19 | typed | none |
| `lastDiaryNumber` | string | 19/19 | typed | none |
| `activePlumbs[]` | list | 14/19 non-empty | typed | see 5.6 |
| `ownershipSheetB` | object | 19/19 | typed | see 5.7 |
| `possessionSheetA1` | object | 19/19 | typed | see 5.9 |
| `possessionSheetA2` | object | 19/19 | typed | see 5.10 |
| `encumbranceSheetC` | object | 19/19 | typed | see 5.11 |

`LandRegistryUnitDetailed`, `OwnershipSheetB`, `LRShare`, `Party`,
`LRUnitParcel`, `SheetAParcelList` and `SheetAAdditionalInfo` have no
`extra="allow"`. Change: all of them get it (R2).

`historicalOverview=true` returned a byte-for-byte identical structure for
unit 531/21277. The parameter stays supported; the mock returns the same data
for both values until a unit with history is captured (OQ1).

### 5.6 E8 `activePlumbs[]`

| Key | Type | Presence | Now | Change |
|---|---|---|---|---|
| `fileNumber` | string, "Z-12564/2026" | 18/18 | typed | none |
| `cadPlumb` | bool, always false here | 18/18 | typed | none |
| `plumbMark` | string, "(E-80)" | 4/18, condominium only | extra | declare `plumb_mark: str \| None`; document as the condominium unit the plomba concerns |

### 5.7 E8 `ownershipSheetB`

`lrEntries[]` (3 units non-empty): sheet-level entries, all ZABILJEŽBA
(rejected proposals, opening of an individual correction procedure). Shape as
in 5.8 without `lrOwners` and `amount`. Now typed; no change.

`lrUnitShares[]`:

| Key | Type | Presence | Now | Change |
|---|---|---|---|---|
| `lrUnitShareId` | int | 1666/1666 | typed | none |
| `description` | string, "12. Suvlasnički dio: 1/48" or "16. Suvlasnički dio: 61/4651 ETAŽNO VLASNIŠTVO (E-16)" | 1666/1666 | typed | none |
| `orderNumber` | string | 1666/1666 | typed | none |
| `status` | int, 0 | 1666/1666 | typed | none |
| `lrOwners` | list, null, or absent | 1580 non-empty lists and 1 null (unit 870 share 192) on the Savar units; on the condominium the key is absent from the 14 shares owned through sub-shares | typed | accept null explicitly (`list[Party] \| None` normalised to `[]`) and add `has_direct_owners` |
| `lrOwners[]` | Party | | | see 5.8 |
| `subSharesAndEntries[]` | list, heterogeneous | 31 shares non-empty | raw, partly parsed | see below |
| `condominiumNumber` | string, "E-16" | condominium only | typed | none |
| `condominiums` | list of string | condominium only | typed | none |

`subSharesAndEntries[]` holds two different things:

| Element kind | Distinguishing keys | Observed | Now |
|---|---|---|---|
| sub-share | `lrUnitShareId`, `status`, `lrOwners`, `subSharesAndEntries`, `description` "22.3. Suvlasnički dio etaže: 1/2", `orderNumber` "3" | 30, condominium only | parsed by `_sub_shares()` |
| share entry | `lrEntryId`, `description` (an entry text), `orderNumber` "39.1" | 5 condominium, 14 Savar | fails `LRShare` validation and is skipped silently |

The share entries are ZABILJEŽBA on that share: lifetime-maintenance
contracts, disputes, rejected inheritance decisions, cross-references to
sheet C. Change: type the field as
`list[LRShare | LREntry]` with a `model_validator(mode="before")` that routes
by the presence of `lrUnitShareId`; expose `sub_shares` and `share_entries`
properties; remove the `try/except: pass` in `_sub_shares()` (R7);
`get_all_owners()` and `owner_rows()` keep recursing through `sub_shares`
only. Nesting deeper than one level was not observed; the union is recursive
anyway.

### 5.8 E8 `Party` (`lrOwners[]` on shares, sub-shares and sheet C entries)

| Key | Type | Presence | Now | Change |
|---|---|---|---|---|
| `lrOwnerId` | int | 1683/1683 | typed | none |
| `name` | string | 1683/1683 | typed | none |
| `address` | string | 1088/1683 | typed | none |
| `taxNumber` | string, 11 digits | 632/1683 | typed | none |
| `lrEntry` | object or null | 1390 objects, 207 null (older shares), absent on sheet C beneficiaries | dropped | declare `entry: LREntry \| None` (alias `lrEntry`) |

`lrEntry` carries `orderNumber` ("127.2", "22.3.1" on sub-share owners) and
`description`, the registration entry that put this owner on the share. The
description grammar, observed on 1390 entries:

```text
Zaprimljeno 14.05.2026.g. pod brojem Z-15677/2026<br><br>
[<b>Prvenstveni red upisa: Z-8920/2012</b><br><br>]
UKNJIŽBA, PRAVO VLASNIŠTVA[, <basis document ...>]
[<br><br>IZ ZK ULOŠKA PRENESENI VLASNICI]
```

`LREntry` already parses receipt date, diary number, action type and basis
document from this text. Change: extend `parse_lr_entry` to return
`priority_diary_number` (the "Prvenstveni red upisa" reference) and
`transferred_from_unit` (true when the text contains "IZ ZK ULOŠKA
PRENESENI"), and add both as optional fields on `LREntry`. Every Party model
gets `extra="allow"`.

### 5.9 E8 `possessionSheetA1`

The sheet uses one of two keys, never both:

| Key | When | Observed |
|---|---|---|
| `cadParcels[]` | every parcel of the sample whose parcel-info has the direct shape (5.1) | 9 Savar units |
| `lrParcels[]` | every parcel whose parcel-info has the linked shape | 8 Savar units and the Split unit |

`cadParcels[]` elements are full cadastre parcel records: every root key of
5.1 except `lrUnit`, `parcelLinks` and `lrUnitsFromParcelLinks`, plus
`parcelParts[]` (5.2 shape without the change-log keys) and
`possessionSheets[]` whose `possessors` is always empty. `statusInLrUnit` is
absent.

`lrParcels[]` elements:

| Key | Type | Presence | Now | Change |
|---|---|---|---|---|
| `parcelId` | int | 67/67 | typed | none |
| `parcelNumber` | string | 67/67 | typed | none |
| `address` | string | 66/67 | typed | document: old land-register culture or toponym ("PAŠNJAK", "ORANICA", "VRT", "ZGRADA"), not a location |
| `area` | string of int | 67/67 | typed | none |
| `statusInLrUnit` | int, 0 | 67/67 | typed | none |
| `parcelParts[]` | list | 3/67 non-empty | raw | see below |

The lean shape omits every cadastre flag that `LRUnitParcel` declares with
a default: `graphic` and `alphaNumeric` (default True), `legalRegime`,
`hasBuildingRight`, `isAdditionalDataSet` and `isHarmonized` (default
False), `status`, `resourceCode` and `buildingRemark` (default 0), and
`cadMunicipalityId`. An absent value therefore serialises as a fact ("not
harmonised", "no legal regime", "graphics available"). Change: make each of
these `| None` with default `None` so that "not supplied" is distinguishable
from `False`/`0`; the CLI prints such fields as blank, not as "ne"/"0". Only
the cadastre-shaped `ParcelInfo` keeps them required, because E7 always
supplies them. `area_numeric` returns `None` instead of `0` when the string
does not parse.

`lrParcels[].parcelParts[]`: `name`, `area`, `building` always; `parcelPartId`,
`type` ("Zgrada"), `buildingRight` (0) on building parts. Change: replace
`LRUnitParcel.parcel_parts: list[dict]` with `list[ParcelPart]` after making
`ParcelPart.parcel_part_id`, `possession_sheet_id` and
`possession_sheet_number` optional (they are absent in this shape and present
in the cadastre shape). Replace `LRUnitParcel.possession_sheets: list[dict]`
with `list[PossessionSheet]`.

`SheetAParcelList` gets `source_key: Literal["lrParcels", "cadParcels"]`, set
by a before-validator from whichever key was present, so the CLI and MCP can
say which register the parcel list came from. Serialisation keeps the
`lrParcels` alias.

### 5.10 E8 `possessionSheetA2`

`lrEntries[]` (3 units non-empty): entries whose description starts with
`<span class='lr-entry-black' >`. Content observed: building registration
note under the Building Act, cultural-heritage note, use permit note. Shape as
5.8's `LREntry` without `lrOwners`. Now typed; change: none beyond the HTML
handling in section 7.

### 5.11 E8 `encumbranceSheetC`

`lrEntryGroups[]`:

| Key | Type | Presence | Now | Change |
|---|---|---|---|---|
| `description` | string, "9. Na suvlasnički dio: 88 (59/4651)" | 31/31 | typed | none |
| `shareOrderNumber` | string | 31/31 here; absent when the burden is on the whole unit (earlier capture) | typed | none |
| `lrEntries[]` | list | 31/31 | typed | see below |

`lrEntryGroups[].lrEntries[]`:

| Key | Type | Presence | Now | Change |
|---|---|---|---|---|
| `lrEntryId` | int | 31/31 | typed | none |
| `orderNumber` | string | 31/31 | typed | none |
| `description` | string, HTML | 31/31 | typed | none |
| `lrOwners[]` | Party without `lrEntry` | 30/31 | typed | none |
| `amount` | string, "134.000,00 EUR", "43.000,00 KN", "10.092.021,00 HRD" | 24/31, mortgages and liens | extra | declare `amount: str \| None` plus computed `amount_value: Decimal \| None` and `amount_currency: str \| None` parsed from the Croatian number format |

`EncumbranceSheetC.has_encumbrances()` is documented as "any active
encumbrances" but only tests whether `lrEntryGroups` is non-empty; nothing
in the observed shape says whether a group is still in force (OQ1). Change:
rename it to `has_entries()` and keep `has_encumbrances()` as a deprecated
alias with a docstring that states the limitation, until a historical
capture shows how deleted entries are marked.

### 5.12 E9 file-status

All 14 keys are declared. `resolutionTypeName`, `solvingDate` and
`executionDate` are absent while the file is pending. Change: none.

### 5.13 E1 offices

`id` string, `name` string, 21 records. Change: none.

## 6. Behavioural requirements

### 6.1 Building parcels

The API spells building parcels with a leading asterisk (`*35/1`). Users
write them as "35/1.ZGR", "35/1 ZGR", "35/1 zgr", "zgr. 35/1" or "*35/1".

- `normalize_parcel_number(text) -> str` in `cadastral_api.utils` maps every
  form above to `*35/1` and leaves other numbers untouched. It is applied by
  `find_parcel`, `get_parcel_by_number`, `get_lr_unit_from_parcel`, the CLI
  parcel arguments, the batch input parsers and the MCP `parcel_number`
  parameters.
- Exact-match selection after an E3 search compares against the normalised
  form, so "35/1" resolves to `*35/1` only when the caller asked for the
  building parcel; plain "35/1" with no such parcel of its own reports
  `PARCEL_NOT_FOUND` with reason `only_building_parcel_exists` and the
  candidate list.
- `ParcelInfo.is_building_parcel` is true when `parcelNumber` starts with `*`
  or `buildingRemark == 1`. `parcel_number_display` renders the Croatian form
  using the vocabulary in [terminology.md](terminology.md); the JSON output
  keeps the API spelling in `parcel_number` and adds `is_building_parcel`.
- Building parcels have no land-registry reference of any shape.
  `get_lr_unit_from_parcel` reports `LR_UNIT_NOT_FOUND` with reason
  `parcel_not_in_land_registry` as today; the CLI explains that the building
  is registered on its land parcel.

### 6.2 Unknown-field detection at runtime

`CadastralAPIClient(unknown_fields="warn" | "ignore" | "error")`, default
`warn`. After validation the client walks `source_fields` of the returned
model tree; each unknown key path is logged once per process. `error` raises
`CadastralAPIError(INVALID_RESPONSE, reason="unknown_fields")`. The CLI
`info` command prints the setting; the MCP server runs with `ignore`.

### 6.3 Parcel-info reference resolution

`resolved_lr_unit()` keeps its order (direct, then `lrUnitsFromParcelLinks`,
then `parcelLinks[].lrUnit`). New: `ParcelInfo.lr_reference_shape` returns
"direct", "linked" or "none", and `LandRegistryUnitDetailed` records it in
`lr_unit_derived_from_links` as today plus the new `source_key` of sheet A1.

## 7. Entry text handling

Entry descriptions are HTML fragments. Observed markup, across 4588 line
breaks in the capture: `<br>`, `<b>...</b>` (priority order line),
`<span class='lr-entry-black' >` (opening tag only, never closed, on every
sheet A2 and sheet C entry). Requirements:

- `strip_html` removes tags and decodes entities; it must tolerate the
  unclosed span.
- `LREntry.style_class` (`str | None`) records the span's class value
  ("lr-entry-black") so a future "lr-entry-red" or similar (expected for
  deleted entries in a historical overview, OQ1) is not lost.
- `parse_lr_entry` currently maps "uknjižuje se" to the generic action
  `upis`, so an unconditional registration (uknjižba) is indistinguishable
  from other entries. The statutory kinds are uknjižba, predbilježba and
  zabilježba; deletion (brisanje) is an effect on an earlier entry, not a
  fourth kind. Change: `action_type` values become `uknjižba`,
  `predbilježba`, `zabilježba` and `upis` (fallback when the verb is
  "upisuje se"); add `deletes_prior_entry: bool` set when the text says
  "briše se" / "brisanje", and keep `brisanje` as the `action_type` only
  when no other kind is named. Fixture texts for each combination go in the
  coverage gate.
- `LREntry.description_text` is the stripped text; `description` stays raw.

## 8. Propagation to CLI, MCP and documentation

- Output keys: every new field gets an entry in
  `cli/src/cadastral_cli/output_keys.py` and a Croatian spelling in
  `po/hr.po`: `entry`, `priority_diary_number`, `transferred_from_unit`,
  `share_entries`, `sub_shares`, `plumb_mark`, `amount`, `amount_value`,
  `amount_currency`, `last_change_log_file_num`, `part_type`,
  `building_right`, `is_building_parcel`, `parcel_number_display`,
  `reference_shape`, `lr_reference_shape`, `source_key`, `style_class`,
  `description_text`, `source_fields`, `possession_sheet_id`, `main_book`,
  `court_name`, `office_name`, `unknown_fields`.
- `get-lr-unit --show-owners` prints, per owner, the entry order number,
  receipt date and diary number; `--all` prints the share entries under the
  share and the amount on sheet C rows. `get-parcel` prints the building
  marker and the last-change file number with `--detail full`.
- New CLI commands: `list-main-books`, `list-books-of-dc`,
  `search-possession-sheet`; `get-lr-unit` accepts `--main-book-name`.
  Croatian names for each go in `localized.py`; user docs follow
  [documentation-guide.md](documentation-guide.md).
- MCP: `get_lr_unit` and `get_lr_unit_from_parcel` at `detail="ownership"`
  add `entry` (order number, date, diary number, action type) to each owner
  row and a `share_entries` list; `detail="full"` is the raw dump and covers
  the rest by construction. New tools `find_main_book`, `find_book_of_dc`,
  `find_possession_sheet`. `get_lr_unit` accepts `main_book_name`.
- `docs/sdk-guide.md` gains a section on entry provenance, share entries,
  sheet A1 variants and building parcels.
- `CHANGELOG.md` records each user-visible addition under `[Unreleased]`.

## 9. Mock server and fixtures

The mock must serve every shape in section 5. Data is derived from the
capture through a redaction script `scripts/redact_capture.py` that:

- replaces every `name`, `address` and `taxNumber` under `possessors`,
  `lrOwners` and sub-shares with deterministic placeholders ("Posjednik 12"
  under `possessors`, "Vlasnik 12" under `lrOwners`, "Adresa 12", a synthetic
  11-digit OIB with a valid check digit);
- rewrites personal names inside entry descriptions and `condominiums`
  texts with the same placeholders, keeping dates, diary numbers, amounts,
  legal references and structure intact;
- keeps every key, type, null and empty list exactly as received;
- leaves ids, parcel numbers, areas, cultures and toponyms unchanged.

Required mock data sets:

| Set | Content |
|---|---|
| parcels | the 59 parcel-info records of k.o. Savar in all three shapes, including the 6 building parcels |
| search | E3 results consistent with the parcels, including the asterisk spelling and wildcard behaviour of 4.2 |
| possession sheets | E4 results for every sheet number that appears in the parcels |
| main books, books of DC | E5 and E6 records for SAVAR, LUKA and the Split book 30783 |
| lr-units | all 17 Savar units (both A1 variants, share entries, a null `lrOwners`, sheet B entries, sheet A2 entries, plombe) and the Split condominium (sub-shares, `plumbMark`, sheet C amounts) |
| file-status | the pending Z-12564/2026 record and the two resolved records already present |

Test fixtures under `api/src/cadastral_api/tests/fixtures/` are produced by
the same script: one file per endpoint shape listed above, named
`<endpoint>_<case>.json`.

## 10. Coverage gate

`api/src/cadastral_api/tests/test_api_coverage.py`:

1. Walks every Pydantic model reachable from the root models (`ParcelInfo`,
   `LandRegistryUnitDetailed`, `FileStatus`, the search results,
   `CadastralOffice`) and collects the declared alias paths, expanding lists
   as `[]` and unions as the union of their members.
2. Walks every fixture in `fixtures/` and collects the observed key paths.
3. Fails, listing the paths, when an observed path is not declared (R1), when
   a declared field is `dict`, `list[dict]` or `Any` (R3), or when a model
   that received data lacks `extra="allow"` (R2).
4. Validates every fixture and asserts `source_fields` is empty on every
   model in the tree.

The gate is added to the release checklist in
[release-process.md](release-process.md). A capture script
(`scripts/capture_api_sample.py`, not run in CI) re-fetches the section 2
sample so the fixtures can be refreshed; it refuses to run unless
`CADASTRAL_API_BASE_URL` is set explicitly on its command line.

## 11. Open questions

Unverified in this capture; each needs one targeted capture before its
handling is finalised. Until then the behaviour stated is the requirement.

| Id | Question | Interim requirement |
|---|---|---|
| OQ1 | What `historicalOverview=true` adds on a unit with deleted entries or shares with `status != 0` | keep the parameter; models accept any `status` int; `ShareStatus` maps 0 to active and everything else to historical |
| OQ2 | Shape of a cadastre plomba (`cadPlumb: true`) | `Plumb` unchanged; `get_plombe_details` keeps skipping them |
| OQ3 | Shape of `possessors[]` on condominium parcels (`condominiumShareNumber`, `condominiumShareOwnership`) | fields stay declared as optional |
| OQ4 | Endpoint that returns a possession sheet by `possessionSheetId` | E4 exposed as search only |
| OQ5 | Whether E8 accepts a book-of-DC id as `mainBookId` | `find_book_of_dc` returns records only |
| OQ6 | Units of type `ETAŽNI` (simple condominium) and any `lrUnitTypeId` other than 1 and 3 | `LRUnitType.OTHER` |
| OQ7 | Non-empty `possessionSheets[].possessors` inside `cadParcels[]` | typed as `list[Possessor]`, observed empty |
| OQ8 | Non-null `key2`, `value2`, `value3`, `displayValue1` on E3 or E4 | declared as `str \| None`, documented as reserved |

## 12. Implementation order

1. Models: `extra="allow"` everywhere, `source_fields`, `KeyValueSearchResult`
   hierarchy, `Party.entry`, share union, `Plumb.plumb_mark`,
   `LREntry.amount` and parsers, `ParcelPart` additions, typed
   `LRUnitParcel` lists, `SheetAParcelList.source_key`, building-parcel
   helpers, `LRUnitType`.
2. Redaction script, fixtures for every shape, coverage gate; the gate must
   pass on the new models.
3. Client: E4, E5, E6 methods, main-book-name overload, parcel-number
   normalisation, `unknown_fields` setting.
4. Mock server: new routes and the regenerated data sets.
5. CLI and MCP propagation, output keys, translations, user docs, changelog.
6. Update [croatian-cadastral-api-specification.md](croatian-cadastral-api-specification.md)
   field lists to point here and remove statements this capture disproved
   (notably "`cadParcels` is a legacy mock key" and "`lrEntry` is optional
   and rare").

Acceptance: the coverage gate passes on all fixtures; `cadastral get-lr-unit
--unit-number 13998 --main-book 30783 --all --format json` against the mock
emits every key of the Split fixture with no `source_fields`; `cadastral
search "35/1.ZGR" -m SAVAR` against the mock finds `*35/1`.
