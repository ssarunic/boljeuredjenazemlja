"""Localized command and option names (cadastral_cli.localized).

- Every command and every option (long and short) of the CLI has an entry in
  the alias tables, so a new command cannot ship without a Croatian spelling.
- A Croatian short spelling never equals a pair of English single-letter flags
  of the same command (``-ae``), which click would otherwise read as a
  combination.
- Croatian spellings are unique within their scope (no two commands, and no
  two options of one command, share a spelling in any language).
- Aliases resolve, with and without diacritics, in either active language.
- Help shows only the active language's spelling.
"""

from __future__ import annotations

import click
import pytest
from cadastral_api.i18n import SUPPORTED_LANGUAGES, set_language
from click.testing import CliRunner

from cadastral_cli import localized
from cadastral_cli.main import cli


def _walk(group: click.Group, path: str = "") -> list[tuple[str, click.Command]]:
    found = []
    for name, command in group.commands.items():
        full = f"{path} {name}".strip()
        found.append((full, command))
        if isinstance(command, click.Group):
            found.extend(_walk(command, full))
    return found


@pytest.fixture(autouse=True)
def restore_language():
    yield
    set_language("hr")


def test_every_command_has_an_alias_entry() -> None:
    missing = [path for path, _ in _walk(cli) if path not in localized.COMMANDS]
    stale = [path for path in localized.COMMANDS if path not in dict(_walk(cli))]
    assert not missing, f"commands without an alias entry: {missing}"
    assert not stale, f"alias entries without a command: {stale}"


def test_every_option_has_an_alias_entry() -> None:
    missing = []
    for path, command in [("", cli), *_walk(cli)]:
        for param in command.params:
            if not isinstance(param, click.Option):
                continue
            for canonical in [*param._canonical_opts, *param._canonical_secondary_opts]:  # type: ignore[attr-defined]
                if canonical not in localized.OPTIONS:
                    if (path, canonical) not in localized.OPTION_OVERRIDES:
                        missing.append(f"{path} {canonical}")
    assert not missing, f"options without an alias entry: {missing}"


def test_short_spellings_are_ascii_and_short() -> None:
    bad = []
    for lang in SUPPORTED_LANGUAGES:
        catalog = localized._catalog(lang)
        entries = [(localized.OPTION_CONTEXT, c) for c in localized.OPTIONS]
        entries += [(f"{localized.OPTION_CONTEXT} {p}", c) for p, c in localized.OPTION_OVERRIDES]
        for context, canonical in entries:
            if canonical.startswith("--"):
                continue
            spelling = localized._lookup(catalog, context, canonical)
            if spelling == canonical:
                continue  # untranslated (English): the canonical spelling is used
            body = spelling[1:]
            if not (
                spelling.startswith("-") and len(body) == 2 and body.isascii() and body.isalpha()
            ):
                bad.append(f"{lang}: {canonical} -> {spelling}")
    assert not bad, f"localized short spellings must be '-' plus two ASCII letters: {bad}"


def test_short_spellings_do_not_shadow_combined_flags() -> None:
    """``-sv`` must not be readable as ``-s -v`` where both are boolean flags."""
    shadowed = []
    for path, command in _walk(cli):
        flags: set[str] = set()
        for param in command.params:
            if isinstance(param, click.Option) and param.is_flag:
                flags.update(o[1:] for o in param._canonical_opts if len(o) == 2)  # type: ignore[attr-defined]
        for param in command.params:
            if not isinstance(param, click.Option):
                continue
            for canonical in [*param._canonical_opts, *param._canonical_secondary_opts]:  # type: ignore[attr-defined]
                for spelling in localized.option_spellings(path, canonical):
                    if len(spelling) == 3 and spelling[1] in flags and spelling[2] in flags:
                        shadowed.append(
                            f"{path}: {spelling} reads as -{spelling[1]} -{spelling[2]}"
                        )
    assert not shadowed, shadowed


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
def test_spellings_are_unique_per_scope(lang: str) -> None:
    catalog = localized._catalog(lang)
    for path, command in _walk(cli):
        seen: dict[str, str] = {}
        for param in command.params:
            if not isinstance(param, click.Option):
                continue
            for canonical in [*param._canonical_opts, *param._canonical_secondary_opts]:  # type: ignore[attr-defined]
                context = localized.option_context(path, canonical)
                spelling = localized._lookup(catalog, context, canonical)
                if spelling.startswith("--"):
                    spelling = localized.fold(spelling)  # short flags stay case-sensitive
                assert spelling not in seen or seen[spelling] == canonical, (
                    f"{lang}: '{spelling}' on {path} is both {seen[spelling]} and {canonical}"
                )
                seen[spelling] = canonical
    groups = [(p, c) for p, c in _walk(cli) if isinstance(c, click.Group)]
    for group_path, group in [("", cli), *groups]:
        names: dict[str, str] = {}
        for canonical in group.commands:
            full = f"{group_path} {canonical}".strip()
            spelling = localized.fold(localized._lookup(catalog, localized.COMMAND_CONTEXT, full))
            leaf = spelling.split(" ")[-1]
            assert leaf not in names or names[leaf] == canonical, (
                f"{lang}: '{leaf}' names both {names[leaf]} and {canonical}"
            )
            names[leaf] = canonical


def test_croatian_spellings_differ_from_english() -> None:
    same = [
        path
        for path in localized.COMMANDS
        if localized._lookup(localized._catalog("hr"), "command", path) == path
        and path.split(" ")[-1] != "info"
    ]
    assert not same, f"commands with no Croatian spelling: {same}"


