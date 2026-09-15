# MCP Usage Guide

How an AI agent (Claude Desktop, Claude Code, any MCP client) should use the
Cadastral MCP server. The server exposes thirteen tools, three resources and
four prompts over the Model Context Protocol; it is a demonstration that runs against
the included mock server by default (see [legal.md](legal.md) before pointing it
anywhere else).

## The one rule: pick the register

The cadastre (katastar) and the land registry (zemljišne knjige, ZK,
gruntovnica) are different registers and often name different people.

| The user asks about | Register | Tool |
|---|---|---|
| vlasnik, tko je vlasnik, suvlasnički udjeli, prema zemljišnim knjigama, tereti, hipoteka, plomba | land registry (vlastovnica, list B; teretovnica, list C) | `get_lr_unit` |
| posjednik, posjedovni list, površina, način uporabe, kultura | cadastre (posjedovni list) | `get_parcel` |

Every person record carries a `register` field (`cadastre` or `land_registry`).
Possessors are never proof of ownership; say so when you report them.

Numeric ids (`parcel_id`, `possession_sheet_id`, `main_book_id`,
`institution_id`, `office_id`, `book_id`) are integers in every tool result and
are accepted as integers or numeric strings in references. Codes that are
labels rather than ids (the municipality registration number `334979`, parcel
and unit numbers) are strings.

## Tools

### `find_parcel(parcel_number, municipality, max_matches=0)`

Finds one parcel and returns its `parcel_id`, `parcel_number`,
`municipality_code`, `is_building_parcel` and, when the municipality's GIS data
is available, `map_url` (the interactive map centred on the parcel). Use it to
confirm a parcel exists or to get its id; `get_parcel` gives the record.

`max_matches` above 0 adds the complete search response: `matches` lists every
record the server matched (`parcel_id`, `parcel_number`, `is_building_parcel`),
up to that many, with `matches_total` and `matches_truncated`. Use it to answer
"which parcels start with 103" rather than to pick one.

The search matches on a substring, so a number that does not exist can come
back as a longer one ("973" as 973/1). Check `exact_match`. When it is `false`,
`match_note` and `other_matches` say what was found instead; report that as "no
such parcel, here is what exists", not as a hit. A building parcel is never
answered with a land parcel or the other way round. Building parcels may be
written "35/1 ZGR", "35/1.ZGR", "zgr. 35/1" or "*35/1"; all resolve exactly.

### `get_parcel(parcels, source="cadastre", offset=0, limit=None, possessor_name=None, condominium_unit=None)`

The detailed cadastre record of one or more parcels: area, land use, possession
sheet, land registry reference, `cadastre_lr_harmonized`, `map_url`. `parcels`
is a list of references; pass one for a single parcel, several for a list.

```json
{"parcels": [{"parcel_number": "103/2", "municipality": "SAVAR"},
             {"parcel_number": "45", "municipality": "SAVAR"},
             {"parcel_id": "6565198"}],
 "source": "cadastre"}
```

`source` chooses the register:

- `"cadastre"` (default): include the possession sheet (possessors).
- `"land_registry"`: omit possessors; each entry carries `land_registry_hint`
  with the unit reference to pass to `get_lr_unit`.
- `"none"`: parcel metadata only.

The result is `{results, total, successful, failed, source}` with one entry per
reference, in order. An entry has `status` (`success` or `error`), `ref` (the
reference as given), `register`, `data` (the parcel record; `data.lr_unit` is
the land registry reference, filled from the parcel links when the cadastre
carries no direct one, with `data.lr_reference_shape` saying `direct`, `linked`
or `none`) and `map_url` when available. A failed parcel does
not stop the others. An entry resolved from a fallback match carries
`exact_match: false` and `match_note`, as `find_parcel` does.

Every successful entry carries `provenance`: `register` (`cadastre`),
`source_url` (the request that answered) and `retrieved_at` (UTC). Pass it on
with any fact you forward, so that nothing is mistaken for an official
extract; it is `null` only for a record that was not fetched from a server.
The entry also carries `area_check`, which compares the cadastre area with
the graphical area of the cadastral map (`gis_m2`, when the municipality's GIS
data is available) and with the land register's area when the cadastre record
carries it on the parcel link (`land_registry_m2`; otherwise `note` says that
`get_lr_unit` with `detail="parcels"` reads it from sheet A). `compared` lists
the areas that were available, `max_difference_fraction` the spread relative
to the largest, and `mismatch` is true above 5 % (`tolerance_fraction`). A
failed entry carries `error_type` and, when the server said more,
`error_details`: `parcel_not_found`, `municipality_not_found`,
`lr_unit_not_found`, `access_denied` (HTTP 401/403), `rate_limit`, `timeout`,
`http_error`, `response_too_large`, `invalid_request` (a bad reference or
option) or `internal_error`. Read it before concluding anything from an empty
answer: "not found", "refused" and "throttled" are different facts.

