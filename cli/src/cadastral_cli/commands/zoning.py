"""Spatial-plan commands for CLI - what the plans' building areas say about a parcel."""

import json
import math
from typing import Any

import click
from cadastral_api import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError
from cadastral_api.i18n import _
from cadastral_api.models.planning_entities import ParcelZoning, ZoneKind, ZoningStatus
from rich.console import Console
from rich.table import Table

from cadastral_cli.formatters import (
    command_help,
    create_rich_table,
    describe_error,
    print_error,
    print_output,
    print_success,
)

from .search import _resolve_municipality

console = Console()


_GET_ZONING_HELP = command_help(_("""Find out which spatial-plan building area a parcel lies in.

Matches the parcel boundary against the building areas (građevinska područja)
derived from the spatial plans in force: inside a settlement, in a detached
zone with its designation (for example T2 tourist settlement), or outside.
This is a screening only: it does not say whether anything may be built, and
the result is an interpretation of the plans, not the plans themselves.

Examples:
  cadastral get-zoning 103/2 -m SAVAR
  cadastral get-zoning 396/1 -m 334979 --format json
  cadastral get-zoning 45 -m SAVAR --format csv -o zoning.csv
  cadastral get-zoning 103/2 -m SAVAR --format geojson --show-geometry"""))


def _status_label(status: ZoningStatus) -> str:
    labels = {
        ZoningStatus.INSIDE_SETTLEMENT: _("Inside a settlement building area"),
        ZoningStatus.DETACHED_ZONE: _("In a detached building area outside a settlement"),
        ZoningStatus.TOUCHES_BELOW_THRESHOLD: _(
            "Touches a building area, below the overlap threshold"
        ),
        ZoningStatus.OUTSIDE: _("Outside building areas"),
    }
    return labels[status]


def _finite_percent(
    ctx: click.Context, param: click.Parameter, value: float | None
) -> float | None:
    """Reject NaN and infinity, which ``FloatRange`` lets through."""
    if value is not None and not math.isfinite(value):
        raise click.BadParameter(_("must be a number between 0 and 100"))
    return value


def _kind_label(kind: ZoneKind) -> str:
    return {
        ZoneKind.SETTLEMENT: _("settlement"),
        ZoneKind.DETACHED: _("detached"),
    }[kind]


@click.command("get-zoning", help=_GET_ZONING_HELP)
@click.argument("parcel_number")
@click.option("--municipality", "-m", required=True, help=_("Municipality name or code"))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv", "geojson"]),
    default="table",
    help=_("Output format"),
)
@click.option("--output", "-o", type=click.Path(), help=_("Save output to file"))
@click.option(
    "--show-geometry",
    is_flag=True,
    help=_("Include the zone polygons in JSON output"),
)
@click.option(
    "--min-overlap",
    type=click.FloatRange(0, 100),
    default=2.0,
    show_default=True,
    callback=_finite_percent,
    help=_("Zones covering less than this share of the parcel (percent) are listed separately"),
)
@click.pass_context
def get_zoning(
    ctx: click.Context,
    parcel_number: str,
    municipality: str,
    output_format: str,
    output: str | None,
    show_geometry: bool,
    min_overlap: float,
) -> None:
    """Find out which spatial-plan building area a parcel lies in."""
    try:
        with CadastralAPIClient() as client:
            municipality_code = _resolve_municipality(client, municipality)

            with console.status(
                _("Matching parcel {parcel_number} against the spatial plans...").format(
                    parcel_number=parcel_number
                )
            ):
                zoning = client.get_parcel_zoning(
                    parcel_number, municipality_code, min_overlap=min_overlap / 100.0
                )

            if zoning is None:
                print_error(
                    _("Geometry not found for parcel '{parcel_number}'").format(
                        parcel_number=parcel_number
                    )
                )
                console.print(
                    _("\nNote: GIS data must be downloaded first (this happens automatically)"),
                    style="yellow",
                )
                raise SystemExit(1)

            if output_format == "table":
                _print_zoning_table(zoning)
            elif output_format == "geojson":
                # GeoJSON is a standard format: keys are never localized
                text = json.dumps(_zoning_geojson(zoning), indent=2, ensure_ascii=False)
                if output:
                    with open(output, "w", encoding="utf-8") as f:
                        f.write(text)
                    print_success(_("GeoJSON saved to: {output}").format(output=output))
                else:
                    print(text)
            elif output_format == "csv":
                print_output(_zoning_rows(zoning), "csv", output)
            else:
                exclude = None
                if not show_geometry:
                    without_polygons = {"__all__": {"zone": {"polygons"}}}
                    exclude = {"matches": without_polygons, "below_threshold": without_polygons}
                print_output(zoning.model_dump(mode="json", exclude=exclude), "json", output)

    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=describe_error(e)))
        raise SystemExit(1) from e


