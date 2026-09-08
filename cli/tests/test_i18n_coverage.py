"""Translation coverage gate.

These tests fail when the localization resources drift away from the source
code, so they can be run before every release:

    cd cli && pytest tests/test_i18n_coverage.py

What is checked, without needing the gettext binaries installed:

1. Every translatable string in the source (``_()``, ``ngettext()``,
   ``pgettext()``, ``npgettext()``, ``N_()``), including click's own
   messages, has an entry in each ``po/<lang>.po`` (run
   ``./scripts/generate_pot.sh`` and ``./scripts/update_translations.sh``).
2. For every non-source language the entry is translated and not fuzzy.
3. ``.po`` entries that are no longer referenced by the source are marked
   obsolete (``#~``) instead of lingering as live entries.
4. Named ``{placeholders}`` in a translation match the ones in the source
   string, so ``str.format`` cannot raise ``KeyError`` at runtime.
5. The compiled ``.mo`` catalogs match the ``.po`` files
   (run ``./scripts/compile_translations.sh`` to fix).
6. User-facing strings that bypass gettext entirely are detected by static
   analysis of the CLI: ``help=`` texts on click options, click command help
   (which otherwise falls back to the untranslated docstring), and string
   literals handed straight to ``console.print`` & friends.
7. ``set_language()`` really switches the ``_`` alias that command modules
   import, so the ``--lang`` flag is not a no-op.
"""

from __future__ import annotations

import ast
import gettext
import importlib
import re
from dataclasses import dataclass, field
from pathlib import Path

import click
import pytest
from cadastral_api import i18n

REPO_ROOT = Path(__file__).resolve().parents[2]
PO_DIR = REPO_ROOT / "po"
LOCALE_DIR = Path(i18n.__file__).parent / "locale"
DOMAIN = i18n.DOMAIN

# Source trees scanned for translatable strings (mirrors scripts/generate_pot.sh).
SOURCE_DIRS = [
    REPO_ROOT / "api" / "src" / "cadastral_api",
    REPO_ROOT / "cli" / "src" / "cadastral_cli",
]
# Third-party code whose gettext messages reach the terminal through the same
# catalog (i18n binds click's "Usage:", "Options", "Missing option" ... to it).
VENDORED_DIRS = [Path(click.__file__).parent]
# Only the CLI renders text for humans; the API package raises typed exceptions.
CLI_SRC = REPO_ROOT / "cli" / "src" / "cadastral_cli"

# The language the msgids are written in. Empty msgstr is fine there because
# gettext falls back to the msgid.
SOURCE_LANGUAGE = "en"

# gettext keyword -> (msgctxt index, msgid index, msgid_plural index)
GETTEXT_KEYWORDS: dict[str, tuple[int | None, int, int | None]] = {
    "_": (None, 0, None),
    "N_": (None, 0, None),
    "gettext": (None, 0, None),
    "ngettext": (None, 0, 1),
    "pgettext": (0, 1, None),
    "npgettext": (0, 1, 2),
}

PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)")
# Three or more letters in a row means "a word a human will read".
HUMAN_TEXT_RE = re.compile(r"[A-Za-zÀ-ſ]{3,}")
# Technical fragments that legitimately appear untranslated inside f-strings:
# rich markup, URLs, ``cadastral <command> --flag`` examples and bare flags.
TECHNICAL_RE = re.compile(
    r"\[/?[a-z][a-z0-9 _]*\]"  # [bold red] ... [/]
    r"|https?://\S+"
    r"|\bcadastral(?:\s+[a-z][a-z-]*)+"
    r"|(?<!\w)--?[a-z][a-z-]*(?:[ =][A-Za-z0-9/_.-]+)?"  # --format wkt, -m SAVAR
)


# --------------------------------------------------------------------------
# Source string extraction (AST based, equivalent to xgettext for our usage)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class MessageKey:
    msgctxt: str | None
    msgid: str

    def __str__(self) -> str:
        return f"{self.msgctxt}|{self.msgid}" if self.msgctxt else self.msgid


@dataclass
class SourceMessage:
    key: MessageKey
    msgid_plural: str | None = None
    locations: list[str] = field(default_factory=list)