With `source="cadastre"`, `offset` and `limit` page through the possessor
records of each parcel, counted across its possession sheets in sheet order
(a parcel under a condominium keeps hundreds of possessors on one sheet, so
the page item is the possessor, not the sheet). Every sheet stays in `data`
with its header and its own `total_possessors`, holding only the possessors
that fall inside the window. The entry carries `total_possessors` (records),
`distinct_possessors` (different names among them: a person holding a flat and
a storage room is two records, often with two addresses, and the records are
kept as the cadastre holds them), `possessors_truncated` and a `page` block
(`offset`, `limit`, `total`,
`returned`, `truncated`, `next_offset`); when `truncated` is true, call again
with `offset=next_offset` for the rest. An entry too large to return in one
response becomes that parcel's `error`, naming a smaller `limit` and the
`source` values that omit the possessors altogether.

To find one person or one unit on a large sheet, filter instead of paging:
`possessor_name` keeps the possessors whose name contains every word of the
text (case and diacritics ignored, words in any order: `"brkic andelic"` finds
"Anđelić Brkić"), `condominium_unit` the possessors of one unit number ("E-16",
"E16" and "16" agree). Both need `source="cadastre"`. A filtered entry carries
`possessor_filter` and `matching_possessors`; `page.total` counts the matching
records, `total_possessors` and `distinct_possessors` still the whole parcel.

On a condominium sheet (`is_condominium` true on the sheet) a possessor's
`ownership` is the share of their own unit ("1/1" of a flat, "1/2" of a shared
one), not of the parcel; the unit's share of the parcel is
`condominium_share_ownership` (the share of the common areas), and the sheet's
`total_ownership` counts each unit once: its common-area share times the
co-owners' shares of the unit added together (capped at 1), so two co-owners
of one flat count that flat once whether the cadastre records them "1/2"
each, "1/1" each or without a unit share. It is null when the cadastre gives
no common-area shares, and it describes the whole sheet regardless of
`possessor_name`, `condominium_unit`, `offset` or `limit`. When it is not 1
the sheet carries `total_ownership_note` with the exact fraction: the cadastre
copies the units' shares from the land-registry unit's list B, where they are
set per unit and not recomputed to a whole (unit 8974 of GRAD ZAGREB sums to
13029/10000 on both sides), so report the excess and check it against the
unit's shares rather than treating it as an error of the sum.

### `get_lr_unit(units, detail="ownership", limit=None, offset=0, owner_name=None, include_plombe_detail=False, historical_overview=False)`

One or more land registry units: registered owners with shares (list B),
parcels (list A), encumbrances (list C), pending entries (plombe). `units` is a
list of references; each names a unit in one of three ways:

```json
{"units": [{"parcel_number": "279/6", "municipality": "SAVAR"},
           {"lr_unit_number": "769", "main_book_id": 21277},
           {"lr_unit_number": "769", "main_book_name": "SAVAR"}]}
```

- By parcel: the unit the parcel belongs to. Resolved through parcel links when
  the parcel has no direct unit; the entry reports `lr_unit_derived_from_links`.
  This is the normal route for "who owns parcel X".
- By unit number and `main_book_id` (the reference `get_parcel` returns under
  `data.lr_unit`).
- By unit number and `main_book_name` (glavna knjiga, normally the cadastral
  municipality name); `find_main_book` lists the books.

The result is `{results, total, unique, successful, failed, duplicates,
condominiums_found}` with one entry per reference, in order. An entry has
`status`, `ref`, `lr_unit_number`, `main_book_id` and `data` or `error`. A unit
that several references resolve to is fetched once: the later entries have
`status: "duplicate"` and `same_unit_as`, the index of the entry with the data.
A reference that fails (unit not found, parcel not in the land registry,
building parcel) is an `error` entry and does not stop the others. Every
reference has exactly one of the three statuses, so `successful + failed +
duplicates = total`; `successful` alone equals `unique`, the units fetched.

