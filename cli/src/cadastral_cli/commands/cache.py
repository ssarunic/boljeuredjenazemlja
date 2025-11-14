"""Cache management commands for CLI."""

import click
from rich.console import Console
from rich.table import Table

from cadastral_api import CadastralAPIClient
from cadastral_apii18n import _
from cadastral_cliformatters import print_error, print_success

console = Console()


@click.group("cache")
def cache_group() -> None:
    """
    Cache management commands.

    \b
    Examples:
      cadastral cache list
      cadastral cache clear --municipality 334979
      cadastral cache clear --all
    """
    pass


@cache_group.command("list")
@click.pass_context
def cache_list(ctx: click.Context) -> None:
    """
    List cached municipalities.

    \b
    Example:
      cadastral cache list
    """
    try:
        import os
        from datetime import datetime

        with CadastralAPIClient() as client:
            cache_dir = client.gis_cache.cache_dir

            if not cache_dir.exists():
                console.print(_("Cache directory does not exist yet"), style="yellow")
                return

            # Find cached municipalities
            cached = []
            total_size = 0

            for item in cache_dir.iterdir():
                if item.is_dir() and item.name.startswith("ko-"):
                    # Extract municipality code
                    muni_code = item.name.replace("ko-", "")

                    # Calculate directory size
                    dir_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                    total_size += dir_size

                    # Get last modified time
                    zip_file = item / f"ko-{muni_code}.zip"
                    if zip_file.exists():
                        mtime = datetime.fromtimestamp(zip_file.stat().st_mtime)
                        last_modified = mtime.strftime("%Y-%m-%d %H:%M")
                    else:
                        last_modified = _("N/A")

                    cached.append({
                        "municipality": muni_code,
                        "size": dir_size,
                        "last_modified": last_modified,
                    })

            if not cached:
                console.print(_("Cache is empty"), style="yellow")
                console.print(_("\nDownload GIS data: cadastral download-gis <municipality> -o ./output"), style="dim")
                return

            # Sort by municipality code
            cached.sort(key=lambda x: x["municipality"])

            console.print(_("\nCached GIS Data ({count} municipalities):\n").format(
                count=len(cached)
            ), style="green")

            table = Table(show_header=True, box=None, padding=(0, 2))
            table.add_column(_("Municipality"), style="bold")
            table.add_column(_("Size"), justify="right")
            table.add_column(_("Last Modified"))

            for item in cached:
                size_kb = item["size"] / 1024
                table.add_row(
                    item["municipality"],
                    f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB",
                    item["last_modified"]
                )

            console.print(table)
            console.print(_("\nTotal Cache Size: {size} MB").format(
                size=f"{total_size / 1024 / 1024:.1f}"
            ), style="bold")
            console.print(_("Cache Location: {cache_dir}").format(
                cache_dir=cache_dir
            ), style="dim")

    except Exception as e:
        print_error(_("Error listing cache: {error}").format(error=str(e)))
        raise SystemExit(1)


@cache_group.command("clear")
@click.option("--municipality", "-m", help="Clear specific municipality")
@click.option("--all", "-a", "clear_all", is_flag=True, help="Clear all cache")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation")
@click.pass_context
def cache_clear(ctx: click.Context, municipality: str | None, clear_all: bool, force: bool) -> None:
    """
    Clear cached GIS data.

    \b
    Examples:
      cadastral cache clear --municipality 334979
      cadastral cache clear --all
      cadastral cache clear -m SAVAR --force
    """
    if not municipality and not clear_all:
        print_error(_("Either --municipality or --all is required"))
        console.print(_("\nTry: cadastral cache clear --help"), style="yellow")
        raise SystemExit(1)

    try:
        with CadastralAPIClient() as client:
            if clear_all:
                # Confirm deletion
                if not force:
                    console.print(_("This will delete ALL cached GIS data."), style="yellow bold")
                    if not click.confirm(_("Are you sure?")):
                        console.print(_("Cancelled."), style="yellow")
                        return

                cache_dir = client.gis_cache.cache_dir
                if not cache_dir.exists():
                    console.print(_("Cache is already empty"), style="yellow")
                    return

                # Calculate size before clearing
                import os
                total_size = sum(
                    f.stat().st_size for f in cache_dir.rglob('*') if f.is_file()
                )

                with console.status(_("Clearing all cache...")):
                    client.gis_cache.clear_all()

                print_success(_("Cleared all cache ({size} MB freed)").format(
                    size=f"{total_size / 1024 / 1024:.1f}"
                ))

            else:
                # Clear specific municipality
                from .search import _resolve_municipality

                municipality_code = _resolve_municipality(client, municipality)

                # Check if cached
                if not client.gis_cache.is_cached(municipality_code):
                    console.print(_("Municipality {municipality_code} is not cached").format(
                        municipality_code=municipality_code
                    ), style="yellow")
                    return

                # Get size
                muni_dir = client.gis_cache.get_municipality_dir(municipality_code)
                dir_size = sum(f.stat().st_size for f in muni_dir.rglob('*') if f.is_file())

                with console.status(_("Clearing cache for municipality {municipality_code}...").format(
                    municipality_code=municipality_code
                )):
                    client.gis_cache.clear_municipality(municipality_code)

                print_success(_("Cleared municipality {municipality_code} ({size} KB freed)").format(
                    municipality_code=municipality_code,
                    size=f"{dir_size / 1024:.1f}"
                ))

    except SystemExit:
        raise
    except Exception as e:
        print_error(_("Error clearing cache: {error}").format(error=str(e)))
        raise SystemExit(1)


@cache_group.command("info")
@click.pass_context
def cache_info(ctx: click.Context) -> None:
    """
    Show detailed cache information.

    \b
    Example:
      cadastral cache info
    """
    try:
        with CadastralAPIClient() as client:
            cache_dir = client.gis_cache.cache_dir

            header = _("CACHE INFORMATION")
            console.print(f"\n{header}", style="bold cyan")
            console.print("=" * len(header), style="bold cyan")
            console.print(_("Location: {cache_dir}").format(cache_dir=cache_dir))

            if not cache_dir.exists():
                console.print(_("Status: Empty (directory does not exist)"), style="yellow")
                return

            # Count files and calculate sizes
            import os
            total_size = 0
            zip_count = 0
            gml_count = 0
            muni_count = 0

            for item in cache_dir.rglob('*'):
                if item.is_file():
                    size = item.stat().st_size
                    total_size += size

                    if item.suffix == '.zip':
                        zip_count += 1
                    elif item.suffix == '.gml':
                        gml_count += 1

            for item in cache_dir.iterdir():
                if item.is_dir() and item.name.startswith("ko-"):
                    muni_count += 1

            console.print(_("Status: Active"), style="green")
            console.print(_("Total Size: {size} MB").format(
                size=f"{total_size / 1024 / 1024:.2f}"
            ))
            console.print(_("Municipalities: {count}").format(count=muni_count))
            console.print(_("ZIP Files: {count}").format(count=zip_count))
            console.print(_("GML Files: {count}").format(count=gml_count))

            console.print(_("\nTo list cached municipalities: cadastral cache list"), style="dim")
            console.print(_("To clear cache: cadastral cache clear --all"), style="dim")

    except Exception as e:
        print_error(_("Error getting cache info: {error}").format(error=str(e)))
        raise SystemExit(1)
