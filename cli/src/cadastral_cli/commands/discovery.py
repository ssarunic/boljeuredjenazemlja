"""Discovery commands for CLI - list offices, municipalities, etc."""

import click
from rich.console import Console

from cadastral_api import CadastralAPIClient, __version__
from cadastral_api.exceptions import CadastralAPIError
from cadastral_api.i18n import _
from cadastral_cli.formatters import print_error, print_output

console = Console()


@click.command("list-offices")
@click.option("--format", "-f", "output_format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.option("--output", "-o", type=click.Path(), help="Save output to file")
@click.pass_context
def list_offices(ctx: click.Context, output_format: str, output: str | None) -> None:
    """
    List all cadastral offices in Croatia.

    \b
    Example:
      cadastral list-offices
      cadastral list-offices --format json
    """
    try:
        with CadastralAPIClient() as client:
            with console.status(_("Fetching cadastral offices...")):
                offices = client.list_cadastral_offices()

            if not offices:
                console.print(_("No offices found"), style="yellow")
                return

            # Format output
            data = [
                {
                    _("ID"): office.id,
                    _("Name"): office.name,
                }
                for office in offices
            ]

            if output_format == "table":
                console.print(_("\n{count} Cadastral Offices in Croatia:\n").format(
                    count=len(offices)
                ), style="green")
                print_output(data, format="table")
            else:
                export_data = [
                    {
                        "office_id": office.id,
                        "office_name": office.name,
                    }
                    for office in offices
                ]
                print_output(export_data, format=output_format, file=output)

    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=str(e)))
        raise SystemExit(1)


@click.command("list-municipalities")
@click.option("--office", "-o", help="Filter by cadastral office ID")
@click.option("--department", "-d", help="Filter by department ID")
@click.option("--search", "-s", help="Search by name")
@click.option("--format", "-f", "output_format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.option("--output", "-out", type=click.Path(), help="Save output to file")
@click.option("--count-only", is_flag=True, help="Show count only")
@click.pass_context
def list_municipalities(
    ctx: click.Context,
    office: str | None,
    department: str | None,
    search: str | None,
    output_format: str,
    output: str | None,
    count_only: bool
) -> None:
    """
    List municipalities with optional filtering.

    \b
    Examples:
      cadastral list-municipalities
      cadastral list-municipalities --office 114
      cadastral list-municipalities --office 114 --department 116
      cadastral list-municipalities --search ZADAR
    """
    try:
        with CadastralAPIClient() as client:
            # Build filter description
            filter_parts = []
            if search:
                filter_parts.append(f"search='{search}'")
            if office:
                filter_parts.append(f"office={office}")
            if department:
                filter_parts.append(f"department={department}")

            status_msg = _("Fetching municipalities")
            if filter_parts:
                status_msg += _(" ({filters})").format(filters=', '.join(filter_parts))
            status_msg += "..."

            with console.status(status_msg):
                municipalities = client.search_municipality(
                    search_term=search,
                    office_id=office,
                    department_id=department
                )

            if not municipalities:
                console.print(_("No municipalities found"), style="yellow")
                return

            if count_only:
                console.print(_("Found {count} municipality(ies)").format(
                    count=len(municipalities)
                ), style="green")
                return

            # Format output
            data = [
                {
                    _("Code"): m.municipality_reg_num,
                    _("Name"): m.municipality_name,
                    _("Office"): m.institution_id,
                    _("Department"): m.department_id or _("N/A"),
                }
                for m in municipalities
            ]

            if output_format == "table":
                filter_desc = _(" ({filters})").format(filters=', '.join(filter_parts)) if filter_parts else ""
                console.print(_("\n{count} municipalities{filter_desc}:\n").format(
                    count=len(municipalities),
                    filter_desc=filter_desc
                ), style="green")
                print_output(data, format="table")
            else:
                export_data = [
                    {
                        "municipality_code": m.municipality_reg_num,
                        "municipality_name": m.municipality_name,
                        "office_id": m.institution_id,
                        "department_id": m.department_id,
                        "display_name": m.display_value,
                    }
                    for m in municipalities
                ]
                print_output(export_data, format=output_format, file=output)

    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=str(e)))
        raise SystemExit(1)


@click.command("info")
@click.pass_context
def info(ctx: click.Context) -> None:
    """
    Display system information and cache status.

    \b
    Example:
      cadastral info
    """
    try:
        with CadastralAPIClient() as client:
            header = _("Croatian Cadastral CLI")
            console.print(f"\n{header}", style="bold cyan")
            console.print("=" * len(header), style="bold cyan")
            console.print(_("Version: {version}").format(version=__version__))
            console.print(_("API Base: {base_url}").format(base_url=client.base_url))
            console.print()

            header = _("Cache Information")
            console.print(f"{header}", style="bold cyan")
            console.print("=" * len(header), style="bold cyan")
            cache_dir = client.gis_cache.cache_dir
            console.print(_("Cache Directory: {cache_dir}").format(cache_dir=cache_dir))

            # Check cache size and cached municipalities
            import os
            from pathlib import Path

            if cache_dir.exists():
                total_size = 0
                cached_munis = []

                for item in cache_dir.iterdir():
                    if item.is_dir() and item.name.startswith("ko-"):
                        # Calculate directory size
                        dir_size = sum(f.stat().st_size for f in item.rglob('*') if f.is_file())
                        total_size += dir_size

                        # Extract municipality code
                        muni_code = item.name.replace("ko-", "")
                        size_kb = dir_size / 1024
                        cached_munis.append(f"  • {muni_code} ({size_kb:.1f} KB)")

                if cached_munis:
                    console.print(_("Cache Size: {size} MB").format(
                        size=f"{total_size / 1024 / 1024:.1f}"
                    ))
                    console.print(_("Cached Municipalities: {count}").format(
                        count=len(cached_munis)
                    ))
                    for muni in cached_munis[:10]:  # Show first 10
                        console.print(muni)
                    if len(cached_munis) > 10:
                        console.print(_("  ... and {more} more").format(
                            more=len(cached_munis) - 10
                        ))
                else:
                    console.print(_("Cache is empty"))
            else:
                console.print(_("Cache directory does not exist yet"))

            console.print()
            header = _("API Settings")
            console.print(f"{header}", style="bold cyan")
            console.print("=" * len(header), style="bold cyan")
            console.print(_("Rate Limit: {rate_limit} seconds between requests").format(
                rate_limit=client.rate_limit
            ))
            console.print(_("Timeout: {timeout} seconds").format(
                timeout=client.timeout
            ))
            console.print()

            console.print(_("To clear cache: cadastral cache clear --all"), style="dim")

    except Exception as e:
        print_error(_("Error getting system info: {error}").format(error=str(e)))
        raise SystemExit(1)