`detail` shapes `data` for every unit. Every level names the unit
(`lr_unit_number`, `main_book_id`, `main_book_name`, `institution_id`,
`institution_name`) and carries `provenance` (`register: "land_registry"`,
`source_url`, `retrieved_at`), and every level but `parcels` and
`encumbrances` carries `distinct_owners`, the number of different people
among the owner records (case, diacritics and spacing ignored; two records
with different tax numbers are two people): one person on two shares is two
records and one owner, so compare it with `total_owners` to judge
fragmentation before reading names. A failed entry carries `error_type` and
`error_details` as in `get_parcel`.

- `"ownership"` (default): owners with structured shares
  (`share = {num, den, decimal}`), each with `entry` (the registration entry
  that put the owner on the share: order number, receipt date, diary number,
  action type), plus `share_entries` (notes on individual shares) and
  `summary`. Fits in context.
- `"summary"`: identity and totals only.
- `"shares"`: list B (vlastovnica) as the register holds it: the raw shares
  under `ownership_sheet_b.lr_unit_shares`, each with its sub-shares, entries
  and status, plus the sheet-level entries in `ownership_sheet_b.lr_entries`;
  `total_shares` and `total_owners` give the whole sheet's size. Use it when
  the flattened `ownership` rows are not enough (historical shares with
  `historical_overview`, share descriptions, entries on the sheet itself).
- `"parcels"`: list A (posjedovnica): the unit's parcels under `parcels`, with
  `total_parcels`, `total_area_m2`, `sheet_a1_source_key` and the list A2
  entries. When `sheet_a1_source_key` is `lrParcels` the records are the
  land register's own: `parcel_number` is the land-register number (not the
  cadastre's where a new survey renumbered the parcels), `parcel_id` is null
  and `lr_parcel_id` is an id of the land-register parcel table that
  `get_parcel` cannot use; find the cadastre parcel with `find_parcel` by
  number and cadastral municipality.
- `"encumbrances"`: list C (teretovnica): the entry groups under
  `entry_groups` (`amount`, `beneficiaries`, entries), with
  `total_entry_groups`.
- `"full"`: every sheet at once, including geometry.

`offset` and `limit` page through the list the level is about: owner records
for `ownership`, top-level shares for `shares` and `full`, parcels for
`parcels`, entry groups for `encumbrances`. Every level but `summary` carries a
`page` block (`offset`, `limit`, `total`, `returned`, `truncated`,
`next_offset`); when `truncated` is true, call again with `offset=next_offset`
for the rest. `owners_limit` is an older synonym of `limit`. In `shares` and
`full` a share is a page item whether or not it has owners (a share may hold
only annotations), and the shares outside the window are dropped whole,
counted in `shares_omitted`; `total_owners` and `owners_truncated` report the
owner records of the whole sheet. A response too large to return becomes that
unit's `error`, naming the sheet at fault and the smaller options: a per-sheet
level with a small limit is always small enough, so a unit that `full` refuses
(a list C that alone exceeds the ceiling, for instance) can still be read
completely, one sheet and one page at a time.

`owner_name` finds one person in a unit without paging through it: only the
owners whose name contains every word of the text (case and diacritics
ignored, words in any order, so "sarunic" and "Saša Šarunić" both find
"ŠARUNIĆ SAŠA") come back. In `ownership` those are the owner rows; in
`shares` and `full` the shares holding such an owner, kept whole with their
co-owners and entries. The page then walks the matches, `matching_owners` or
`matching_shares` counts them (0 when the name is not on the sheet, which is
an answer, not an error) and `total_owners` / `total_shares` still describe the
whole sheet; the result carries `owner_name` back. `summary`, `parcels` and
`encumbrances` return no owners and refuse it.

`include_plombe_detail` resolves what each pending plomba is (request type,
status, dates) into `plombe_detail` per unit, at one extra request per plomba.
`get_file_status` does the same for one file number you already hold.

`historical_overview` asks the register for the historical overview (povijesni
pregled) as well: deleted entries and shares whose status is not active. Off by
default, so the owners returned are the current ones.

Condominiums (etažno vlasništvo): an entry carries `is_condominium: true`; each
share is one apartment with `condominium_number` and `condominium_descriptions`.

### `resolve_municipality(name_or_code)`

