"""Batch parcel information commands for CLI."""

import click
from rich.console import Console

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError
from cadastral_api.i18n import _, ngettext
from cadastral_cli.batch_processor import process_batch
from cadastral_cli.formatters import print_error, print_success, print_output
from cadastral_cli.input_parsers import parse_cli_list, parse_input_file

console = Console()


@click.command("batch-fetch")
@click.argument("parcels", required=False)
@click.option(
    "--input",
    "-i",
    "input_file",
    type=click.Path(exists=True),
    help="Input file (CSV or JSON) with parcel specifications",
)
@click.option(
    "--municipality",
    "-m",
    help="Municipality name or code (required for CLI list mode)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Save output to file",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="Output format",
)
@click.option(
    "--detail",
    type=click.Choice(["basic", "full"]),
    default="basic",
    help="Detail level: basic (summary only) or full (complete parcel info for each)",
)
@click.option(
    "--show-owners",
    is_flag=True,
    help="Include detailed ownership information in output",
)
@click.option(
    "--continue-on-error/--stop-on-error",
    default=True,
    help="Continue processing after errors (default: continue)",
)
@click.pass_context
def batch_fetch(
    ctx: click.Context,
    parcels: str | None,
    input_file: str | None,
    municipality: str | None,
    output: str | None,
    output_format: str,
    detail: str,
    show_owners: bool,
    continue_on_error: bool,
) -> None:
    """
    Fetch information for multiple parcels in batch mode.

    Supports two input methods:

    \b
    1. CLI comma-separated list (for quick batches):
       cadastral batch-fetch "103/2,45,396/1" --municipality SAVAR

    \b
    2. File input (for large batches):
       cadastral batch-fetch --input parcels.csv
       cadastral batch-fetch --input parcels.json

    \b
    CSV Format (parcel numbers with municipality):
      parcel_number,municipality
      103/2,334979
      45,
      396/1,

    Note: Empty municipality cells inherit from the previous row.

    \b
    CSV Format (direct parcel IDs):
      parcel_id
      12345678
      87654321

    \b
    JSON Format:
      [
        {"parcel_number": "103/2", "municipality": "334979"},
        {"parcel_number": "45", "municipality": "SAVAR"}
      ]

    Or:
      [
        {"parcel_id": "12345678"},
        {"parcel_id": "87654321"}
      ]

    \b
    Examples:
      # Quick batch with CLI list
      cadastral batch-fetch "103/2,45,396/1" -m SAVAR

      # Batch from CSV file
      cadastral batch-fetch --input parcels.csv --format csv -o results.csv

      # Batch with full details for each parcel (like get-parcel)
      cadastral batch-fetch "103/2,45,396/1" -m SAVAR --detail full

      # Batch with ownership details in JSON format
      cadastral batch-fetch --input parcels.json --show-owners --format json -o results.json
    """
    try:
        # Validate input
        if not parcels and not input_file:
            print_error(_("Must provide either PARCELS argument or --input file"))
            console.print("\nUse 'cadastral batch-fetch --help' for usage information.")
            raise SystemExit(1)

        if parcels and input_file:
            print_error(_("Cannot use both PARCELS argument and --input file"))
            raise SystemExit(1)

        # Parse input
        try:
            if input_file:
                # File input mode
                console.print(f"📄 Reading parcels from: {input_file}", style="dim")
                parcel_list = parse_input_file(input_file)
            else:
                # CLI list mode
                if not municipality:
                    print_error(_("--municipality/-m required when using CLI list mode"))
                    raise SystemExit(1)

                parcel_list = parse_cli_list(parcels, municipality)

        except ValueError as e:
            print_error(_("Input parsing error: {error}").format(error=str(e)))
            raise SystemExit(1)

        parcel_count_msg = ngettext(
            "📊 Found {count} parcel to process\n",
            "📊 Found {count} parcels to process\n",
            len(parcel_list)
        ).format(count=len(parcel_list))
        console.print(parcel_count_msg, style="dim")

        # Process batch
        with CadastralAPIClient() as client:
            summary = process_batch(
                client=client,
                parcels=parcel_list,
                continue_on_error=continue_on_error,
                show_progress=True,
            )

        # Format and display results
        if output_format == "table":
            _print_table_output(summary, detail, show_owners)
        elif output_format == "json":
            data = summary.to_dict(include_full_data=(show_owners or detail == "full"))
            print_output(data, format="json", file=output)
        elif output_format == "csv":
            data = _format_csv_data(summary, show_owners)
            print_output(data, format="csv", file=output)

        # Print summary
        console.print()
        if summary.failed == 0:
            print_success(
                _("✓ Successfully processed all {total} parcel(s)").format(
                    total=summary.total
                )
            )
        else:
            console.print(
                _("⚠️  Processed {successful}/{total} parcels ({rate}% success rate)").format(
                    successful=summary.successful,
                    total=summary.total,
                    rate=f"{summary.success_rate:.1f}"
                ),
                style="yellow",
            )
            failed_msg = ngettext(
                "   {count} parcel failed - see output for details",
                "   {count} parcels failed - see output for details",
                summary.failed
            ).format(count=summary.failed)
            console.print(failed_msg, style="yellow")

        # Exit with error code if any failures (only in non-interactive mode)
        if summary.failed > 0:
            raise SystemExit(1)

    except CadastralAPIError as e:
        print_error(_("API error: {error_type}").format(error_type=e.error_type.value))
        if hasattr(e, 'details') and e.details:
            console.print(f"   Details: {e.details}", style="dim red")
        raise SystemExit(1)
    except Exception as e:
        print_error(_("Unexpected error: {error}").format(error=str(e)))
        if ctx.obj.get("verbose"):
            raise
        raise SystemExit(1)


