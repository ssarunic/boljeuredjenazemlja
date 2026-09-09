# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Every release corresponds to an
annotated git tag `vX.Y.Z`; see [specs/release-process.md](specs/release-process.md).

The whole monorepo (SDK, CLI, MCP server, mock server) shares one version
number and one tag.

## [Unreleased]

### Added

- Complete API coverage per `specs/api-coverage-specification.md`. Every key
  the public API returns is now a declared, typed field: `Party.entry` (the
  registration entry that put an owner on a share, with `priority_diary_number`
  and `transferred_from_unit` parsed from its text), `LRShare.sub_shares` and
  `LRShare.share_entries` (the two kinds of `subSharesAndEntries` element,
  routed by a discriminated union instead of being dropped), `Plumb.plumb_mark`,
  `LREntry.amount` with parsed `amount_value` and `amount_currency`,
  `LREntry.style_class` and `description_text`, `ParcelPart.part_type`,
  `building_right` and `last_change_log_file_num`, typed `LRUnitParcel.parcel_parts`
  and `possession_sheets`, `SheetAParcelList.source_key` (`lrParcels` or
  `cadParcels`), `LandRegistryUnit.reference_shape`, `ParcelInfo.lr_reference_shape`,
  `is_building_parcel` and `parcel_number_display`, and the `LRUnitType` enum.
  Every model that receives server JSON keeps unknown keys in `source_fields`
  (`SourceModel` base) and the client's `unknown_fields` setting (`warn`,
  `ignore`, `error`; `CADASTRAL_API_UNKNOWN_FIELDS`) reports them.
- SDK: the three search endpoints that had no client method. `find_possession_sheet`,
  `find_main_book`, `find_book_of_dc` and `resolve_main_book_id`, with the typed
  `KeyValueSearchResult` hierarchy (`PossessionSheetSearchResult`,
  `MainBookSearchResult`, `BookOfDCSearchResult`; `ParcelSearchResult` and
  `MunicipalitySearchResult` are subclasses now). `get_lr_unit_detailed` accepts
  `main_book_name` instead of the id and reports `main_book_ambiguous` or
  `main_book_not_found`.
- SDK: building parcels. `normalize_parcel_number` maps `35/1.ZGR`, `35/1 ZGR`,
  `zgr. 35/1` and `*35/1` to the API spelling, `display_parcel_number` renders
  `zgr. 35/1`; every parcel lookup applies it, and asking for a land parcel
  when only the building parcel exists reports `only_building_parcel_exists`.
- CLI: `list-main-books` (`glavne-knjige`), `list-books-of-dc` (`kpu`) and
  `search-possession-sheet` (`posjedovni-list`); `get-lr-unit --main-book-name`
  (`--naziv-glavne-knjige`, `-n`/`-ng`). `get-lr-unit --show-owners` prints each
  owner's registration entry (order number, receipt date, diary number); `--all`
  lists the notes registered on individual shares and the secured amount on
  list C entries; the parcel list says whether it comes from the land register
  or the cadastre. `get-parcel` marks building parcels and prints the file of
  the last change per land use. JSON output carries the new fields under the
  keys listed in `output_keys.py`; `batch-fetch` resolves the land registry
  reference through parcel links too and reports `is_building_parcel`.
- MCP: tools `find_main_book`, `find_book_of_dc` and `find_possession_sheet`;
  `get_lr_unit` accepts `main_book_name`; `detail="ownership"` owner rows carry
  `entry` and the result carries `share_entries` and `sheet_a1_source_key`.
- Mock server: routes for possession sheet, main book and books-of-DC search;
  the parcel search reproduces the observed prefix, asterisk-wildcard and
  `ZGR` semantics; data sets regenerated from the redacted capture (59 parcels
  of k.o. Savar in all three shapes including six building parcels, all 17
  Savar units and the Split condominium, the real offices list).
- Coverage gate `api/src/cadastral_api/tests/test_api_coverage.py` over 21
  redacted fixtures (`api/src/cadastral_api/tests/fixtures/`), produced by
  `scripts/redact_capture.py` from a raw sample that `scripts/capture_api_sample.py`
  fetches (it refuses to run without an explicit `--base-url`).
- `specs/api-coverage-specification.md`: field-level inventory of every public
  API endpoint from a live capture and the specification for complete coverage
  in the SDK models, client, CLI, MCP server and mock server, including a
  coverage gate test.
