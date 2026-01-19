"""Search commands for CLI."""

import click
from rich.console import Console

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.i18n import _, ngettext
from cadastral_cli.formatters import format_table, print_error, print_output

console = Console()


@click.command()
@click.argument("parcel_number")
@click.option("--municipality", "-m", required=True, help="Municipality name or code (e.g., SAVAR or 334979)")
@click.option("--exact/--partial", default=True, help="Exact match or partial search")
@click.option("--format", "-f", "output_format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.option("--output", "-o", type=click.Path(), help="Save output to file")
@click.pass_context
def search(ctx: click.Context, parcel_number: str, municipality: str, exact: bool, output_format: str, output: str | None) -> None:
    """
    Quick search for parcels with basic information.

    \b
    Examples:
      cadastral search 103/2 --municipality SAVAR
      cadastral search 103/2 -m 334979
      cadastral search 114 -m 334979 --partial
    """
    try:
        with CadastralAPIClient() as client:
            # Resolve municipality
            municipality_code = _resolve_municipality(client, municipality)

            # Search for parcel
            with console.status(_("Searching for parcel {parcel_number}...").format(
                parcel_number=parcel_number
            )):
                parcel = client.get_parcel_by_number(parcel_number, municipality_code, exact_match=exact)

            if not parcel:
                print_error(_("Parcel '{parcel_number}' not found in municipality {municipality}").format(
                    parcel_number=parcel_number,
                    municipality=municipality
                ))
                console.print(f"\n{_('Suggestions')}:", style="yellow")
                console.print(
                    f"  • {_('Try partial search')}: cadastral search {parcel_number} "
                    f"-m {municipality} --partial"
                )
                console.print(f"  • {_('Check parcel number format')}")
                console.print(f"  • {_('View on map')}: https://oss.uredjenazemlja.hr/map")
                raise SystemExit(1)

            # Format basic output
            data = {
                _("Parcel Number"): parcel.parcel_number,
                _("Municipality"): f"{parcel.municipality_name} ({parcel.municipality_reg_num})",
                _("Address"): parcel.address or _("N/A"),
                _("Area"): f"{parcel.area_numeric:,} m²" if parcel.area_numeric else _("N/A"),
                _("Land Use"): ", ".join(parcel.land_use_summary.keys()) if parcel.land_use_summary else _("N/A"),
                _("Building Permitted"): _("Yes") if parcel.has_building_right else _("No"),
                _("Owners"): (
                    ngettext("{count} owner", "{count} owners", parcel.total_owners).format(
                        count=parcel.total_owners
                    )
                    if parcel.total_owners
                    else _("Unknown")
                ),
            }

            if output_format == "table":
                console.print(format_table(data), highlight=False)
                console.print(
                    f"\n💡 {_('For full details')}: cadastral get-parcel {parcel_number} "
                    f"-m {municipality_code}",
                    style="dim"
                )
            else:
                # For JSON/CSV, use more detailed structure
                export_data = {
                    "parcel_number": parcel.parcel_number,
                    "municipality_code": parcel.municipality_reg_num,
                    "municipality_name": parcel.municipality_name,
                    "address": parcel.address,
                    "area_m2": parcel.area_numeric,
                    "land_use": list(parcel.land_use_summary.keys()),
                    "building_permitted": parcel.has_building_right,
                    "total_owners": parcel.total_owners,
                    "parcel_id": parcel.parcel_id,
                }
                print_output(export_data, output_format=output_format, file=output)

    except CadastralAPIError as e:
        if e.error_type == ErrorType.PARCEL_NOT_FOUND:
            parcel_num = e.details.get("parcel_number", parcel_number)
            muni_code = e.details.get("municipality_reg_num", municipality)
            print_error(_("Parcel '{parcel_number}' not found in municipality {municipality}").format(
                parcel_number=parcel_num,
                municipality=muni_code
            ))
        elif e.error_type == ErrorType.MUNICIPALITY_NOT_FOUND:
            search = e.details.get("search_term", municipality)
            print_error(_("Municipality '{municipality}' not found").format(municipality=search))
        else:
            print_error(_("API error: {error_type}").format(error_type=e.error_type.value))
        raise SystemExit(1)


@click.command("search-municipality")
@click.argument("search_term", required=False)
@click.option("--office", "-o", help="Filter by cadastral office ID (e.g., 114)")
@click.option("--department", "-d", help="Filter by department ID (e.g., 116)")
@click.option("--format", "-f", "output_format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.option("--output", "-out", type=click.Path(), help="Save output to file")
@click.option("--count-only", is_flag=True, help="Show count only")
@click.pass_context
def search_municipality(
    ctx: click.Context,
    search_term: str | None,
    office: str | None,
    department: str | None,
    output_format: str,
    output: str | None,
    count_only: bool
) -> None:
    """
    Search and filter municipalities.

    \b
    Examples:
      cadastral search-municipality SAVAR
      cadastral search-municipality --office 114
      cadastral search-municipality --office 114 --department 116
      cadastral search-municipality SAVAR --office 114
    """
    if not search_term and not office and not department:
        print_error(_("At least one of search_term, --office, or --department is required"))
        console.print(f"\n{_('Try')}: cadastral search-municipality --help", style="yellow")
        raise SystemExit(1)

    try:
        with CadastralAPIClient() as client:
            with console.status(_("Finding municipalities...")):
                results = client.find_municipality(
                    search_term=search_term,
                    office_id=office,
                    department_id=department
                )

            if not results:
                print_error(_("No municipalities found"))
                raise SystemExit(1)

            if count_only:
                console.print(
                    _("Found {count} municipality(ies)").format(count=len(results)),
                    style="green"
                )
                return

            # Format output
            data = [
                {
                    _("Code"): m.municipality_reg_num,
                    _("Name"): m.municipality_name,
                    _("Office"): m.institution_id,
                    _("Department"): m.department_id or _("N/A"),
                }
                for m in results
            ]

            if output_format == "table":
                filter_desc = []
                if search_term:
                    filter_desc.append(f"search='{search_term}'")
                if office:
                    filter_desc.append(f"office={office}")
                if department:
                    filter_desc.append(f"department={department}")

                console.print(
                    _("\nFound {count} municipalities ({filters}):\n").format(
                        count=len(results),
                        filters=', '.join(filter_desc)
                    ),
                    style="green"
                )
                print_output(data, output_format="table")
            else:
                # For JSON/CSV export
                export_data = [
                    {
                        "municipality_code": m.municipality_reg_num,
                        "municipality_name": m.municipality_name,
                        "office_id": m.institution_id,
                        "department_id": m.department_id,
                        "display_name": m.display_value,
                    }
                    for m in results
                ]
                print_output(export_data, output_format=output_format, file=output)

    except CadastralAPIError as e:
        if e.error_type == ErrorType.MUNICIPALITY_NOT_FOUND:
            search = e.details.get("search_term", search_term or "")
            print_error(_("No municipalities found for '{search}'").format(search=search))
        else:
            print_error(_("API error: {error_type}").format(error_type=e.error_type.value))
        raise SystemExit(1) from e


def _resolve_municipality(client: CadastralAPIClient, municipality: str) -> str:
    """
    Resolve municipality name to code.

    Args:
        client: API client
        municipality: Municipality name or code

    Returns:
        Municipality registration number

    Raises:
        SystemExit: If municipality not found
    """
    # If it's already a code (all digits), return it
    if municipality.isdigit():
        return municipality

    # Find by name
    try:
        results = client.find_municipality(municipality)
        if not results:
            print_error(_("Municipality '{municipality}' not found").format(
                municipality=municipality
            ))
            console.print(f"\n{_('Suggestions')}:", style="yellow")
            console.print(
                f"  • {_('Search for municipalities')}: "
                f"cadastral search-municipality {municipality}"
            )
            console.print(f"  • {_('List all municipalities')}: cadastral list-municipalities")
            console.print(f"  • {_('Use municipality code directly')}: --municipality 334979")
            raise SystemExit(1)

        if len(results) > 1:
            print_error(_("Multiple municipalities found for '{municipality}'").format(
                municipality=municipality
            ))
            console.print(f"\n{_('Please specify using municipality code')}:", style="yellow")
            for r in results[:5]:
                console.print(f"  • {r.municipality_reg_num} - {r.municipality_name}")
            raise SystemExit(1)

        return results[0].municipality_reg_num

    except CadastralAPIError as e:
        if e.error_type == ErrorType.MUNICIPALITY_NOT_FOUND:
            search = e.details.get("search_term", municipality)
            print_error(_("Municipality '{municipality}' not found").format(municipality=search))
        else:
            print_error(_("Failed to resolve municipality: {error_type}").format(
                error_type=e.error_type.value
            ))
        raise SystemExit(1) from e
