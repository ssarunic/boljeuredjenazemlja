"""GIS commands for CLI - geometry and spatial data."""

import json

import click
from rich.console import Console
from rich.table import Table

from ... import CadastralAPIClient
from ...exceptions import CadastralAPIError
from ...i18n import _
from ..formatters import print_error, print_success
from .search import _resolve_municipality

console = Console()


@click.command("get-geometry")
@click.argument("parcel_number")
@click.option("--municipality", "-m", required=True, help="Municipality name or code")
@click.option("--format", "-f", "output_format", type=click.Choice(["wkt", "geojson", "csv", "json"]), default="wkt", help="Export format")
@click.option("--output", "-o", type=click.Path(), help="Save output to file")
@click.option("--show-stats", is_flag=True, help="Include geometry statistics")
@click.pass_context
def get_geometry(
    ctx: click.Context,
    parcel_number: str,
    municipality: str,
    output_format: str,
    output: str | None,
    show_stats: bool
) -> None:
    """
    Get parcel boundary coordinates for GIS integration.

    \b
    Examples:
      cadastral get-geometry 103/2 -m SAVAR
      cadastral get-geometry 103/2 -m 334979 --format wkt
      cadastral get-geometry 103/2 -m 334979 --format geojson -o parcel.geojson
      cadastral get-geometry 103/2 -m 334979 --format csv -o coords.csv
    """
    try:
        with CadastralAPIClient() as client:
            # Resolve municipality
            municipality_code = _resolve_municipality(client, municipality)

            # Get geometry
            with console.status(_("Fetching geometry for parcel {parcel_number}...").format(
                parcel_number=parcel_number
            )):
                geometry = client.get_parcel_geometry(parcel_number, municipality_code)

            if not geometry:
                print_error(_("Geometry not found for parcel '{parcel_number}'").format(
                    parcel_number=parcel_number
                ))
                console.print(_("\nNote: GIS data must be downloaded first (this happens automatically)"), style="yellow")
                raise SystemExit(1)

            # Show statistics if requested
            if show_stats and output_format in ["wkt", "geojson"]:
                _print_geometry_stats(geometry)
                console.print()

            # Format and output geometry
            if output_format == "wkt":
                output_data = geometry.to_wkt()
                if output:
                    with open(output, "w", encoding="utf-8") as f:
                        f.write(output_data)
                    print_success(_("WKT saved to: {output}").format(output=output))
                else:
                    console.print(output_data)

            elif output_format == "geojson":
                geojson = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [geometry.to_geojson_coords()]
                    },
                    "properties": {
                        "parcel_number": geometry.broj_cestice,
                        "municipality": geometry.maticni_broj_ko,
                        "area_m2": geometry.povrsina_graficka,
                        "srs": geometry.srs_name,
                    }
                }
                output_data = json.dumps(geojson, indent=2, ensure_ascii=False)
                if output:
                    with open(output, "w", encoding="utf-8") as f:
                        f.write(output_data)
                    print_success(_("GeoJSON saved to: {output}").format(output=output))
                else:
                    console.print(output_data)

            elif output_format == "csv":
                csv_output = "x,y,vertex\n"
                for i, coord in enumerate(geometry.coordinates, 1):
                    csv_output += f"{coord.x},{coord.y},{i}\n"

                if output:
                    with open(output, "w", encoding="utf-8") as f:
                        f.write(csv_output)
                    print_success(_("CSV saved to: {output}").format(output=output))
                else:
                    console.print(csv_output)

            elif output_format == "json":
                json_data = {
                    "parcel_number": geometry.broj_cestice,
                    "municipality": geometry.maticni_broj_ko,
                    "area_m2": geometry.povrsina_graficka,
                    "srs": geometry.srs_name,
                    "vertex_count": geometry.coordinate_count,
                    "bounds": {
                        "min_x": geometry.bounds[0],
                        "min_y": geometry.bounds[1],
                        "max_x": geometry.bounds[2],
                        "max_y": geometry.bounds[3],
                    },
                    "coordinates": [[c.x, c.y] for c in geometry.coordinates]
                }
                output_data = json.dumps(json_data, indent=2, ensure_ascii=False)
                if output:
                    with open(output, "w", encoding="utf-8") as f:
                        f.write(output_data)
                    print_success(_("JSON saved to: {output}").format(output=output))
                else:
                    console.print(output_data)

    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=str(e)))
        raise SystemExit(1)


