"""Land registry unit commands for CLI."""

from typing import Any

import click
from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.i18n import _, ngettext
from cadastral_api.models.entities import FileStatus, LandRegistryUnitDetailed
from cadastral_api.utils import display_parcel_number
from rich.console import Console
from rich.table import Table

from cadastral_cli.formatters import (
    command_help,
    describe_error,
    error_type_value_label,
    print_error,
    print_output,
    print_success,
)
from cadastral_cli.input_parsers import LRUnitInput, parse_lr_unit_file
from cadastral_cli.list_processing import ListSummary, lr_unit_row, process_lr_unit_list
from cadastral_cli.lr_unit_output import print_lr_unit_full

from .search import _resolve_municipality

console = Console()


_GET_LR_UNIT_HELP = command_help(_("""Get detailed land registry unit information.

Retrieve complete information about a land registry unit (zemljišnoknjižni uložak),
including ownership (Sheet B), parcels (Sheet A), and encumbrances (Sheet C).

One unit, named by number and main book or found from a parcel; or a list of
units from a file with --input: a CSV or JSON with lr_unit_number and
main_book_id, or the JSON that get-parcel writes for a list of parcels.

Examples:
  # Get by unit number and main book ID
  cadastral get-lr-unit --unit-number 769 --main-book 21277

  # Get by unit number and main book name (resolved through the main-book search)
  cadastral get-lr-unit --unit-number 769 --main-book-name SAVAR

  # Get from parcel (automatic lookup)
  cadastral get-lr-unit --from-parcel 279/6 -m SAVAR

  # Show only ownership information
  cadastral get-lr-unit -u 769 -b 21277 --show-owners

  # Show all sheets
  cadastral get-lr-unit -p 279/6 -m SAVAR --all

  # Export to JSON
  cadastral get-lr-unit -u 769 -b 21277 --format json --output lr-unit.json

  # Several units from a file, all sheets of each
  cadastral get-lr-unit --input lr_units.csv --all

  # The units of a list of parcels (pipeline)
  cadastral get-parcel "103/2,45,396/1" -m SAVAR --detail registry --format json -o parcels.json
  cadastral get-lr-unit --input parcels.json --show-owners

⚠️  Demo project: before using any server other than the included mock, verify
your rights to use it; use at your own risk"""))


@click.command("get-lr-unit", help=_GET_LR_UNIT_HELP)
@click.option("--unit-number", "-u", help=_("Land registry unit number (e.g., '769')"))
@click.option("--main-book", "-b", type=int, help=_("Main book ID (e.g., 21277)"))
@click.option(
    "--main-book-name", "-n", help=_("Main book name (e.g., SAVAR), used instead of the ID")
)
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
    "--input",
    "-i",
    "input_file",
    type=click.Path(exists=True),
    help=_("File (CSV or JSON) with the units to read, or a get-parcel list result"),
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help=_("Output format"),
)
@click.option("--output", type=click.Path(), help=_("Save output to file"))
@click.option(
    "--continue-on-error/--stop-on-error",
    default=True,
    help=_("Continue processing after errors (default: continue)"),
)
@click.pass_context
def get_lr_unit(
    ctx: click.Context,
    unit_number: str | None,
    main_book: int | None,
    main_book_name: str | None,
    from_parcel: str | None,
    municipality: str | None,
    show_owners: bool,
    show_parcels: bool,
    show_encumbrances: bool,
    plombe_detail: bool,
    show_all: bool,
    input_file: str | None,
    output_format: str,
    output: str | None,
    continue_on_error: bool,
) -> None:
    """Get detailed land registry unit information."""
    # Validate arguments
    if input_file:
        if unit_number or main_book or main_book_name or from_parcel:
            print_error(
                _("Cannot combine --input with --unit-number, --main-book or --from-parcel")
            )
            raise SystemExit(1)
        _get_lr_unit_list(
            ctx,
            input_file,
            show_owners,
            show_parcels,
            show_encumbrances,
            plombe_detail,
            show_all,
            output_format,
            output,
            continue_on_error,
        )
        return
    if from_parcel:
        if not municipality:
            print_error(_("--municipality is required when using --from-parcel"))
            raise SystemExit(1)
        if unit_number or main_book or main_book_name:
            print_error(_("Cannot use --unit-number or --main-book with --from-parcel"))
            raise SystemExit(1)
    elif not (unit_number and (main_book or main_book_name)):
        print_error(
            _("Either --from-parcel or --unit-number with --main-book or --main-book-name "
              "are required")
        )
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
                    lr_unit = client.get_lr_unit_detailed(
                        unit_number, main_book, main_book_name=main_book_name
                    )

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
        reason = e.details.get("reason")
        if e.error_type == ErrorType.LR_UNIT_NOT_FOUND:
            if reason == "parcel_not_in_land_registry" and e.details.get("is_building_parcel"):
                print_error(
                    _("Building parcel {parcel} has no land registry unit of its own; "
                      "the building is registered on its land parcel").format(
                        parcel=display_parcel_number(e.details.get("parcel_number", from_parcel))
                    )
                )
            elif reason == "main_book_ambiguous":
                print_error(
                    _("Main book name '{name}' matches several books: {candidates}. "
                      "Use --main-book with the ID").format(
                        name=main_book_name, candidates=e.details.get("candidates", "")
                    )
                )
            elif reason == "main_book_not_found":
                print_error(_("Main book '{name}' not found").format(name=main_book_name))
            elif reason == "lr_unit_ambiguous":
                print_error(
                    _("Parcel {parcel} is linked to several land registry units: {candidates}. "
                      "Use --unit-number and --main-book to choose one").format(
                        parcel=e.details.get("parcel_number", from_parcel),
                        candidates=e.details.get("candidates", ""),
                    )
                )
            else:
                print_error(_("Land registry unit not found"))
        elif e.error_type == ErrorType.PARCEL_NOT_FOUND:
            if reason == "only_building_parcel_exists":
                print_error(
                    _("There is no land parcel {parcel}, only the building parcel zgr. {parcel}. "
                      "Write it as '{parcel} ZGR'").format(
                        parcel=e.details.get("parcel_number", from_parcel)
                    )
                )
            else:
                print_error(_("Parcel not found"))
        else:
            print_error(_("API error: {error}").format(error=describe_error(e)))
        raise SystemExit(1) from e


