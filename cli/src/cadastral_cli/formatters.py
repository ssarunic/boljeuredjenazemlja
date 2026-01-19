"""Output formatters for CLI."""

import csv
import json
from io import StringIO
from typing import Any

from rich.console import Console
from rich.table import Table
from tabulate import tabulate

from cadastral_api.i18n import _


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