- Map link for parcel geometry. `ParcelGeometry.map_url(zoom=19)` and
  `build_map_url()` in the SDK build the interactive-map URL centred on the
  parcel (EPSG:3765 centre, zoom, standard layer set); `ParcelGeometry.to_geojson()`
  returns a GeoJSON Feature whose properties include it. The MCP tool
  `get_parcel_geometry` returns `map_url` in `dict` and `geojson` output and
  accepts a `zoom` argument; `find_parcel` and each successful
  `batch_fetch_parcels` entry return `map_url` too when the municipality's GIS
  data is available (best effort, omitted otherwise). The CLI `get-geometry` command prints the link with
  `--show-stats` and includes `map_url` in `json` and `geojson` output;
  `get-parcel` uses the same builder.
- `specs/gateway-service.md`: specification for a hosted gateway exposing the SDK
  as a REST API and as a remote MCP server (single container, SQLite, no external
  services).
- `docs/sdk-guide.md`, `docs/development-guide.md`, `docs/legal.md`: SDK reference,
  developer setup and release procedure, and the full terms of use, moved out of
  the top-level README.

### Changed

- SDK: entry kinds follow the Land Registry Act. `ActionType` gains `uknjižba`
  (unconditional registration, previously folded into the generic `upis`);
  `upis` is now only the fallback for "upisuje se". A deletion is reported by
  the new `LREntry.deletes_prior_entry` flag, and `brisanje` is the kind only
  when the text names no other kind. CLI and MCP `action_type` values change
  accordingly.
- SDK: `ParcelInfo.total_owners` is renamed `total_possessors` (the cadastre
  records possessors, not owners); no alias is kept. CLI JSON key `total_owners` becomes
  `total_possessors` (Croatian `broj_posjednika`, unchanged). The `Possessor`,
  `PossessionSheet` and `ParcelInfo` descriptions no longer say "owner", and
  `cli/tests/test_terminology.py` enforces that.
- SDK: `LRShare.share_status` (`ShareStatus.ACTIVE` for status 0, otherwise
  `HISTORICAL`) replaces the unused enum; `LRUnitParcel.area_numeric` is `None`
  instead of 0 when the area is missing or unparsable. `has_encumbrances()` is
  renamed to what it tests: `EncumbranceSheetC.has_entries()` and
  `LandRegistryUnitDetailed.has_sheet_c_entries()`; the summary key and the CLI
  JSON key `has_encumbrances` become `has_sheet_c_entries` (Croatian
  `ima_upise_u_teretovnici`). No aliases are kept.
- SDK: a parcel without a direct unit whose links name different units raises
  `LR_UNIT_NOT_FOUND` with reason `lr_unit_ambiguous` and the candidates
  instead of silently taking the first; `ParcelInfo.lr_unit_candidates()`
  lists them. The CLI explains the message.
- SDK: share totals (`OwnershipSheetB.total_ownership_accounted`,
  `PossessionSheet.total_ownership`) are summed exactly as fractions
  (`total_ownership_fraction()` returns the `Fraction`) and converted once, so
  three thirds are 1.0.
- Terms of use: the "never use against government systems" wording is replaced
  everywhere (README, `docs/legal.md`, CLAUDE.md, `.env.example`, module
  docstrings, CLI help footers, documentation banner) by "verify that you have
  the rights to use that server and its data first; use at your own risk".
- Documentation: `docs/en/cli/commands/` gains pages for the three new commands;
  `get-lr-unit` and `get-parcel` pages describe the main book name, the entry
  column and building parcels; the glossary gains čestica zgrade, knjiga
  položenih ugovora and upis. Croatian edition regenerated.
