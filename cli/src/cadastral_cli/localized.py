"""Localized spellings (aliases) of command names, option names and choices.

The English names are canonical: they are what the code, the JSON output and
the MCP server use. Each alias below is a gettext entry with a context; the
translation in ``po/<lang>.po`` is the spelling of that language, so a
missing or fuzzy alias fails the translation coverage gate like any other
string.

Rules:

- Every spelling of every supported language is accepted at all times, so a
  command copied from the Croatian documentation works in an English
  environment and the other way round.
- Diacritics are folded when matching (``cestica`` finds ``čestica``).
- Help output shows only the spelling of the active language.

Adding a command or option: add its canonical name to the tables below,
run the translation scripts, translate the new entry in ``po/hr.po``.
``cli/tests/test_localized_cli.py`` checks that nothing is left out.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from functools import lru_cache
from typing import Any

import click
from cadastral_api import i18n
from cadastral_api.i18n import SUPPORTED_LANGUAGES, pgettext

COMMAND_CONTEXT = "command"
OPTION_CONTEXT = "option"
CHOICE_CONTEXT = "choice"

# Canonical command path -> spelling in the active language. The literal
# pgettext() calls make the entries visible to xgettext and to the gate.
COMMANDS: dict[str, str] = {
    "search": pgettext("command", "search"),
    "search-municipality": pgettext("command", "search-municipality"),
    "get-parcel": pgettext("command", "get-parcel"),
    "get-lr-unit": pgettext("command", "get-lr-unit"),
    "batch-fetch": pgettext("command", "batch-fetch"),
    "batch-lr-unit": pgettext("command", "batch-lr-unit"),
    "get-geometry": pgettext("command", "get-geometry"),
    "download-gis": pgettext("command", "download-gis"),
    "list-offices": pgettext("command", "list-offices"),
    "list-municipalities": pgettext("command", "list-municipalities"),
    "info": pgettext("command", "info"),
    "cache": pgettext("command", "cache"),
    "cache list": pgettext("command", "cache list"),
    "cache clear": pgettext("command", "cache clear"),
    "cache info": pgettext("command", "cache info"),
}

# Canonical option spelling -> spelling in the active language, shared by
# every command that has the option.
OPTIONS: dict[str, str] = {
    "--help": pgettext("option", "--help"),
    "--lang": pgettext("option", "--lang"),
    "--verbose": pgettext("option", "--verbose"),
    "--version": pgettext("option", "--version"),
    "--municipality": pgettext("option", "--municipality"),
    "-m": pgettext("option", "-m"),
    "--exact": pgettext("option", "--exact"),
    "--partial": pgettext("option", "--partial"),
    "--format": pgettext("option", "--format"),
    "--output": pgettext("option", "--output"),
    "--office": pgettext("option", "--office"),
    "--department": pgettext("option", "--department"),
    "--count-only": pgettext("option", "--count-only"),
    "--search": pgettext("option", "--search"),
    "--detail": pgettext("option", "--detail"),
    "--show-owners": pgettext("option", "--show-owners"),
    "--show-geometry": pgettext("option", "--show-geometry"),
    "--unit-number": pgettext("option", "--unit-number"),
    "--main-book": pgettext("option", "--main-book"),
    "--from-parcel": pgettext("option", "--from-parcel"),
    "--show-parcels": pgettext("option", "--show-parcels"),
    "--show-encumbrances": pgettext("option", "--show-encumbrances"),
    "--plombe-detail": pgettext("option", "--plombe-detail"),
    "--all": pgettext("option", "--all"),
    "--input": pgettext("option", "--input"),
    "--from-batch-output": pgettext("option", "--from-batch-output"),
    "--continue-on-error": pgettext("option", "--continue-on-error"),
    "--stop-on-error": pgettext("option", "--stop-on-error"),
    "--show-stats": pgettext("option", "--show-stats"),
    "--extract": pgettext("option", "--extract"),
    "--no-extract": pgettext("option", "--no-extract"),
    "--clear-cache": pgettext("option", "--clear-cache"),
    "--force": pgettext("option", "--force"),
    # Short spellings. English ones are single letters; Croatian ones are two
    # ASCII letters taken from the Croatian long spelling (``-gk`` for
    # ``--glavna-knjiga``), see specs/terminology.md section 4.
    "-u": pgettext("option", "-u"),
    "-b": pgettext("option", "-b"),
    "-p": pgettext("option", "-p"),
    "-o": pgettext("option", "-o"),
    "-P": pgettext("option", "-P"),
    "-e": pgettext("option", "-e"),
    "-D": pgettext("option", "-D"),
    "-a": pgettext("option", "-a"),
    "-f": pgettext("option", "-f"),
    "-i": pgettext("option", "-i"),
    "-d": pgettext("option", "-d"),
    "-s": pgettext("option", "-s"),
    "-v": pgettext("option", "-v"),
    "-out": pgettext("option", "-out"),
}

# Per-command spellings that differ from the shared one. The same English
# flag can mean different things: on the cadastre commands ``--show-owners``
# shows possessors, on the land registry commands it shows owners.
OPTION_OVERRIDES: dict[tuple[str, str], str] = {
    ("get-parcel", "--show-owners"): pgettext("option get-parcel", "--show-owners"),
    ("batch-fetch", "--show-owners"): pgettext("option batch-fetch", "--show-owners"),
    ("download-gis", "--output"): pgettext("option download-gis", "--output"),
    # ``-o`` is --output by default; on these commands it is something else.
    ("get-lr-unit", "-o"): pgettext("option get-lr-unit", "-o"),
    ("list-municipalities", "-o"): pgettext("option list-municipalities", "-o"),
    ("search-municipality", "-o"): pgettext("option search-municipality", "-o"),
    ("download-gis", "-o"): pgettext("option download-gis", "-o"),
    # ``-f`` is --format by default; on ``cache clear`` it is --force.
    ("cache clear", "-f"): pgettext("option cache clear", "-f"),
}

# Choice values that are words rather than format names.
CHOICES: dict[str, str] = {
    "table": pgettext("choice", "table"),
}

# The program name (``cadastral`` and ``uz`` are both installed; both work).
PROGRAM = pgettext("program", "cadastral")

# Metavars of positional arguments, keyed by click's default (the name in
# upper case), and the usage placeholders click leaves untranslated.
ARGUMENTS: dict[str, str] = {
    "PARCEL_NUMBER": pgettext("argument", "PARCEL_NUMBER"),
    "SEARCH_TERM": pgettext("argument", "SEARCH_TERM"),
    "PARCELS": pgettext("argument", "PARCELS"),
    "MUNICIPALITY": pgettext("argument", "MUNICIPALITY"),
}
OPTIONS_METAVAR = pgettext("usage", "[OPTIONS]")
SUBCOMMAND_METAVAR = pgettext("usage", "COMMAND [ARGS]...")

# Value placeholders click derives from the parameter type (``--općina TEXT``).
METAVARS: dict[str, str] = {
    "TEXT": pgettext("metavar", "TEXT"),
    "INTEGER": pgettext("metavar", "INTEGER"),
    "FLOAT": pgettext("metavar", "FLOAT"),
    "PATH": pgettext("metavar", "PATH"),
}


# ---------------------------------------------------------------------------
# Catalog access
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def _catalog(lang: str) -> Any:
    return i18n._load_catalog(lang)


def _lookup(catalog: Any, context: str, msgid: str) -> str:
    # Looked up through getattr on purpose: the coverage gate rejects direct
    # pgettext() calls with non-literal arguments, and these are table-driven.
    translate = getattr(catalog, "pgettext")  # noqa: B009
    return str(translate(context, msgid))


def spellings(context: str, msgid: str) -> list[str]:
    """Every accepted spelling: the canonical one first, then each language's."""
    out = [msgid]
    for lang in SUPPORTED_LANGUAGES:
        spelling = _lookup(_catalog(lang), context, msgid)
        if spelling and spelling not in out:
            out.append(spelling)
    return out


