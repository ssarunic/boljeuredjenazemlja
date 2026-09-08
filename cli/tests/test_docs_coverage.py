"""Documentation coverage gate.

Fails when the CLI user documentation drifts away from the CLI, in either
language. The rules are in specs/documentation-guide.md, section 6:

1. Every leaf command has a page under docs/en/cli/commands/ and every page
   there belongs to an existing command.
2. Generated regions (and the whole Croatian tree) match what
   scripts/build_docs.py would produce now, including captured output.
3. Every ``cadastral ...`` example in a ``bash`` block parses against the
   real click command tree, in both editions.
4. po/docs-hr.po has no untranslated or fuzzy entry, and matches the
   paragraphs of the English pages (no missing, no stale live entries).
5. (folded into 2) docs/hr/cli/ is exactly the rendering of the catalog.
6. Every relative link points to an existing file and heading.
7. Command pages carry the fixed headings; the Croatian counterpart has the
   same number of headings, paragraphs and code blocks.
8. Bold text in prose quotes something the CLI of that language really prints
   (a catalog string, or text captured on the same page), so a Croatian page
   cannot describe a label the Croatian CLI does not show.

Also: no ``TODO`` placeholder remains on any page.

Run:
    cd cli && pytest tests/test_docs_coverage.py
"""

from __future__ import annotations

import importlib.util
import re
import shlex
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

import click
import polib
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BUILD_SCRIPT = REPO_ROOT / "scripts" / "build_docs.py"

_spec = importlib.util.spec_from_file_location("build_docs", BUILD_SCRIPT)
assert _spec is not None and _spec.loader is not None
build_docs = importlib.util.module_from_spec(_spec)
sys.modules["build_docs"] = build_docs  # dataclasses need the module registered
_spec.loader.exec_module(build_docs)

EN = build_docs.TREES["en"]
LANGS = list(build_docs.TREES)
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
PLACEHOLDER_RE = re.compile(r"\{[^}]*\}")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def build_result() -> dict:
    """One dry-run build for the whole module (starts the mock server once)."""
    return build_docs.build(capture_output=True, write=False)


@pytest.fixture(scope="module")
def pages() -> dict[str, dict[str, str]]:
    """Committed pages per language, keyed by path relative to the tree."""
    result: dict[str, dict[str, str]] = {}
    for lang, root in build_docs.TREES.items():
        result[lang] = {}
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.md")):
            rel = path.relative_to(root).as_posix()
            if rel.startswith(build_docs.EXAMPLES_DIR_NAME + "/"):
                continue
            result[lang][rel] = path.read_text(encoding="utf-8")
    return result


@lru_cache(maxsize=None)
def cli_catalog(lang: str) -> list[str]:
    """Strings the CLI prints under ``lang``: msgids for English, msgstrs otherwise."""
    po = polib.pofile(str(build_docs.CLI_CATALOG["hr"]))
    strings: list[str] = []
    for entry in po:
        if entry.obsolete:
            continue
        if lang == "en":
            strings.append(entry.msgid)
            if entry.msgid_plural:
                strings.append(entry.msgid_plural)
        else:
            if entry.msgstr:
                strings.append(entry.msgstr)
            strings.extend(v for v in entry.msgstr_plural.values() if v)
    return strings


@lru_cache(maxsize=None)
def catalog_patterns(lang: str) -> list[re.Pattern[str]]:
    patterns = []
    for text in cli_catalog(lang):
        for line in text.splitlines():
            line = " ".join(line.split())
            if not line:
                continue
            escaped = re.escape(line)
            escaped = re.sub(r"\\\{[^}]*\\\}", ".+?", escaped)
            escaped = escaped.replace(r"\ ", r"\s+")
            patterns.append(re.compile(rf"^{escaped}:?$", re.IGNORECASE))
    return patterns


# ---------------------------------------------------------------------------
# 1. Pages <-> commands
# ---------------------------------------------------------------------------


def test_every_command_has_a_page_and_every_page_a_command(build_result: dict) -> None:
    tree = build_result["trees"]["en"]
    expected = {c["slug"] for c in build_docs.leaf_commands(tree)}
    commands_dir = EN / build_docs.COMMANDS_DIR_NAME
    actual = {p.stem for p in commands_dir.glob("*.md")}
    assert expected - actual == set(), f"commands without a page: {sorted(expected - actual)}"
    assert actual - expected == set(), f"pages without a command: {sorted(actual - expected)}"


# ---------------------------------------------------------------------------
# 2 + 5. Generated regions and the Croatian tree are fresh
# ---------------------------------------------------------------------------