def _zone_rows(zoning: ParcelZoning) -> list[tuple[str, Any]]:
    """Every intersecting zone with its kind of match: above or below the threshold."""
    return [("match", m) for m in zoning.matches] + [
        ("below_threshold", m) for m in zoning.below_threshold
    ]


def _zoning_rows(zoning: ParcelZoning) -> list[dict[str, Any]]:
    """One CSV row per intersecting zone (one row with the status when there is none).

    Zones under the threshold are rows too, marked in the ``match`` column,
    so a boundary case is never exported as if nothing intersected.
    """
    base = {
        "parcel_number": zoning.parcel_number,
        "municipality_code": zoning.municipality_code,
        "status": zoning.status.value,
        "in_building_area": zoning.in_building_area,
        "buildability": zoning.buildability,
    }
    zone_rows = _zone_rows(zoning)
    if not zone_rows:
        return [base]
    rows = []
    for kind_of_match, match in zone_rows:
        zone = match.zone
        rows.append(
            {
                **base,
                "match": kind_of_match,
                "zone_kind": zone.zone_kind.value,
                "generation": zone.generation.value,
                "designation_code": zone.designation_code,
                "designation": zone.designation,
                "zone_name": zone.zone_name,
                "plan_name": zone.plan_name,
                "plan_id": zone.plan_id,
                "overlap_fraction": match.overlap_fraction,
                "overlap_m2": match.overlap_m2,
            }
        )
    return rows


def _zoning_geojson(zoning: ParcelZoning) -> dict[str, Any]:
    """GeoJSON FeatureCollection of every intersecting zone (EPSG:3765).

    Each feature's ``match`` property is ``match`` or ``below_threshold``.
    """
    features = []
    for kind_of_match, match in _zone_rows(zoning):
        feature = match.zone.to_geojson()
        feature["properties"]["match"] = kind_of_match
        feature["properties"]["overlap_fraction"] = match.overlap_fraction
        feature["properties"]["overlap_m2"] = match.overlap_m2
        features.append(feature)
    return {
        "type": "FeatureCollection",
        "features": features,
        "properties": {
            "parcel_number": zoning.parcel_number,
            "municipality_code": zoning.municipality_code,
            "status": zoning.status.value,
            "buildability": zoning.buildability,
            "min_overlap": zoning.min_overlap,
            "dataset": zoning.dataset.model_dump(mode="json"),
        },
    }


def _print_zoning_table(zoning: ParcelZoning) -> None:
    """Rich table view of a parcel's zoning."""
    header = _("SPATIAL PLAN: BUILDING AREAS")
    console.print(f"\n{header}", style="bold cyan")
    console.print("=" * len(header), style="bold cyan")

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(_("Field"), style="bold")
    table.add_column(_("Value"), no_wrap=False, overflow="fold")
    table.add_row(_("Parcel"), zoning.parcel_number)
    table.add_row(_("Municipality"), zoning.municipality_code)
    if zoning.parcel_area_m2 is not None:
        table.add_row(_("Area (GIS)"), f"{zoning.parcel_area_m2:.2f} m²")
    table.add_row(_("Status"), _status_label(zoning.status))
    table.add_row(_("Buildability"), _("Not determined (screening only)"))
    if zoning.plans:
        table.add_row(_("Plans"), ", ".join(zoning.plans))
    console.print(table)

    if zoning.matches:
        zones = create_rich_table(
            _("Zones"),
            [_("Kind"), _("Code"), _("Designation"), _("Zone"), _("Plan"), _("Overlap")],
        )
        for match in zoning.matches:
            zone = match.zone
            zones.add_row(
                _kind_label(zone.zone_kind),
                zone.designation_code or "",
                zone.designation or "",
                zone.zone_name or "",
                zone.plan_name or "",
                f"{match.overlap_fraction:.0%}",
            )
        console.print()
        console.print(zones)

    if zoning.below_threshold:
        console.print()
        console.print(
            _("Below the {threshold:.0%} threshold: {zones}").format(
                threshold=zoning.min_overlap,
                zones="; ".join(
                    f"{m.zone.label()} ({m.overlap_fraction:.1%})" for m in zoning.below_threshold
                ),
            ),
            style="dim",
        )

    console.print()
    console.print(
        _(
            "Building areas are an interpretation of the spatial plans by the county "
            "spatial-planning institutes and may deviate from the plans in force. They must "
            "not be used to issue acts for spatial interventions or other public documents; "
            "for official purposes use the original plans in force."
        ),
        style="yellow",
    )
    dataset = zoning.dataset
    state = f" ({dataset.state})" if dataset.state else ""
    console.print(_("Source: {dataset}").format(dataset=f"{dataset.name}{state}"), style="dim")
    console.print(
        _("Whether anything may be built is not determined here; read the plan or ask for a "
          "lokacijska informacija."),
        style="dim",
    )
