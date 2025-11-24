"""Batch land registry unit commands for CLI."""

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.i18n import _, ngettext
from cadastral_api.models.entities import LandRegistryUnitDetailed
from cadastral_cli.formatters import print_error, print_success, print_output
from cadastral_cli.lr_unit_output import print_lr_unit_full

console = Console()


@dataclass
class LRUnitInput:
    """Represents a single LR unit input specification."""

    lr_unit_number: str
    main_book_id: int

    def __repr__(self) -> str:
        """String representation."""
        return f"LRUnitInput(lr_unit_number={self.lr_unit_number}, main_book_id={self.main_book_id})"


@dataclass
class LRUnitResult:
    """Result of processing a single LR unit in a batch."""

    status: str  # "success" or "error"
    input: LRUnitInput
    lr_unit_data: LandRegistryUnitDetailed | None = None
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self, include_full_data: bool = False) -> dict[str, Any]:
        """Convert to dictionary for output."""
        result: dict[str, Any] = {
            "status": self.status,
            "lr_unit_number": self.input.lr_unit_number,
            "main_book_id": self.input.main_book_id,
        }

        if self.status == "success" and self.lr_unit_data:
            summary = self.lr_unit_data.summary()
            result["main_book_name"] = self.lr_unit_data.main_book_name
            result["institution_name"] = self.lr_unit_data.institution_name
            result["status_name"] = self.lr_unit_data.status_name
            result["total_parcels"] = summary["total_parcels"]
            result["total_area_m2"] = summary["total_area_m2"]
            result["num_owners"] = summary["num_owners"]
            result["has_encumbrances"] = summary["has_encumbrances"]

            if include_full_data:
                # Include detailed ownership and parcel information
                result["owners"] = []
                for share in self.lr_unit_data.ownership_sheet_b.lr_unit_shares:
                    if share.is_active:
                        for owner in share.owners:
                            result["owners"].append({
                                "name": owner.name,
                                "address": owner.address,
                                "tax_number": owner.tax_number,
                                "share": share.description,
                            })

                result["parcels"] = []
                for parcel in self.lr_unit_data.get_all_parcels():
                    result["parcels"].append({
                        "parcel_number": parcel.parcel_number,
                        "area": parcel.area_numeric,
                        "address": parcel.address,
                    })
        else:
            result["error_type"] = self.error_type
            result["error_message"] = self.error_message

        return result


@dataclass
class LRUnitBatchSummary:
    """Summary of batch LR unit processing results."""

    total: int
    successful: int
    failed: int
    results: list[LRUnitResult]

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        return (self.successful / self.total * 100) if self.total > 0 else 0

    def to_dict(self, include_full_data: bool = False) -> dict[str, Any]:
        """Convert to dictionary for output."""
        return {
            "summary": {
                "total": self.total,
                "successful": self.successful,
                "failed": self.failed,
                "success_rate": f"{self.success_rate:.1f}%",
            },
            "results": [r.to_dict(include_full_data=include_full_data) for r in self.results],
        }


