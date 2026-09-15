---
name: cadastral-lookup
description: >-
  Use for ANY Croatian/Serbian cadastre (katastar) or land-registry (zemljišne
  knjige, gruntovnica, ZK) question - looking up parcels (čestica, k.č.) by
  cadastral municipality (katastarska općina, k.o.), finding owners (vlasnici,
  suvlasnički udjeli, vlastovnica / B-list), possessors (posjedovni list),
  land-registry units (zemljišnoknjižni uložak), encumbrances (teret,
  teretovnica / C-list), or parcel geometry. Reach for the cadastral MCP tools
  (find them via tool search for "cadastre" / "katastar" / "land registry").
---

# Cadastral & land-registry lookup

This project exposes a cadastral/land-registry MCP server. Its tools are the way
to answer parcel and ownership questions - prefer them over guessing. If they are
not already loaded, find them by searching available tools for `cadastre`,
`katastar`, `land registry`, `zemljišne knjige`, or `parcel`.

## Pick the right register (the #1 mistake to avoid)

Cadastre and land registry are **different registers and often list different
people**. Choose deliberately:

- "vlasnik", "tko je vlasnik", "prema zemljišnim knjigama", "ZK", "gruntovnica",
  ownership shares -> **land registry** (vlastovnica / B-list).
- "posjednik", "posjedovni list", "kataster" -> **cadastre** (possessors).

Every returned person record carries a `register` field
(`cadastre` | `land_registry`) - check it.

## Tool playbook

Two tools do the work; both take a **list of references** (one for a single
item, several for a portfolio) and return one entry per reference, in order.

- **Owner of specific parcel(s), "prema ZK"** -> `get_lr_unit` with
  `{"parcel_number": ..., "municipality": ...}` references. It resolves the
  land-registry unit even when the parcel has no direct unit (via parcel links;
  check `lr_unit_derived_from_links`) and returns B-list owners.
- **Cadastre possessors / area / land use of parcel(s)** -> `get_parcel` with
  `source="cadastre"` (`find_parcel` for a bare existence check + parcel_id).
- **A portfolio** -> one `get_parcel` call with all references
  (`source="land_registry"` if owners are wanted), then one `get_lr_unit` call
  with the parcel references or the returned `data.lr_unit` references. Units
  shared by several parcels are fetched once (`status: "duplicate"`,
  `same_unit_as`).
- **By unit number directly** -> `get_lr_unit` with
  `{"lr_unit_number": "769", "main_book_id": 21277}`, or with
  `"main_book_name": "SAVAR"` when only the main book (glavna knjiga) name is
  known; `find_main_book` lists the books.
- **Building parcels** ("35/1 ZGR", "zgr. 35/1", "*35/1") -> any spelling works;
  they have no land-registry unit of their own (the building is registered on
  its land parcel), so their `get_lr_unit` entry is an error saying so.
- **Is the possessor the owner** (posjednik vs vlasnik) -> `compare_registers`
  with the parcel references: `relationship` per parcel (`same`,
  `overlapping`, `disjoint`, `cadastre_only`), matched pairs (`fuzzy` when
  the match rests on the name without "POK./UD."), who is in one register
  only, `party_type_inferred` (always an inference), distinct people across
  the set. Read both registers through it instead of comparing by hand.
- **Assembling land, due diligence over a set** -> `build_assembly` with up
  to 50 parcel references: matrix of persons x parcels, persons ranked by
  controlled area (grouped by surname), parcels ranked by ease of
  acquisition with the `weights` and per-parcel `factors` shown (a factor
  not evaluated is left out, never counted against the parcel);
  `include_zoning` for the building-area factor; `export` for CSV/GeoJSON
  text. Quote the caveats in `notes` (inferred party types, cadastre areas).
- **Possession sheet by number** -> `find_possession_sheet`; **KPU books** ->
  `find_book_of_dc`.
- **What a pending plomba is** -> `get_lr_unit` with `include_plombe_detail`,
  or `get_file_status` for one file number and the unit's `institution_id`.
- **Municipalities of an office** -> `list_municipalities` with the
  `office_id` from `list_cadastral_offices`.
- **Map / boundaries** -> `get_parcel_geometry`.
- **Parcels in an area, or around a parcel** -> `find_parcels_in_area` (bbox,
  polygon or centre + radius, EPSG:3765 metres as `get_parcel_geometry`
  returns them) and `find_parcel_neighbours` (shared boundary, corner touch).
  Both read the cached cadastral map and give numbers and graphical areas
  only; follow with `get_parcel` / `get_lr_unit` for the registers.

## Response shaping

`get_lr_unit` takes `detail` = `summary` | `ownership` (default) | `shares` |
`parcels` | `encumbrances` | `full`:

- Default `ownership` returns B-list owners + structured shares
  (`share = {num, den, decimal}`) + a summary - it already fits in context.
- `shares` is raw list B (shares with sub-shares, entries, status), `parcels`
  is list A and `encumbrances` is list C, each on its own; reach for `full`
  only when every sheet and the geometry are needed at once.
- For large units, pass `limit` and page with `offset`: every level carries a
  `page` block (`total`, `returned`, `truncated`, `next_offset`). A response
  too large to return comes back as that unit's `error` with the smaller
  options named; use a per-sheet level with a limit instead of retrying `full`.
- `historical_overview=true` adds deleted entries and non-active shares.
- Every entry has a `status` (`success`, `error`, `duplicate`); read the
  `error` and `error_type` of a failed reference instead of retrying blindly:
  `*_not_found` means no such record, `access_denied` that the server refused,
  `rate_limit` that it throttled, `response_too_large` that the entry must be
  paged (`limit`, `offset`), `invalid_request` that the reference was wrong.
  Tool-level errors end with `[error_type=...]` for the same reason.

## Notes

- Every successful entry carries `provenance` (`register`, `source_url`,
  `retrieved_at`): quote it with any fact you forward, so the answer is never
  taken for an official extract. `get_parcel` entries also carry `area_check`
  (cadastre area against the cadastral map's graphical area and, when known,
  the land register's; `mismatch` above 5 %). `get_lr_unit` entries carry
  `distinct_owners` next to `total_owners` (one person on two shares is two
  records, one owner) for judging fragmentation.
- A parcel with `in_land_registry: false` (or the
  `parcel_not_in_land_registry` error) is cadastre-only - report it as such
  rather than inventing an owner.
- Names come with a `name_normalized` companion; the raw `name` preserves
  source quirks (use it for fidelity, the normalized form for matching/display).
- Each owner row carries `entry` (the registration entry: order number, receipt
  date, diary number, action type); `share_entries` are notes registered on
  single shares. Cite them when asked how or when someone became owner.
