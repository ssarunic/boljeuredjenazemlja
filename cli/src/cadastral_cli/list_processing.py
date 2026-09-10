"""Looking up a list of items (parcels or land registry units) one by one.

``get-parcel`` and ``get-lr-unit`` accept a single item or a list. A list is
processed here: every item is fetched in turn, failures are recorded instead
of aborting (unless asked otherwise), and the caller renders the collected
results. The summary rows built here are the per-item records of the JSON
and CSV output; the key names are listed in ``output_keys``.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.i18n import _
from cadastral_api.models.entities import LandRegistryUnitDetailed, ParcelInfo
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from cadastral_cli.formatters import describe_error
from cadastral_cli.input_parsers import LRUnitInput, ParcelInput

# Progress goes to stderr so that ``--format json`` on stdout stays parseable.
progress_console = Console(stderr=True)

In = TypeVar("In")
D = TypeVar("D")


@dataclass
class ItemResult(Generic[In, D]):
    """Outcome of one item of a list lookup."""

    status: str  # "success" or "error"
    input: In
    data: D | None = None
    error_type: str | None = None
    error_message: str | None = None

    @property
    def ok(self) -> bool:
        return self.status == "success" and self.data is not None


@dataclass
class ListSummary(Generic[In, D]):
    """All results of a list lookup with the success counts."""

    results: list[ItemResult[In, D]] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def successful(self) -> int:
        return sum(1 for r in self.results if r.status == "success")

    @property
    def failed(self) -> int:
        return self.total - self.successful

    @property
    def success_rate(self) -> float:
        return (self.successful / self.total * 100) if self.total else 0.0

    def envelope(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        """The JSON document of a list lookup: counts plus one row per item."""
        return {
            "summary": {
                "total": self.total,
                "successful": self.successful,
                "failed": self.failed,
                "success_rate": f"{self.success_rate:.1f}%",
            },
            "results": rows,
        }


def process_list(
    inputs: list[In],
    fetch: Callable[[In], D | None],
    describe: Callable[[In], str],
    progress_title: str,
    not_found: str,
    not_found_type: str,
    continue_on_error: bool = True,
    show_progress: bool = True,
) -> ListSummary[In, D]:
    """Fetch every input with ``fetch`` and collect the outcomes.

    ``fetch`` returning ``None`` counts as "not found" (``not_found_type`` is
    the ``ErrorType`` value recorded for it). With
    ``continue_on_error`` False the first failure is re-raised after being
    recorded; the caller decides how to report it.
    """
    summary: ListSummary[In, D] = ListSummary()
    progress: Progress | None = None
    task = None
    if show_progress:
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=progress_console,
            transient=True,
        )
        task = progress.add_task(progress_title, total=len(inputs))
        progress.start()

    try:
        for index, item in enumerate(inputs, 1):
            if progress is not None and task is not None:
                progress.update(
                    task,
                    description=_("Processing {current}/{total}: {input}").format(
                        current=index, total=len(inputs), input=describe(item)
                    ),
                    completed=index - 1,
                )
            try:
                data = fetch(item)
            except CadastralAPIError as error:
                summary.results.append(
                    ItemResult(
                        status="error",
                        input=item,
                        error_type=error.error_type.value,
                        error_message=describe_error(error),
                    )
                )
                if not continue_on_error:
                    raise
                continue
            except Exception as error:  # noqa: BLE001 - recorded per item on purpose
                summary.results.append(
                    ItemResult(
                        status="error",
                        input=item,
                        error_type="unexpected_error",
                        error_message=str(error),
                    )
                )
                if not continue_on_error:
                    raise
                continue

            if data is None:
                summary.results.append(
                    ItemResult(
                        status="error",
                        input=item,
                        error_type=not_found_type,
                        error_message=not_found,
                    )
                )
            else:
                summary.results.append(ItemResult(status="success", input=item, data=data))
    finally:
        if progress is not None:
            progress.stop()

    return summary


# ---------------------------------------------------------------------------
# Parcels
# ---------------------------------------------------------------------------


def resolve_municipality(client: CadastralAPIClient, municipality: str) -> str:
    """Municipality name or registration number -> registration number."""
    if municipality.isdigit() and len(municipality) == 6:
        return municipality
    results = client.find_municipality(search_term=municipality)
    if not results:
        raise CadastralAPIError(
            ErrorType.MUNICIPALITY_NOT_FOUND, details={"search_term": municipality}
        )
    for result in results:
        if result.municipality_name.upper() == municipality.upper():
            return str(result.municipality_reg_num)
    return str(results[0].municipality_reg_num)


def process_parcel_list(
    client: CadastralAPIClient,
    inputs: list[ParcelInput],
    continue_on_error: bool = True,
    show_progress: bool = True,
) -> ListSummary[ParcelInput, ParcelInfo]:
    """Look up every parcel of ``inputs`` (by number and municipality, or by id)."""

    def fetch(item: ParcelInput) -> ParcelInfo | None:
        if item.parcel_id:
            return client.get_parcel_info(item.parcel_id)
        assert item.parcel_number is not None and item.municipality is not None
        code = resolve_municipality(client, item.municipality)
        return client.get_parcel_by_number(item.parcel_number, code, exact_match=True)

    return process_list(
        inputs,
        fetch,
        describe=str,
        progress_title=_("Processing parcels..."),
        not_found=_("Parcel not found"),
        not_found_type=ErrorType.PARCEL_NOT_FOUND.value,
        continue_on_error=continue_on_error,
        show_progress=show_progress,
    )


def parcel_row(result: ItemResult[ParcelInput, ParcelInfo]) -> dict[str, Any]:
    """One parcel of a list lookup as a flat record (JSON row, CSV line)."""
    row: dict[str, Any] = {"status": result.status}
    if result.input.parcel_id:
        row["parcel_id"] = result.input.parcel_id
    else:
        row["parcel_number"] = result.input.parcel_number
        row["municipality"] = result.input.municipality

    parcel = result.data
    if result.ok and parcel is not None:
        row["parcel_id"] = parcel.parcel_id
        row["parcel_number"] = parcel.parcel_number
        row["municipality_code"] = parcel.municipality_reg_num
        row["municipality_name"] = parcel.municipality_name
        row["area_m2"] = parcel.area_numeric
        row["building_permitted"] = parcel.has_building_right
        row["total_possessors"] = parcel.total_possessors
        row["is_building_parcel"] = parcel.is_building_parcel
        # The unit may be reachable only through parcel links.
        lr_unit = parcel.resolved_lr_unit()
        row["lr_unit_number"] = lr_unit.lr_unit_number if lr_unit else None
        row["main_book_id"] = lr_unit.main_book_id if lr_unit else None
    else:
        row["error_type"] = result.error_type
        row["error_message"] = result.error_message
    return row


# ---------------------------------------------------------------------------
# Land registry units
# ---------------------------------------------------------------------------


def process_lr_unit_list(
    client: CadastralAPIClient,
    inputs: list[LRUnitInput],
    continue_on_error: bool = True,
    show_progress: bool = True,
) -> ListSummary[LRUnitInput, LandRegistryUnitDetailed]:
    """Read every land registry unit of ``inputs``."""

    def fetch(item: LRUnitInput) -> LandRegistryUnitDetailed:
        return client.get_lr_unit_detailed(item.lr_unit_number, item.main_book_id)

    return process_list(
        inputs,
        fetch,
        describe=lambda item: item.lr_unit_number,
        progress_title=_("Processing LR units..."),
        not_found=_("Land registry unit not found"),
        not_found_type=ErrorType.LR_UNIT_NOT_FOUND.value,
        continue_on_error=continue_on_error,
        show_progress=show_progress,
    )


def lr_unit_row(result: ItemResult[LRUnitInput, LandRegistryUnitDetailed]) -> dict[str, Any]:
    """One unit of a list lookup as a flat record (JSON row, CSV line)."""
    row: dict[str, Any] = {
        "status": result.status,
        "lr_unit_number": result.input.lr_unit_number,
        "main_book_id": result.input.main_book_id,
    }
    unit = result.data
    if result.ok and unit is not None:
        summary = unit.summary()
        row["main_book_name"] = unit.main_book_name
        row["institution_name"] = unit.institution_name
        row["status_name"] = unit.status_name
        row["total_parcels"] = summary["total_parcels"]
        row["total_area_m2"] = summary["total_area_m2"]
        row["num_owners"] = summary["num_owners"]
        row["has_sheet_c_entries"] = summary["has_sheet_c_entries"]
    else:
        row["error_type"] = result.error_type
        row["error_message"] = result.error_message
    return row
