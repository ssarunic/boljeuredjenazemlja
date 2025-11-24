#!/usr/bin/env python3.12
"""Example demonstrating LR unit functionality.

⚠️ DEMO/EDUCATIONAL USE ONLY
This example uses the mock server at http://localhost:8000
"""

import sys
from pathlib import Path

# Add API source to path
api_src = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(api_src))

from cadastral_api import CadastralAPIClient
from rich.console import Console
from rich.table import Table

console = Console()


def main():
    """Demonstrate LR unit functionality."""
    console.print("\n[bold cyan]═══ Land Registry Unit Demo ═══[/bold cyan]\n")
    console.print("[yellow]Using mock server at http://localhost:8000[/yellow]")
    console.print("[yellow]Make sure the mock server is running![/yellow]\n")

    with CadastralAPIClient(base_url="http://localhost:8000") as client:
        # Example 1: Get LR unit by number and main book
        console.print("[bold]Example 1: Get LR unit by number and main book ID[/bold]")
        console.print("Command: [cyan]get_lr_unit_detailed(unit_number='769', main_book_id=21277)[/cyan]\n")

        lr_unit = client.get_lr_unit_detailed("769", 21277)

        # Display basic info
        table = Table(title="LAND REGISTRY UNIT", show_header=False, box=None)
        table.add_column("Field", style="bold cyan")
        table.add_column("Value")

        table.add_row("Unit Number", lr_unit.lr_unit_number)
        table.add_row("Main Book", lr_unit.main_book_name)
        table.add_row("Institution", lr_unit.institution_name)
        table.add_row("Status", lr_unit.status_name)
        table.add_row("Unit Type", lr_unit.lr_unit_type_name)
        table.add_row("Last Diary", lr_unit.last_diary_number)

        console.print(table)
        console.print()

        # Display summary
        summary = lr_unit.summary()

        summary_table = Table(title="SUMMARY", show_header=False, box=None)
        summary_table.add_column("Metric", style="bold yellow")
        summary_table.add_column("Value", style="green")

        summary_table.add_row("Total Parcels", str(summary["total_parcels"]))
        summary_table.add_row("Total Area", f"{summary['total_area_m2']} m²")
        summary_table.add_row("Number of Owners", str(summary["num_owners"]))
        summary_table.add_row("Has Encumbrances", "Yes" if summary["has_encumbrances"] else "No")

        console.print(summary_table)
        console.print()

        # Example 2: Show ownership details (Sheet B)
        console.print("\n[bold]Example 2: Ownership Sheet (Sheet B)[/bold]")
        console.print("All owners with their shares:\n")

        ownership_table = Table(title="OWNERSHIP SHEET (LIST B)", box=None)
        ownership_table.add_column("Share", style="cyan")
        ownership_table.add_column("Owner", style="bold")
        ownership_table.add_column("Address")
        ownership_table.add_column("OIB")

        for share in lr_unit.ownership_sheet_b.lr_unit_shares:
            if share.is_active:
                for owner in share.owners:
                    ownership_table.add_row(
                        share.description,
                        owner.name,
                        owner.address or "-",
                        owner.tax_number or "-",
                    )

        console.print(ownership_table)
        console.print()

        # Example 3: Show all parcels (Sheet A)
        console.print("\n[bold]Example 3: Parcel List (Sheet A)[/bold]")
        console.print("All parcels in this LR unit:\n")

        parcel_table = Table(title="PARCEL LIST (SHEET A)", box=None)
        parcel_table.add_column("Parcel Number", style="cyan")
        parcel_table.add_column("Address")
        parcel_table.add_column("Area (m²)", justify="right", style="green")

        for parcel in lr_unit.get_all_parcels():
            parcel_table.add_row(
                parcel.parcel_number,
                parcel.address or "-",
                str(parcel.area_numeric),
            )

        # Add total
        total_area = lr_unit.possessory_sheet_a1.total_area()
        parcel_table.add_section()
        parcel_table.add_row("TOTAL", "", f"[bold green]{total_area}[/bold green]")

        console.print(parcel_table)
        console.print()

        # Example 4: Show encumbrances (Sheet C)
        console.print("\n[bold]Example 4: Encumbrances (Sheet C)[/bold]\n")

        if lr_unit.has_encumbrances():
            enc_table = Table(title="ENCUMBRANCES SHEET (LIST C)", box=None)
            enc_table.add_column("Description", style="yellow")
            enc_table.add_column("Details")

            for group in lr_unit.encumbrance_sheet_c.lr_entry_groups:
                entries_text = "\n".join(
                    f"• {entry.order_number}: {entry.description[:80]}..."
                    for entry in group.lr_entries
                )
                enc_table.add_row(group.description, entries_text)

            console.print(enc_table)
        else:
            console.print("[green]No encumbrances found[/green]")

        console.print()

        # Example 5: Get LR unit from parcel number
        console.print("\n[bold]Example 5: Get LR unit from parcel number[/bold]")
        console.print("Command: [cyan]get_lr_unit_from_parcel('279/6', 'TESTMUNICIPALITY')[/cyan]\n")

        # This would work if we had the parcel lookup implemented in mock server
        # For now, just show the method signature
        console.print("[dim]Note: This requires parcel search to be working in mock server[/dim]")
        console.print("[dim]client.get_lr_unit_from_parcel('279/6', 'TESTMUNICIPALITY')[/dim]\n")

        console.print("[bold green]✓ All examples completed successfully![/bold green]\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"\n[bold red]✗ Error: {e}[/bold red]\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