def _callee_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _literal(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def iter_python_files(*roots: Path) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        files.extend(sorted(p for p in root.rglob("*.py") if "__pycache__" not in p.parts))
    return files


def extract_source_messages() -> tuple[dict[MessageKey, SourceMessage], list[str]]:
    """Return (messages, problems) for all gettext calls in the source trees.

    ``problems`` lists gettext calls in our own code whose arguments are not
    string literals and therefore cannot be extracted (and cannot be translated).
    """
    messages: dict[MessageKey, SourceMessage] = {}
    problems: list[str] = []

    for path in iter_python_files(*SOURCE_DIRS, *VENDORED_DIRS):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        own_code = any(path.is_relative_to(root) for root in SOURCE_DIRS)
        rel = path.relative_to(REPO_ROOT) if own_code else Path("click") / path.name
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            spec = GETTEXT_KEYWORDS.get(_callee_name(node.func) or "")
            if spec is None:
                continue
            ctxt_idx, msgid_idx, plural_idx = spec
            args = node.args
            location = f"{rel}:{node.lineno}"

            def arg(idx: int | None) -> str | None:
                return _literal(args[idx]) if idx is not None and idx < len(args) else None

            msgid = arg(msgid_idx)
            if msgid is None:
                # i18n.py defines the delegating wrappers themselves.
                if own_code and path.name != "i18n.py":
                    problems.append(
                    f"{location}: {_callee_name(node.func)}() called with a non-literal string"
                )
                continue
            key = MessageKey(arg(ctxt_idx), msgid)
            msg = messages.setdefault(key, SourceMessage(key, arg(plural_idx)))
            msg.locations.append(location)

    return messages, problems


# --------------------------------------------------------------------------
# Minimal .po parser (enough for files produced by xgettext/msgmerge)
# --------------------------------------------------------------------------


@dataclass
class PoEntry:
    msgid: str
    msgstr: str = ""
    msgctxt: str | None = None
    msgid_plural: str | None = None
    msgstr_plural: dict[int, str] = field(default_factory=dict)
    flags: set[str] = field(default_factory=set)
    obsolete: bool = False
    line: int = 0

    @property
    def key(self) -> MessageKey:
        return MessageKey(self.msgctxt, self.msgid)

    @property
    def is_fuzzy(self) -> bool:
        return "fuzzy" in self.flags

    @property
    def is_translated(self) -> bool:
        if self.msgid_plural is not None:
            return bool(self.msgstr_plural) and all(self.msgstr_plural.values())
        return bool(self.msgstr)

    def translations(self) -> list[str]:
        if self.msgid_plural is not None:
            return [self.msgstr_plural[i] for i in sorted(self.msgstr_plural)]
        return [self.msgstr]


_ESCAPES = {
    "n": "\n", "t": "\t", "r": "\r", "a": "\a", "b": "\b", "f": "\f", "v": "\v",
    '"': '"', "\\": "\\",
}


def _unquote(raw: str) -> str:
    raw = raw.strip()
    if not (raw.startswith('"') and raw.endswith('"')):
        raise ValueError(f"not a PO string: {raw!r}")
    body = raw[1:-1]
    out: list[str] = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            out.append(_ESCAPES.get(body[i + 1], body[i + 1]))
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def parse_po(path: Path) -> list[PoEntry]:
    entries: list[PoEntry] = []
    current: PoEntry | None = None
    target: tuple[str, int | None] | None = None  # which field continuation lines append to

    def flush() -> None:
        nonlocal current, target
        if current is not None:
            entries.append(current)
        current, target = None, None

    def append(text: str) -> None:
        assert current is not None and target is not None
        name, idx = target
        if name == "msgstr_plural":
            current.msgstr_plural[idx] = current.msgstr_plural.get(idx, "") + text  # type: ignore[index]
        else:
            setattr(current, name, (getattr(current, name) or "") + text)

    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            flush()
            continue

        obsolete = stripped.startswith("#~")
        if obsolete:
            stripped = stripped[2:].strip()

        if stripped.startswith("#"):
            if current is None:
                current = PoEntry(msgid="", line=lineno)
            if stripped.startswith("#,"):
                current.flags.update(f.strip() for f in stripped[2:].split(","))
            continue

        if current is None:
            current = PoEntry(msgid="", line=lineno)
        current.obsolete = current.obsolete or obsolete

        keyword, _, rest = stripped.partition(" ")
        if keyword == "msgctxt":
            if current.msgctxt is not None or current.msgid:
                flush()
                current = PoEntry(msgid="", line=lineno, obsolete=obsolete)
            current.msgctxt = ""
            target = ("msgctxt", None)
        elif keyword == "msgid":
            if current.msgid or current.msgstr or current.msgstr_plural:
                flush()
                current = PoEntry(msgid="", line=lineno, obsolete=obsolete)
            target = ("msgid", None)
        elif keyword == "msgid_plural":
            current.msgid_plural = ""
            target = ("msgid_plural", None)
        elif keyword == "msgstr":
            target = ("msgstr", None)
        elif keyword.startswith("msgstr["):
            idx = int(keyword[len("msgstr[") : -1])
            current.msgstr_plural.setdefault(idx, "")
            target = ("msgstr_plural", idx)
        elif stripped.startswith('"'):
            rest = stripped
        else:
            raise ValueError(f"{path}:{lineno}: unexpected line {line!r}")
        append(_unquote(rest))

    flush()
    # Drop the header entry (empty msgid).
    return [e for e in entries if e.msgid or e.msgctxt]


def live_entries(entries: list[PoEntry]) -> dict[MessageKey, PoEntry]:
    return {e.key: e for e in entries if not e.obsolete}


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def source() -> tuple[dict[MessageKey, SourceMessage], list[str]]:
    return extract_source_messages()


@pytest.fixture(scope="module")
def source_messages(source) -> dict[MessageKey, SourceMessage]:
    return source[0]


def _languages() -> list[str]:
    return list(i18n.SUPPORTED_LANGUAGES)


def _translated_languages() -> list[str]:
    return [lang for lang in _languages() if lang != SOURCE_LANGUAGE]


@pytest.fixture(scope="module")
def po_catalogs() -> dict[str, list[PoEntry]]:
    return {lang: parse_po(PO_DIR / f"{lang}.po") for lang in _languages()}


def _format(items: list[str], limit: int = 40) -> str:
    shown = "\n".join(f"  - {item}" for item in items[:limit])
    if len(items) > limit:
        shown += f"\n  ... and {len(items) - limit} more"
    return shown


# --------------------------------------------------------------------------
# 0. Resources exist and extraction works
# --------------------------------------------------------------------------


@pytest.mark.parametrize("lang", _languages())
def test_language_resources_exist(lang: str) -> None:
    assert (PO_DIR / f"{lang}.po").is_file(), f"missing po/{lang}.po"
    mo = LOCALE_DIR / lang / "LC_MESSAGES" / f"{DOMAIN}.mo"
    assert mo.is_file(), f"missing compiled catalog {mo} (run ./scripts/compile_translations.sh)"


def test_source_strings_are_extractable(source) -> None:
    messages, problems = source
    assert messages, "no translatable strings found - extraction is broken"
    assert not problems, (
        "gettext calls with non-literal arguments cannot be extracted or translated:\n"
        + _format(problems)
    )


# --------------------------------------------------------------------------
# 1-3. .po files are in sync with the source
# --------------------------------------------------------------------------


@pytest.mark.parametrize("lang", _languages())
def test_every_source_string_has_a_po_entry(
    lang: str, source_messages, po_catalogs
) -> None:
    live = live_entries(po_catalogs[lang])
    missing = [
        f"{key} ({', '.join(msg.locations[:2])})"
        for key, msg in sorted(source_messages.items(), key=lambda kv: str(kv[0]))
        if key not in live
    ]
    assert not missing, (
        f"{len(missing)} source string(s) are missing from po/{lang}.po "
        "(run ./scripts/generate_pot.sh && ./scripts/update_translations.sh):\n" + _format(missing)
    )


@pytest.mark.parametrize("lang", _translated_languages())
def test_every_used_string_is_translated(lang: str, source_messages, po_catalogs) -> None:
    live = live_entries(po_catalogs[lang])
    untranslated = []
    fuzzy = []
    for key in sorted(source_messages, key=str):
        entry = live.get(key)
        if entry is None:
            continue  # reported by test_every_source_string_has_a_po_entry
        if not entry.is_translated:
            untranslated.append(f"po/{lang}.po:{entry.line}: {key}")
        elif entry.is_fuzzy:
            fuzzy.append(f"po/{lang}.po:{entry.line}: {key}")
    assert not untranslated and not fuzzy, (
        f"po/{lang}.po has {len(untranslated)} untranslated and {len(fuzzy)} fuzzy "
        "entries that are used by the source:\n" + _format(untranslated + fuzzy)
    )


@pytest.mark.parametrize("lang", _languages())
def test_no_live_po_entries_without_a_source_reference(
    lang: str, source_messages, po_catalogs
) -> None:
    stale = [
        f"po/{lang}.po:{entry.line}: {entry.key}"
        for entry in po_catalogs[lang]
        if not entry.obsolete and entry.key not in source_messages
    ]
    assert not stale, (
        f"po/{lang}.po has {len(stale)} live entries no longer used by the source; "
        "run ./scripts/update_translations.sh so they become obsolete (#~):\n" + _format(stale)
    )


# --------------------------------------------------------------------------
# 4. Placeholders survive translation
# --------------------------------------------------------------------------


@pytest.mark.parametrize("lang", _languages())
def test_translation_placeholders_match_source(lang: str, po_catalogs) -> None:
    problems = []
    for entry in po_catalogs[lang]:
        if entry.obsolete or not entry.is_translated:
            continue
        allowed = set(PLACEHOLDER_RE.findall(entry.msgid))
        if entry.msgid_plural is not None:
            allowed |= set(PLACEHOLDER_RE.findall(entry.msgid_plural))
        for translation in entry.translations():
            used = set(PLACEHOLDER_RE.findall(translation))
            extra = used - allowed
            if extra:
                problems.append(
                    f"po/{lang}.po:{entry.line}: {entry.key} uses unknown placeholder(s) "
                    f"{sorted(extra)}"
                )
    assert not problems, (
        "placeholders in translations must exist in the source string:\n" + _format(problems)
    )


# --------------------------------------------------------------------------
# 5. Compiled catalogs match the .po files
# --------------------------------------------------------------------------


@pytest.mark.parametrize("lang", _languages())
def test_compiled_catalog_matches_po(lang: str, po_catalogs) -> None:
    mo_path = LOCALE_DIR / lang / "LC_MESSAGES" / f"{DOMAIN}.mo"
    with mo_path.open("rb") as fp:
        catalog: dict = gettext.GNUTranslations(fp)._catalog  # type: ignore[attr-defined]  # noqa: E501

    mismatches = []
    for entry in po_catalogs[lang]:
        if entry.obsolete or entry.is_fuzzy or not entry.is_translated:
            continue
        base = f"{entry.msgctxt}\x04{entry.msgid}" if entry.msgctxt else entry.msgid
        if entry.msgid_plural is None:
            expected = {base: entry.msgstr}
        else:
            expected = {(base, idx): text for idx, text in entry.msgstr_plural.items()}
        for mo_key, text in expected.items():
            if catalog.get(mo_key) != text:
                mismatches.append(f"po/{lang}.po:{entry.line}: {entry.key}")
                break
    assert not mismatches, (
        f"{mo_path.relative_to(REPO_ROOT)} is out of date for {len(mismatches)} entries "
        "(run ./scripts/compile_translations.sh):\n" + _format(mismatches)
    )


# --------------------------------------------------------------------------
# 6. CLI strings that bypass gettext
# --------------------------------------------------------------------------

CLICK_DECORATORS = {"command", "group", "option", "argument", "version_option"}
CLICK_COMMAND_DECORATORS = {"command", "group"}
OUTPUT_CALLS = {"print", "status", "echo", "secho", "add_column", "rule"}
OUTPUT_HELPERS = {
    "print_error", "print_success", "print_info", "print_warning", "create_rich_table",
}
OUTPUT_TITLE_KWARGS = {"title"}

# Literals that are technical rather than human text and may stay untranslated.
ALLOWED_OUTPUT_LITERALS: set[str] = set()


def _is_gettext_call(node: ast.AST) -> bool:
    return isinstance(node, ast.Call) and (_callee_name(node.func) in GETTEXT_KEYWORDS)


def _wraps_gettext_call(node: ast.AST) -> bool:
    """``_("...")`` itself or a call whose first argument is one, e.g. ``command_help(_())``."""
    if _is_gettext_call(node):
        return True
    return isinstance(node, ast.Call) and bool(node.args) and _wraps_gettext_call(node.args[0])


def _module_gettext_names(tree: ast.Module) -> set[str]:
    """Names assigned at module level to a gettext call, e.g. ``_HELP = _("...")``."""
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Assign) and _wraps_gettext_call(node.value):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
    return names


