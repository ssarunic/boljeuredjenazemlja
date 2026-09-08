"""Output formatters for CLI."""

import csv
import json
from io import StringIO
from typing import Any

from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.i18n import _
from rich.console import Console
from rich.table import Table
from tabulate import tabulate

console = Console()


def format_table(
    data: dict[str, Any] | list[dict[str, Any]], headers: list[str] | None = None
) -> str:
    """Format data as table using tabulate."""
    if isinstance(data, dict):
        # Single item - format as key-value pairs
        table_data = [[k, v] for k, v in data.items()]
        return tabulate(table_data, tablefmt="plain")

    # Multiple items
    if not data:
        return _("No results found.")

    if headers is None:
        headers = list(data[0].keys())

    table_data = [[item.get(h, "") for h in headers] for item in data]
    return tabulate(table_data, headers=headers, tablefmt="grid")


def format_json(data: Any, pretty: bool = True) -> str:
    """Format data as JSON."""
    if pretty:
        return json.dumps(data, indent=2, ensure_ascii=False)
    return json.dumps(data, ensure_ascii=False)


def format_csv(data: list[dict[str, Any]]) -> str:
    """Format data as CSV."""
    if not data:
        return ""

    output = StringIO()
    writer = csv.DictWriter(output, fieldnames=list(data[0].keys()))
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def print_output(data: Any, output_format: str = "table", file: str | None = None) -> None:
    """Print output in specified format."""
    if output_format == "json":
        output = format_json(data)
    elif output_format == "csv":
        if not isinstance(data, list):
            data = [data]
        output = format_csv(data)
    else:  # table
        output = format_table(data)

    if file:
        with open(file, "w", encoding="utf-8") as f:
            f.write(output)
        console.print(_("✓ Output saved to: {file}").format(file=file), style="green")
    else:
        print(output)


def print_error(message: str) -> None:
    """Print error message."""
    console.print(_("✗ Error: {message}").format(message=message), style="bold red")


def print_success(message: str) -> None:
    """Print success message."""
    console.print(f"✓ {message}", style="green")


def print_info(message: str) -> None:
    """Print info message."""
    console.print(message, style="blue")


def create_rich_table(title: str, columns: list[str]) -> Table:
    """Create a rich table with styling."""
    table = Table(title=title, show_header=True, header_style="bold magenta")
    for col in columns:
        table.add_column(col)
    return table


def command_help(text: str) -> str:
    """Prepare a translated command description for click.

    Click rewraps paragraphs to the terminal width. Indented blocks (examples,
    file formats) have to keep their layout, so click's ``\b`` no-wrap marker
    is inserted in front of every paragraph that contains an indented line.
    Keeping the marker out of the translatable text keeps the .po entries plain.
    """
    paragraphs = text.strip("\n").split("\n\n")
    prepared = []
    for paragraph in paragraphs:
        if any(line.startswith("  ") for line in paragraph.split("\n")):
            prepared.append("\b\n" + paragraph)
        else:
            prepared.append(paragraph)
    return "\n\n".join(prepared)


def error_type_label(error_type: ErrorType) -> str:
    """Human-readable, translated label for an API error type."""
    labels = {
        ErrorType.CONNECTION: _("Connection error"),
        ErrorType.TIMEOUT: _("Request timed out"),
        ErrorType.RATE_LIMIT: _("Rate limit exceeded"),
        ErrorType.INVALID_RESPONSE: _("Invalid response from server"),
        ErrorType.PARCEL_NOT_FOUND: _("Parcel not found"),
        ErrorType.MUNICIPALITY_NOT_FOUND: _("Municipality not found"),
        ErrorType.LR_UNIT_NOT_FOUND: _("Land registry unit not found"),
        ErrorType.SERVER_ERROR: _("Server error"),
    }
    return labels.get(error_type, str(error_type.value))


def describe_error(error: CadastralAPIError) -> str:
    """Translated description of a ``CadastralAPIError`` including its details."""
    parts = [error_type_label(error.error_type)]
    details = ", ".join(
        f"{key}={value}" for key, value in error.details.items() if value is not None
    )
    if details:
        parts.append(f"({details})")
    if error.cause is not None:
        cause = str(error.cause) or type(error.cause).__name__
        parts.append(
            _("- caused by: {cause}").format(cause=f"{type(error.cause).__name__}: {cause}")
        )
    return " ".join(parts)


def error_type_value_label(value: str | None) -> str:
    """Translated label for an error type stored as a string (batch results)."""
    if not value:
        return _("unknown")
    if value == "unexpected_error":
        return _("Unexpected error")
    try:
        return error_type_label(ErrorType(value))
    except ValueError:
        return value