def active_spelling(context: str, msgid: str) -> str:
    """The spelling in the active language (the canonical one if untranslated)."""
    spelling = _lookup(i18n.TRANSLATIONS, context, msgid)
    return spelling or msgid


def fold(text: str) -> str:
    """Case-insensitive, diacritic-insensitive form used for matching."""
    text = text.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


# ---------------------------------------------------------------------------
# Options and choices
# ---------------------------------------------------------------------------


def option_context(command_path: str, canonical: str) -> str:
    if (command_path, canonical) in OPTION_OVERRIDES:
        return f"{OPTION_CONTEXT} {command_path}"
    return OPTION_CONTEXT


def option_spellings(command_path: str, canonical: str) -> list[str]:
    if canonical not in OPTIONS and (command_path, canonical) not in OPTION_OVERRIDES:
        return [canonical]
    return spellings(option_context(command_path, canonical), canonical)


def option_display(command_path: str, canonical: str) -> str:
    if canonical not in OPTIONS and (command_path, canonical) not in OPTION_OVERRIDES:
        return canonical
    return active_spelling(option_context(command_path, canonical), canonical)


class LocalizedChoice(click.Choice):
    """A Choice that accepts and displays localized values (``tablica`` for ``table``)."""

    def __init__(self, choices: Iterable[str]) -> None:
        super().__init__(list(choices))
        self.aliases: dict[str, str] = {}
        for canonical in self.choices:
            if canonical in CHOICES:
                for spelling in spellings(CHOICE_CONTEXT, canonical):
                    self.aliases[fold(spelling)] = canonical

    def display(self, canonical: str) -> str:
        return active_spelling(CHOICE_CONTEXT, canonical) if canonical in CHOICES else canonical

    def convert(self, value: Any, param: click.Parameter | None, ctx: click.Context | None) -> Any:
        if isinstance(value, str):
            value = self.aliases.get(fold(value), value)
        return super().convert(value, param, ctx)

    def get_metavar(self, param: click.Parameter, ctx: click.Context) -> str:
        shown = "|".join(self.display(c) for c in self.choices)
        return f"[{shown}]" if param.param_type_name == "option" else f"{{{shown}}}"