@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
@pytest.mark.parametrize(
    "args",
    [
        ["get-parcel", "--help"],
        ["čestica", "--pomoć"],
        ["cestica", "--help"],
        ["uložak", "--od-čestice", "103/2", "-ko", "SAVAR", "--sve", "--help"],
        ["uložak", "-bu", "769", "-gk", "21277", "-vl", "-ce", "-te", "--help"],
        ["get-lr-unit", "-oc", "103/2", "-m", "SAVAR", "-sv", "-ob", "json", "--help"],
        ["cache", "clear", "-sv", "-bp", "--help"],
        ["list-municipalities", "-ur", "114", "-od", "116", "-tr", "ZADAR", "--help"],
        ["predmemorija", "popis", "--help"],
        ["cache", "obriši", "--help"],
        ["pretraži", "103/2", "--općina", "SAVAR", "--oblik", "tablica", "--help"],
    ],
)
def test_aliases_resolve_in_every_language(lang: str, args: list[str]) -> None:
    set_language(lang)
    result = CliRunner().invoke(cli, args, catch_exceptions=False)
    assert result.exit_code == 0, result.output


def test_help_shows_only_the_active_spelling() -> None:
    set_language("hr")
    croatian = CliRunner().invoke(cli, ["čestica", "--help"]).output
    assert "--općina" in croatian and "--municipality" not in croatian
    assert "--posjednici" in croatian and "--show-owners" not in croatian
    assert "-ko, " in croatian and "-m, " not in croatian
    assert "-ob, --oblik" in croatian and "-f, " not in croatian
    assert "tablica" in croatian
    croatian = CliRunner().invoke(cli, ["uložak", "--pomoć"]).output
    assert "-bu, --broj-uloška" in croatian and "-u, " not in croatian
    assert "-gk, --glavna-knjiga" in croatian and "-b, " not in croatian
    assert "-vl, --vlasnici" in croatian and "-o, " not in croatian
    set_language("en")
    english = CliRunner().invoke(cli, ["get-parcel", "--help"]).output
    assert "--municipality" in english and "--općina" not in english
    assert "-m, --municipality" in english and "-ko, --municipality" not in english
    assert "table" in english and "tablica" not in english


def _listed_commands(output: str) -> list[str]:
    """Command names in the 'Commands' section of a group's help output."""
    section = output.split("\n\n")[-1]
    return [line.split()[0] for line in section.splitlines()[1:] if line.strip()]


def test_group_listing_uses_active_spelling() -> None:
    # Descriptions are evaluated at import time (the language is chosen before
    # the modules load), so only the command column is checked here.
    set_language("hr")
    listed = _listed_commands(CliRunner().invoke(cli, ["--help"]).output)
    assert "čestica" in listed and "get-parcel" not in listed
    set_language("en")
    listed = _listed_commands(CliRunner().invoke(cli, ["--help"]).output)
    assert "get-parcel" in listed and "čestica" not in listed


def test_localized_choice_value_is_canonical_inside() -> None:
    choice = localized.LocalizedChoice(["table", "json"])
    assert choice.convert("tablica", None, None) == "table"
    assert choice.convert("TABLICA", None, None) == "table"
    assert choice.convert("json", None, None) == "json"


@pytest.mark.parametrize(
    ("lang", "line", "expected"),
    [
        (
            "hr",
            "cadastral get-parcel 103/2 -m SAVAR --show-owners",
            "uz čestica 103/2 -ko SAVAR --posjednici",
        ),
        (
            "hr",
            'cadastral get-parcel "103/2,45" -m SAVAR --detail registry --format json -o out.json',
            'uz čestica "103/2,45" -ko SAVAR --detalji registry --oblik json -dt out.json',
        ),
        (
            "hr",
            "cadastral get-lr-unit --input parcels.json --all --stop-on-error",
            "uz uložak --ulaz parcels.json --sve --stani-kod-greške",
        ),
        ("hr", "cadastral cache clear --all --force", "uz predmemorija obriši --sve --bez-pitanja"),
        ("hr", "cadastral cache clear -a -f", "uz predmemorija obriši -sv -bp"),
        (
            "hr",
            "cadastral get-lr-unit -u 769 -b 21277 -o -P -e -D",
            "uz uložak -bu 769 -gk 21277 -vl -ce -te -pl",
        ),
        (
            "hr",
            "cadastral list-municipalities -o 114 -d 116 -f json",
            "uz općine -ur 114 -od 116 -ob json",
        ),
        ("hr", "cadastral download-gis 334979 -o ./gis", "uz preuzmi-gis 334979 -mp ./gis"),
        ("en", "uz uložak -bu 769 -gk 21277 -vl", "cadastral get-lr-unit -u 769 -b 21277 -o"),
        (
            "hr",
            "cadastral search 1 -m SAVAR --partial --format=table",
            "uz pretraži 1 -ko SAVAR --djelomično --oblik=tablica",
        ),
        (
            "en",
            "uz čestica 103/2 -ko SAVAR --posjednici",
            "cadastral get-parcel 103/2 -m SAVAR --show-owners",
        ),
        ("hr", "pip install -e ./cli", "pip install -e ./cli"),
    ],
)
def test_localize_cmdline(lang: str, line: str, expected: str) -> None:
    set_language(lang)
    assert localized.localize_cmdline(line, cli) == expected
