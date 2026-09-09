"""Shared output formatting for land registry units."""

import re
from datetime import datetime

from cadastral_api.i18n import _
from cadastral_api.models.entities import (
    FileStatus,
    LandRegistryUnitDetailed,
    LREntry,
    LRShare,
    Party,
)
from cadastral_api.utils import parse_fraction
from rich.console import Console
from rich.table import Table

console = Console()


def _date_text(value: datetime | None) -> str:
    """Render a timestamp as a plain YYYY-MM-DD date, or '-' when missing."""
    return value.date().isoformat() if value else "-"


def _fraction_text(description: str) -> str:
    """Render the share fraction as 'num/den' via the structured parser.

    Falls back to the substring after the last colon when no fraction is found.
    """
    parsed = parse_fraction(description)
    if parsed is not None:
        return f"{parsed[0]}/{parsed[1]}"
    return description.split(":")[-1].strip() if ":" in description else description


def _entry_text(entry: LREntry | None) -> str:
    """Provenance of an owner: entry order number, receipt date and diary number."""
    if entry is None:
        return "-"
    parts = [
        entry.order_number,
        entry.entry_date.isoformat() if entry.entry_date else "-",
        entry.diary_number or "-",
    ]
    return " · ".join(parts)


def _shorten(text: str, max_length: int = 160) -> str:
    return text if len(text) <= max_length else text[: max_length - 1] + "…"


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
    table.add_column(_("Field"), style="bold cyan")
    table.add_column(_("Value"))

    table.add_row(_("Unit Number"), lr_unit.lr_unit_number)
    table.add_row(_("Main Book"), lr_unit.main_book_name)
    table.add_row(_("Institution"), lr_unit.institution_name)
    table.add_row(_("Status"), lr_unit.status_name)
    table.add_row(_("Unit Type"), lr_unit.lr_unit_type_name)
    table.add_row(_("Last Diary Number"), lr_unit.last_diary_number)
    # Pending entries (plombe) are shown here, in the always-printed basic info,
    # so they are never hidden behind the absence of a --show flag.
    if lr_unit.has_pending_plombe():
        # On condominiums the plomba names the unit it concerns ("(E-80)").
        plombe = ", ".join(
            f"{p.file_number} {p.plumb_mark}" if p.plumb_mark else p.file_number
            for p in lr_unit.active_plumbs
        )
        table.add_row(_("Pending entries (plombe)"), f"[bold red]{plombe}[/bold red]")

    console.print(table)

    if lr_unit.has_pending_plombe():
        console.print(
            f"⚠️  {_('This unit has pending entries (plombe) - a change may be in progress.')}",
            style="yellow",
        )


def print_lr_unit_plombe_detail(
    lr_unit: LandRegistryUnitDetailed,
    details: dict[str, FileStatus],
) -> None:
    """Print the detail behind each pending plomba (what / status / dates).

    ``details`` maps file_number -> FileStatus (land-registry plombe that
    resolved). Every active plomba is still listed: cadastre plombe and any that
    did not resolve are shown as "detail unavailable" so nothing is hidden.
    """
    table = Table(title=_("PENDING ENTRIES DETAIL (PLOMBE)"), box=None)
    table.add_column(_("File Number"), style="bold red")
    table.add_column(_("Request"))
    table.add_column(_("Status"), style="cyan")
    table.add_column(_("Received"), justify="right")
    table.add_column(_("Outcome"))

    for plumb in lr_unit.active_plumbs:
        status = details.get(plumb.file_number)
        if status is not None:
            if status.is_resolved or status.resolution_type_name:
                outcome = status.resolution_type_name or _("Resolved")
                outcome = f"{outcome} ({_date_text(status.execution_date)})"
            else:
                outcome = _("In progress")
            table.add_row(
                plumb.file_number,
                status.application_content or "-",
                status.status_description or "-",
                _date_text(status.receiving_date),
                outcome,
            )
        else:
            # Cadastre plombe are not resolvable via the (land-registry)
            # file-status endpoint; others simply had no record.
            note = (
                _("cadastre plomba (no land-registry detail)")
                if plumb.cad_plumb
                else _("detail unavailable")
            )
            table.add_row(plumb.file_number, f"[dim]{note}[/dim]", "-", "-", "-")

    console.print(table)


