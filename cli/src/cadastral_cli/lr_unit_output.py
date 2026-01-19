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

    # Show condominium info if applicable
    if summary.get("is_condominium"):
        table.add_row(_("Property Type"), _("Condominium (Etažno vlasništvo)"))
        table.add_row(_("Number of Units"), str(summary.get("condominium_units", 0)))

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
    total_area = lr_unit.possessory_sheet_a1.total_area()
    table.add_section()
    table.add_row(_("TOTAL"), "", f"[bold green]{total_area}[/bold green]")

    console.print(table)


def print_lr_unit_ownership_sheet(lr_unit: LandRegistryUnitDetailed) -> None:
    """Print ownership sheet (Sheet B).

    For condominiums, also shows apartment descriptions and handles nested co-owners.
    """
    is_condo = lr_unit.is_condominium()

    table = Table(title=_("OWNERSHIP SHEET (LIST B)"), box=None)
    table.add_column(_("Share"), style="cyan")
    table.add_column(_("Owner"), style="bold")
    table.add_column(_("Address"))
    table.add_column(_("OIB"))

    # Add apartment description column for condominiums
    if is_condo:
        table.add_column(_("Apartment"), style="dim", max_width=50)

    for share in lr_unit.ownership_sheet_b.lr_unit_shares:
        if share.is_active:
            # Extract share text (fraction + condominium number if present)
            share_text = share.description.split(":")[-1].strip() if ":" in share.description else share.description

            # Get apartment description for condominiums
            apt_desc = ""
            if is_condo and share.condominium_descriptions:
                apt_desc = _format_apartment_description(share.condominium_descriptions[0])

            # Handle direct owners
            if share.owners:
                for owner in share.owners:
                    row = [
                        share_text,
                        owner.name,
                        owner.address or "-",
                        owner.tax_number or "-",
                    ]
                    if is_condo:
                        row.append(apt_desc)
                    table.add_row(*row)

            # Handle nested co-owners (subSharesAndEntries) - common in condominiums
            elif share.has_sub_owners():
                # First, add a row for the share itself with the apartment description
                for sub in share.sub_shares_and_entries:
                    sub_desc = sub.get("description", "")
                    # Extract sub-share fraction
                    sub_share_text = sub_desc.split(":")[-1].strip() if ":" in sub_desc else sub_desc
                    sub_owners = sub.get("lrOwners", [])

                    for owner_data in sub_owners:
                        row = [
                            f"  {sub_share_text}",  # Indent sub-share
                            owner_data.get("name", "-"),
                            owner_data.get("address", "-") or "-",
                            owner_data.get("taxNumber", "-") or "-",
                        ]
                        if is_condo:
                            row.append(apt_desc if sub == share.sub_shares_and_entries[0] else "")
                        table.add_row(*row)

    console.print(table)


def _format_apartment_description(description: str, max_length: int = 60) -> str:
    """Format apartment description, extracting key info and truncating if needed.

    Args:
        description: Full apartment description from API
        max_length: Maximum length before truncation

    Returns:
        Shortened, formatted description
    """
    if not description:
        return ""

    # Try to extract floor and area info
    # Example: "STAN na III. (trećem) katu, označen br. 13, površine 59,08 m2..."
    # Extract floor
    floor_match = re.search(r'na\s+(\w+\.?\s*(?:\([^)]+\))?\s*katu)', description, re.IGNORECASE)
    floor_info = floor_match.group(1) if floor_match else ""

    # Extract area
    area_match = re.search(r'površine\s+([\d,\.]+)\s*m2', description, re.IGNORECASE)
    area_info = f"{area_match.group(1)} m²" if area_match else ""

    # Extract apartment number
    apt_match = re.search(r'označen\s+br\.?\s*(\d+)', description, re.IGNORECASE)
    apt_num = f"#{apt_match.group(1)}" if apt_match else ""

    # Build short description
    parts = [p for p in [apt_num, floor_info, area_info] if p]
    if parts:
        return ", ".join(parts)

    # Fallback: truncate original
    if len(description) > max_length:
        return description[:max_length] + "..."
    return description


def print_lr_unit_encumbrance_sheet(lr_unit: LandRegistryUnitDetailed) -> None:
    """Print encumbrance sheet (Sheet C)."""
    table = Table(title=_("ENCUMBRANCES SHEET (LIST C)"), box=None)
    table.add_column(_("Description"), style="yellow")
    table.add_column(_("Details"))

    if not lr_unit.has_encumbrances():
        table.add_row(f"[green]{_('No encumbrances found')}[/green]", "")
    else:
        for group in lr_unit.encumbrance_sheet_c.lr_entry_groups:
            entries_text = "\n".join(
                _format_encumbrance_entry(entry.order_number, clean_html(entry.description))
                for entry in group.lr_entries
            )
            table.add_row(group.description, entries_text)

    console.print(table)


def _format_encumbrance_entry(order_number: str, description: str, max_length: int = 2000) -> str:
    """Format a single encumbrance entry, truncating if needed."""
    if len(description) > max_length:
        return f"• {order_number}: {description[:max_length]}..."
    return f"• {order_number}: {description}"


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
