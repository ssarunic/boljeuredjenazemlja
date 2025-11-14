"""Parcel information commands for CLI."""

import click
from rich.console import Console
from rich.table import Table

from cadastral_api import CadastralAPIClient
from cadastral_apiexceptions import CadastralAPIError, ErrorType
from cadastral_apii18n import _, ngettext
from cadastral_cliformatters import print_error, print_output
from .search import _resolve_municipality

console = Console()


@click.command("get-parcel")
@click.argument("parcel_number")
@click.option("--municipality", "-m", required=True, help="Municipality name or code")
@click.option("--detail", type=click.Choice(["basic", "full", "owners", "landuse", "geometry"]), default="full", help="Detail level")
@click.option("--show-owners", is_flag=True, help="Include ownership details")
@click.option("--show-geometry", is_flag=True, help="Include boundary coordinates")
@click.option("--format", "-f", "output_format", type=click.Choice(["table", "json", "yaml", "csv"]), default="table", help="Output format")
@click.option("--output", "-o", type=click.Path(), help="Save output to file")
@click.pass_context
def get_parcel(
    ctx: click.Context,
    parcel_number: str,
    municipality: str,
    detail: str,
    show_owners: bool,
    show_geometry: bool,
    output_format: str,
    output: str | None
) -> None:
    """
    Get complete parcel information with ownership details.

    \b
    Examples:
      cadastral get-parcel 103/2 -m SAVAR
      cadastral get-parcel 103/2 -m 334979 --show-owners
      cadastral get-parcel 103/2 -m 334979 --detail owners
      cadastral get-parcel 103/2 -m 334979 --format json -o parcel.json
    """
    try:
        with CadastralAPIClient() as client:
            # Resolve municipality
            municipality_code = _resolve_municipality(client, municipality)

            # Get parcel
            with console.status(_("Fetching parcel {parcel_number}...").format(
                parcel_number=parcel_number
            )):
                parcel = client.get_parcel_by_number(parcel_number, municipality_code)

            if not parcel:
                print_error(_("Parcel '{parcel_number}' not found").format(
                    parcel_number=parcel_number
                ))
                raise SystemExit(1)

            # Get geometry if requested or for full detail (needed for accurate map URL)
            geometry = None
            if show_geometry or detail in ["geometry", "full"]:
                with console.status(_("Fetching geometry...")):
                    geometry = client.get_parcel_geometry(parcel_number, municipality_code)

            # Format output based on detail level
            if output_format != "table":
                # For non-table formats, output structured data
                data = _format_structured_data(parcel, geometry, detail, show_owners)
                print_output(data, format=output_format, file=output)
            else:
                # Rich formatted table output
                _print_table_output(parcel, geometry, detail, show_owners, show_geometry)

    except CadastralAPIError as e:
        if e.error_type == ErrorType.PARCEL_NOT_FOUND:
            parcel_num = e.details.get("parcel_number", parcel_number)
            muni_code = e.details.get("municipality_reg_num", municipality_code)
            print_error(_("Parcel '{parcel_number}' not found in municipality {municipality}").format(
                parcel_number=parcel_num,
                municipality=muni_code
            ))
        else:
            print_error(_("API error: {error_type}").format(error_type=e.error_type.value))
        raise SystemExit(1)


def _print_table_output(parcel, geometry, detail: str, show_owners: bool, show_geometry: bool) -> None:
    """Print rich formatted table output."""

    if detail == "basic":
        _print_basic_info(parcel)
    elif detail == "owners":
        _print_ownership_info(parcel)
    elif detail == "landuse":
        _print_landuse_info(parcel)
    elif detail == "geometry":
        _print_basic_info(parcel)
        if geometry:
            _print_geometry_info(geometry)
    else:  # full
        # Use unified function for consistent output
        print_parcel_details(
            parcel=parcel,
            geometry=geometry,
            show_owners=show_owners,
            show_geometry=show_geometry
        )