Cadastral municipality (katastarska općina, k.o.) name to its complete search
record: `code` (the registration number), `name`, `full_name` (with the
cadastral office), `municipality_id`, `office_id` and `department_id`. Once you
have the code, use it; it is unambiguous where a name may not be. A name that
matches several municipalities returns the first with the others under
`other_matches` and `matches_total`.

### `list_municipalities(search=None, office_id=None, department_id=None, offset=0, limit=200)`

Cadastral municipalities filtered by name (substring), cadastral office
(`id` from `list_cadastral_offices`) or department, paged with `offset` and
`limit` (`limit=null` returns all). Each record is shaped as in
`resolve_municipality`; the result carries `total` and a `page` block. Use it
for "which cadastral municipalities belong to the Zadar office".

### `get_parcel_geometry(parcel_number, municipality, format="geojson", zoom=19)`

Boundary of a parcel as `geojson` (a Feature whose properties include
`map_url`), `wkt` (bare polygon) or `dict` (coordinates and `map_url`).
Coordinates are EPSG:3765. The first request for a municipality downloads its
GIS data; later requests use the cache. `zoom` 19 fits one ordinary parcel, 20
suits very small ones.

### `get_parcel_zoning(parcel_number, municipality, include_geometry=False, min_overlap=0.02)`

Screening of a parcel against the spatial plans' building areas. `status` is
`inside_settlement`, `detached_zone`, `touches_below_threshold` or `outside`;
`buildability` is always `"unknown"` (the tool never decides whether anything
may be built); `matches` lists every building-area zone covering
the parcel with its designation code and text (`T2` tourist settlement, `T3`
camp, `GPN` settlement area ...), zone name, plan name and identifier,
`generation` of the code list and the estimated overlap. `dataset.disclaimer`
says the layer is an interpretation of the plans by the county institutes and
not valid for official acts; repeat it to the user. `generation_note` explains
why T1/T2/T3 mean different things in old and new-generation plans. Zone
polygons (EPSG:3765) are included only with `include_geometry=True`.

### `list_cadastral_offices(filter_name=None)`

Cadastral offices, optionally filtered by name.

### `find_main_book(search=None, office_id=None, institution_name=None)`

Land registry main books (glavne knjige) with `main_book_id`, `main_book_name`,
`institution_id` and `court_name`. Searching "SAVAR" returns book 21277 of the
Zadar court.

### `find_book_of_dc(search=None, office_id=None, institution_name=None)`

Books of deposited contracts (knjige položenih ugovora, KPU): flats sold before
their building had a land registry unit. Returns the search records only.

### `find_possession_sheet(sheet_number, municipality)`

Cadastre possession sheets by number (prefix match). The cadastre has no lookup
by sheet id; to see a sheet's possessors, call `get_parcel` on one of its
parcels.

### `get_file_status(file_number, institution_id)`

Processing status of one land-registry file (spis, plomba) by its number, for
example "Z-12564/2026": what the request is (`application_content`), where it
is in processing (`status_description`), the registration number, the
resolution once there is one, and the dates. `institution_id` is the
land-registry office that holds the unit (`institution_id` of the unit from
`get_lr_unit`, or of the book from `find_main_book`). `found: false` with a
`message` means the register has no such file at that office; it is not an
error.

### `compare_registers(parcels)`

Are the cadastre possessors of a parcel its registered owners? `parcels` is a
list of references as for `get_parcel`. For each one the cadastre record and
the land-registry unit the parcel belongs to are read (a unit shared by
several parcels is read once) and the two lists of people are matched: by
tax number when both records carry one, otherwise by name with case,
diacritics, spacing, punctuation and a share suffix ignored; a match that
rests on the name without a relative's name ("ŠARUNIĆ AUGUSTIN POK. BOŽE"
against "Šarunić Augustin") is `fuzzy` and noted.

Each successful entry has `parcel_number`, `municipality_code`, `lr_unit`,
`provenance` for both registers, `map_url` and `data`:

- `relationship`: `same` (the registers name the same people), `overlapping`
  (some people in both), `disjoint` (different people), `cadastre_only` (the
  parcel is not in the land registry), `no_owners`, `no_possessors`, or
  `land_registry_unavailable` (the unit could not be read; the entry then
  also carries `land_registry_error` with its `error_type`).
