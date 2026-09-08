"""Terminology gate.

Enforces the "Do not write" table of specs/terminology.md: legal and
cadastral terms that reviewers have rejected must not come back, neither in
what the CLI prints (po/hr.po) nor in the documentation (po/docs-hr.po,
docs/hr/cli/, docs/en/cli/, the Croatian text of scripts/build_docs.py).

Run:
    cd cli && pytest tests/test_terminology.py
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import polib
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SPEC = REPO_ROOT / "specs" / "terminology.md"
CLI_CATALOG = REPO_ROOT / "po" / "hr.po"
DOCS_CATALOG = REPO_ROOT / "po" / "docs-hr.po"
DOCS_HR = REPO_ROOT / "docs" / "hr" / "cli"
DOCS_EN = REPO_ROOT / "docs" / "en" / "cli"
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_docs.py"

ROW_RE = re.compile(
    r"^\|\s*`(?P<pattern>.+?)`\s*\|\s*(?P<fix>.+?)\s*\|\s*(?P<scope>hr|en)\s*\|\s*$"
)


@dataclass(frozen=True)
class Rule:
    pattern: re.Pattern[str]
    fix: str
    scope: str


def load_rules() -> list[Rule]:
    rules: list[Rule] = []
    in_table = False
    for line in SPEC.read_text(encoding="utf-8").splitlines():
        if line.startswith("## 4."):
            in_table = True
            continue
        if in_table and line.startswith("## "):
            break
        match = ROW_RE.match(line) if in_table else None
        if match:
            rules.append(
                Rule(re.compile(match.group("pattern")), match.group("fix"), match.group("scope"))
            )
    assert rules, f"no rules found in {SPEC}"
    return rules


def catalog_strings(path: Path, side: str) -> list[tuple[str, str]]:
    """(location, text) pairs: translations for 'hr', source strings for 'en'."""
    po = polib.pofile(str(path))
    out: list[tuple[str, str]] = []
    for entry in po:
        if entry.obsolete:
            continue
        where = f"{path.relative_to(REPO_ROOT)}:{entry.linenum}"
        if side == "hr":
            texts = [entry.msgstr, *entry.msgstr_plural.values()]
        else:
            texts = [entry.msgid, entry.msgid_plural]
        out.extend((where, t) for t in texts if t)
    return out


def file_lines(root: Path) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    paths = [root] if root.is_file() else sorted(root.rglob("*.md"))
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            out.append((f"{path.relative_to(REPO_ROOT)}:{number}", line))
    return out


def corpus(scope: str) -> list[tuple[str, str]]:
    if scope == "hr":
        return (
            catalog_strings(CLI_CATALOG, "hr")
            + (catalog_strings(DOCS_CATALOG, "hr") if DOCS_CATALOG.exists() else [])
            + file_lines(DOCS_HR)
            + file_lines(BUILD_SCRIPT)
        )
    return catalog_strings(CLI_CATALOG, "en") + file_lines(DOCS_EN)


@pytest.mark.parametrize("rule", load_rules(), ids=lambda r: r.pattern.pattern)
def test_rejected_term_does_not_come_back(rule: Rule) -> None:
    hits = [
        f"{where}: {text.strip()[:100]}"
        for where, text in corpus(rule.scope)
        if rule.pattern.search(text)
    ]
    assert not hits, (
        f"'{rule.pattern.pattern}' is a rejected term; write '{rule.fix}' instead "
        f"(see specs/terminology.md):\n" + "\n".join(hits)
    )