class LocalizedOption(click.Option):
    """An Option that accepts every language's spelling and shows the active one.

    Instances are ordinary ``click.Option`` objects re-classed by
    :func:`localize_command`, which keeps the ``@click.option`` decorators in
    the command modules untouched (and visible to the i18n gate).
    """

    _canonical_opts: list[str]
    _canonical_secondary_opts: list[str]
    _command_path: str

    def _display(self, opts: list[str]) -> list[str]:
        return [option_display(self._command_path, o) for o in opts]

    def get_help_record(self, ctx: click.Context) -> tuple[str, str] | None:
        return self._with_active_spellings(lambda: click.Option.get_help_record(self, ctx))

    def get_error_hint(self, ctx: click.Context) -> str:
        return self._with_active_spellings(lambda: click.Option.get_error_hint(self, ctx))

    def _with_active_spellings(self, render: Any) -> Any:
        saved = (self.opts, self.secondary_opts)
        self.opts = self._display(self._canonical_opts)
        self.secondary_opts = self._display(self._canonical_secondary_opts)
        try:
            return render()
        finally:
            self.opts, self.secondary_opts = saved


def localize_command(command: click.Command, command_path: str) -> None:
    """Attach every language's spellings to the options of ``command``."""
    command.canonical_path = command_path  # type: ignore[attr-defined]
    command.options_metavar = active_spelling("usage", "[OPTIONS]")
    if isinstance(command, click.Group):
        command.subcommand_metavar = active_spelling("usage", "COMMAND [ARGS]...")
    for param in command.params:
        if isinstance(param, click.Argument) and param.name:
            canonical = param.name.upper()
            if canonical in ARGUMENTS and param.metavar is None:
                param.metavar = active_spelling("argument", canonical)
            continue
        if not isinstance(param, click.Option):
            continue
        if isinstance(param, LocalizedOption):
            # Already localized under another path (a subcommand registered
            # before its group was): redo the spellings under the full path,
            # which decides the per-command overrides.
            param._command_path = command_path
            param.opts = _expand(command_path, param._canonical_opts)
            param.secondary_opts = _expand(command_path, param._canonical_secondary_opts)
            continue
        type_metavar = param.type.name.upper()
        if param.metavar is None and type_metavar in METAVARS and not param.is_flag:
            param.metavar = active_spelling("metavar", type_metavar)
        canonical_opts = list(param.opts)
        canonical_secondary = list(param.secondary_opts)
        param.opts = _expand(command_path, canonical_opts)
        param.secondary_opts = _expand(command_path, canonical_secondary)
        if isinstance(param.type, click.Choice) and not isinstance(param.type, LocalizedChoice):
            if any(c in CHOICES for c in param.type.choices):
                param.type = LocalizedChoice(param.type.choices)
        param.__class__ = LocalizedOption
        param._canonical_opts = canonical_opts  # type: ignore[attr-defined]
        param._canonical_secondary_opts = canonical_secondary  # type: ignore[attr-defined]
        param._command_path = command_path  # type: ignore[attr-defined]


def _expand(command_path: str, canonical_opts: list[str]) -> list[str]:
    """All accepted spellings of the options, each also without diacritics."""
    expanded: list[str] = []
    for canonical in canonical_opts:
        for spelling in option_spellings(command_path, canonical):
            for variant in (spelling, fold(spelling) if spelling.startswith("--") else spelling):
                if variant not in expanded:
                    expanded.append(variant)
    return expanded


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------