# ---------------------------------------------------------------------------
# A list of units
# ---------------------------------------------------------------------------


def _get_lr_unit_list(
    ctx: click.Context,
    input_file: str,
    show_owners: bool,
    show_parcels: bool,
    show_encumbrances: bool,
    plombe_detail: bool,
    show_all: bool,
    output_format: str,
    output: str | None,
    continue_on_error: bool,
) -> None:
    """Read several units from a file and report one record per unit."""
    try:
        try:
            if output_format == "table":
                console.print(
                    _("📄 Reading LR units from: {file}").format(file=input_file), style="dim"
                )
            inputs = parse_lr_unit_file(input_file)
        except (ValueError, FileNotFoundError) as e:
            print_error(_("Input parsing error: {error}").format(error=str(e)))
            raise SystemExit(1) from e

        if output_format == "table":
            console.print(
                ngettext(
                    "📊 Found {count} LR unit to process\n",
                    "📊 Found {count} LR units to process\n",
                    len(inputs),
                ).format(count=len(inputs)),
                style="dim",
            )

        with_sheets = show_owners or show_parcels or show_encumbrances or show_all
        plombe: dict[int, dict[str, FileStatus]] = {}
        with CadastralAPIClient() as client:
            summary = process_lr_unit_list(
                client, inputs, continue_on_error=continue_on_error, show_progress=True
            )
            if plombe_detail:
                for result in summary.results:
                    if result.ok and result.data is not None and result.data.has_pending_plombe():
                        plombe[id(result)] = client.get_plombe_details(result.data)

        if output_format == "table":
            printed = 0
            for result in summary.results:
                if not result.ok or result.data is None:
                    continue
                if printed:
                    console.print("\n---\n")
                print_lr_unit_full(
                    result.data,
                    show_owners,
                    show_parcels,
                    show_encumbrances,
                    show_all,
                    plombe.get(id(result)),
                )
                printed += 1
            if summary.failed and printed:
                console.print("\n---\n")
            _print_list_errors(summary)
        elif output_format == "json":
            rows = []
            for result in summary.results:
                row = lr_unit_row(result)
                if result.ok and result.data is not None and with_sheets:
                    row["full_data"] = _format_structured_data(
                        result.data,
                        show_owners,
                        show_parcels,
                        show_encumbrances,
                        show_all,
                        plombe.get(id(result)),
                    )
                rows.append(row)
            print_output(summary.envelope(rows), output_format="json", file=output)
        else:
            rows = []
            for result in summary.results:
                row = lr_unit_row(result)
                if show_owners and result.ok and result.data is not None:
                    owners = []
                    for owner in result.data.ownership_sheet_b.owner_rows():
                        frac = owner["share"]
                        share = (
                            f"{frac['num']}/{frac['den']}" if frac else owner["share_description"]
                        )
                        owners.append(f"{owner['name']} ({share})")
                    row["owners"] = "; ".join(owners)
                rows.append(row)
            print_output(rows, output_format="csv", file=output)

        _print_list_footer(summary)
        if summary.failed > 0:
            raise SystemExit(1)

    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=describe_error(e)))
        if e.details:
            console.print(_("   Details: {details}").format(details=e.details), style="dim red")
        raise SystemExit(1) from e
    except SystemExit:
        raise
    except Exception as e:
        print_error(_("Unexpected error: {error}").format(error=str(e)))
        if ctx.obj.get("verbose"):
            raise
        raise SystemExit(1) from e