def print_parcel_details(
    parcel,
    geometry=None,
    show_owners: bool = False,
    show_geometry: bool = False,
    parcel_index: int | None = None,
    total_parcels: int | None = None
) -> None:
    """
    Print detailed parcel information in a consistent format.

    Used by both get-parcel and batch-fetch commands to ensure consistent output.

    Args:
        parcel: ParcelInfo object with parcel data
        geometry: Optional ParcelGeometry object for map URLs and geometry display
        show_owners: Whether to show ownership information
        show_geometry: Whether to show geometry details
        parcel_index: Optional index for batch mode (1-based)
        total_parcels: Optional total count for batch mode
    """
    # Optional batch mode header
    if parcel_index is not None and total_parcels is not None:
        console.print(
            f"\n[bold green]━━━ {_('Parcel')} {parcel_index}/{total_parcels}: "
            f"✓ {parcel.parcel_number} ━━━[/bold green]"
        )

    # Basic info
    _print_basic_info(parcel)
    console.print()

    # Land use
    _print_landuse_info(parcel)

    # Ownership
    if show_owners or parcel.total_owners > 0:
        console.print()
        _print_ownership_info(parcel)

    # Land registry
    console.print()
    _print_registry_info(parcel)

    # Geometry
    if show_geometry and geometry:
        console.print()
        _print_geometry_info(geometry)

    # Additional info (includes MAP URL)
    console.print()
    _print_additional_info(parcel, geometry)


def _print_basic_info(parcel) -> None:
    """Print basic parcel information."""
    header = _("PARCEL INFORMATION")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(_("Field"), style="bold")
    table.add_column(_("Value"))

    table.add_row(_("Parcel Number"), parcel.parcel_number)
    table.add_row(_("Parcel ID"), str(parcel.parcel_id))
    table.add_row(_("Municipality"), f"{parcel.municipality_name} ({parcel.municipality_reg_num})")
    table.add_row(_("Address"), parcel.address or _("N/A"))
    table.add_row(_("Area"), f"{parcel.area_numeric:,} m²" if parcel.area_numeric else _("N/A"))
    table.add_row(_("Building Permitted"), _("Yes") if parcel.has_building_right else _("No"))

    console.print(table)


def _print_landuse_info(parcel) -> None:
    """Print land use information."""
    header = _("LAND USE")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")

    if not parcel.land_use_summary:
        console.print(_("No land use data available"), style="dim")
        return

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column(_("Type"), style="bold")
    table.add_column(_("Area (m²)"), justify="right")
    table.add_column(_("Percentage"), justify="right")
    table.add_column(_("Buildings"))

    total_area = parcel.area_numeric or sum(parcel.land_use_summary.values())

    for land_type, area in parcel.land_use_summary.items():
        percentage = (area / total_area * 100) if total_area > 0 else 0
        # Find if this land type has buildings
        has_building = any(
            part.building for part in parcel.parcel_parts if part.name == land_type
        )
        table.add_row(
            land_type,
            f"{area:,}",
            f"{percentage:.1f}%",
            _("Yes") if has_building else _("No")
        )

    console.print(table)


def _print_ownership_info(parcel) -> None:
    """Print ownership information."""
    owners_text = ngettext("{count} owner", "{count} owners", parcel.total_owners).format(
        count=parcel.total_owners
    )
    header = f"{_('OWNERSHIP')} ({owners_text})"
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")

    if not parcel.possession_sheets:
        console.print(_("No ownership data available"), style="dim")
        return

    for i, sheet in enumerate(parcel.possession_sheets, 1):
        if len(parcel.possession_sheets) > 1:
            console.print(
                f"\n{_('Possession Sheet')} {i} - {sheet.possession_sheet_number}",
                style="bold yellow"
            )

        if not sheet.possessors:
            console.print(f"  {_('No possessors listed')}", style="dim")
            continue

        table = Table(show_header=True, box=None, padding=(0, 2))
        table.add_column(_("Name"), style="bold")
        table.add_column(_("Ownership"), justify="right")
        table.add_column(_("Address"))

        for possessor in sheet.possessors:
            ownership_str = possessor.ownership or _("N/A")
            if possessor.ownership_decimal is not None:
                ownership_str = f"{possessor.ownership} ({possessor.ownership_decimal * 100:.1f}%)"

            table.add_row(
                possessor.name,
                ownership_str,
                possessor.address
            )

        console.print(table)


def _print_registry_info(parcel) -> None:
    """Print land registry information."""
    header = _("LAND REGISTRY")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")

    if not parcel.lr_unit:
        console.print(_("No land registry data available"), style="dim")
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(_("Field"), style="bold")
    table.add_column(_("Value"))

    lr = parcel.lr_unit
    table.add_row(_("Unit Number"), lr.lr_unit_number or _("N/A"))
    table.add_row(
        _("Main Book"),
        f"{lr.main_book_name} ({lr.main_book_id})" if lr.main_book_name else _("N/A")
    )
    table.add_row(_("Institution"), lr.institution_name or _("N/A"))
    table.add_row(_("Status"), _("Active") if lr.active else _("Inactive"))
    table.add_row(_("Verified"), _("Yes") if lr.verified else _("No"))

    console.print(table)