- `summary`: the same in a sentence.
- `matched` (pairs with `fuzzy`, `by_tax_number`, `shares_agree`),
  `possessors_only`, `owners_only`, and the full `possessors` and `owners`
  lists; every person carries `name`, `register`, `share`, `tax_number`,
  `address` and `party_type_inferred` (`individual`, `company`, `state`,
  `municipality` or `unknown`, read from the name and always marked
  `inferred: true` with its `basis`).
- `distinct_possessors`, `distinct_owners`, `distinct_people` (across both
  registers; a matched pair is one person), `party_types` (of the distinct
  people) and `public_body_owner_share` (the share registered to the state
  or a municipality, when the shares are given).
- `area_check`: the cadastre area against the land register's (sheet A of
  the unit) and the map's graphical area, `mismatch` above 5 %.

The response also carries `units_fetched`, `relationships` (a count per
relationship) and `people` (distinct possessors, owners and people across
every successful entry; a person on several parcels counts once). Use it
before an acquisition: the possessor is who uses the land, the owner is who
signs; a `disjoint` parcel needs both at the table.

### `build_assembly(parcels, include_zoning=False, weights=None, export=None, persons_offset=0, persons_limit=50)`

Land-assembly analysis of a set of up to 50 parcels: the three tables an
investor needs before talking to anyone. For every reference the cadastre
record, the land-registry unit (a shared unit once) and the register
comparison are read; with `include_zoning` the building-areas screening as
well (one WFS lookup per parcel, slower).

- `parcels`: one row per parcel, easiest to acquire first, with
  `relationship`, `distinct_owners`, `distinct_possessors`,
  `has_encumbrances`, `has_pending_plombe` and `pending_plombe`,
  `public_body_owner_share`, `zoning_status`, `in_building_area`,
  `designation_code`, `plan_name`, `area_mismatch`, `score`, `map_url` and
  the `provenance` of both registers.
- `persons`: the persons ranked by the area they control (a page;
  `persons_page` says where to continue), each with `owner_of`,
  `possessor_of`, `owned_area_m2` (share x cadastre area), `possessed_area_m2`,
  `controlled_area_m2` (owned, plus the parcels only possessed),
  `shares_unknown`, `fuzzy_matches`, `surname` and `party_type_inferred`.
  `surname_groups` gathers them by surname (the registers write it first).
- `matrix`: one cell per person and parcel with `role` (`owner`, `possessor`,
  `both`), the shares and `fuzzy`.
- `scores`: the factors behind each parcel's score and `weights`. The score
  is a weighted share of yes/no factors: `single_owner`,
  `owner_is_possessor`, `no_encumbrances`, `no_pending_plombe` and
  `in_building_area` (only with `include_zoning`); a factor that could not
  be evaluated (no unit, no zoning) is left out of both the numerator and
  the denominator, and `notes` say which. Pass `weights` to change any of
  them, e.g. `{"in_building_area": 0.4}`; the weights used come back.
- `totals`: `parcel_count`, `total_area_m2`, `area_by_land_use`,
  `area_by_relationship`, `area_by_zoning_status`, `distinct_people`,
  `distinct_owners`, `distinct_possessors`, `party_types`,
  `public_body_parcels`, `fuzzy_matches`, `parcels_with_encumbrances`,
  `parcels_with_pending_plombe`, `parcels_in_building_area`.

References that could not be read are listed under `failed` with their
`error_type`; the analysis covers the rest (`total`, `successful`,
`units_fetched`, `zoning_requested` and `generated_at` say what it rests on). `export` adds one table as text
under `export`: `"parcels_csv"`, `"persons_csv"` or `"matrix_csv"` (CSV with
fixed English columns; the matrix in long form, one row per person and
parcel) or `"geojson"` (a `FeatureCollection` of the parcels that have an
outline, scores in the properties, the others under `skipped`). Party types
are inferred from names and controlled areas use cadastre areas; the
`notes` repeat both caveats. A response too large to return says so and
names the way out (fewer parcels, a `persons_limit`, one export at a time).

### `find_parcels_in_area(municipality, bbox=None, polygon=None, center=None, radius_m=None, relation="intersects", offset=0, limit=50, include_geojson=False)`

The parcels of a municipality inside an area, read from the cached cadastral
map (downloaded on first use), so that a target area can be defined without
knowing any parcel number. Give exactly one area, in EPSG:3765 (HTRS96/TM)
metres, the coordinates `get_parcel_geometry` returns:

