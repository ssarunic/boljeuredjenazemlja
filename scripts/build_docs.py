#!/usr/bin/env python3
"""Build the CLI user documentation (docs/en/cli and docs/hr/cli).

This implements section 5 of specs/documentation-guide.md:

1. Generated regions in the English pages are rewritten from the click
   command tree and the gettext catalog (banner, options, synopsis,
   reference index, errors table).
2. ``output`` regions are filled by running the command against the mock
   server, from a clean home directory seeded with the geometry fixture.
3. Authored paragraphs are extracted into po/docs.pot and merged into
   po/docs-hr.po (block-level extractor built on polib; no gettext binaries).
4. The Croatian tree is rendered by applying po/docs-hr.po to the English
   pages and re-rendering every generated region under ``--lang hr``.
5. Untranslated and fuzzy counts are printed.

Usage:
    python scripts/build_docs.py              full build
    python scripts/build_docs.py --no-output  keep output regions as they are
    python scripts/build_docs.py --check      report stale files, exit 1 if any

The gate (cli/tests/test_docs_coverage.py) imports this module and compares
what a build would produce with what is committed.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

import polib

REPO = Path(__file__).resolve().parents[1]
DOCS_DIR = REPO / "docs"
TREES = {"en": DOCS_DIR / "en" / "cli", "hr": DOCS_DIR / "hr" / "cli"}
SOURCE_LANG = "en"
TARGET_LANGS = ("hr",)
EN = TREES["en"]
EXAMPLES_DIR_NAME = "examples"
COMMANDS_DIR_NAME = "commands"
PO_DIR = REPO / "po"
POT_PATH = PO_DIR / "docs.pot"
PO_PATHS = {"hr": PO_DIR / "docs-hr.po"}
CLI_CATALOG = {"hr": PO_DIR / "hr.po"}
MOCK_SRC = REPO / "mock-server" / "src"
GEOMETRY_FIXTURES = REPO / "mock-server" / "data" / "geometry"
PROGRAM_NAMES = ("cadastral", "uz")
CANONICAL_BASE_URL = "http://localhost:8000"
CANONICAL_HOME = "~"
TERMINAL_COLUMNS = "100"
WRAP_WIDTH = 80
FIXTURE_MTIME = 1767225600  # 2026-01-01 00:00 UTC, keeps "Last Modified" stable

BEGIN_RE = re.compile(
    r"^(?P<indent>[ \t]*)<!-- BEGIN GENERATED: (?P<kind>[a-z-]+)(?: (?P<args>.*?))? -->[ \t]*$"
)
END_RE = re.compile(r"^[ \t]*<!-- END GENERATED: (?P<kind>[a-z-]+) -->[ \t]*$")
FENCE_RE = re.compile(r"^([ \t]*)(```|~~~)")
HEADING_RE = re.compile(r"^(#{1,6}) (.+?)\s*#*\s*$")
ITEM_RE = re.compile(r"^([ \t]*)([-*+]|\d+[.)]) (.*)$")
QUOTE_RE = re.compile(r"^[ \t]*> ?(.*)$")
TABLE_SEP_RE = re.compile(r"^\|?[\s:\-|]+\|?$")
SUMMARY_RE = re.compile(r"^([ \t]*)<summary>(.*?)</summary>[ \t]*$")
SPINNER_RE = re.compile("[\u2800-\u28ff]")
TRANSLATABLE_RE = re.compile(r"[A-Za-zÀ-ž]{2,}")

# Text the build writes itself (banner, table headings). Everything the CLI
# prints comes from the CLI catalog instead, never from here.
STRINGS = {
    "en": {
        "lang_name": "English",
        "disclaimer": (
            "**Practice data only.** This tool is a demonstration. It works with the "
            "practice server that comes with it and must not be connected to the official "
            "Croatian cadastre or land registry. Nothing shown on this page is real property data."
        ),
        "generated": (
            "Generated from `cadastral {version}` by `scripts/build_docs.py`. Text "
            "between the generated markers is rewritten on every build."
        ),
        "translated": (
            "This page is rendered from the English source and `po/docs-hr.po`. Do not "
            "edit it by hand."
        ),
        "col_type": "Type this",
        "col_what": "What it does",
        "col_default": "If you leave it out",
        "required": "Required",
        "flag_off": "Not switched on",
        "not_used": "Not used",
        "default_is": "`{value}` is used",
        "argument": "A value you type right after the command name, without a name in front of it",
        "argument_optional": "Optional. A value you type right after the command name",
        "no_options": "This command has no choices. Type it as it is.",
        "help_intro": "This is what `{command} --help` prints:",
        "index_intro": (
            "Every command, with a link to its page. The command is what you type; the "
            "link is what it is for."
        ),
        "group_other": "Other",
        "errors_col_message": "What the tool prints",
        "errors_col_kind": "Kind of problem",
        "errors_intro": "Every error starts with this mark and one of the messages below:",
        "subcommands_intro": "Type one of these after `cadastral {name}`:",
    },
    "hr": {
        "lang_name": "Hrvatski",
        "disclaimer": (
            "**Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim "
            "poslužiteljem koji dolazi uz njega i ne smije se spajati na službeni katastar ni "
            "zemljišne knjige Republike Hrvatske. Ništa na ovoj stranici nisu stvarni podaci "
            "o nekretninama."
        ),
        "generated": (
            "Izrađeno iz `cadastral {version}` skriptom `scripts/build_docs.py`. Tekst "
            "između generiranih oznaka ponovno se ispisuje pri svakoj izradi."
        ),
        "translated": (
            "Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. "
            "Ne uređujte je ručno."
        ),
        "col_type": "Upišite",
        "col_what": "Što radi",
        "col_default": "Ako izostavite",
        "required": "Obavezno",
        "flag_off": "Nije uključeno",
        "not_used": "Ne koristi se",
        "default_is": "Koristi se `{value}`",
        "argument": "Vrijednost koju upisujete odmah iza naziva naredbe, bez naziva ispred nje",
        "argument_optional": "Neobavezno. Vrijednost koju upisujete odmah iza naziva naredbe",
        "no_options": "Ova naredba nema izbora. Upišite je kako jest.",
        "help_intro": "Ovo ispisuje `{command} --help`:",
        "index_intro": (
            "Sve naredbe, s poveznicom na stranicu svake od njih. Naredba je ono što "
            "upisujete; poveznica govori čemu služi."
        ),
        "group_other": "Ostalo",
        "errors_col_message": "Što alat ispisuje",
        "errors_col_kind": "Vrsta problema",
        "errors_intro": "Svaka greška počinje ovom oznakom i jednom od poruka u nastavku:",
        "subcommands_intro": "Iza `cadastral {name}` upišite jedno od ovoga:",
    },
}

# Reference index groups: (group name per language, command slugs in order).
INDEX_GROUPS: list[tuple[dict[str, str], list[str]]] = [
    (
        {"en": "Look up one parcel", "hr": "Pretraga jedne čestice"},
        ["search", "get-parcel", "get-lr-unit"],
    ),
    (
        {"en": "Look up many parcels at once", "hr": "Pretraga više čestica odjednom"},
        ["batch-fetch", "batch-lr-unit"],
    ),
    (
        {"en": "Find municipalities and offices", "hr": "Pronalaženje općina i ureda"},
        ["search-municipality", "list-municipalities", "list-offices"],
    ),
    ({"en": "Boundaries and maps", "hr": "Granice i karte"}, ["get-geometry", "download-gis"]),
    (
        {"en": "Check the tool itself", "hr": "Provjera samog alata"},
        ["info", "cache-list", "cache-info", "cache-clear"],
    ),
]

COMMAND_PAGE_TEMPLATE = """<!-- BEGIN GENERATED: banner -->
<!-- END GENERATED: banner -->