def test_generated_content_is_fresh(build_result: dict) -> None:
    stale = build_docs.stale_files(build_result)
    assert not stale, "run: python scripts/build_docs.py\n" + "\n".join(stale)


# ---------------------------------------------------------------------------
# 3. Every example parses
# ---------------------------------------------------------------------------


def _examples(text: str) -> list[tuple[int, str]]:
    found: list[tuple[int, str]] = []
    for block in build_docs.parse_blocks(text):
        if block.kind != "code":
            continue
        fence = block.lines[0].strip()
        if not fence.startswith(("```bash", "```sh", "```shell", "```console")):
            continue
        pending = ""
        for offset, line in enumerate(block.lines[1:-1]):
            stripped = line.strip()
            if stripped.startswith("$ "):
                stripped = stripped[2:]
            if pending:
                stripped = pending + " " + stripped
                pending = ""
            if stripped.endswith("\\"):
                pending = stripped[:-1].strip()
                continue
            if stripped.startswith(tuple(f"{p} " for p in build_docs.PROGRAM_NAMES)):
                found.append((block.lineno + 1 + offset, stripped))
    return found


def _parse_with_click(words: list[str]) -> None:
    from cadastral_cli.main import cli

    ctx = cli.make_context("cadastral", list(words), resilient_parsing=False)
    command: click.Command = cli
    while isinstance(command, click.Group):
        rest = list(
            getattr(ctx, "_protected_args", None) or getattr(ctx, "protected_args", [])
        ) + list(ctx.args)
        if not rest:
            if command.invoke_without_command:
                return
            raise click.UsageError("missing command", ctx)
        name, sub, sub_args = command.resolve_command(ctx, rest)
        assert sub is not None and name is not None
        ctx = sub.make_context(name, sub_args, parent=ctx)
        command = sub


