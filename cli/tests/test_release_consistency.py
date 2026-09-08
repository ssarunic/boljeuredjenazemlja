"""Release consistency gate.

Fails when the release metadata drifts. The rules are in
specs/release-process.md:

1. Every version string in the monorepo (four ``pyproject.toml`` files, two
   ``__version__`` constants, the MCP ``server_version``) is the same X.Y.Z.
2. CHANGELOG.md has a non-empty, dated section for that version, so a tag is
   never cut for a version nobody described.
3. CHANGELOG.md keeps its ``[Unreleased]`` heading, which is where the next
   release is described.
4. If the tag ``v<version>`` already exists locally, ``[Unreleased]`` must be
   the only place new work is described: a release version cannot be reused
   for further changes.

Run:
    cd cli && pytest tests/test_release_consistency.py
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RELEASE_SCRIPT = REPO_ROOT / "scripts" / "release.py"


@pytest.fixture(scope="module")
def release() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release", RELEASE_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_version_strings_agree(release: ModuleType) -> None:
    versions = release.read_versions()
    assert len(versions) == len(release.VERSION_FILES)
    distinct = sorted(set(versions.values()))
    assert len(distinct) == 1, "version strings disagree:\n" + "\n".join(
        f"  {v:10}  {rel}" for rel, v in versions.items()
    )
    assert release.SEMVER.match(distinct[0]), f"{distinct[0]!r} is not X.Y.Z"


def test_changelog_documents_current_version(release: ModuleType) -> None:
    version = release.current_version()
    text = release.CHANGELOG.read_text(encoding="utf-8")
    assert release.UNRELEASED_HEADING in text, "CHANGELOG.md lost its [Unreleased] section"
    headings = [m.group("v") for m in release.RELEASE_HEADING.finditer(text)]
    assert version in headings, (
        f"CHANGELOG.md has no '## [{version}] - YYYY-MM-DD' section; found {headings or 'none'}"
    )
    assert release.release_notes(version), f"CHANGELOG.md: section [{version}] is empty"


def test_release_check_command_passes() -> None:
    result = subprocess.run(
        ["python3", str(RELEASE_SCRIPT), "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_tagged_version_is_not_reused_for_new_work(release: ModuleType) -> None:
    """Once v<version> exists, further changes belong under [Unreleased]."""
    version = release.current_version()
    tag = f"v{version}"
    try:
        tags = release.git("tag", "-l", tag)
    except release.ReleaseError:
        pytest.skip("not inside a git checkout")
    if not tags:
        pytest.skip(f"tag {tag} not created yet")
    tagged = release.git("show", f"{tag}:CHANGELOG.md")
    current = release.CHANGELOG.read_text(encoding="utf-8")
    tagged_notes = release.changelog_sections(tagged)
    current_notes = release.changelog_sections(current)
    key = next(k for k in current_notes if k.startswith(f"[{version}]"))
    assert current_notes[key] == tagged_notes.get(key), (
        f"CHANGELOG.md section [{version}] changed after {tag} was created; "
        "describe new work under [Unreleased] and cut a new version"
    )