def _parse_lr_unit_csv(file_path: Path) -> list[LRUnitInput]:
    """Parse CSV file with LR unit specifications.

    Expected format:
        lr_unit_number,main_book_id
        769,21277
        123,45678

    Args:
        file_path: Path to CSV file

    Returns:
        List of LRUnitInput objects
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    inputs = []
    with file_path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)

        if not reader.fieldnames:
            raise ValueError("CSV file is empty or has no header")

        if "lr_unit_number" not in reader.fieldnames or "main_book_id" not in reader.fieldnames:
            raise ValueError("CSV must have 'lr_unit_number' and 'main_book_id' columns")

        for row_num, row in enumerate(reader, start=2):
            lr_unit_number = row.get("lr_unit_number", "").strip()
            main_book_id_str = row.get("main_book_id", "").strip()

            if not lr_unit_number:
                raise ValueError(f"Row {row_num}: lr_unit_number cannot be empty")
            if not main_book_id_str:
                raise ValueError(f"Row {row_num}: main_book_id cannot be empty")

            try:
                main_book_id = int(main_book_id_str)
            except ValueError:
                raise ValueError(f"Row {row_num}: main_book_id must be an integer")

            inputs.append(LRUnitInput(lr_unit_number=lr_unit_number, main_book_id=main_book_id))

    if not inputs:
        raise ValueError("No valid LR units found in CSV file")

    return inputs


def _parse_lr_unit_json(file_path: Path) -> list[LRUnitInput]:
    """Parse JSON file with LR unit specifications.

    Expected format:
        [
            {"lr_unit_number": "769", "main_book_id": 21277},
            {"lr_unit_number": "123", "main_book_id": 45678}
        ]

    Args:
        file_path: Path to JSON file

    Returns:
        List of LRUnitInput objects
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with file_path.open(encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("JSON must be an array of LR unit objects")

    if not data:
        raise ValueError("JSON array is empty")

    inputs = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {idx}: must be an object with lr_unit_number and main_book_id")

        lr_unit_number = str(item.get("lr_unit_number", "")).strip()
        main_book_id = item.get("main_book_id")

        if not lr_unit_number:
            raise ValueError(f"Item {idx}: lr_unit_number is required")
        if main_book_id is None:
            raise ValueError(f"Item {idx}: main_book_id is required")
        if not isinstance(main_book_id, int):
            raise ValueError(f"Item {idx}: main_book_id must be an integer")

        inputs.append(LRUnitInput(lr_unit_number=lr_unit_number, main_book_id=main_book_id))

    return inputs


def _parse_batch_fetch_output(file_path: Path) -> list[LRUnitInput]:
    """Parse batch-fetch JSON output and extract unique LR units.

    Reads JSON output from batch-fetch command and extracts unique
    LR unit references (lr_unit_number + main_book_id pairs).

    Args:
        file_path: Path to batch-fetch JSON output file

    Returns:
        List of unique LRUnitInput objects
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    with file_path.open(encoding="utf-8") as f:
        data = json.load(f)

    # Handle both direct array and object with "results" key
    if isinstance(data, dict) and "results" in data:
        results = data["results"]
    elif isinstance(data, list):
        results = data
    else:
        raise ValueError("Invalid batch-fetch output format")

    # Extract unique LR units
    seen = set()
    inputs = []

    for item in results:
        if item.get("status") != "success":
            continue

        lr_unit_number = item.get("lr_unit_number")
        main_book_id = item.get("main_book_id")

        if not lr_unit_number or main_book_id is None:
            continue

        # Deduplicate
        key = (lr_unit_number, main_book_id)
        if key in seen:
            continue
        seen.add(key)

        inputs.append(LRUnitInput(lr_unit_number=lr_unit_number, main_book_id=main_book_id))

    if not inputs:
        raise ValueError("No LR unit references found in batch-fetch output")

    return inputs


def _parse_lr_unit_input(file_path: str | Path) -> list[LRUnitInput]:
    """Auto-detect file format and parse LR unit input.

    Args:
        file_path: Path to input file (.csv or .json)

    Returns:
        List of LRUnitInput objects
    """
    file_path = Path(file_path)
    suffix = file_path.suffix.lower()

    if suffix == ".csv":
        return _parse_lr_unit_csv(file_path)
    elif suffix == ".json":
        return _parse_lr_unit_json(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix} (use .csv or .json)")


def _process_lr_unit_batch(
    client: CadastralAPIClient,
    inputs: list[LRUnitInput],
    continue_on_error: bool = True,
    show_progress: bool = True,
) -> LRUnitBatchSummary:
    """Process a batch of LR unit lookups.

    Args:
        client: API client instance
        inputs: List of LR unit input specifications
        continue_on_error: Continue processing after errors
        show_progress: Show progress bar

    Returns:
        LRUnitBatchSummary with results
    """
    results: list[LRUnitResult] = []
    successful = 0
    failed = 0

    if show_progress:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        )
        task = progress.add_task(_("Processing LR units..."), total=len(inputs))
        progress.start()
    else:
        progress = None
        task = None

    try:
        for i, lr_input in enumerate(inputs, 1):
            if progress and task is not None:
                progress.update(
                    task,
                    description=_("Processing {current}/{total}: LR unit {unit}").format(
                        current=i, total=len(inputs), unit=lr_input.lr_unit_number
                    ),
                    completed=i - 1,
                )

            try:
                lr_unit_data = client.get_lr_unit_detailed(
                    lr_input.lr_unit_number,
                    lr_input.main_book_id,
                )

                results.append(
                    LRUnitResult(
                        status="success",
                        input=lr_input,
                        lr_unit_data=lr_unit_data,
                    )
                )
                successful += 1

            except CadastralAPIError as e:
                error_msg = str(e) or e.error_type.value
                results.append(
                    LRUnitResult(
                        status="error",
                        input=lr_input,
                        error_type=e.error_type.value,
                        error_message=error_msg,
                    )
                )
                failed += 1

                if not continue_on_error:
                    raise

            except Exception as e:
                results.append(
                    LRUnitResult(
                        status="error",
                        input=lr_input,
                        error_type="unexpected_error",
                        error_message=str(e),
                    )
                )
                failed += 1

                if not continue_on_error:
                    raise

    finally:
        if progress:
            progress.stop()

    return LRUnitBatchSummary(
        total=len(inputs),
        successful=successful,
        failed=failed,
        results=results,
    )


def _print_table_output(summary: LRUnitBatchSummary, show_owners: bool) -> None:
    """Print results as rich formatted tables - same format as get-lr-unit --all."""
    # Track if we've printed any successful LR units
    printed_count = 0

    # Print each successful LR unit in full detail
    for result in summary.results:
        if result.status == "success" and result.lr_unit_data:
            if printed_count > 0:
                console.print("\n---\n")

            # Use shared print function with show_all=True
            print_lr_unit_full(result.lr_unit_data, show_all=True)
            printed_count += 1

    # Print errors if any
    if summary.failed > 0:
        if printed_count > 0:
            console.print("\n---\n")
        header = _("ERRORS")
        console.print(f"{header}", style="bold red")
        console.print("=" * len(header), style="bold red")

        error_table = Table(show_header=True, box=None, padding=(0, 2))
        error_table.add_column("#", justify="right", style="dim")
        error_table.add_column(_("LR Unit"), style="bold")
        error_table.add_column(_("Error Type"))
        error_table.add_column(_("Error Message"))

        error_num = 0
        for result in summary.results:
            if result.status == "error":
                error_num += 1
                error_table.add_row(
                    str(error_num),
                    f"{result.input.lr_unit_number} (book: {result.input.main_book_id})",
                    result.error_type or _("unknown"),
                    result.error_message or _("No error message"),
                )

        console.print(error_table)


def _format_csv_data(summary: LRUnitBatchSummary, show_owners: bool) -> list[dict]:
    """Format batch results for CSV export."""
    rows = []

    for result in summary.results:
        row = result.to_dict(include_full_data=False)

        if result.status == "success" and result.lr_unit_data and show_owners:
            # Add ownership summary
            owners = []
            for share in result.lr_unit_data.ownership_sheet_b.lr_unit_shares:
                if share.is_active:
                    for owner in share.owners:
                        share_text = share.description.split(":")[-1].strip() if ":" in share.description else share.description
                        owners.append(f"{owner.name} ({share_text})")
            row["owners_list"] = "; ".join(owners)

        rows.append(row)

    return rows


@click.command("batch-lr-unit")
@click.option(
    "--input",
    "-i",
    "input_file",
    type=click.Path(exists=True),
    help="Input file (CSV or JSON) with LR unit specifications",
)
@click.option(
    "--from-batch-output",
    "-b",
    "batch_output_file",
    type=click.Path(exists=True),
    help="Read LR unit refs from batch-fetch JSON output",
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
def batch_lr_unit(
    ctx: click.Context,
    input_file: str | None,
    batch_output_file: str | None,
    output: str | None,
    output_format: str,
    show_owners: bool,
    continue_on_error: bool,
) -> None:
    """
    Fetch information for multiple land registry units in batch mode.

    Supports two input methods:

    \b
    1. Direct LR unit file (CSV or JSON):
       cadastral batch-lr-unit --input lr_units.csv

    \b
    2. From batch-fetch output (reads unique LR unit refs):
       cadastral batch-fetch "103/2,45" -m SAVAR --format json -o parcels.json
       cadastral batch-lr-unit --from-batch-output parcels.json

    \b
    CSV Format:
      lr_unit_number,main_book_id
      769,21277
      123,45678

    \b
    JSON Format:
      [
        {"lr_unit_number": "769", "main_book_id": 21277},
        {"lr_unit_number": "123", "main_book_id": 45678}
      ]

    \b
    Examples:
      # From direct LR unit input
      cadastral batch-lr-unit --input lr_units.csv

      # From batch-fetch output (pipeline)
      cadastral batch-fetch "103/2,45,396/1" -m SAVAR --format json -o parcels.json
      cadastral batch-lr-unit --from-batch-output parcels.json

      # With ownership details in JSON format
      cadastral batch-lr-unit -i lr_units.json --show-owners --format json -o results.json

    \b
    ⚠️  DEMO/EDUCATIONAL USE ONLY - Mock server data only
    """
    try:
        # Validate input
        if not input_file and not batch_output_file:
            print_error(_("Must provide either --input file or --from-batch-output file"))
            console.print("\nUse 'cadastral batch-lr-unit --help' for usage information.")
            raise SystemExit(1)

        if input_file and batch_output_file:
            print_error(_("Cannot use both --input and --from-batch-output"))
            raise SystemExit(1)

        # Parse input
        try:
            if batch_output_file:
                console.print(f"📄 Reading LR unit refs from batch-fetch output: {batch_output_file}", style="dim")
                lr_unit_list = _parse_batch_fetch_output(Path(batch_output_file))
            else:
                console.print(f"📄 Reading LR units from: {input_file}", style="dim")
                lr_unit_list = _parse_lr_unit_input(input_file)

        except (ValueError, FileNotFoundError) as e:
            print_error(_("Input parsing error: {error}").format(error=str(e)))
            raise SystemExit(1)

        unit_count_msg = ngettext(
            "📊 Found {count} LR unit to process\n",
            "📊 Found {count} LR units to process\n",
            len(lr_unit_list)
        ).format(count=len(lr_unit_list))
        console.print(unit_count_msg, style="dim")

        # Process batch
        with CadastralAPIClient() as client:
            summary = _process_lr_unit_batch(
                client=client,
                inputs=lr_unit_list,
                continue_on_error=continue_on_error,
                show_progress=True,
            )

        # Format and display results
        if output_format == "table":
            _print_table_output(summary, show_owners)
        elif output_format == "json":
            data = summary.to_dict(include_full_data=show_owners)
            print_output(data, format="json", file=output)
        elif output_format == "csv":
            data = _format_csv_data(summary, show_owners)
            print_output(data, format="csv", file=output)

        # Print summary
        console.print()
        if summary.failed == 0:
            print_success(
                _("✓ Successfully processed all {total} LR unit(s)").format(
                    total=summary.total
                )
            )
        else:
            console.print(
                _("⚠️  Processed {successful}/{total} LR units ({rate}% success rate)").format(
                    successful=summary.successful,
                    total=summary.total,
                    rate=f"{summary.success_rate:.1f}"
                ),
                style="yellow",
            )
            failed_msg = ngettext(
                "   {count} LR unit failed - see output for details",
                "   {count} LR units failed - see output for details",
                summary.failed
            ).format(count=summary.failed)
            console.print(failed_msg, style="yellow")

        # Exit with error code if any failures
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