```json
{"municipality": "SAVAR", "bbox": [380590, 4880880, 380680, 4880980]}
{"municipality": "SAVAR", "polygon": "POLYGON((380590 4880880, 380680 4880880, 380590 4880980, 380590 4880880))"}
{"municipality": "SAVAR", "center": [380616.77, 4880907.83], "radius_m": 50}
```

`polygon` is WKT or a list of `[x, y]` vertices. `relation` is `"intersects"`
(default; the parcel touches the area) or `"within"` (it lies wholly inside,
its boundary included); a radius query measures the distance from the point
to each parcel's outline (0 when the point is inside it). Longitude/latitude
is refused with a hint: the tools do not reproject.

The result is `{municipality_code, query, parcels, total, total_area_m2,
page, dataset}`: `parcels` are rows with `parcel_number`, `area_m2` (the
graphical area from the map), `centroid`, `bounds`, `distance_m` (radius
queries) and `map_url`, paged with `offset` and `limit` (default 50);
`total` and `total_area_m2` count every match, not only the page. `dataset`
is the map's provenance: `parcel_count` of the municipality, `crs`, `source`
server, `downloaded_at` and a note that these are outlines and graphical
areas from the cadastral map, not a survey. `include_geojson` adds the page
as a GeoJSON `FeatureCollection` (EPSG:3765). The rows carry no owners or
land use: pass the numbers to `get_parcel` / `get_lr_unit` for the registers.

### `find_parcel_neighbours(parcel_number, municipality, tolerance_m=0.10, offset=0, limit=50, include_geojson=False)`

The parcels around one parcel, from the cached cadastral map: those sharing a
boundary with it (`shared_boundary_m`, longest first) and those touching it
at a corner only (`touches_at_point: true`, `shared_boundary_m: 0`). Two
outlines within `tolerance_m` of each other count as touching (digitising
gaps). The result is `{municipality_code, parcel, neighbours, total,
total_area_m2, tolerance_m, page, dataset}` with the same row shape as
`find_parcels_in_area`; `parcel` is the seed's row. A parcel that is not in
the municipality's GIS data is an error naming the municipality code. Use it
to walk outward from a seed parcel; the numbers go to `get_parcel` /
`get_lr_unit` for the registers' records.

### `download_municipality_gis(municipality, force=False)`

Downloads the GIS data of a whole cadastral municipality (the ATOM ZIP with
the parcel boundaries in GML) into the local cache that `get_parcel_geometry`
and `get_parcel_zoning` read, or refreshes it with `force=true`. Returns the
`download_url`, whether it was `already_cached`, `downloaded_at` (when the
cached ZIP was downloaded, UTC: the age of the data every geometry, map link,
zoning answer and `area_check` for this municipality rests on), the cached
`zip_path` and `gml_path`, the ZIP size, the `parcel_count` of the
municipality and the `source` server the cache came from. The two geometry tools download on demand;
this is for fetching ahead of many lookups or refreshing stale data.

## Playbook

- **Who owns parcel X (prema ZK)**: `get_lr_unit` with
  `{"parcel_number", "municipality"}`. One call.
- **Possessors of parcel X (kataster)**: `get_parcel` with `source="cadastre"`.
- **A portfolio**: `get_parcel` with all references and `source="land_registry"`
  for the cadastre facts, then `get_lr_unit` with the parcel references (or the
  `data.lr_unit` references) for the owners. Duplicated units are fetched once.
- **By unit number**: `get_lr_unit` with `lr_unit_number` and `main_book_id`, or
  `main_book_name` when only the book name is known.
- **Building parcels** (zgr.) have no unit of their own; `get_lr_unit` reports
  the error for that reference. The building is registered on its land parcel.
- **Cadastre-only parcels**: `get_parcel` reports `data.lr_unit` null and, with
  `source="land_registry"`, `land_registry_hint.in_land_registry: false`. Say
  the parcel is not in the land registry rather than inventing an owner.
- **Map or boundary**: `get_parcel_geometry`, or the `map_url` that `find_parcel`
  and `get_parcel` already return.
- **Is the possessor the owner** (posjednik vs vlasnik, one parcel or a set):
  `compare_registers` with the parcel references. It reads both registers
  and says `same`, `overlapping` or `disjoint` per parcel, who is in one
  register only, and how many distinct people the set involves.
- **Assembling land from a set of parcels** (who to sit down with, where to
  start): `build_assembly` with the references (from `find_parcels_in_area`
  or a list), `include_zoning` when the building area matters, `export` for
  a CSV to paste into an email. Read `scores[].factors` and `weights` before
  quoting a ranking; the rule is transparent on purpose.