def print_lr_unit_summary(lr_unit: LandRegistryUnitDetailed) -> None:
    """Print summary statistics."""
    summary = lr_unit.summary()

    table = Table(title=_("SUMMARY"), show_header=False, box=None)
    table.add_column(_("Metric"), style="bold yellow")
    table.add_column(_("Value"), style="green")

    # Show condominium info if applicable
    if summary.get("is_condominium"):
        table.add_row(_("Property Type"), _("Condominium (Etažno vlasništvo)"))
        table.add_row(_("Number of Units"), str(summary.get("condominium_units", 0)))

    table.add_row(_("Total Parcels"), str(summary["total_parcels"]))
    table.add_row(_("Total Area"), f"{summary['total_area_m2']} m²")
    table.add_row(_("Number of Owners"), str(summary["num_owners"]))
    table.add_row(
        _("Sheet C entries"),
        _("Yes") if summary["has_sheet_c_entries"] else _("No")
    )

    console.print(table)

    # Hint for detailed view
    if summary["num_owners"] > 0:
        console.print(f"\n💡 {_('Use --show-owners to see ownership details')}")
    if summary["total_parcels"] > 0:
        console.print(f"💡 {_('Use --show-parcels to see all parcels')}")
    if summary["has_sheet_c_entries"]:
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
            str(parcel.area_numeric) if parcel.area_numeric is not None else "-",
        )

    # Add total
    total_area = lr_unit.possessory_sheet_a1.total_area()
    table.add_section()
    table.add_row(_("TOTAL"), "", f"[bold green]{total_area}[/bold green]")

    console.print(table)

    # The server sends the list either as land-register records (lrParcels,
    # where the address is the old culture or toponym) or as cadastre records
    # (cadParcels). Say which, so the reader knows what the address column is.
    source = lr_unit.sheet_a1_source_key
    if source == "cadParcels":
        console.print(_("Parcel list as recorded in the cadastre."), style="dim")
    elif source == "lrParcels":
        console.print(
            _("Parcel list as recorded in the land register; the address column is the "
              "culture or toponym of the old land register, not a location."),
            style="dim",
        )


def print_lr_unit_ownership_sheet(
    lr_unit: LandRegistryUnitDetailed, show_entries: bool = False
) -> None:
    """Print ownership sheet (Sheet B).

    Each owner row ends with the registration entry that put the owner on the
    share (order number, receipt date, diary number). For condominiums, also
    shows apartment descriptions and handles nested co-owners. With
    ``show_entries`` the annotations registered on a share (zabilježbe) are
    listed under it.
    """
    is_condo = lr_unit.is_condominium()

    table = Table(title=_("OWNERSHIP SHEET (LIST B)"), box=None)
    table.add_column(_("Share"), style="cyan")
    table.add_column(_("Owner"), style="bold")
    table.add_column(_("Address"))
    table.add_column(_("OIB"))
    table.add_column(_("Entry"), style="dim")

    # Add apartment description column for condominiums
    if is_condo:
        table.add_column(_("Apartment"), style="dim", max_width=50)

    def add_owner(share_text: str, owner: Party, apt_desc: str) -> None:
        row = [
            share_text,
            owner.name,
            owner.address or "-",
            owner.tax_number or "-",
            _entry_text(owner.entry),
        ]
        if is_condo:
            row.append(apt_desc)
        table.add_row(*row)

    def add_note(text: str) -> None:
        row = ["", f"[dim]{text}[/dim]", "", "", ""]
        if is_condo:
            row.append("")
        table.add_row(*row)

    def add_share(share: LRShare, indent: str, apt_desc: str) -> None:
        share_text = f"{indent}{_fraction_text(share.description)}"
        if share.owners:
            for owner in share.owners:
                add_owner(share_text, owner, apt_desc)
                apt_desc = ""
        elif not share.sub_shares:
            # The server sent no owner for this share (lrOwners missing).
            row = [share_text, f"[dim]{_('No owner recorded')}[/dim]", "-", "-", "-"]
            if is_condo:
                row.append(apt_desc)
            table.add_row(*row)
        # Co-owners of a divided share (common in condominiums)
        for sub in share.sub_shares:
            add_share(sub, indent + "  ", apt_desc)
            apt_desc = ""
        if show_entries:
            for entry in share.share_entries:
                add_note(f"↳ {entry.order_number}: {_shorten(entry.description_text)}")

    for share in lr_unit.ownership_sheet_b.lr_unit_shares:
        if share.is_active:
            apt_desc = ""
            if is_condo and share.condominium_descriptions:
                apt_desc = _format_apartment_description(share.condominium_descriptions[0])
            add_share(share, "", apt_desc)

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

    if not lr_unit.has_sheet_c_entries():
        table.add_row(f"[green]{_('No encumbrances found')}[/green]", "")
    else:
        for group in lr_unit.encumbrance_sheet_c.lr_entry_groups:
            lines: list[str] = []
            for entry in group.lr_entries:
                lines.append(
                    _format_encumbrance_entry(entry.order_number, clean_html(entry.description))
                )
                if entry.amount:
                    lines.append(f"  {_('Amount')}: {entry.amount}")
                lines.extend(_format_parties(entry.get_parties()))
            # The derived beneficiary is normally one of the entry parties already
            # printed; list it only when it is not.
            listed = [party for entry in group.lr_entries for party in entry.get_parties()]
            if group.beneficiary and group.beneficiary not in listed:
                lines.extend(_format_parties([group.beneficiary]))
            table.add_row(group.description, "\n".join(lines))

    console.print(table)


