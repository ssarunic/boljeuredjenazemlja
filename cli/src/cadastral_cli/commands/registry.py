"""Land registry unit commands for CLI."""

from typing import Any

import click
from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.i18n import _
from cadastral_api.models.entities import FileStatus, LandRegistryUnitDetailed
from rich.console import Console

from cadastral_cli.formatters import command_help, describe_error, print_error, print_output
from cadastral_cli.lr_unit_output import print_lr_unit_full

from .search import _resolve_municipality

console = Console()


_GET_LR_UNIT_HELP = command_help(_("""Get detailed land registry unit information.

Retrieve complete information about a land registry unit (zemljišnoknjižni uložak),
including ownership (Sheet B), parcels (Sheet A), and encumbrances (Sheet C).

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

⚠️  DEMO/EDUCATIONAL USE ONLY - Mock server data only"""))


@click.command("get-lr-unit", help=_GET_LR_UNIT_HELP)
@click.option("--unit-number", "-u", help=_("Land registry unit number (e.g., '769')"))
@click.option("--main-book", "-b", type=int, help=_("Main book ID (e.g., 21277)"))
@click.option("--from-parcel", "-p", help=_("Get LR unit from parcel number"))
@click.option(
    "--municipality", "-m", help=_("Municipality name or code (required with --from-parcel)")
)
@click.option("--show-owners", "-o", is_flag=True, help=_("Display ownership details (Sheet B)"))
@click.option("--show-parcels", "-P", is_flag=True, help=_("Display all parcels in unit (Sheet A)"))
@click.option("--show-encumbrances", "-e", is_flag=True, help=_("Display encumbrances (Sheet C)"))
@click.option(
    "--plombe-detail",
    "-D",
    is_flag=True,
    help=_("Resolve detail of pending entries (plombe) - one extra request per plomba"),
)
@click.option("--all", "-a", "show_all", is_flag=True, help=_("Show all sheets"))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help=_("Output format"),
)
@click.option("--output", type=click.Path(), help=_("Save output to file"))
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
    plombe_detail: bool,
    show_all: bool,
    output_format: str,
    output: str | None,
) -> None:
    """Get detailed land registry unit information."""
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

            # Resolve plomba detail on request (one extra request per plomba).
            plombe_details = None
            if plombe_detail and lr_unit.has_pending_plombe():
                with console.status(_("Resolving pending entries (plombe) detail...")):
                    plombe_details = client.get_plombe_details(lr_unit)

            # Format output
            if output_format != "table":
                # Structured output
                data = _format_structured_data(
                    lr_unit, show_owners, show_parcels, show_encumbrances, show_all, plombe_details
                )
                print_output(data, output_format=output_format, file=output)
            else:
                # Rich table output
                print_lr_unit_full(
                    lr_unit, show_owners, show_parcels, show_encumbrances, show_all, plombe_details
                )

                # Disclose cadastre/ZK divergence and offer the cadastre drill-down
                # (only meaningful when we came from a specific parcel).
                if from_parcel and lr_unit.cadastre_harmonized is False:
                    console.print(
                        _("⚠️  Cadastre and land registry are NOT harmonized for this "
                          "parcel - possessors (kataster) and registered owners (ZK) "
                          "may differ."),
                        style="yellow",
                    )
                    drill = (
                        f"cadastral get-parcel {from_parcel} "
                        f"-m {municipality} --show-owners"
                    )
                    console.print(
                        "   " + _("To see the other register, run: {command}").format(
                            command=drill
                        ),
                        style="dim",
                    )

    except CadastralAPIError as e:
        if e.error_type == ErrorType.LR_UNIT_NOT_FOUND:
            print_error(_("Land registry unit not found"))
        elif e.error_type == ErrorType.PARCEL_NOT_FOUND:
            print_error(_("Parcel not found"))
        else:
            print_error(_("API error: {error}").format(error=describe_error(e)))
        raise SystemExit(1) from e


def _format_structured_data(
    lr_unit: LandRegistryUnitDetailed,
    show_owners: bool,
    show_parcels: bool,
    show_encumbrances: bool,
    show_all: bool,
    plombe_details: dict[str, FileStatus] | None = None,
) -> dict[str, Any]:
    """Format LR unit data for JSON/CSV output."""
    data = {
        "lr_unit_number": lr_unit.lr_unit_number,
        "main_book_name": lr_unit.main_book_name,
        "institution_name": lr_unit.institution_name,
        "status": lr_unit.status_name,
        "unit_type": lr_unit.lr_unit_type_name,
        "last_diary_number": lr_unit.last_diary_number,
        "active_plumbs": [p.model_dump(by_alias=False) for p in lr_unit.active_plumbs],
        "cadastre_harmonized": lr_unit.cadastre_harmonized,
    }

    # Plomba detail (only when --plombe-detail was requested and resolved).
    if plombe_details is not None:
        data["plombe_detail"] = {
            file_number: status.model_dump(mode="json", by_alias=False)
            for file_number, status in plombe_details.items()
        }

    # Add summary
    summary = lr_unit.summary()
    data["summary"] = summary

    # Add owners if requested
    if show_owners or show_all:
        data["owners"] = lr_unit.ownership_sheet_b.owner_rows()

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
            entries = []
            for entry in group.lr_entries:
                item: dict[str, Any] = {
                    "order_number": entry.order_number,
                    "description": entry.description,
                    "action_type": entry.action_type.value if entry.action_type else None,
                    "diary_number": entry.diary_number,
                    "entry_date": entry.entry_date.isoformat() if entry.entry_date else None,
                    "basis_document": entry.basis_document,
                    "basis_date": entry.basis_date.isoformat() if entry.basis_date else None,
                    "beneficiaries": [
                        {
                            "name": p.name,
                            "name_normalized": p.name_normalized,
                            "share": p.share,
                            "address": p.address,
                            "tax_number": p.tax_number,
                        }
                        for p in entry.get_parties()
                    ],
                }
                # Whatever else the server nested under the entry, verbatim
                # (keys are data, not localized).
                if entry.source_fields:
                    item["source_fields"] = entry.source_fields
                entries.append(item)
            encumbrances.append({
                "description": group.description,
                "share_order_number": group.share_order_number,
                "right_type": group.right_type.value if group.right_type else None,
                "entries": entries,
            })
        data["encumbrances"] = encumbrances

    return data