def _print_geometry_info(geometry) -> None:
    """Print geometry information."""
    header = _("GEOMETRY")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(_("Field"), style="bold")
    table.add_column(_("Value"))

    table.add_row(_("Coordinate System"), geometry.srs_name)
    table.add_row(_("Vertices"), str(geometry.coordinate_count))
    table.add_row(_("GIS Area"), f"{geometry.povrsina_graficka:.2f} m²")

    min_x, min_y, max_x, max_y = geometry.bounds
    table.add_row(_("Bounding Box"), "")
    table.add_row("  Min X", f"{min_x:,.2f} m")
    table.add_row("  Min Y", f"{min_y:,.2f} m")
    table.add_row("  Max X", f"{max_x:,.2f} m")
    table.add_row("  Max Y", f"{max_y:,.2f} m")
    table.add_row(_("  Width"), f"{max_x - min_x:,.2f} m")
    table.add_row(_("  Height"), f"{max_y - min_y:,.2f} m")

    console.print(table)
    console.print(
        f"\n💡 {_('To export coordinates')}: cadastral get-geometry {geometry.broj_cestice} "
        "--format wkt",
        style="dim"
    )


def _print_additional_info(parcel, geometry=None) -> None:
    """Print additional information."""
    header = _("ADDITIONAL INFO")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(_("Field"), style="bold")
    table.add_column(_("Value"), no_wrap=False, overflow="fold")

    # Generate map URL with center coordinates if geometry is available
    if geometry:
        center_x, center_y = geometry.center
        map_url = (
            f"https://oss.uredjenazemlja.hr/map?"
            f"center={center_x:.2f},{center_y:.2f}&zoom=19&"
            f"layers=DOF5_2023_2024,DKP_CESTICE,DKP_KATASTARSKE_OPCINE,zupanija,ulica,kucni_broj"
        )
    else:
        # Fallback to basic map URL without center coordinates
        map_url = (
            "https://oss.uredjenazemlja.hr/map?"
            "layers=DOF5_2023_2024,DKP_CESTICE,DKP_KATASTARSKE_OPCINE,zupanija,ulica,kucni_broj"
        )

    table.add_row(_("Map URL"), map_url)
    table.add_row(_("Detail Sheet"), parcel.detail_sheet_number or _("N/A"))

    console.print(table)


def _format_structured_data(parcel, geometry, detail: str, show_owners: bool) -> dict:
    """Format parcel data for JSON/CSV export."""
    data = {
        "parcel_number": parcel.parcel_number,
        "parcel_id": parcel.parcel_id,
        "municipality_code": parcel.municipality_reg_num,
        "municipality_name": parcel.municipality_name,
        "address": parcel.address,
        "area_m2": parcel.area_numeric,
        "building_permitted": parcel.has_building_right,
    }

    if detail in ["full", "landuse"]:
        data["land_use"] = parcel.land_use_summary
        data["parcel_parts"] = [
            {
                "type": part.name,
                "area": part.area_numeric,
                "has_building": part.building,
            }
            for part in parcel.parcel_parts
        ]

    if detail in ["full", "owners"] or show_owners:
        data["total_owners"] = parcel.total_owners
        data["ownership"] = [
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
                ]
            }
            for sheet in parcel.possession_sheets
        ]

    if detail == "full":
        data["land_registry"] = {
            "unit_number": parcel.lr_unit.lr_unit_number if parcel.lr_unit else None,
            "main_book": parcel.lr_unit.main_book_name if parcel.lr_unit else None,
            "institution": parcel.lr_unit.institution_name if parcel.lr_unit else None,
            "active": parcel.lr_unit.active if parcel.lr_unit else None,
        }

    if geometry and detail == "geometry":
        data["geometry"] = {
            "srs_name": geometry.srs_name,
            "vertices": geometry.coordinate_count,
            "area_gis": geometry.povrsina_graficka,
            "bounds": {
                "min_x": geometry.bounds[0],
                "min_y": geometry.bounds[1],
                "max_x": geometry.bounds[2],
                "max_y": geometry.bounds[3],
            },
            "coordinates": [[c.x, c.y] for c in geometry.coordinates],
        }

    return data