class LocalizedGroup(click.Group):
    """A Group whose subcommands answer to their localized names as well."""

    canonical_path: str = ""

    def add_command(self, cmd: click.Command, name: str | None = None) -> None:
        super().add_command(cmd, name)
        canonical = name or cmd.name or ""
        path = f"{self.canonical_path} {canonical}".strip()
        if isinstance(cmd, LocalizedGroup):
            cmd.canonical_path = path
            for sub_name, sub in cmd.commands.items():
                localize_command(sub, f"{path} {sub_name}")
        localize_command(cmd, path)

    def _alias_map(self) -> dict[str, str]:
        aliases: dict[str, str] = {}
        for canonical in self.commands:
            path = f"{self.canonical_path} {canonical}".strip()
            for spelling in spellings(COMMAND_CONTEXT, path) if path in COMMANDS else [canonical]:
                aliases[fold(spelling.split(" ")[-1])] = canonical
        return aliases

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        command = super().get_command(ctx, cmd_name)
        if command is not None:
            return command
        canonical = self._alias_map().get(fold(cmd_name))
        return super().get_command(ctx, canonical) if canonical else None

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        rows = []
        for canonical in self.list_commands(ctx):
            command = self.get_command(ctx, canonical)
            if command is None or command.hidden:
                continue
            rows.append((display_name(f"{self.canonical_path} {canonical}".strip()), command))
        if not rows:
            return
        limit = formatter.width - 6 - max(len(name) for name, _ in rows)
        with formatter.section(i18n._("Commands")):
            formatter.write_dl(
                [(name, cmd.get_short_help_str(limit)) for name, cmd in sorted(rows)]
            )


def display_name(command_path: str) -> str:
    """The active-language spelling of the last segment of ``command_path``."""
    if command_path not in COMMANDS:
        return command_path.split(" ")[-1]
    return active_spelling(COMMAND_CONTEXT, command_path).split(" ")[-1]


def help_option_names() -> list[str]:
    return spellings(OPTION_CONTEXT, "--help")


def program_name() -> str:
    return active_spelling("program", "cadastral")


def program_names() -> list[str]:
    return spellings("program", "cadastral")


# ---------------------------------------------------------------------------
# Command lines
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r'"[^"]*"|\'[^\']*\'|\S+')


def localize_cmdline(cmdline: str, root: click.Group) -> str:
    """Rewrite a documented command line into the active language's spellings.

    ``cadastral get-parcel 103/2 -m SAVAR --show-owners`` becomes
    ``uz čestica 103/2 -ko SAVAR --posjednici`` under Croatian. Values are
    kept as they are, except choice values that have a localized spelling.
    Lines that do not start with a program name are returned unchanged.
    """
    tokens = [(m.start(), m.end(), m.group()) for m in _TOKEN_RE.finditer(cmdline)]
    if not tokens or tokens[0][2] not in program_names():
        return cmdline
    replacements: dict[int, str] = {0: program_name()}
    group: click.Group | None = root
    command: click.Command = root
    path = ""
    value_for: click.Option | None = None
    for index in range(1, len(tokens)):
        token = tokens[index][2]
        if value_for is not None:
            if isinstance(value_for.type, LocalizedChoice):
                replacements[index] = _localize_choice(value_for.type, token)
            value_for = None
            continue
        if group is not None and not token.startswith("-"):
            sub = group.get_command(None, token)  # type: ignore[arg-type]
            if sub is not None and sub.name:
                path = f"{path} {sub.name}".strip()
                replacements[index] = display_name(path)
                command = sub
                group = sub if isinstance(sub, click.Group) else None
                continue
        if token.startswith("-"):
            name, equals, value = token.partition("=")
            option = _find_option(command, name)
            if option is not None:
                shown = _spelling_of(option, name)
                if equals and isinstance(option.type, LocalizedChoice):
                    value = _localize_choice(option.type, value)
                replacements[index] = shown + equals + value
                if not equals and not option.is_flag and option.nargs == 1:
                    value_for = option
    out = []
    last = 0
    for index, (start, end, token) in enumerate(tokens):
        out.append(cmdline[last:start])
        out.append(replacements.get(index, token))
        last = end
    out.append(cmdline[last:])
    return "".join(out)


def _find_option(command: click.Command, name: str) -> click.Option | None:
    for param in command.params:
        if isinstance(param, click.Option) and (name in param.opts or name in param.secondary_opts):
            return param
    return None


def _spelling_of(option: click.Option, name: str) -> str:
    if not isinstance(option, LocalizedOption):
        return name
    for canonical in [*option._canonical_opts, *option._canonical_secondary_opts]:
        if name in option_spellings(option._command_path, canonical) or fold(name) == fold(
            canonical
        ):
            return option_display(option._command_path, canonical)
    return name


def _localize_choice(choice: LocalizedChoice, value: str) -> str:
    canonical = choice.aliases.get(fold(value), value)
    return choice.display(canonical) if canonical in choice.choices else value


def alias_table() -> dict[str, Any]:
    """Active-language spellings for the documentation build."""
    return {
        "program": program_name(),
        "commands": {path: active_spelling(COMMAND_CONTEXT, path) for path in COMMANDS},
        "options": {
            canonical: active_spelling(OPTION_CONTEXT, canonical) for canonical in OPTIONS
        },
        "option_overrides": {
            f"{path} {canonical}": active_spelling(f"{OPTION_CONTEXT} {path}", canonical)
            for (path, canonical) in OPTION_OVERRIDES
        },
        "choices": {canonical: active_spelling(CHOICE_CONTEXT, canonical) for canonical in CHOICES},
    }