def _print_detailed_parcels(summary, show_owners: bool) -> None:
    """Print detailed information for each parcel (similar to get-parcel output)."""
    from .parcel import print_parcel_details

    # Create API client for fetching geometry data
    with CadastralAPIClient() as client:
        for i, result in enumerate(summary.results, 1):
            if result.status == "error":
                # Print error info
                console.print(f"\n[bold red]━━━ {_('Parcel')} {i}/{summary.total}: ✗ {_('ERROR')} ━━━[/bold red]")
                if result.input.parcel_id:
                    console.print(f"{_('Parcel ID')}: {result.input.parcel_id}")
                else:
                    console.print(f"{_('Parcel')}: {result.input.parcel_number} ({result.input.municipality})")
                console.print(f"{_('Error')}: {result.error_type or _('unknown')}")
                console.print(f"{_('Message')}: {result.error_message or _('No error message')}")
                continue

            # Print detailed parcel info
            parcel = result.parcel_data
            if not parcel:
                continue

            # Fetch geometry for accurate MAP URL with center coordinates
            geometry = None
            try:
                geometry = client.get_parcel_geometry(
                    parcel.parcel_number,
                    parcel.municipality_reg_num
                )
            except Exception:
                # Silently ignore geometry fetch errors, will use fallback MAP URL
                pass

            # Use unified function for consistent output (including MAP URL)
            print_parcel_details(
                parcel=parcel,
                geometry=geometry,
                show_owners=show_owners,
                show_geometry=False,
                parcel_index=i,
                total_parcels=summary.total
            )


