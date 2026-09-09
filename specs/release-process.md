# Release Process

This document defines how releases of this repository are versioned, tagged
and described. There is no packaging, publishing or deployment step: a release
is a named, reproducible point in the history that users, bug reports and
documentation can refer to. Releases are cut occasionally, after a major
feature lands or an important bug is fixed, not on a schedule.

## 1. Versioning

The whole monorepo (`api/`, `cli/`, `mcp/`, `mock-server/`) shares one
version number. The projects are developed and tested together, the CLI and
the MCP server depend on the SDK from the same checkout, and a single number
is the only one a user can report unambiguously.

Versions follow [Semantic Versioning](https://semver.org/) `MAJOR.MINOR.PATCH`.
While the major version is `0`, the API is not considered stable and `MINOR`
may include breaking changes. As a working rule:

| Bump    | When                                                                            |
| ------- | ------------------------------------------------------------------------------- |
| `PATCH` | Bug fixes, translation fixes, documentation-only changes worth pointing at      |
| `MINOR` | New commands, options, MCP tools, models or fields; behaviour changes           |
| `MAJOR` | Reserved for a first stable release, or for incompatible changes after that     |

The version string is written in seven files. They must always be identical:

| File                                  | Line                              |
| ------------------------------------- | --------------------------------- |
| `pyproject.toml`                      | `version = "X.Y.Z"`               |
| `api/pyproject.toml`                  | `version = "X.Y.Z"`               |
| `cli/pyproject.toml`                  | `version = "X.Y.Z"`               |
| `mcp/pyproject.toml`                  | `version = "X.Y.Z"`               |
| `api/src/cadastral_api/__init__.py`   | `__version__ = "X.Y.Z"`           |
| `cli/src/cadastral_cli/__init__.py`   | `__version__ = "X.Y.Z"`           |
| `mcp/src/cadastral_mcp/config.py`     | `server_version: str = "X.Y.Z"`   |

Do not edit these by hand; `scripts/release.py` rewrites all of them, and the
gate in section 5 fails when they disagree. `cadastral --version`,
`cadastral info` and `cadastral-mcp --version` all print this number.

## 2. Tags

Every release is an annotated git tag named `vX.Y.Z` (lower-case `v`, no
other prefix or suffix) on the `main` branch. The tag message is the
release's CHANGELOG section, so `git tag -n99 vX.Y.Z` or `git show vX.Y.Z`
shows what the release contains without opening any file.

Tags are immutable. A mistake in a released version is fixed by a new
`PATCH` release, never by moving or deleting the tag.

Between releases the version string in the repository is the version of the
last release. `main` at any commit after `vX.Y.Z` therefore reports `X.Y.Z`
even though it contains more than the tag. This is deliberate: it keeps
release commits to a single, mechanical change and avoids guessing the next
number in advance.

## 3. Changelog

`CHANGELOG.md` at the repository root follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). It has one section
per release, newest first, plus an `[Unreleased]` section at the top.

Every change that a user of the SDK, CLI or MCP server could notice is added
under `[Unreleased]` in the same commit or pull request that makes it, under
one of the standard headings `Added`, `Changed`, `Deprecated`, `Removed`,
`Fixed`, `Security`. Internal refactoring, linting and test-only changes are
not listed unless they change behaviour.

Entries are written for the user, not the developer: name the command,
option, tool or model that changed and what is different, not the file. One
bullet per change, present tense, no commit hashes.

When a release is cut the script renames `[Unreleased]` to
`[X.Y.Z] - YYYY-MM-DD`, inserts a fresh empty `[Unreleased]` above it and
updates the comparison links at the bottom of the file.

## 4. Cutting a release

Preconditions, all checked by the script:

- The current branch is `main` (override with `--allow-branch` only for a
  hotfix branch that will be merged back).
- The working tree is clean and `main` is up to date with `origin/main`
  (the script checks cleanliness; pull first).
- The new version is greater than the current one and the tag does not exist.
- `[Unreleased]` in `CHANGELOG.md` is not empty, or a `[X.Y.Z]` section
  already exists.
- All test suites and gates pass (`pytest` from the repository root), including
  the API coverage gate `api/src/cadastral_api/tests/test_api_coverage.py`
  (every key of the redacted fixtures is a declared field, no `source_fields`).

Steps:

```bash
git checkout main && git pull
pytest -q --no-cov                     # everything green, including the gates
scripts/release.py 0.2.0 --dry-run     # review what will change
scripts/release.py 0.2.0               # bump, finalize CHANGELOG, commit, tag
git show v0.2.0                        # review the release commit and tag message
git push origin main v0.2.0            # publish
```

The script makes one commit, `Release vX.Y.Z`, that touches only
`CHANGELOG.md` and the seven version files, and one annotated tag pointing at
it. It never pushes.

Pushing the tag triggers `.github/workflows/release.yml`, which creates a
GitHub Release named `vX.Y.Z` whose body is the CHANGELOG section (obtained
with `scripts/release.py --notes X.Y.Z`). The GitHub Release is a convenience
view of the tag; the tag and the changelog are the source of truth.

## 5. Gate

`cli/tests/test_release_consistency.py` runs with the other gates on every
push and pull request. It fails when:

1. the seven version strings are not the same `X.Y.Z`;
2. `CHANGELOG.md` has no dated, non-empty section for that version;
3. `CHANGELOG.md` has lost its `[Unreleased]` heading;
4. a tag `vX.Y.Z` exists for the current version but the `[X.Y.Z]` section
   has been edited since the tag was created (new work goes under
   `[Unreleased]`, then a new version is cut).

`scripts/release.py --check` performs rules 1 and 2 from the command line.

## 6. The first tag

Release tagging was introduced at version `0.1.0`, the number the projects
had carried since the initial commit. The `[0.1.0]` section of the changelog
summarises everything up to that point. The tag is created by hand once,
because the version strings already say `0.1.0` and the script only cuts a
greater version:

```bash
git tag -a v0.1.0 -m "Release v0.1.0" -m "$(scripts/release.py --notes 0.1.0)"
git push origin v0.1.0
```

Subsequent releases use `scripts/release.py` as described in section 4.