def _print_list_errors(summary: ListSummary[LRUnitInput, LandRegistryUnitDetailed]) -> None:
    if summary.failed == 0:
        return
    header = _("ERRORS")
    console.print(header, style="bold red")
    console.print("=" * len(header), style="bold red")
    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column("#", justify="right", style="dim")
    table.add_column(_("LR Unit"), style="bold")
    table.add_column(_("Error Type"))
    table.add_column(_("Error Message"))
    for index, result in enumerate(summary.results, 1):
        if result.status == "error":
            table.add_row(
                str(index),
                f"{result.input.lr_unit_number} ({_('Main Book')} {result.input.main_book_id})",
                error_type_value_label(result.error_type),
                result.error_message or _("No error message"),
            )
    console.print(table)


def _print_list_footer(summary: ListSummary[LRUnitInput, LandRegistryUnitDetailed]) -> None:
    console.print()
    if summary.failed == 0:
        print_success(
            ngettext(
                "Successfully processed {total} LR unit",
                "Successfully processed all {total} LR units",
                summary.total,
            ).format(total=summary.total)
        )
        return
    console.print(
        _("⚠️  Processed {successful}/{total} LR units ({rate}% success rate)").format(
            successful=summary.successful, total=summary.total, rate=f"{summary.success_rate:.1f}"
        ),
        style="yellow",
    )
    console.print(
        ngettext(
            "   {count} LR unit failed - see output for details",
            "   {count} LR units failed - see output for details",
            summary.failed,
        ).format(count=summary.failed),
        style="yellow",
    )


# ---------------------------------------------------------------------------
# One unit
# ---------------------------------------------------------------------------


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
        # Which key the server used for sheet A1: lrParcels (land-register
        # records, address = culture/toponym) or cadParcels (cadastre records).
        "source_key": lr_unit.sheet_a1_source_key,
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

    # Add owners if requested. Each row carries ``entry``, the registration
    # entry that put the owner on the share; ``share_entries`` are the
    # annotations (zabilježbe) registered on individual shares.
    if show_owners or show_all:
        data["owners"] = lr_unit.ownership_sheet_b.owner_rows()
        data["share_entries"] = lr_unit.ownership_sheet_b.share_entry_rows()

    # Add parcels if requested
    if show_parcels or show_all:
        parcels = []
        for parcel in lr_unit.get_all_parcels():
            parcels.append({
                "parcel_number": parcel.parcel_number,
                "parcel_id": parcel.parcel_id,
                "area": parcel.area_numeric,
                "address": parcel.address,
                "parcel_parts": [
                    {
                        "type": part.name,
                        "area": part.area_numeric,
                        "has_building": part.building,
                        "part_type": part.part_type,
                        "building_right": part.building_right,
                    }
                    for part in parcel.parcel_parts
                ],
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
                    "priority_diary_number": entry.priority_diary_number,
                    "description_text": entry.description_text,
                    "style_class": entry.style_class,
                    # Secured amount of a mortgage or lien, as sent and parsed
                    "amount": entry.amount,
                    "amount_value": (
                        float(entry.amount_value) if entry.amount_value is not None else None
                    ),
                    "amount_currency": entry.amount_currency,
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
