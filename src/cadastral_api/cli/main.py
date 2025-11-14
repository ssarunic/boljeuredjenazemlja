"""Main CLI application for Croatian Cadastral API.

⚠️ DEMO/EDUCATIONAL PROJECT ONLY ⚠️

This is a demonstration showing how a cadastral API could work theoretically.
DO NOT use with Croatian government production systems.

- Uses mock server by default (http://localhost:8000)
- For educational and testing purposes only
- Production use is NOT AUTHORIZED due to sensitive data and terms of service
- Author available to advise Croatian government on official AI implementation

See README.md for full disclaimer.
"""

import click
from rich.console import Console

from .. import CadastralAPIClient, __version__
from ..exceptions import CadastralAPIError
from ..i18n import _, get_current_language, set_language, SUPPORTED_LANGUAGES
from .commands import batch, cache, discovery, gis, parcel, search

console = Console()


@click.group()
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
    """
    Croatian Cadastral System CLI - Access cadastral and land registry data.

    \b
    Examples:
      cadastral search 103/2 --municipality SAVAR
      cadastral get-parcel 103/2 -m 334979 --show-owners
      cadastral list-municipalities --office 114
      cadastral get-geometry 103/2 -m 334979 --format wkt

    Documentation: https://github.com/yourusername/croatian-cadastral-api
    """
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
            raise SystemExit(1)
    else:
        ctx.obj["lang"] = get_current_language()


# Register command groups
cli.add_command(search.search)
cli.add_command(search.search_municipality)
cli.add_command(parcel.get_parcel)
cli.add_command(batch.batch_fetch)
cli.add_command(gis.get_geometry)
cli.add_command(gis.download_gis)
cli.add_command(discovery.list_offices)
cli.add_command(discovery.list_municipalities)
cli.add_command(discovery.info)
cli.add_command(cache.cache_group)


def main() -> None:
    """Entry point for CLI."""
    try:
        cli(obj={})
    except CadastralAPIError as e:
        console.print(_("\n✗ Error: {error}").format(error=e), style="bold red")
        raise SystemExit(1)
    except KeyboardInterrupt:
        console.print(_("\n\nOperation cancelled by user."), style="yellow")
        raise SystemExit(130)
    except Exception as e:
        console.print(_("\n✗ Unexpected error: {error}").format(error=e), style="bold red")
        try:
            if "--verbose" in click.get_current_context().args:
                raise
        except RuntimeError:
            pass  # No context available
        raise SystemExit(1)


if __name__ == "__main__":
    main()
