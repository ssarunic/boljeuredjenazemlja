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

- **Owner of specific parcel(s), "prema ZK"** -> `get_lr_unit_from_parcel`
  (parcel_number + municipality). It resolves the land-registry unit even when
  the parcel has no direct unit (via parcel links) and returns B-list owners.
  Check `lr_unit_derived_from_links` to see how it resolved.
- **Cadastre possessors of a parcel** -> `batch_fetch_parcels` with
  `source="cadastre"` (or `find_parcel` for one parcel + basic info).
- **A portfolio / many parcels** -> `batch_fetch_parcels` (same k.o. is most
  efficient), then `batch_lr_units` with the returned `lr_unit` references for
  registered owners.
- **By unit number directly** -> `get_lr_unit(unit_number, main_book_id)`, or
  `get_lr_unit(unit_number, main_book_name="SAVAR")` when only the main book
  (glavna knjiga) name is known; `find_main_book` lists the books.
- **Building parcels** ("35/1 ZGR", "zgr. 35/1", "*35/1") -> any spelling works;
  they have no land-registry unit of their own (the building is registered on
  its land parcel), so `get_lr_unit_from_parcel` reports
  `parcel_not_in_land_registry` for them.
- **Possession sheet by number** -> `find_possession_sheet`; **KPU books** ->
  `find_book_of_dc`.
- **Map / boundaries** -> `get_parcel_geometry`.

## Response shaping

LR-unit tools take `detail` = `summary` | `ownership` (default) | `full`:

- Default `ownership` returns B-list owners + structured shares
  (`share = {num, den, decimal}`) + a summary - it already fits in context.
- For large units, pass `owners_limit` and summarise; `total_owners` /
  `owners_truncated` report what was capped. Reach for `full` only when geometry
  or the C-sheet (encumbrances) is actually needed.

## Notes

- A parcel with `in_land_registry: false` (or the
  `parcel_not_in_land_registry` error) is cadastre-only - report it as such
  rather than inventing an owner.
- Names come with a `name_normalized` companion; the raw `name` preserves
  source quirks (use it for fidelity, the normalized form for matching/display).
- Each owner row carries `entry` (the registration entry: order number, receipt
  date, diary number, action type); `share_entries` are notes registered on
  single shares. Cite them when asked how or when someone became owner.
