"""Main CLI application for Croatian Cadastral API.

⚠️ DEMO/EDUCATIONAL PROJECT ONLY ⚠️

This is a demonstration showing how a cadastral API could work.

- Uses the mock server by default (http://localhost:8000)
- Before using any other server, including the Croatian government systems,
  verify that you have the rights to use it and its data; use at your own risk
- Author available to advise Croatian government on official AI implementation

See README.md for full disclaimer.
"""

import sys

import click
from cadastral_api.exceptions import CadastralAPIError
from cadastral_api.i18n import N_, SUPPORTED_LANGUAGES, _, get_current_language, set_language
from rich.console import Console

# click renders the "[required]" marker in option help as _(extra["required"]),
# i.e. through a variable, so xgettext never extracts the literal. Mark it here
# so it lands in the catalogs and the translated form is used at runtime.
N_("required")


def _preselect_language(argv: list[str]) -> None:
    """Apply ``--lang`` before the command modules are imported.

    Help texts are evaluated when the command modules load, so the language
    has to be chosen before that happens. click re-validates the option later.
    """
    for index, arg in enumerate(argv):
        value = None
        if arg == "--lang" and index + 1 < len(argv):
            value = argv[index + 1]
        elif arg.startswith("--lang="):
            value = arg[len("--lang="):]
        if value in SUPPORTED_LANGUAGES:
            set_language(value)
            return


_preselect_language(sys.argv[1:])

from cadastral_cli import __version__  # noqa: E402
from cadastral_cli.formatters import command_help, describe_error  # noqa: E402
from cadastral_cli.localized import (  # noqa: E402
    LocalizedGroup,
    help_option_names,
    localize_command,
)

from .commands import (  # noqa: E402
    cache,
    discovery,
    gis,
    parcel,
    registry,
    search,
)

console = Console()


_CLI_HELP = command_help(
    _("""Croatian Cadastral System CLI - Access cadastral and land registry data.

Examples:
  cadastral search 103/2 --municipality SAVAR
  cadastral get-parcel 103/2 -m 334979 --show-owners
  cadastral list-municipalities --office 114
  cadastral get-geometry 103/2 -m 334979 --format wkt

Documentation: https://github.com/yourusername/croatian-cadastral-api""")
)


@click.group(
    cls=LocalizedGroup,
    help=_CLI_HELP,
    context_settings={"help_option_names": help_option_names()},
)
@click.version_option(version=__version__, prog_name="cadastral")
@click.option("--verbose", "-v", is_flag=True, help=_("Verbose output"))
@click.option(
    "--lang",
    type=click.Choice(SUPPORTED_LANGUAGES),
    help=_("Language for output (overrides system locale)"),
    envvar="CADASTRAL_LANG",
)
@click.pass_context
def cli(ctx: click.Context, verbose: bool, lang: str | None) -> None:
    """Croatian Cadastral System CLI - Access cadastral and land registry data."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["client"] = None  # Will be initialized per command

    # Set language if specified
    if lang:
        try:
            set_language(lang)
            ctx.obj["lang"] = lang
        except ValueError as e:
            console.print(_("✗ Error: {error}").format(error=str(e)), style="bold red")
            raise SystemExit(1) from e
    else:
        ctx.obj["lang"] = get_current_language()


# Register command groups
cli.add_command(search.search)
cli.add_command(search.search_municipality)
cli.add_command(search.search_possession_sheet)
cli.add_command(parcel.get_parcel)
cli.add_command(registry.get_lr_unit)
cli.add_command(gis.get_geometry)
cli.add_command(gis.download_gis)
cli.add_command(discovery.list_offices)
cli.add_command(discovery.list_municipalities)
cli.add_command(discovery.list_main_books)
cli.add_command(discovery.list_books_of_dc)
cli.add_command(discovery.info)
cli.add_command(cache.cache_group)
localize_command(cli, "")  # --verbose, --lang, --version answer to their Croatian spellings too


def main() -> None:
    """Entry point for CLI."""
    try:
        cli(obj={})
    except CadastralAPIError as e:
        console.print(_("\n✗ Error: {error}").format(error=describe_error(e)), style="bold red")
        raise SystemExit(1) from e
    except KeyboardInterrupt as exc:
        console.print(_("\n\nOperation cancelled by user."), style="yellow")
        raise SystemExit(130) from exc
    except Exception as e:
        console.print(_("\n✗ Unexpected error: {error}").format(error=e), style="bold red")
        try:
            if "--verbose" in click.get_current_context().args:
                raise
        except RuntimeError:
            pass  # No context available
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
