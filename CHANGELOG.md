# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/). Every release corresponds to an
annotated git tag `vX.Y.Z`; see [specs/release-process.md](specs/release-process.md).

The whole monorepo (SDK, CLI, MCP server, mock server) shares one version
number and one tag.

## [Unreleased]

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