def _print_table_output(summary, detail: str, show_owners: bool) -> None:
    """Print results as rich formatted tables."""
    from rich.table import Table

    # Print summary
    header = _("BATCH PROCESSING SUMMARY")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")
    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column(_("Field"), style="bold")
    summary_table.add_column(_("Value"))

    summary_table.add_row(_("Total Parcels"), str(summary.total))
    summary_table.add_row(
        _("Successful"), f"[green]{summary.successful}[/green]"
    )
    summary_table.add_row(_("Failed"), f"[red]{summary.failed}[/red]")
    summary_table.add_row(_("Success Rate"), f"{summary.success_rate:.1f}%")

    console.print(summary_table)
    console.print()

    # If detail is "full", print detailed info for each parcel
    if detail == "full":
        _print_detailed_parcels(summary, show_owners)
        return

    # Print results table
    header = _("RESULTS")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")
    results_table = Table(show_header=True, box=None, padding=(0, 2))
    results_table.add_column("#", justify="right", style="dim")
    results_table.add_column(_("Status"), justify="center")
    results_table.add_column(_("Parcel"), style="bold")
    results_table.add_column(_("Municipality"))
    results_table.add_column(_("Area (m²)"), justify="right")
    results_table.add_column(_("Parcel ID"))
    results_table.add_column(_("LR Unit"))

    if show_owners:
        results_table.add_column(_("Owners"), justify="right")

    for i, result in enumerate(summary.results, 1):
        # Format status
        if result.status == "success":
            status = "[green]✓[/green]"
        else:
            status = "[red]✗[/red]"

        # Format parcel identifier
        if result.input.parcel_id:
            parcel_display = f"ID: {result.input.parcel_id}"
        else:
            parcel_display = result.input.parcel_number

        # Format row data
        if result.status == "success" and result.parcel_data:
            municipality = f"{result.parcel_data.municipality_name} ({result.parcel_data.municipality_reg_num})"
            area = f"{result.parcel_data.area_numeric:,}" if result.parcel_data.area_numeric else "N/A"
            parcel_id = str(result.parcel_data.parcel_id)
            # Format LR unit reference
            if result.parcel_data.lr_unit:
                lr_unit = result.parcel_data.lr_unit.lr_unit_number
            else:
                lr_unit = "-"
            owners = str(result.parcel_data.total_owners) if show_owners else ""

            row = [str(i), status, parcel_display, municipality, area, parcel_id, lr_unit]
            if show_owners:
                row.append(owners)
            results_table.add_row(*row)
        else:
            # Error row
            municipality = result.input.municipality or "N/A"
            error_msg = f"[red]{result.error_type or 'error'}[/red]"

            row = [str(i), status, parcel_display, municipality, error_msg, "-", "-"]
            if show_owners:
                row.append("-")
            results_table.add_row(*row)

    console.print(results_table)

    # Print failed parcels details if any
    if summary.failed > 0:
        header = _("ERRORS")
        console.print(f"\n{header}", style="bold red")
        console.print("=" * len(header), style="bold red")
        error_table = Table(show_header=True, box=None, padding=(0, 2))
        error_table.add_column("#", justify="right", style="dim")
        error_table.add_column(_("Parcel"), style="bold")
        error_table.add_column(_("Error Type"))
        error_table.add_column(_("Error Message"))

        error_count = 0
        for i, result in enumerate(summary.results, 1):
            if result.status == "error":
                error_count += 1
                if result.input.parcel_id:
                    parcel_display = f"ID: {result.input.parcel_id}"
                else:
                    parcel_display = f"{result.input.parcel_number} ({result.input.municipality})"

                error_table.add_row(
                    str(i),
                    parcel_display,
                    result.error_type or _("unknown"),
                    result.error_message or _("No error message"),
                )

        console.print(error_table)


def _format_csv_data(summary, show_owners: bool) -> list[dict]:
    """Format batch results for CSV export."""
    rows = []

    for result in summary.results:
        row = result.to_dict(include_full_data=False)

        # Flatten for CSV format
        if result.status == "success" and result.parcel_data:
            if show_owners and result.parcel_data.possession_sheets:
                # Add ownership summary
                owners = []
                for sheet in result.parcel_data.possession_sheets:
                    for possessor in sheet.possessors:
                        owners.append(f"{possessor.name} ({possessor.ownership})")
                row["owners"] = "; ".join(owners)

        rows.append(row)

    return rows
