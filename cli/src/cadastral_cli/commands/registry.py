"""Land registry unit commands for CLI."""

import click
from rich.console import Console

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.i18n import _
from cadastral_cli.formatters import print_error, print_output
from cadastral_cli.lr_unit_output import print_lr_unit_full
from .search import _resolve_municipality

console = Console()


@click.command("get-lr-unit")
@click.option("--unit-number", "-u", help="Land registry unit number (e.g., '769')")
@click.option("--main-book", "-b", type=int, help="Main book ID (e.g., 21277)")
@click.option("--from-parcel", "-p", help="Get LR unit from parcel number")
@click.option("--municipality", "-m", help="Municipality name or code (required with --from-parcel)")
@click.option("--show-owners", "-o", is_flag=True, help="Display ownership details (Sheet B)")
@click.option("--show-parcels", "-P", is_flag=True, help="Display all parcels in unit (Sheet A)")
@click.option("--show-encumbrances", "-e", is_flag=True, help="Display encumbrances (Sheet C)")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show all sheets")
@click.option("--format", "-f", "output_format", type=click.Choice(["table", "json", "csv"]), default="table", help="Output format")
@click.option("--output", type=click.Path(), help="Save output to file")
@click.option("--lang", type=click.Choice(["hr", "en"]), help="Language for output")
@click.pass_context
def get_lr_unit(
    ctx: click.Context,
    unit_number: str | None,
    main_book: int | None,
    from_parcel: str | None,
    municipality: str | None,
    show_owners: bool,
    show_parcels: bool,
    show_encumbrances: bool,
    show_all: bool,
    output_format: str,
    output: str | None,
    lang: str | None,
) -> None:
    """
    Get detailed land registry unit information.

    Retrieve complete information about a land registry unit (zemljišnoknjižni uložak),
    including ownership (Sheet B), parcels (Sheet A), and encumbrances (Sheet C).

    \b
    Examples:
      # Get by unit number and main book ID
      cadastral get-lr-unit --unit-number 769 --main-book 21277

      # Get from parcel (automatic lookup)
      cadastral get-lr-unit --from-parcel 279/6 -m SAVAR

      # Show only ownership information
      cadastral get-lr-unit -u 769 -b 21277 --show-owners

      # Show all sheets
      cadastral get-lr-unit -p 279/6 -m SAVAR --all

      # Export to JSON
      cadastral get-lr-unit -u 769 -b 21277 --format json -o lr-unit.json

    \b
    ⚠️  DEMO/EDUCATIONAL USE ONLY - Mock server data only
    """
    # Validate arguments
    if from_parcel:
        if not municipality:
            print_error(_("--municipality is required when using --from-parcel"))
            raise SystemExit(1)
        if unit_number or main_book:
            print_error(_("Cannot use --unit-number or --main-book with --from-parcel"))
            raise SystemExit(1)
    elif not (unit_number and main_book):
        print_error(_("Either --from-parcel or both --unit-number and --main-book are required"))
        raise SystemExit(1)

    try:
        with CadastralAPIClient() as client:
            # Get LR unit
            if from_parcel:
                municipality_code = _resolve_municipality(client, municipality)
                with console.status(_("Fetching land registry unit from parcel {parcel}...").format(
                    parcel=from_parcel
                )):
                    lr_unit = client.get_lr_unit_from_parcel(from_parcel, municipality_code)
            else:
                with console.status(_("Fetching land registry unit {unit}...").format(
                    unit=unit_number
                )):
                    lr_unit = client.get_lr_unit_detailed(unit_number, main_book)

            # Format output
            if output_format != "table":
                # Structured output
                data = _format_structured_data(lr_unit, show_owners, show_parcels, show_encumbrances, show_all)
                print_output(data, output_format=output_format, file=output)
            else:
                # Rich table output
                print_lr_unit_full(lr_unit, show_owners, show_parcels, show_encumbrances, show_all)

    except CadastralAPIError as e:
        if e.error_type == ErrorType.LR_UNIT_NOT_FOUND:
            print_error(_("Land registry unit not found"))
        elif e.error_type == ErrorType.PARCEL_NOT_FOUND:
            print_error(_("Parcel not found"))
        else:
            print_error(_("API error: {error_type}").format(error_type=e.error_type.value))
        raise SystemExit(1) from e


def _format_structured_data(
    lr_unit,
    show_owners: bool,
    show_parcels: bool,
    show_encumbrances: bool,
    show_all: bool,
) -> dict:
    """Format LR unit data for JSON/CSV output."""
    data = {
        "lr_unit_number": lr_unit.lr_unit_number,
        "main_book_name": lr_unit.main_book_name,
        "institution_name": lr_unit.institution_name,
        "status": lr_unit.status_name,
        "unit_type": lr_unit.lr_unit_type_name,
        "last_diary_number": lr_unit.last_diary_number,
    }

    # Add summary
    summary = lr_unit.summary()
    data["summary"] = summary

    # Add owners if requested
    if show_owners or show_all:
        owners = []
        for share in lr_unit.ownership_sheet_b.lr_unit_shares:
            if share.is_active:
                for owner in share.owners:
                    owners.append({
                        "name": owner.name,
                        "address": owner.address,
                        "tax_number": owner.tax_number,
                        "share": share.description,
                    })
        data["owners"] = owners

    # Add parcels if requested
    if show_parcels or show_all:
        parcels = []
        for parcel in lr_unit.get_all_parcels():
            parcels.append({
                "parcel_number": parcel.parcel_number,
                "area": parcel.area_numeric,
                "address": parcel.address,
            })
        data["parcels"] = parcels

    # Add encumbrances if requested
    if show_encumbrances or show_all:
        encumbrances = []
        for group in lr_unit.encumbrance_sheet_c.lr_entry_groups:
            encumbrances.append({
                "description": group.description,
                "entries": [entry.description for entry in group.lr_entries],
            })
        data["encumbrances"] = encumbrances

    return data