- **Which parcels are in this area / around this parcel**:
  `find_parcels_in_area` (bounding box, polygon or radius, EPSG:3765 metres)
  and `find_parcel_neighbours` give parcel numbers, graphical areas and
  `total_area_m2` from the cached cadastral map, no registers involved; then
  `get_parcel` / `get_lr_unit` with the numbers for possessors and owners.
- **A large unit** (a condominium with hundreds of shares, a long list C):
  `get_lr_unit` with `owner_name` when one person is wanted ("is X an owner",
  "which flat does X own"); otherwise `detail="ownership"` and a `limit`, then
  `offset=next_offset` until `page.truncated` is false; `detail="shares"`,
  `"encumbrances"` or `"parcels"` with a limit for the raw sheets. Do not retry
  `full` on a unit it refused.
- **A parcel under a large building** (hundreds of possessors on its
  possession sheet): `get_parcel` with `possessor_name` or `condominium_unit`
  when one person or one unit is wanted; otherwise a `limit`, then
  `offset=next_offset` until `page.truncated` is false; or `source="none"` for
  the parcel alone and `get_lr_unit` for the owners. Do not retry a refused
  parcel without a limit.
- **Which parcels exist with a number**: `find_parcel` with `max_matches`. When
  no single parcel can be chosen (only the building parcel `*35/1` exists, say)
  the answer has `success: false` and `match_note`, and `matches` still lists
  the records.
- **What is pending on a unit**: `summary.pending_plombe` lists the file
  numbers; `include_plombe_detail` or `get_file_status` say what each one is.
- **Municipalities of an office**: `list_municipalities` with the `office_id`
  from `list_cadastral_offices`.
- **Not harmonized**: `cadastre_lr_harmonized: false` on a parcel means the
  cadastre and the land registry disagree about it; show both registers.

Names come with a `name_normalized` companion; the raw `name` preserves source
quirks. Cite `entry` (order number, date, diary number) when asked how or when
someone became owner.

## Resources and prompts

Resources: `cadastral://parcel/{parcel_id}` (the parcel record),
`cadastral://municipality/{code}` (the municipality search record),
`cadastral://office/{code}` (the office by id). Prompts:
`explain_ownership_structure(parcel_id)`, `property_report(parcel_id)`,
`compare_parcels(parcel_ids)`, `land_use_summary(parcel_id)`; all four take
the numeric `parcel_id` that `find_parcel` returns and read the cadastre
record (possessors, not land-registry owners).

## Troubleshooting

- **`error_type`**: every failed entry of `get_parcel` and `get_lr_unit`
  carries one, and every tool error message ends with `[error_type=...]`.
  `access_denied` means the server refused (HTTP 401/403), `rate_limit` that
  it throttled, `*_not_found` that nothing exists under that reference,
  `response_too_large` that the entry must be paged, `invalid_request` that
  the reference or an option was wrong. Only `*_not_found` means "no such
  record".
- **Municipality not found**: check the spelling or use the registration code
  from `resolve_municipality`.
- **No parcels found**: check the number format ("103/2", not "103-2") and the
  municipality; for a building parcel add "ZGR".
- **has no geometry in the GIS data**: the parcel is not in the municipality's
  GML file. If the cached data may be stale, clear it with
  `cadastral cache clear -m <code>`.
- **Could not retrieve the land registry unit**: check the reference. A parcel
  that is `parcel_not_in_land_registry` is cadastre-only.
- **Could not match parcel against the building areas ... status_code=404**:
  the building-areas lookup went to the default endpoint, the mock server's
  imitation of the WFS at `<CADASTRAL_API_BASE_URL>/planning/wfs`, which
  exists only on the mock. When the server is pointed elsewhere, set
  `CADASTRAL_PLANNING_WFS_URLS` to the building-areas WFS mirror(s) as well
  (see `.env.example`; verify your rights first) and restart the MCP server.
- **Rate limiting**: the server spaces its requests; pass lists to `get_parcel`
  and `get_lr_unit` instead of calling once per item.

## Reminders

1. This is a demonstration; the default target is the mock server.
2. Before pointing the server elsewhere, verify your rights to use that server
   and its data. You do so at your own risk.
3. Ownership data is sensitive personal data; keep raw captures out of the
   repository.