- CLI: `get-lr-unit --show-encumbrances` prints, under each list C entry, the
  persons it is registered in favour of (**In favour of** / **U korist**). In
  `json` output each entry is now an object (`order_number`, `description`,
  `beneficiaries`, and `source_fields` with the server's nested data verbatim)
  instead of a plain description string, and each group carries
  `share_order_number`.
- CLI: short option flags now have Croatian spellings as well, two letters taken
  from the Croatian long option (`-bu` for `--broj-uloška`, `-gk` for
  `--glavna-knjiga`, `-vl` for `--vlasnici`, `-ob` for `--oblik`, ...). Croatian
  help and documentation show them; the English single-letter flags keep working
  in every language, like `-ko` did before.
- Top-level README rewritten as a short teaser: three usage examples and a
  capability table linking to the per-command CLI documentation. Stale SDK method
  names, the wrong rate-limit default, and the unimplemented HTTP transport claim
  were removed.
- `api/`, `cli/`, and `mcp/` READMEs trimmed to short pointers into `docs/`.

### Fixed

- SDK: parcels of a land registry unit (`LRUnitParcel`) no longer invent facts
  for keys the lean `lrParcels` shape does not send. `graphic`, `alpha_numeric`,
  `is_harmonized`, `legal_regime`, `status`, `resource_code`, `building_remark`,
  `has_building_right` and `area` are `None` when absent instead of defaulting
  to true, false or zero; `area_numeric` stays 0 for a missing area.
- SDK: encumbrance entries (teretovnica, list C) no longer lose their
  beneficiaries. The server lists the persons an entry is registered in favour
  of under `lrOwners` (the entry text ends with "u korist:"), which the model
  silently dropped. `LREntry.owners` now types that list; `LREntry`,
  `EncumbranceGroup` and `EncumbranceSheetC` keep any other undeclared field
  (`extra="allow"`, exposed as `LREntry.source_fields`); and
  `LREntry.get_parties()` / `EncumbranceGroup.get_parties()` return the
  beneficiaries as `Party` objects. The MCP `detail="full"` output includes
  them through the model dump. Mock unit 657 now carries a list C with this
  structure, and the API specification documents it.
- SDK: `EncumbranceGroup.right_type` and `EncumbranceGroup.beneficiary` were
  always `null`. They are now derived when the server does not send them:
  `right_type` is parsed from the entry text (`parse_right_type()` in
  `cadastral_api.utils`: pravo plodouživanja → `usufruct`, založno pravo →
  `mortgage`, služnost → `easement`, tražbina → `lien`, zabrana otuđenja →
  `prohibition`, prvokup → `preemption`, zabilježba → `annotation`, anything
  else → `other`) and `beneficiary` is the first person in the entries'
  `lrOwners`. The CLI `get-lr-unit` `json` output carries `right_type` per
  encumbrance group.
- SDK: `LREntry.action_type`, `diary_number`, `entry_date` and `basis_document`
  were always `null`. They are now parsed from the entry text
  (`parse_lr_entry()` in `cadastral_api.utils`): the action (uknjižba → `upis`,
  predbilježba, zabilježba, brisanje), the diary number normalised to
  `Z-487/49`, the receipt date (first date in the text, Croatian month names or
  numeric), the legal basis (the phrase after "Na temelju") and `basis_date`,
  the date inside that phrase. The CLI `get-lr-unit` `json` output carries them
  per entry.
- SDK: a share written into a beneficiary's name (`"... ZA 2/6"`) is no longer
  treated as part of the name. `Party.share` exposes it as `{num, den, decimal}`
  (the shape of a Sheet B `share_fraction`), `name_normalized` drops the suffix
  and the raw `name` is kept. The CLI `get-lr-unit` `json` beneficiaries carry
  `name_normalized` and `share`.
- CLI: `get-geometry` `json`, `geojson` and `csv` output is no longer soft-wrapped
  at the terminal width, which broke lines longer than the window (such as the
  map link) when the output was piped.
- MCP server: `get_parcel_geometry` with `format="geojson"` failed on every
  parcel because the geometry model had no `to_geojson()` method.
- MCP server: `get_parcel_geometry` reports a clear error when the parcel is
  not in the municipality's GIS data instead of failing with
  `'NoneType' object has no attribute 'to_geojson'` (or `model_dump`).
- SDK: the GIS cache records which server each municipality ZIP came from
  (`source.txt` next to the ZIP) and downloads the municipality again when the
  configured API base URL differs or the marker is missing. Synthetic geometry
  downloaded from the mock server can no longer be served to a client configured
  for another server; caches written by earlier versions are refreshed on first
  use.

## [0.1.0] - 2026-09-08

Baseline release. Everything the repository contained when release tagging
was introduced.

### Added

- Python SDK (`api/`) with Pydantic V2 models, rate-limited HTTP client,
  GIS geometry parsing from INSPIRE GML files, and a local GIS cache.
- Command-line interface (`cli/`): `search`, `get-parcel`, `get-lr-unit`,
  `batch-fetch`, `batch-lr-unit`, `list-municipalities`, `list-offices`,
  `info`, `get-geometry`, `download-gis`, `cache clear`; table, JSON, CSV,
  WKT and GeoJSON output.
- MCP server (`mcp/`) exposing cadastre and land-registry lookups to AI
  agents over STDIO and HTTP, with bilingual tool descriptions and a routing
  skill.
- Mock API server (`mock-server/`) with sample municipalities, offices,
  parcels, land-registry units and geometry, so the tools can be exercised
  without touching any production system.
- Land-registry unit support: sheets A, B and C, condominiums (etažno
  vlasništvo), plombe with detail resolution, explicit register source
  (cadastre vs. land registry) and a cadastre/land-registry divergence notice.
- Complete Croatian localization of the CLI, including Croatian command and
  option names, with a translation coverage gate.
- Bilingual CLI user documentation (`docs/en/cli/`, `docs/hr/cli/`) generated
  by `scripts/build_docs.py`, with documentation and terminology gates in CI.

[Unreleased]: https://github.com/ssarunic/boljeuredjenazemlja/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ssarunic/boljeuredjenazemlja/releases/tag/v0.1.0