def test_every_example_parses(
    pages: dict[str, dict[str, str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    # Path options with exists=True are resolved against the example files.
    monkeypatch.chdir(EN / build_docs.EXAMPLES_DIR_NAME)
    failures: list[str] = []
    for lang, tree in pages.items():
        for rel, text in tree.items():
            for lineno, cmdline in _examples(text):
                try:
                    words = shlex.split(cmdline)[1:]
                    _parse_with_click(words)
                except click.exceptions.Exit:
                    continue  # --help / --version
                except (click.ClickException, SystemExit) as exc:
                    failures.append(f"{lang}/{rel}:{lineno}: {cmdline}\n    {exc}")
                except ValueError as exc:  # shlex
                    failures.append(f"{lang}/{rel}:{lineno}: {cmdline}\n    {exc}")
    assert not failures, "examples the CLI rejects:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# 4. Croatian catalog complete and in sync with the English pages
# ---------------------------------------------------------------------------


def test_docs_catalog_is_complete_and_in_sync(build_result: dict) -> None:
    pot_ids = {e.msgid for e in build_result["pot"]}
    for lang, po_path in build_docs.PO_PATHS.items():
        assert po_path.exists(), f"{po_path} missing: run python scripts/build_docs.py"
        po = polib.pofile(str(po_path))
        live = [e for e in po if not e.obsolete]
        live_ids = {e.msgid for e in live}
        missing = sorted(pot_ids - live_ids)
        stale = sorted(live_ids - pot_ids)
        untranslated = [e.msgid for e in live if not e.msgstr]
        fuzzy = [e.msgid for e in live if "fuzzy" in e.flags]
        problems = []
        if missing:
            problems.append(
                f"{len(missing)} paragraph(s) not in catalog (run the build): " + _preview(missing)
            )
        if stale:
            problems.append(
                f"{len(stale)} stale live entr(y/ies) (run the build): " + _preview(stale)
            )
        if untranslated:
            problems.append(f"{len(untranslated)} untranslated: " + _preview(untranslated))
        if fuzzy:
            problems.append(f"{len(fuzzy)} fuzzy: " + _preview(fuzzy))
        assert not problems, f"{po_path.relative_to(REPO_ROOT)}:\n" + "\n".join(problems)


def _preview(items: list[str], limit: int = 5) -> str:
    shown = [f"\n    - {i[:90]}" for i in items[:limit]]
    if len(items) > limit:
        shown.append(f"\n    ... {len(items) - limit} more")
    return "".join(shown)


# ---------------------------------------------------------------------------
# 6. Links resolve
# ---------------------------------------------------------------------------


def _slug(heading: str) -> str:
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


@lru_cache(maxsize=None)
def _headings(path: Path) -> set[str]:
    slugs: set[str] = set()
    for block in build_docs.parse_blocks(path.read_text(encoding="utf-8")):
        if block.kind == "heading" and block.text:
            slugs.add(_slug(block.text))
        if block.kind == "generated":
            for line in block.lines:
                match = build_docs.HEADING_RE.match(line.strip())
                if match:
                    slugs.add(_slug(match.group(2)))
    return slugs


def test_links_resolve(pages: dict[str, dict[str, str]]) -> None:
    failures: list[str] = []
    for lang, tree in pages.items():
        root = build_docs.TREES[lang]
        for rel, text in tree.items():
            for match in LINK_RE.finditer(text):
                target = match.group(1)
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                path_part, _, anchor = target.partition("#")
                target_path = (root / rel).parent / path_part if path_part else root / rel
                target_path = target_path.resolve()
                if not target_path.exists():
                    failures.append(f"{lang}/{rel}: {target} (file not found)")
                    continue
                if anchor and target_path.suffix == ".md" and anchor not in _headings(target_path):
                    failures.append(f"{lang}/{rel}: {target} (no such heading)")
    assert not failures, "broken links:\n" + "\n".join(failures)


# ---------------------------------------------------------------------------
# 7. Page structure
# ---------------------------------------------------------------------------


def _structure(text: str) -> tuple[int, int, int]:
    blocks = build_docs.parse_blocks(text)
    headings = sum(1 for b in blocks if b.kind == "heading")
    prose = sum(1 for b in blocks if b.kind in ("para", "item", "quote"))
    code = sum(1 for b in blocks if b.kind == "code")
    return headings, prose, code


def test_command_pages_have_the_fixed_headings(pages: dict[str, dict[str, str]]) -> None:
    failures: list[str] = []
    for rel, text in pages["en"].items():
        if not rel.startswith(build_docs.COMMANDS_DIR_NAME + "/"):
            continue
        headings = [
            b.text for b in build_docs.parse_blocks(text) if b.kind == "heading" and b.level == 2
        ]
        missing = [h for h in build_docs.REQUIRED_COMMAND_HEADINGS if h not in headings]
        if missing:
            failures.append(f"{rel}: missing {missing}")
        if not build_docs.page_title(text):
            failures.append(f"{rel}: no level-1 title")
    assert not failures, "\n".join(failures)


def test_translated_pages_mirror_the_source_structure(pages: dict[str, dict[str, str]]) -> None:
    failures: list[str] = []
    for lang in LANGS:
        if lang == "en":
            continue
        for rel, text in pages["en"].items():
            other = pages[lang].get(rel)
            if other is None:
                failures.append(f"{lang}/{rel}: missing")
                continue
            if _structure(text) != _structure(other):
                failures.append(
                    f"{lang}/{rel}: headings/paragraphs/code blocks {_structure(other)} != en {_structure(text)}"  # noqa: E501
                )
    assert not failures, "\n".join(failures)


# ---------------------------------------------------------------------------
# 8. Bold text quotes what the CLI prints
# ---------------------------------------------------------------------------


def _captured_text(text: str) -> str:
    parts = []
    for block in build_docs.parse_blocks(text):
        if block.kind == "generated" and block.region and block.region[0] == "output":
            parts.append("\n".join(line.strip() for line in block.lines))
    return "\n".join(parts)


def _printed_by_cli(label: str, lang: str, captured: str) -> bool:
    label = " ".join(label.split()).rstrip(":")
    if label and label in captured:
        return True
    return any(p.match(label) for p in catalog_patterns(lang))


def test_bold_text_is_screen_text(pages: dict[str, dict[str, str]]) -> None:
    failures: list[str] = []
    for lang, tree in pages.items():
        for rel, text in tree.items():
            captured = _captured_text(text)
            for block in build_docs.parse_blocks(text):
                if (
                    block.kind not in build_docs.PROSE_KINDS
                    or block.kind == "heading"
                    or not block.text
                ):
                    continue
                for match in BOLD_RE.finditer(block.text):
                    label = match.group(1)
                    if not _printed_by_cli(label, lang, captured):
                        failures.append(
                            f"{lang}/{rel}:{block.lineno}: **{label}** is not something the {lang} CLI prints"  # noqa: E501
                        )
    assert not failures, "\n".join(failures)


# ---------------------------------------------------------------------------
# No placeholders left behind
# ---------------------------------------------------------------------------


def test_no_todo_placeholders(pages: dict[str, dict[str, str]]) -> None:
    left = [
        f"{lang}/{rel}"
        for lang, tree in pages.items()
        for rel, text in tree.items()
        if "TODO" in text
    ]
    assert not left, "pages with TODO placeholders: " + ", ".join(left)
