"""Batch processing logic for multiple parcel lookups."""

from dataclasses import dataclass
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from cadastral_cli import CadastralAPIClient
from cadastral_cliexceptions import CadastralAPIError, ErrorType
from cadastral_climodels.entities import ParcelInfo
from .input_parsers import ParcelInput

console = Console()


@dataclass
class BatchResult:
    """Result of processing a single parcel in a batch."""

    status: str  # "success" or "error"
    input: ParcelInput
    parcel_data: ParcelInfo | None = None
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self, include_full_data: bool = False) -> dict[str, Any]:
        """Convert to dictionary for output."""
        result: dict[str, Any] = {
            "status": self.status,
        }

        # Add input information
        if self.input.parcel_id:
            result["parcel_id"] = self.input.parcel_id
        else:
            result["parcel_number"] = self.input.parcel_number
            result["municipality"] = self.input.municipality

        # Add result data
        if self.status == "success" and self.parcel_data:
            result["parcel_id"] = self.parcel_data.parcel_id
            result["parcel_number"] = self.parcel_data.parcel_number
            result["municipality_code"] = self.parcel_data.municipality_reg_num
            result["municipality_name"] = self.parcel_data.municipality_name
            result["area_m2"] = self.parcel_data.area_numeric
            result["building_permitted"] = self.parcel_data.has_building_right
            result["total_owners"] = self.parcel_data.total_owners

            if include_full_data:
                result["full_data"] = {
                    "address": self.parcel_data.address,
                    "land_use": self.parcel_data.land_use_summary,
                    "ownership": [
                        {
                            "sheet_number": sheet.possession_sheet_number,
                            "possessors": [
                                {
                                    "name": p.name,
                                    "ownership": p.ownership,
                                    "ownership_decimal": p.ownership_decimal,
                                    "address": p.address,
                                }
                                for p in sheet.possessors
                            ],
                        }
                        for sheet in self.parcel_data.possession_sheets
                    ],
                }
        else:
            result["error_type"] = self.error_type
            result["error_message"] = self.error_message

        return result


@dataclass
class BatchSummary:
    """Summary of batch processing results."""

    total: int
    successful: int
    failed: int
    results: list[BatchResult]

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


def _resolve_municipality(client: CadastralAPIClient, municipality: str) -> str:
    """Resolve municipality name to registration number.

    Args:
        client: API client instance
        municipality: Municipality name or registration number

    Returns:
        Municipality registration number

    Raises:
        CadastralAPIError: If municipality not found
    """
    # If already a numeric code, return as-is
    if municipality.isdigit() and len(municipality) == 6:
        return municipality

    # Search for municipality
    results = client.search_municipality(search_term=municipality)

    if not results:
        raise CadastralAPIError(
            ErrorType.MUNICIPALITY_NOT_FOUND,
            details={"search_term": municipality},
        )

    # Use first exact match or first result
    for result in results:
        if result.municipality_name.upper() == municipality.upper():
            return result.municipality_reg_num

    # Fallback to first result
    return results[0].municipality_reg_num


def process_batch(
    client: CadastralAPIClient,
    parcels: list[ParcelInput],
    continue_on_error: bool = True,
    show_progress: bool = True,
) -> BatchSummary:
    """Process a batch of parcel lookups.

    Args:
        client: API client instance
        parcels: List of parcel input specifications
        continue_on_error: Continue processing after errors
        show_progress: Show progress bar

    Returns:
        BatchSummary with results

    Raises:
        CadastralAPIError: If continue_on_error=False and an error occurs
    """
    results: list[BatchResult] = []
    successful = 0
    failed = 0

    # Create progress bar
    if show_progress:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console,
        )
        task = progress.add_task("Processing parcels...", total=len(parcels))
        progress.start()
    else:
        progress = None
        task = None

    try:
        for i, parcel_input in enumerate(parcels, 1):
            # Update progress
            if progress and task is not None:
                progress.update(
                    task,
                    description=f"Processing {i}/{len(parcels)}: {parcel_input}",
                    completed=i - 1,
                )

            try:
                # Process based on input type
                if parcel_input.is_direct_id:
                    # Direct parcel ID lookup
                    parcel_data = client.get_parcel_info(parcel_input.parcel_id)
                else:
                    # Resolve municipality and search for parcel
                    municipality_code = _resolve_municipality(
                        client, parcel_input.municipality
                    )
                    parcel_data = client.get_parcel_by_number(
                        parcel_input.parcel_number,
                        municipality_code,
                        exact_match=True,
                    )

                if parcel_data:
                    results.append(
                        BatchResult(
                            status="success",
                            input=parcel_input,
                            parcel_data=parcel_data,
                        )
                    )
                    successful += 1
                else:
                    # Parcel not found (returned None)
                    results.append(
                        BatchResult(
                            status="error",
                            input=parcel_input,
                            error_type=ErrorType.PARCEL_NOT_FOUND.value,
                            error_message="Parcel not found",
                        )
                    )
                    failed += 1

            except CadastralAPIError as e:
                # Handle API errors
                error_msg = str(e)

                # If error message is empty, construct one from details
                if not error_msg or error_msg == e.error_type.value:
                    if e.details:
                        detail_parts = [f"{k}={v}" for k, v in e.details.items() if v is not None]
                        if detail_parts:
                            error_msg = f"{e.error_type.value}: {', '.join(detail_parts)}"
                    if e.cause:
                        cause_msg = str(e.cause) if str(e.cause) else type(e.cause).__name__
                        error_msg = f"{error_msg} (caused by {type(e.cause).__name__}: {cause_msg})"

                results.append(
                    BatchResult(
                        status="error",
                        input=parcel_input,
                        error_type=e.error_type.value,
                        error_message=error_msg,
                    )
                )
                failed += 1

                if not continue_on_error:
                    raise

            except Exception as e:
                # Handle unexpected errors
                results.append(
                    BatchResult(
                        status="error",
                        input=parcel_input,
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

    return BatchSummary(
        total=len(parcels),
        successful=successful,
        failed=failed,
        results=results,
    )
