# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Every release corresponds to an
annotated git tag `vX.Y.Z`; see [specs/release-process.md](specs/release-process.md).

The whole monorepo (SDK, CLI, MCP server, mock server) shares one version
number and one tag.

## [Unreleased]

### Added

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
