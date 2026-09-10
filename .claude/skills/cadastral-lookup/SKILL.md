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
- **Possession sheet by number** -> `find_possession_sheet`; **KPU books** ->
  `find_book_of_dc`.
- **Map / boundaries** -> `get_parcel_geometry`.

## Response shaping

`get_lr_unit` takes `detail` = `summary` | `ownership` (default) | `full`:

- Default `ownership` returns B-list owners + structured shares
  (`share = {num, den, decimal}`) + a summary - it already fits in context.
- For large units, pass `owners_limit` and summarise; `total_owners` /
  `owners_truncated` report what was capped. Reach for `full` only when geometry
  or the C-sheet (encumbrances) is actually needed; a `full` dump too large to
  return comes back as that unit's `error` with the smaller options named.
- Every entry has a `status` (`success`, `error`, `duplicate`); read the
  `error` of a failed reference instead of retrying blindly.

## Notes

- A parcel with `in_land_registry: false` (or the
  `parcel_not_in_land_registry` error) is cadastre-only - report it as such
  rather than inventing an owner.
- Names come with a `name_normalized` companion; the raw `name` preserves
  source quirks (use it for fidelity, the normalized form for matching/display).
- Each owner row carries `entry` (the registration entry: order number, receipt
  date, diary number, action type); `share_entries` are notes registered on
  single shares. Cite them when asked how or when someone became owner.
