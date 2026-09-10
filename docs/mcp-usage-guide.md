# MCP Usage Guide

How an AI agent (Claude Desktop, Claude Code, any MCP client) should use the
Cadastral MCP server. The server exposes nine tools, three resources and four
prompts over the Model Context Protocol; it is a demonstration that runs against
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

### `find_parcel(parcel_number, municipality)`

Finds one parcel and returns its `parcel_id`, `parcel_number`,
`municipality_code`, `is_building_parcel` and, when the municipality's GIS data
is available, `map_url` (the interactive map centred on the parcel). Use it to
confirm a parcel exists or to get its id; `get_parcel` gives the record.

The search matches on a substring, so a number that does not exist can come
back as a longer one ("973" as 973/1). Check `exact_match`. When it is `false`,
`match_note` and `other_matches` say what was found instead; report that as "no
such parcel, here is what exists", not as a hit. A building parcel is never
answered with a land parcel or the other way round. Building parcels may be
written "35/1 ZGR", "35/1.ZGR", "zgr. 35/1" or "*35/1"; all resolve exactly.

### `get_parcel(parcels, source="cadastre")`

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
the land registry reference) and `map_url` when available. A failed parcel does
not stop the others. An entry resolved from a fallback match carries
`exact_match: false` and `match_note`, as `find_parcel` does.

### `get_lr_unit(units, detail="ownership", owners_limit=None, include_plombe_detail=False)`

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

`detail` shapes `data` for every unit:

- `"ownership"` (default): owners with structured shares
  (`share = {num, den, decimal}`), each with `entry` (the registration entry
  that put the owner on the share: order number, receipt date, diary number,
  action type), plus `share_entries` (notes on individual shares) and
  `summary`. Fits in context.
- `"summary"`: identity and totals only.
- `"full"`: every sheet, including list C encumbrances (`amount`,
  `beneficiaries`) and geometry.

`owners_limit` caps owner records per unit in `ownership` and `full`;
`total_owners` and `owners_truncated` report the full count. In `full` the cap
cuts list B off at that many records and `shares_omitted` counts the shares
dropped. A `full` dump too large to return becomes that unit's `error`, naming
the sheet at fault and the smaller options; use `ownership` there.

`include_plombe_detail` resolves what each pending plomba is (request type,
status, dates) into `plombe_detail` per unit, at one extra request per plomba.

Condominiums (etažno vlasništvo): an entry carries `is_condominium: true`; each
share is one apartment with `condominium_number` and `condominium_descriptions`.

### `resolve_municipality(name_or_code)`

Cadastral municipality (katastarska općina, k.o.) name to registration code.
Once you have the code, use it; it is unambiguous where a name may not be.

### `get_parcel_geometry(parcel_number, municipality, format="geojson", zoom=19)`

Boundary of a parcel as `geojson` (a Feature whose properties include
`map_url`), `wkt` (bare polygon) or `dict` (coordinates and `map_url`).
Coordinates are EPSG:3765. The first request for a municipality downloads its
GIS data; later requests use the cache. `zoom` 19 fits one ordinary parcel, 20
suits very small ones.

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
- **Not harmonized**: `cadastre_lr_harmonized: false` on a parcel means the
  cadastre and the land registry disagree about it; show both registers.

Names come with a `name_normalized` companion; the raw `name` preserves source
quirks. Cite `entry` (order number, date, diary number) when asked how or when
someone became owner.

## Resources and prompts

Resources: `cadastral://parcel/{parcel_id}`, `cadastral://municipality/{code}`,
`cadastral://office/{code}`. Prompts: `explain_ownership_structure(parcel_id)`,
`property_report(parcel_id)`, `compare_parcels(parcel_ids)`,
`land_use_summary(parcel_id)`.

## Troubleshooting

- **Municipality not found**: check the spelling or use the registration code
  from `resolve_municipality`.
- **No parcels found**: check the number format ("103/2", not "103-2") and the
  municipality; for a building parcel add "ZGR".
- **has no geometry in the GIS data**: the parcel is not in the municipality's
  GML file. If the cached data may be stale, clear it with
  `cadastral cache clear -m <code>`.
- **Could not retrieve the land registry unit**: check the reference. A parcel
  that is `parcel_not_in_land_registry` is cadastre-only.
- **Rate limiting**: the server spaces its requests; pass lists to `get_parcel`
  and `get_lr_unit` instead of calling once per item.

## Reminders

1. This is a demonstration; the default target is the mock server.
2. Before pointing the server elsewhere, verify your rights to use that server
   and its data. You do so at your own risk.
3. Ownership data is sensitive personal data; keep raw captures out of the
   repository.