# TODO: what this command lets the reader find out

TODO: one or two sentences, in the reader's words.

## When you would use this

- TODO: a concrete situation from legal practice.

## Before you start

TODO: what the reader needs in hand and where they usually find it.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   {example}
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output {example} -->
   <!-- END GENERATED: output -->

4. TODO: how to read what is on the screen.

## Choices you can make

TODO: plain-language explanation of the choices that matter to this reader.

<!-- BEGIN GENERATED: options -->
<!-- END GENERATED: options -->

## If something goes wrong

TODO: quote a message the tool prints and say what to do.

## Related pages

- TODO: link to the command the reader is likely to need next.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
<!-- END GENERATED: synopsis -->

</details>
"""

REQUIRED_COMMAND_HEADINGS = [
    "When you would use this",
    "Before you start",
    "Step by step",
    "Choices you can make",
    "If something goes wrong",
    "Related pages",
]


# ---------------------------------------------------------------------------
# Command tree (one subprocess per language, because help strings are
# evaluated when the command modules are imported)
# ---------------------------------------------------------------------------


def _dump_tree(lang: str) -> dict:
    """Run inside a subprocess: import the CLI under ``lang`` and describe it."""
    os.environ["CADASTRAL_LANG"] = lang
    import click
    from cadastral_api.i18n import set_language

    set_language(lang)
    from cadastral_api.exceptions import ErrorType
    from cadastral_cli import __version__, localized
    from cadastral_cli.formatters import error_type_label
    from cadastral_cli.main import cli

    program = localized.program_name()

    commands: list[dict] = []

    def describe_param(param: click.Parameter, ctx: click.Context) -> dict:
        record = param.get_help_record(ctx) if isinstance(param, click.Option) else None
        opts, secondary = list(param.opts), list(param.secondary_opts)
        if isinstance(param, localized.LocalizedOption):
            opts = param._display(param._canonical_opts)
            secondary = param._display(param._canonical_secondary_opts)
        default = param.default
        if callable(default) or not isinstance(default, (str, int, float, bool)):
            default = None  # click's UNSET sentinel, None, or a computed default
        choices = list(param.type.choices) if isinstance(param.type, click.Choice) else None
        return {
            "kind": "option" if isinstance(param, click.Option) else "argument",
            "name": param.name,
            "opts": opts,
            "secondary_opts": secondary,
            "metavar": param.make_metavar(ctx),
            "type": param.type.name,
            "choices": choices,
            "choices_display": (
                [param.type.display(c) for c in choices]
                if choices and isinstance(param.type, localized.LocalizedChoice)
                else choices
            ),
            "default": default,
            "required": bool(param.required),
            "is_flag": bool(getattr(param, "is_flag", False)),
            "help": getattr(param, "help", None),
            "help_record": list(record) if record else None,
        }

    def walk(cmd: click.Command, path: list[str], parent: click.Context | None) -> None:
        info_name = localized.display_name(" ".join(path)) if path else program
        ctx = click.Context(
            cmd, info_name=info_name, parent=parent, terminal_width=80, max_content_width=80
        )
        is_group = isinstance(cmd, click.Group)
        first_paragraph = (cmd.help or "").strip().split("\n\n", 1)[0]
        display_path = localized.active_spelling("command", " ".join(path)) if path else ""
        entry = {
            "path": path,
            "name": " ".join(path),
            "display_path": display_path,
            "slug": "-".join(path),
            "is_group": is_group,
            "short": " ".join(first_paragraph.split()),
            "usage": cmd.get_usage(ctx),
            "help_text": cmd.get_help(ctx),
            "params": [describe_param(p, ctx) for p in cmd.params],
            "subcommands": [],
        }
        if is_group:
            for name in sorted(cmd.commands):
                entry["subcommands"].append(" ".join(path + [name]))
        if path:
            commands.append(entry)
        if is_group:
            for name in sorted(cmd.commands):
                walk(cmd.commands[name], path + [name], ctx)

    walk(cli, [], None)
    errors = [
        {"type": error_type.value, "label": error_type_label(error_type)}
        for error_type in ErrorType
    ]
    return {
        "lang": lang,
        "version": __version__,
        "program": program,
        "commands": commands,
        "errors": errors,
        "error_prefix": _error_prefix(lang),
    }


def _error_prefix(lang: str) -> str:
    from cadastral_api.i18n import _

    return _("\n✗ Error: {error}").strip().split("{error}")[0].strip()


def _localize_cmdlines(lang: str, cmdlines: list[str]) -> list[str]:
    """Run inside a subprocess: rewrite command lines into ``lang`` spellings."""
    os.environ["CADASTRAL_LANG"] = lang
    from cadastral_api.i18n import set_language

    set_language(lang)
    from cadastral_cli import localized
    from cadastral_cli.main import cli

    return [localized.localize_cmdline(line, cli) for line in cmdlines]


def localize_cmdlines(lang: str, cmdlines: list[str]) -> dict[str, str]:
    """Map each documented command line to its spelling in ``lang``."""
    unique = sorted(set(cmdlines))
    if not unique:
        return {}
    env = _clean_env()
    env["CADASTRAL_LANG"] = lang
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--localize", lang],
        input=json.dumps(unique),
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return dict(zip(unique, json.loads(result.stdout)))


def load_tree(lang: str) -> dict:
    """Describe the CLI as it presents itself under ``lang``."""
    env = _clean_env()
    env["CADASTRAL_LANG"] = lang
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--dump-tree", lang],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(result.stdout)


def leaf_commands(tree: dict) -> list[dict]:
    return [c for c in tree["commands"] if not c["is_group"]]


def command_by_slug(tree: dict, slug: str) -> dict | None:
    for command in tree["commands"]:
        if command["slug"] == slug:
            return command
    return None


def _clean_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("CADASTRAL_")}
    env["PYTHONIOENCODING"] = "utf-8"
    return env


# ---------------------------------------------------------------------------
# Mock server and output capture
# ---------------------------------------------------------------------------


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class MockServer:
    """The mock API server, started on a free port for the duration of a build."""

    def __init__(self) -> None:
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}"
        self._process: subprocess.Popen | None = None

    def __enter__(self) -> MockServer:
        self._process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
                "--log-level",
                "error",
            ],
            cwd=MOCK_SRC,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.time() + 30
        while time.time() < deadline:
            if self._process.poll() is not None:
                stderr = self._process.stderr.read() if self._process.stderr else ""
                raise RuntimeError(f"mock server exited early:\n{stderr}")
            try:
                with urllib.request.urlopen(self.base_url + "/", timeout=1):
                    return self
            except (urllib.error.URLError, ConnectionError, TimeoutError):
                time.sleep(0.2)
        raise RuntimeError("mock server did not become ready in 30 seconds")

    def __exit__(self, *exc: object) -> None:
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()


def _program(name: str) -> list[str]:
    """The installed console script, so usage lines show the real program name."""
    script = Path(sys.executable).parent / name
    if script.exists():
        return [str(script)]
    return [sys.executable, "-m", "cadastral_cli"]


class OutputCapture:
    """Run documented commands in a clean, seeded home directory and record output.

    Every command starts from the same seeded state, so the captured text does
    not depend on which page was rendered before it.
    """

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        # A short path keeps printed paths on one line at the documented width.
        tmp_root = "/tmp" if Path("/tmp").is_dir() else None
        self._root = Path(tempfile.mkdtemp(prefix="cadastral-docs-", dir=tmp_root))
        self.home = self._root / "home"
        self.cwd = self._root / "work"
        self._cache: dict[tuple[str, str], str] = {}

    def _reset(self) -> None:
        for path in (self.home, self.cwd):
            shutil.rmtree(path, ignore_errors=True)
            path.mkdir(parents=True)
        cache_dir = self.home / ".cadastral_api_cache"
        for zip_path in sorted(GEOMETRY_FIXTURES.glob("*.zip")):
            code = zip_path.stem
            target_dir = cache_dir / f"ko-{code}"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = target_dir / f"ko-{code}.zip"
            shutil.copyfile(zip_path, target)
            os.utime(target, (FIXTURE_MTIME, FIXTURE_MTIME))
            os.utime(target_dir, (FIXTURE_MTIME, FIXTURE_MTIME))
        examples = EN / EXAMPLES_DIR_NAME
        if examples.is_dir():
            for path in examples.iterdir():
                if path.is_file():
                    shutil.copyfile(path, self.cwd / path.name)

    def run(self, lang: str, cmdline: str) -> str:
        key = (lang, cmdline)
        if key not in self._cache:
            self._cache[key] = self._run(lang, cmdline)
        return self._cache[key]

    def _run(self, lang: str, cmdline: str) -> str:
        words = shlex.split(cmdline)
        if not words or words[0] not in PROGRAM_NAMES:
            raise ValueError(f"output regions must run one of {PROGRAM_NAMES}, got: {cmdline}")
        self._reset()
        env = _clean_env()
        env.update(
            {
                "HOME": str(self.home),
                "CADASTRAL_API_BASE_URL": self.base_url,
                "CADASTRAL_LANG": lang,
                "COLUMNS": TERMINAL_COLUMNS,
                "LINES": "50",
                "TERM": "dumb",
                "NO_COLOR": "1",
            }
        )
        result = subprocess.run(
            [*_program(words[0]), "--lang", lang, *words[1:]],
            cwd=self.cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        text = result.stdout + result.stderr
        return self._normalize(text)

    def _normalize(self, text: str) -> str:
        text = text.replace(self.base_url, CANONICAL_BASE_URL)
        text = text.replace(str(self.home), CANONICAL_HOME)
        text = text.replace(str(self.cwd) + "/", "")
        lines = [line.rstrip() for line in text.splitlines() if not SPINNER_RE.search(line)]
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines)

    def cleanup(self) -> None:
        shutil.rmtree(self._root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Markdown blocks (translation units)
# ---------------------------------------------------------------------------


@dataclass
class Block:
    kind: str  # heading, para, item, quote, table-row, summary, code, raw, blank, generated
    lines: list[str]
    text: str | None = None  # translation unit (msgid) for prose kinds
    indent: str = ""
    prefix: str = ""
    level: int = 0
    lineno: int = 0
    region: tuple[str, str] | None = None  # (kind, args) for generated blocks


PROSE_KINDS = {"heading", "para", "item", "quote", "table-row", "summary"}


def parse_blocks(text: str) -> list[Block]:
    """Split a page into blocks. Generated regions and code fences are opaque."""
    lines = text.split("\n")
    blocks: list[Block] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        begin = BEGIN_RE.match(line)
        if begin:
            start = i
            kind = begin.group("kind")
            i += 1
            while i < n and not END_RE.match(lines[i]):
                i += 1
            if i >= n:
                raise ValueError(f"unterminated generated region '{kind}' at line {start + 1}")
            blocks.append(
                Block(
                    "generated",
                    lines[start : i + 1],
                    indent=begin.group("indent"),
                    lineno=start + 1,
                    region=(kind, begin.group("args") or ""),
                )
            )
            i += 1
            continue
        fence = FENCE_RE.match(line)
        if fence:
            start = i
            marker = fence.group(2)
            i += 1
            while i < n and not re.match(r"^[ \t]*" + re.escape(marker) + r"[ \t]*$", lines[i]):
                i += 1
            blocks.append(Block("code", lines[start : min(i, n - 1) + 1], lineno=start + 1))
            i += 1
            continue
        if not line.strip():
            blocks.append(Block("blank", [line], lineno=i + 1))
            i += 1
            continue
        summary = SUMMARY_RE.match(line)
        if summary:
            blocks.append(
                Block(
                    "summary",
                    [line],
                    text=summary.group(2).strip(),
                    indent=summary.group(1),
                    lineno=i + 1,
                )
            )
            i += 1
            continue
        if line.lstrip().startswith("<"):
            blocks.append(Block("raw", [line], lineno=i + 1))
            i += 1
            continue
        heading = HEADING_RE.match(line)
        if heading:
            blocks.append(
                Block(
                    "heading",
                    [line],
                    text=heading.group(2).strip(),
                    level=len(heading.group(1)),
                    prefix=heading.group(1) + " ",
                    lineno=i + 1,
                )
            )
            i += 1
            continue
        if line.lstrip().startswith("|"):
            if TABLE_SEP_RE.match(line.strip()):
                blocks.append(Block("raw", [line], lineno=i + 1))
            else:
                blocks.append(Block("table-row", [line], text=line.strip(), lineno=i + 1))
            i += 1
            continue
        item = ITEM_RE.match(line)
        if item:
            indent, marker, first = item.groups()
            start = i
            parts = [first.strip()]
            i += 1
            while i < n and _is_continuation(lines[i], len(indent) + len(marker) + 1):
                parts.append(lines[i].strip())
                i += 1
            blocks.append(
                Block(
                    "item",
                    lines[start:i],
                    text=" ".join(p for p in parts if p),
                    indent=indent,
                    prefix=marker + " ",
                    lineno=start + 1,
                )
            )
            continue
        quote = QUOTE_RE.match(line)
        if quote:
            start = i
            parts = []
            while i < n and QUOTE_RE.match(lines[i]) and lines[i].strip() != ">":
                parts.append(QUOTE_RE.match(lines[i]).group(1).strip())  # type: ignore[union-attr]
                i += 1
            blocks.append(
                Block(
                    "quote",
                    lines[start:i],
                    text=" ".join(parts),
                    prefix="> ",
                    lineno=start + 1,
                )
            )
            continue
        start = i
        parts = []
        while i < n and _is_plain(lines[i]):
            parts.append(lines[i].strip())
            i += 1
        indent = re.match(r"^[ \t]*", lines[start]).group(0)  # type: ignore[union-attr]
        blocks.append(
            Block(
                "para",
                lines[start:i],
                text=" ".join(parts),
                indent=indent,
                lineno=start + 1,
            )
        )
    return blocks


def _is_plain(line: str) -> bool:
    if not line.strip():
        return False
    if BEGIN_RE.match(line) or END_RE.match(line) or FENCE_RE.match(line):
        return False
    if HEADING_RE.match(line) or ITEM_RE.match(line) or QUOTE_RE.match(line):
        return False
    if line.lstrip().startswith(("<", "|")):
        return False
    return True


def _is_continuation(line: str, min_indent: int) -> bool:
    if not line.strip():
        return False
    if len(line) - len(line.lstrip(" \t")) < min_indent:
        return False
    if BEGIN_RE.match(line) or FENCE_RE.match(line) or ITEM_RE.match(line):
        return False
    return not line.lstrip().startswith("<")


def is_translatable(block: Block) -> bool:
    return (
        block.kind in PROSE_KINDS and bool(block.text) and bool(TRANSLATABLE_RE.search(block.text))
    )


def render_block(block: Block, text: str | None = None) -> list[str]:
    """Render a block, optionally with its prose replaced by ``text``."""
    if text is None or block.kind not in PROSE_KINDS:
        return list(block.lines)
    if block.kind == "heading":
        return [block.prefix + text]
    if block.kind == "summary":
        return [f"{block.indent}<summary>{text}</summary>"]
    if block.kind == "table-row":
        return [block.indent + text]
    if block.kind == "item":
        first = block.indent + block.prefix
        return textwrap.wrap(
            text,
            width=WRAP_WIDTH,
            initial_indent=first,
            subsequent_indent=" " * len(first),
            break_long_words=False,
            break_on_hyphens=False,
        ) or [first.rstrip()]
    if block.kind == "quote":
        return textwrap.wrap(
            text,
            width=WRAP_WIDTH,
            initial_indent="> ",
            subsequent_indent="> ",
            break_long_words=False,
            break_on_hyphens=False,
        ) or [">"]
    return textwrap.wrap(
        text,
        width=WRAP_WIDTH,
        initial_indent=block.indent,
        subsequent_indent=block.indent,
        break_long_words=False,
        break_on_hyphens=False,
    )


def join_blocks(blocks: list[Block], replacements: dict[int, list[str]] | None = None) -> str:
    out: list[str] = []
    for index, block in enumerate(blocks):
        if replacements and index in replacements:
            out.extend(replacements[index])
        else:
            out.extend(block.lines)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------


def source_pages() -> dict[str, str]:
    """All English pages keyed by path relative to the English tree."""
    pages: dict[str, str] = {}
    for path in sorted(EN.rglob("*.md")):
        rel = path.relative_to(EN).as_posix()
        if rel.startswith(EXAMPLES_DIR_NAME + "/"):
            continue
        pages[rel] = path.read_text(encoding="utf-8")
    return pages


def example_files() -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    examples = EN / EXAMPLES_DIR_NAME
    if examples.is_dir():
        for path in sorted(examples.iterdir()):
            if path.is_file():
                files[f"{EXAMPLES_DIR_NAME}/{path.name}"] = path.read_bytes()
    return files


def command_page_rel(slug: str) -> str:
    return f"{COMMANDS_DIR_NAME}/{slug}.md"


def page_title(text: str) -> str | None:
    for block in parse_blocks(text):
        if block.kind == "heading" and block.level == 1:
            return block.text
    return None


def ensure_command_pages(tree_en: dict) -> list[str]:
    """Create skeleton pages for commands that have none. Returns the created paths."""
    created: list[str] = []
    for command in leaf_commands(tree_en):
        path = EN / command_page_rel(command["slug"])
        if path.exists():
            continue
        example = _first_example(command) or f"cadastral {command['name']} --help"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(COMMAND_PAGE_TEMPLATE.format(example=example), encoding="utf-8")
        created.append(path.relative_to(REPO).as_posix())
    return created


def _first_example(command: dict) -> str | None:
    for line in command["help_text"].splitlines():
        stripped = line.strip()
        if stripped.startswith("cadastral "):
            return stripped
    return None


# ---------------------------------------------------------------------------
# Generated regions
# ---------------------------------------------------------------------------


@dataclass
class RenderContext:
    lang: str
    tree: dict
    titles: dict[str, str]  # page rel -> H1 title in this language
    capture: OutputCapture | None
    existing: dict[str, str] = field(default_factory=dict)  # rel -> text on disk (this lang)


def _relative_link(from_lang: str, from_rel: str, to_lang: str, to_rel: str) -> str:
    return os.path.relpath(TREES[to_lang] / to_rel, (TREES[from_lang] / from_rel).parent)


def render_region(kind: str, args: str, rel: str, ctx: RenderContext) -> list[str]:
    strings = STRINGS[ctx.lang]
    if kind == "banner":
        links = " | ".join(
            (
                f"**{STRINGS[lang]['lang_name']}**"
                if lang == ctx.lang
                else f"[{STRINGS[lang]['lang_name']}]({_relative_link(ctx.lang, rel, lang, rel)})"
            )
            for lang in TREES
        )
        lines = [
            links,
            "",
            "> " + strings["disclaimer"],
            ">",
            "> " + strings["generated"].format(version=ctx.tree["version"]),
        ]
        if ctx.lang != SOURCE_LANG:
            lines.append("> " + strings["translated"])
        return lines
    if kind == "options":
        return _render_options(rel, ctx)
    if kind == "synopsis":
        command = _page_command(rel, ctx)
        return [
            strings["help_intro"].format(
                command=f"{ctx.tree['program']} {command['display_path']}"
            ),
            "",
            "```text",
            *command["help_text"].rstrip().splitlines(),
            "```",
        ]
    if kind == "output":
        return _render_output(args, rel, ctx)
    if kind == "reference":
        return _render_reference(rel, ctx)
    if kind == "errors":
        return _render_errors(ctx)
    raise ValueError(f"{rel}: unknown generated region '{kind}'")


def _page_command(rel: str, ctx: RenderContext) -> dict:
    slug = Path(rel).stem
    command = command_by_slug(ctx.tree, slug)
    if command is None or not rel.startswith(COMMANDS_DIR_NAME + "/"):
        raise ValueError(f"{rel}: not a command page, cannot render command regions")
    return command


def _escape_cell(text: str) -> str:
    return " ".join(text.split()).replace("|", "\\|")


def _render_options(rel: str, ctx: RenderContext) -> list[str]:
    strings = STRINGS[ctx.lang]
    command = _page_command(rel, ctx)
    rows: list[tuple[str, str, str]] = []
    for param in command["params"]:
        if param["kind"] == "argument":
            what = strings["argument"] if param["required"] else strings["argument_optional"]
            rows.append(
                (
                    f"`{param['metavar']}`",
                    what,
                    strings["required"] if param["required"] else strings["not_used"],
                )
            )
            continue
        spelling = ", ".join(f"`{o}`" for o in param["opts"])
        if param["secondary_opts"]:
            spelling += " / " + ", ".join(f"`{o}`" for o in param["secondary_opts"])
        elif not param["is_flag"] and not param["choices"]:
            spelling += f" `{param['metavar']}`"
        help_text = param["help"] or ""
        if param["choices"]:
            help_text += " (" + ", ".join(f"`{c}`" for c in param["choices_display"]) + ")"
        if param["required"]:
            absent = strings["required"]
        elif param["secondary_opts"]:
            on = param["default"] is True
            absent = strings["default_is"].format(
                value=(param["opts"] if on else param["secondary_opts"])[-1]
            )
        elif param["is_flag"]:
            absent = strings["flag_off"]
        elif param["default"] not in (None, "", False):
            default = param["default"]
            if param["choices"] and default in param["choices"]:
                default = param["choices_display"][param["choices"].index(default)]
            absent = strings["default_is"].format(value=default)
        else:
            absent = strings["not_used"]
        rows.append((spelling, help_text, absent))
    if not rows:
        return [strings["no_options"]]
    lines = [
        f"| {strings['col_type']} | {strings['col_what']} | {strings['col_default']} |",
        "|---|---|---|",
    ]
    for spelling, what, absent in rows:
        lines.append(
            f"| {_escape_cell(spelling)} | {_escape_cell(what)} | {_escape_cell(absent)} |"
        )
    return lines


def _render_output(cmdline: str, rel: str, ctx: RenderContext) -> list[str]:
    if not cmdline.startswith(tuple(f"{p} " for p in PROGRAM_NAMES)):
        raise ValueError(f"{rel}: output region must start with the program name")
    if ctx.capture is not None:
        text = ctx.capture.run(ctx.lang, cmdline)
    else:
        text = _existing_region_body(ctx.existing.get(rel, ""), "output", cmdline)
        if text is None:
            text = "(output not captured: run scripts/build_docs.py without --no-output)"
    return ["```text", *text.splitlines(), "```"]


def _existing_region_body(text: str, kind: str, args: str) -> str | None:
    for block in parse_blocks(text) if text else []:
        if block.kind == "generated" and block.region == (kind, args):
            body = [_dedent_line(line, block.indent) for line in block.lines[1:-1]]
            if body and body[0].strip() == "```text" and body[-1].strip() == "```":
                body = body[1:-1]
            return "\n".join(body)
    return None


def _dedent_line(line: str, indent: str) -> str:
    return line[len(indent) :] if line.startswith(indent) else line.lstrip()


def _render_reference(rel: str, ctx: RenderContext) -> list[str]:
    strings = STRINGS[ctx.lang]
    lines = [strings["index_intro"], ""]
    listed: set[str] = set()
    base = Path(rel).parent
    groups = list(INDEX_GROUPS) + [
        ({"en": strings["group_other"], "hr": strings["group_other"]}, [])
    ]
    all_slugs = [c["slug"] for c in leaf_commands(ctx.tree)]
    for names, slugs in groups:
        if slugs == []:
            slugs = [s for s in all_slugs if s not in listed]
        entries = []
        for slug in slugs:
            command = command_by_slug(ctx.tree, slug)
            if command is None or command["is_group"]:
                continue
            listed.add(slug)
            target = os.path.relpath(Path(command_page_rel(slug)), base)
            title = ctx.titles.get(command_page_rel(slug), command["name"])
            entries.append(
                f"- `{ctx.tree['program']} {command['display_path']}`: [{title}]({target}). "
                f"{command['short']}"
            )
        if entries:
            lines.append(f"## {names[ctx.lang]}")
            lines.append("")
            lines.extend(entries)
            lines.append("")
    while lines and not lines[-1]:
        lines.pop()
    return lines


def _render_errors(ctx: RenderContext) -> list[str]:
    strings = STRINGS[ctx.lang]
    lines = [
        strings["errors_intro"],
        "",
        "```text",
        ctx.tree["error_prefix"],
        "```",
        "",
        f"| {strings['errors_col_message']} | {strings['errors_col_kind']} |",
        "|---|---|",
    ]
    for error in ctx.tree["errors"]:
        lines.append(f"| **{_escape_cell(error['label'])}** | `{error['type']}` |")
    return lines


def fill_regions(text: str, rel: str, ctx: RenderContext) -> str:
    blocks = parse_blocks(text)
    replacements: dict[int, list[str]] = {}
    for index, block in enumerate(blocks):
        if block.kind != "generated":
            continue
        kind, args = block.region  # type: ignore[misc]
        body = render_region(kind, args, rel, ctx)
        indent = block.indent
        replacements[index] = (
            [block.lines[0]]
            + [(indent + line) if line else "" for line in body]
            + [block.lines[-1]]
        )
    return join_blocks(blocks, replacements)


# ---------------------------------------------------------------------------
# Translation (.pot extraction, merge, apply)
# ---------------------------------------------------------------------------


def _new_po(lang: str | None) -> polib.POFile:
    po = polib.POFile(wrapwidth=79)
    po.metadata = {
        "Project-Id-Version": "cadastral-docs",
        "MIME-Version": "1.0",
        "Content-Type": "text/plain; charset=UTF-8",
        "Content-Transfer-Encoding": "8bit",
        "Language": lang or "",
    }
    return po


def extract_pot(pages: dict[str, str]) -> polib.POFile:
    pot = _new_po(None)
    index: dict[str, polib.POEntry] = {}
    for rel, text in pages.items():
        for block in parse_blocks(text):
            if not is_translatable(block):
                continue
            entry = index.get(block.text)  # type: ignore[arg-type]
            if entry is None:
                entry = polib.POEntry(msgid=block.text, msgstr="")
                index[block.text] = entry  # type: ignore[index]
                pot.append(entry)
            entry.occurrences.append((rel, str(block.lineno)))
    return pot


def merge_po(pot: polib.POFile, po_path: Path, lang: str) -> polib.POFile:
    """Keep existing translations, mark changed paragraphs fuzzy, obsolete the rest."""
    existing = polib.pofile(str(po_path), wrapwidth=79) if po_path.exists() else _new_po(lang)
    existing.metadata.setdefault("Language", lang)
    merged = _new_po(lang)
    merged.metadata = dict(existing.metadata)
    by_msgid = {e.msgid: e for e in existing if not e.obsolete}
    candidates = {e.msgid: e for e in existing if e.msgstr}
    for entry in pot:
        old = by_msgid.pop(entry.msgid, None)
        if old is not None:
            new = polib.POEntry(
                msgid=entry.msgid,
                msgstr=old.msgstr,
                flags=list(old.flags),
                tcomment=old.tcomment,
                occurrences=list(entry.occurrences),
            )
        else:
            new = polib.POEntry(msgid=entry.msgid, msgstr="", occurrences=list(entry.occurrences))
            close = difflib.get_close_matches(entry.msgid, list(candidates), n=1, cutoff=0.6)
            if close:
                new.msgstr = candidates[close[0]].msgstr
                new.flags = ["fuzzy"]
                new.tcomment = f"fuzzy match of: {close[0]}"
        merged.append(new)
    for old in existing:
        if old.msgid in by_msgid or old.obsolete:
            if old.msgstr:
                stale = polib.POEntry(msgid=old.msgid, msgstr=old.msgstr, obsolete=True)
                merged.append(stale)
    return merged


def translate_page(text: str, po: polib.POFile | None) -> str:
    """Apply a catalog to the prose blocks of a page. Untranslated text stays English."""
    if po is None:
        return text
    lookup = {e.msgid: e for e in po if not e.obsolete}
    blocks = parse_blocks(text)
    replacements: dict[int, list[str]] = {}
    for index, block in enumerate(blocks):
        if not is_translatable(block):
            continue
        entry = lookup.get(block.text)  # type: ignore[arg-type]
        if entry is None or not entry.msgstr or "fuzzy" in entry.flags:
            continue
        replacements[index] = render_block(block, entry.msgstr)
    return join_blocks(blocks, replacements)


def _is_cmdline(line: str) -> bool:
    return line.strip().startswith(tuple(f"{p} " for p in PROGRAM_NAMES))


def page_cmdlines(text: str) -> list[str]:
    """Documented command lines: in shell code blocks and in output region markers."""
    found: list[str] = []
    for block in parse_blocks(text):
        if block.kind == "code" and block.lines[0].strip().startswith(("```bash", "```sh")):
            found.extend(line.strip() for line in block.lines[1:-1] if _is_cmdline(line))
        elif block.kind == "generated" and block.region and block.region[0] == "output":
            found.append(block.region[1])
    return found


def localize_page_cmdlines(text: str, mapping: dict[str, str]) -> str:
    """Rewrite documented command lines with ``mapping`` (from :func:`localize_cmdlines`)."""
    blocks = parse_blocks(text)
    replacements: dict[int, list[str]] = {}
    for index, block in enumerate(blocks):
        if block.kind == "code" and block.lines[0].strip().startswith(("```bash", "```sh")):
            lines = list(block.lines)
            for i, line in enumerate(lines):
                if _is_cmdline(line):
                    indent = line[: len(line) - len(line.lstrip())]
                    lines[i] = indent + mapping.get(line.strip(), line.strip())
            replacements[index] = lines
        elif block.kind == "generated" and block.region and block.region[0] == "output":
            new_args = mapping.get(block.region[1], block.region[1])
            first = f"{block.indent}<!-- BEGIN GENERATED: output {new_args} -->"
            replacements[index] = [first, *block.lines[1:]]
    return join_blocks(blocks, replacements)


def po_status(po: polib.POFile) -> tuple[int, int]:
    live = [e for e in po if not e.obsolete]
    untranslated = sum(1 for e in live if not e.msgstr)
    fuzzy = sum(1 for e in live if "fuzzy" in e.flags)
    return untranslated, fuzzy


# ---------------------------------------------------------------------------
# Whole build
# ---------------------------------------------------------------------------


def render_tree(
    lang: str,
    tree: dict,
    pages_en: dict[str, str],
    po: polib.POFile | None,
    capture: OutputCapture | None,
) -> dict[str, str]:
    """Render every page of one language tree; returns rel path -> text."""
    existing: dict[str, str] = {}
    for rel in pages_en:
        path = TREES[lang] / rel
        if path.exists():
            existing[rel] = path.read_text(encoding="utf-8")
    translated = {rel: translate_page(text, po) for rel, text in pages_en.items()}
    if lang != SOURCE_LANG:
        cmdlines = [c for t in translated.values() for c in page_cmdlines(t)]
        mapping = localize_cmdlines(lang, cmdlines)
        translated = {
            rel: localize_page_cmdlines(text, mapping) for rel, text in translated.items()
        }
    titles = {rel: (page_title(text) or rel) for rel, text in translated.items()}
    ctx = RenderContext(lang=lang, tree=tree, titles=titles, capture=capture, existing=existing)
    rendered: dict[str, str] = {}
    for rel, text in translated.items():
        out = fill_regions(text, rel, ctx)
        rendered[rel] = out if out.endswith("\n") else out + "\n"
    return rendered


def build(capture_output: bool = True, write: bool = True) -> dict:
    """Run the build. Returns what would be written, keyed by absolute path."""
    trees = {lang: load_tree(lang) for lang in TREES}
    created = ensure_command_pages(trees[SOURCE_LANG]) if write else []
    pages_en = source_pages()
    examples = example_files()
    pot = extract_pot(pages_en)
    catalogs: dict[str, polib.POFile] = {}
    for lang in TARGET_LANGS:
        catalogs[lang] = merge_po(pot, PO_PATHS[lang], lang)

    files: dict[Path, str | bytes] = {}
    capture: OutputCapture | None = None
    server: MockServer | None = None
    try:
        if capture_output:
            server = MockServer().__enter__()
            capture = OutputCapture(server.base_url)
        for lang in TREES:
            po = catalogs.get(lang)
            rendered = render_tree(lang, trees[lang], pages_en, po, capture)
            for rel, text in rendered.items():
                files[TREES[lang] / rel] = text
            if lang != SOURCE_LANG:
                for rel, data in examples.items():
                    files[TREES[lang] / rel] = data
    finally:
        if capture:
            capture.cleanup()
        if server:
            server.__exit__(None, None, None)

    result = {
        "trees": trees,
        "pot": pot,
        "catalogs": catalogs,
        "files": files,
        "created": created,
    }
    if write:
        POT_PATH.parent.mkdir(parents=True, exist_ok=True)
        pot.save(str(POT_PATH))
        for lang, po in catalogs.items():
            po.save(str(PO_PATHS[lang]))
        for path, content in files.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(content, bytes):
                path.write_bytes(content)
            else:
                path.write_text(content, encoding="utf-8")
        _prune_target_trees(files)
    return result


def _prune_target_trees(files: dict[Path, str | bytes]) -> None:
    """Remove files in generated trees that the build did not produce."""
    for lang in TARGET_LANGS:
        root = TREES[lang]
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file() and path not in files:
                path.unlink()
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_dir() and not any(path.iterdir()):
                path.rmdir()


def stale_files(result: dict) -> list[str]:
    """Paths whose committed content differs from what the build produced."""
    stale: list[str] = []
    for path, content in result["files"].items():
        if not path.exists():
            stale.append(f"missing: {path.relative_to(REPO)}")
            continue
        current = (
            path.read_bytes() if isinstance(content, bytes) else path.read_text(encoding="utf-8")
        )
        if current != content:
            stale.append(f"differs: {path.relative_to(REPO)}")
    for lang in TARGET_LANGS:
        root = TREES[lang]
        if root.exists():
            for path in sorted(root.rglob("*")):
                if path.is_file() and path not in result["files"]:
                    stale.append(f"unexpected: {path.relative_to(REPO)}")
    return stale


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--no-output",
        action="store_true",
        help="do not run the mock server; keep output regions as they are",
    )
    parser.add_argument(
        "--check", action="store_true", help="do not write; list files a build would change"
    )
    parser.add_argument("--dump-tree", metavar="LANG", help=argparse.SUPPRESS)
    parser.add_argument("--localize", metavar="LANG", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    if args.dump_tree:
        json.dump(_dump_tree(args.dump_tree), sys.stdout, ensure_ascii=False)
        return 0
    if args.localize:
        localized_lines = _localize_cmdlines(args.localize, json.load(sys.stdin))
        json.dump(localized_lines, sys.stdout, ensure_ascii=False)
        return 0

    result = build(capture_output=not args.no_output, write=not args.check)
    for rel in result["created"]:
        print(f"created skeleton page: {rel} (fill in the TODO sections)")
    for lang, po in result["catalogs"].items():
        untranslated, fuzzy = po_status(po)
        print(f"{PO_PATHS[lang].relative_to(REPO)}: {untranslated} untranslated, {fuzzy} fuzzy")
    if args.check:
        stale = stale_files(result)
        for line in stale:
            print(line)
        print(f"{len(stale)} file(s) would change")
        return 1 if stale else 0
    print(f"wrote {len(result['files'])} page(s) under docs/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