def _format_encumbrance_entry(order_number: str, description: str, max_length: int = 2000) -> str:
    """Format a single encumbrance entry, truncating if needed."""
    if len(description) > max_length:
        return f"• {order_number}: {description[:max_length]}..."
    return f"• {order_number}: {description}"


def _format_parties(parties: list) -> list[str]:
    """Render the persons an entry is registered in favour of, one per line."""
    if not parties:
        return []
    lines = [f"  {_('In favour of')}:"]
    for party in parties:
        detail = f"{party.name}, {party.address}" if party.address else party.name
        if party.tax_number:
            detail += f" ({_('OIB')}: {party.tax_number})"
        lines.append(f"    {detail}")
    return lines


def print_lr_unit_full(
    lr_unit: LandRegistryUnitDetailed,
    show_owners: bool = False,
    show_parcels: bool = False,
    show_encumbrances: bool = False,
    show_all: bool = False,
    plombe_details: dict[str, FileStatus] | None = None,
) -> None:
    """Print complete LR unit information.

    Args:
        lr_unit: Land registry unit data
        show_owners: Show ownership sheet (Sheet B)
        show_parcels: Show parcel list (Sheet A)
        show_encumbrances: Show encumbrances (Sheet C)
        show_all: Show all sheets
        plombe_details: Resolved plomba detail (file_number -> FileStatus). When
            provided and the unit has pending plombe, a detail table is printed
            right after the basic info.
    """
    # Print basic info
    print_lr_unit_basic_info(lr_unit)

    # Print plomba detail right after the basic info, where the plombe are listed.
    if plombe_details is not None and lr_unit.has_pending_plombe():
        console.print()
        print_lr_unit_plombe_detail(lr_unit, plombe_details)

    # Print parcels if requested (Sheet A)
    if show_parcels or show_all:
        console.print()
        print_lr_unit_parcel_list(lr_unit)

    # Print ownership if requested (Sheet B); --all also lists the share entries
    if show_owners or show_all:
        console.print()
        print_lr_unit_ownership_sheet(lr_unit, show_entries=show_all)

    # Print encumbrances if requested (Sheet C)
    if show_encumbrances or show_all:
        console.print()
        print_lr_unit_encumbrance_sheet(lr_unit)

    # If nothing specific requested, show summary
    if not (show_owners or show_parcels or show_encumbrances or show_all):
        console.print()
        print_lr_unit_summary(lr_unit)