def _is_translated_value(node: ast.AST, gettext_names: set[str]) -> bool:
    if _wraps_gettext_call(node):
        return True
    if isinstance(node, ast.Name):
        return node.id in gettext_names
    return False


def _has_human_text(node: ast.AST) -> str | None:
    """Return the literal text if ``node`` is a (f-)string literal containing words.

    Only the constant parts of an f-string count; ``f"{_('Try')}: cadastral search"``
    is fine because the human words are already translated and the rest is a
    command example.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        constant_parts = node.value
    elif isinstance(node, ast.JoinedStr):
        constant_parts = " ".join(
            v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)
        )
    else:
        return None
    if HUMAN_TEXT_RE.search(TECHNICAL_RE.sub(" ", constant_parts)):
        return ast.unparse(node)
    return None


def _cli_modules() -> list[tuple[Path, ast.Module]]:
    return [
        (path, ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
        for path in iter_python_files(CLI_SRC)
    ]


def test_click_help_texts_are_translatable() -> None:
    problems = []
    for path, tree in _cli_modules():
        rel = path.relative_to(REPO_ROOT)
        gettext_names = _module_gettext_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _callee_name(node.func) not in CLICK_DECORATORS:
                continue
            for kw in node.keywords:
                if kw.arg not in {"help", "short_help"}:
                    continue
                if _is_translated_value(kw.value, gettext_names):
                    continue
                if isinstance(kw.value, (ast.Constant, ast.JoinedStr)):
                    problems.append(
                        f"{rel}:{kw.value.lineno}: {kw.arg}={ast.unparse(kw.value)[:60]}"
                    )
    assert not problems, (
        f"{len(problems)} click help text(s) are plain literals and can never be translated; "
        "wrap them in _():\n" + _format(problems)
    )


def test_click_commands_declare_translatable_help() -> None:
    """Click uses the docstring as command help unless ``help=`` is given.

    Docstrings are not extracted by gettext, so every command must pass
    ``help=_("...")`` (or a module constant bound to ``_()``) explicitly.
    """
    problems = []
    for path, tree in _cli_modules():
        rel = path.relative_to(REPO_ROOT)
        gettext_names = _module_gettext_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call):
                    continue
                if _callee_name(deco.func) not in CLICK_COMMAND_DECORATORS:
                    continue
                help_kw = next((kw for kw in deco.keywords if kw.arg == "help"), None)
                if help_kw is None:
                    problems.append(
                        f"{rel}:{node.lineno}: {node.name}() relies on its docstring for --help"
                    )
                elif not _is_translated_value(help_kw.value, gettext_names):
                    problems.append(
                        f"{rel}:{node.lineno}: {node.name}() help is not wrapped in _()"
                    )
    assert not problems, (
        f"{len(problems)} click command(s) show untranslated help:\n" + _format(problems)
    )


def test_console_output_literals_are_translatable() -> None:
    problems = []
    for path, tree in _cli_modules():
        rel = path.relative_to(REPO_ROOT)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = _callee_name(node.func)
            candidates: list[ast.AST] = []
            if name in OUTPUT_CALLS or name in OUTPUT_HELPERS:
                candidates.extend(node.args[:1])
            if name in OUTPUT_HELPERS or name in {"Table", "Panel"}:
                candidates.extend(kw.value for kw in node.keywords if kw.arg in OUTPUT_TITLE_KWARGS)
            for candidate in candidates:
                text = _has_human_text(candidate)
                if text is not None and text not in ALLOWED_OUTPUT_LITERALS:
                    problems.append(f"{rel}:{candidate.lineno}: {name}({text[:70]!r})")
    assert not problems, (
        f"{len(problems)} user-facing literal(s) are printed without _():\n" + _format(problems)
    )


# --------------------------------------------------------------------------
# 7. Runtime language switching
# --------------------------------------------------------------------------


def test_set_language_switches_imported_gettext_alias(source_messages, po_catalogs) -> None:
    """``from cadastral_api.i18n import _`` must follow ``set_language()``.

    Otherwise the ``--lang`` flag silently keeps whatever language was active
    when the command modules were imported.
    """
    hr = live_entries(po_catalogs["hr"])
    probe = next(
        (
            e
            for e in hr.values()
            if e.key in source_messages
            and e.is_translated
            and e.msgstr != e.msgid
            and e.msgid_plural is None
        ),
        None,
    )
    assert probe is not None, "need at least one translated Croatian string to probe with"

    formatters = importlib.import_module("cadastral_cli.formatters")
    original = i18n.get_current_language()
    try:
        i18n.set_language("en")
        assert formatters._(probe.msgid) == probe.msgid
        i18n.set_language("hr")
        assert formatters._(probe.msgid) == probe.msgstr, (
            "set_language('hr') did not affect the `_` imported by cadastral_cli.formatters; "
            "i18n must expose a stable `_` that delegates to the current catalog"
        )
    finally:
        i18n.set_language(original)