@click.command("download-gis")
@click.argument("municipality")
@click.option("--output", "-o", type=click.Path(), required=True, help="Output directory")
@click.option("--extract/--no-extract", default=True, help="Extract ZIP file")
@click.option("--clear-cache", is_flag=True, help="Clear cached data first")
@click.pass_context
def download_gis(
    ctx: click.Context,
    municipality: str,
    output: str,
    extract: bool,
    clear_cache: bool
) -> None:
    """
    Download complete GIS data for a municipality.

    \b
    Examples:
      cadastral download-gis 334979 --output ./gis_data
      cadastral download-gis SAVAR --output ./savar_gis --extract
      cadastral download-gis 334979 -o ./data --clear-cache
    """
    try:
        from pathlib import Path
        import shutil
        import zipfile

        with CadastralAPIClient() as client:
            # Resolve municipality
            municipality_code = _resolve_municipality(client, municipality)

            # Clear cache if requested
            if clear_cache:
                with console.status(_("Clearing cache...")):
                    client.gis_cache.clear_municipality(municipality_code)
                console.print(_("Cache cleared"), style="green")

            # Download GIS data
            console.print(_("Downloading GIS data for municipality {municipality_code}...").format(
                municipality_code=municipality_code
            ), style="cyan")

            with console.status(_("Downloading...")):
                zip_path = client.gis_cache.download_municipality(municipality_code, force=clear_cache)

            zip_size = zip_path.stat().st_size / 1024
            print_success(_("Downloaded: {filename} ({size} KB)").format(
                filename=zip_path.name,
                size=f"{zip_size:.1f}"
            ))

            # Extract if requested
            output_path = Path(output)
            output_path.mkdir(parents=True, exist_ok=True)

            if extract:
                with console.status(_("Extracting...")):
                    with zipfile.ZipFile(zip_path, 'r') as zf:
                        zf.extractall(output_path)

                print_success(_("Extracted to: {output_path}").format(output_path=output_path))

                # List extracted files
                console.print(_("\nFiles:"), style="bold")
                files = list(output_path.glob("*.gml"))
                for file in files:
                    file_size = file.stat().st_size / 1024 / 1024
                    console.print(f"  • {file.name} ({file_size:.1f} MB)")

                # Try to count parcels
                try:
                    from ...gis import GMLParser
                    parcel_file = output_path / "katastarske_cestice.gml"
                    if parcel_file.exists():
                        parser = GMLParser(parcel_file)
                        count = parser.count_parcels()
                        console.print(_("\nTotal parcels: {count}").format(count=count), style="bold green")
                except Exception:
                    pass
            else:
                # Just copy ZIP file
                dest_zip = output_path / zip_path.name
                shutil.copy(zip_path, dest_zip)
                print_success(_("ZIP file copied to: {dest_zip}").format(dest_zip=dest_zip))

            console.print(_("\nTo get parcel geometry: cadastral get-geometry <parcel> -m {municipality_code}").format(
                municipality_code=municipality_code
            ), style="dim")

    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=str(e)))
        raise SystemExit(1)
    except Exception as e:
        print_error(_("Error downloading GIS data: {error}").format(error=str(e)))
        raise SystemExit(1)


def _print_geometry_stats(geometry) -> None:
    """Print geometry statistics."""
    header = _("GEOMETRY STATISTICS")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(_("Field"), style="bold")
    table.add_column(_("Value"))

    table.add_row(_("Parcel"), geometry.broj_cestice)
    table.add_row(_("Coordinate System"), geometry.srs_name)
    table.add_row(_("Vertices"), str(geometry.coordinate_count))
    table.add_row(_("Area (GIS)"), f"{geometry.povrsina_graficka:.2f} m²")

    min_x, min_y, max_x, max_y = geometry.bounds
    table.add_row("", "")
    table.add_row(_("Bounding Box"), "")
    table.add_row(_("  Min X"), f"{min_x:,.2f} m")
    table.add_row(_("  Min Y"), f"{min_y:,.2f} m")
    table.add_row(_("  Max X"), f"{max_x:,.2f} m")
    table.add_row(_("  Max Y"), f"{max_y:,.2f} m")
    table.add_row(_("  Width"), f"{max_x - min_x:,.2f} m")
    table.add_row(_("  Height"), f"{max_y - min_y:,.2f} m")

    console.print(table)
