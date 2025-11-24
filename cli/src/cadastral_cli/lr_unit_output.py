"""Shared output formatting for land registry units."""

import re

from rich.console import Console
from rich.table import Table

from cadastral_api.i18n import _
from cadastral_api.models.entities import LandRegistryUnitDetailed

console = Console()


def clean_html(text: str) -> str:
    """Remove HTML tags and convert to plain text with basic markdown.

    Args:
        text: Text potentially containing HTML tags

    Returns:
        Cleaned text with HTML removed and basic markdown formatting
    """
    if not text:
        return text

    # Replace <br> and <br/> with newlines
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)

    # Replace <span> tags with their content (remove span styling)
    text = re.sub(r'<span[^>]*>(.*?)</span>', r'\1', text, flags=re.IGNORECASE | re.DOTALL)

    # Remove any remaining HTML tags
    text = re.sub(r'<[^>]+>', '', text)

    # Clean up multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Decode HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&amp;', '&')

    return text.strip()


def print_lr_unit_basic_info(lr_unit: LandRegistryUnitDetailed) -> None:
    """Print basic LR unit information."""
    table = Table(title=_("LAND REGISTRY UNIT"), show_header=False, box=None)
    table.add_column("Field", style="bold cyan")
    table.add_column("Value")

    table.add_row(_("Unit Number"), lr_unit.lr_unit_number)
    table.add_row(_("Main Book"), lr_unit.main_book_name)
    table.add_row(_("Institution"), lr_unit.institution_name)
    table.add_row(_("Status"), lr_unit.status_name)
    table.add_row(_("Unit Type"), lr_unit.lr_unit_type_name)
    table.add_row(_("Last Diary Number"), lr_unit.last_diary_number)

    console.print(table)


def print_lr_unit_summary(lr_unit: LandRegistryUnitDetailed) -> None:
    """Print summary statistics."""
    summary = lr_unit.summary()

    table = Table(title=_("SUMMARY"), show_header=False, box=None)
    table.add_column("Metric", style="bold yellow")
    table.add_column("Value", style="green")

    table.add_row(_("Total Parcels"), str(summary["total_parcels"]))
    table.add_row(_("Total Area"), f"{summary['total_area_m2']} m²")
    table.add_row(_("Number of Owners"), str(summary["num_owners"]))
    table.add_row(
        _("Has Encumbrances"),
        _("Yes") if summary["has_encumbrances"] else _("No")
    )

    console.print(table)

    # Hint for detailed view
    if summary["num_owners"] > 0:
        console.print(f"\n💡 {_('Use --show-owners to see ownership details')}")
    if summary["total_parcels"] > 0:
        console.print(f"💡 {_('Use --show-parcels to see all parcels')}")
    if summary["has_encumbrances"]:
        console.print(f"💡 {_('Use --show-encumbrances to see encumbrances')}")


def print_lr_unit_parcel_list(lr_unit: LandRegistryUnitDetailed) -> None:
    """Print parcel list (Sheet A)."""
    table = Table(title=_("PARCEL LIST (SHEET A)"), box=None)
    table.add_column(_("Parcel Number"), style="cyan")
    table.add_column(_("Address"))
    table.add_column(_("Area (m²)"), justify="right", style="green")

    for parcel in lr_unit.get_all_parcels():
        table.add_row(
            parcel.parcel_number,
            parcel.address or "-",
            str(parcel.area_numeric),
        )

    # Add total
    total_area = lr_unit.possession_sheet_a1.total_area()
    table.add_section()
    table.add_row(_("TOTAL"), "", f"[bold green]{total_area}[/bold green]")

    console.print(table)


def print_lr_unit_ownership_sheet(lr_unit: LandRegistryUnitDetailed) -> None:
    """Print ownership sheet (Sheet B)."""
    table = Table(title=_("OWNERSHIP SHEET (LIST B)"), box=None)
    table.add_column(_("Share"), style="cyan")
    table.add_column(_("Owner"), style="bold")
    table.add_column(_("Address"))
    table.add_column(_("OIB"))

    for share in lr_unit.ownership_sheet_b.lr_unit_shares:
        if share.is_active:
            for owner in share.owners:
                # Extract just the fraction from description (e.g., "1. Suvlasnički dio: 4/8" -> "4/8")
                share_text = share.description.split(":")[-1].strip() if ":" in share.description else share.description

                table.add_row(
                    share_text,
                    owner.name,
                    owner.address or "-",
                    owner.tax_number or "-",
                )

    console.print(table)


def print_lr_unit_encumbrance_sheet(lr_unit: LandRegistryUnitDetailed) -> None:
    """Print encumbrance sheet (Sheet C)."""
    if not lr_unit.has_encumbrances():
        console.print(f"[green]{_('No encumbrances found')}[/green]")
        return

    table = Table(title=_("ENCUMBRANCES SHEET (LIST C)"), box=None)
    table.add_column(_("Description"), style="yellow")
    table.add_column(_("Details"))

    for group in lr_unit.encumbrance_sheet_c.lr_entry_groups:
        entries_text = "\n".join(
            f"• {entry.order_number}: {clean_html(entry.description)[:150]}..."
            for entry in group.lr_entries
        )
        table.add_row(group.description, entries_text)

    console.print(table)


def print_lr_unit_full(
    lr_unit: LandRegistryUnitDetailed,
    show_owners: bool = False,
    show_parcels: bool = False,
    show_encumbrances: bool = False,
    show_all: bool = False,
) -> None:
    """Print complete LR unit information.

    Args:
        lr_unit: Land registry unit data
        show_owners: Show ownership sheet (Sheet B)
        show_parcels: Show parcel list (Sheet A)
        show_encumbrances: Show encumbrances (Sheet C)
        show_all: Show all sheets
    """
    # Print basic info
    print_lr_unit_basic_info(lr_unit)

    # Print parcels if requested (Sheet A)
    if show_parcels or show_all:
        console.print()
        print_lr_unit_parcel_list(lr_unit)

    # Print ownership if requested (Sheet B)
    if show_owners or show_all:
        console.print()
        print_lr_unit_ownership_sheet(lr_unit)

    # Print encumbrances if requested (Sheet C)
    if show_encumbrances or show_all:
        console.print()
        print_lr_unit_encumbrance_sheet(lr_unit)

    # If nothing specific requested, show summary
    if not (show_owners or show_parcels or show_encumbrances or show_all):
        console.print()
        print_lr_unit_summary(lr_unit)
