"""Specifications index gate.

Fails when specs/README.md and the specs/ directory drift apart. The rule is
in specs/README.md: every specification gets a row in the index table in the
same commit. Two checks, nothing about status values or keywords, which are
judgement and not something a test can verify:

1. Every ``specs/*.md`` and ``specs/*.py`` except the README itself is linked
   from a row of the index table.
2. Every link in the index table points to a file that exists.

Run:
    cd cli && pytest tests/test_specs_index.py
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SPECS_DIR = REPO_ROOT / "specs"
INDEX = SPECS_DIR / "README.md"

_ROW_LINK = re.compile(r"^\| \[([^\]]+)\]\(([^)]+)\) \|", re.MULTILINE)


def _indexed_targets() -> list[str]:
    return [target for _, target in _ROW_LINK.findall(INDEX.read_text(encoding="utf-8"))]


def _spec_files() -> list[str]:
    return sorted(
        path.name
        for path in SPECS_DIR.iterdir()
        if path.is_file() and path.suffix in {".md", ".py"} and path.name != INDEX.name
    )


def test_every_spec_is_in_the_index() -> None:
    missing = [name for name in _spec_files() if name not in _indexed_targets()]
    assert not missing, (
        "Documents in specs/ without a row in specs/README.md "
        "(add one to the index table):\n" + "\n".join(missing)
    )


def test_every_index_row_points_to_a_file() -> None:
    dangling = [target for target in _indexed_targets() if not (SPECS_DIR / target).is_file()]
    assert not dangling, (
        "Rows of specs/README.md that link to a file that does not exist:\n" + "\n".join(dangling)
    )
