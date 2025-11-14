"""Example of fully localized CLI command - search.py pattern.

This file shows how to localize the search command. Apply the same pattern
to all other command files (parcel.py, discovery.py, gis.py, cache.py).
"""

import click
from rich.console import Console

from ... import CadastralAPIClient
from ...exceptions import CadastralAPIError, MunicipalityNotFoundError, ParcelNotFoundError
from ...i18n import _, ngettext
from ..formatters import print_error, print_output

console = Console()


@click.command()
@click.argument("parcel_number")
@click.option("--municipality", "-m", required=True, help=_("Municipality name or code"))
@click.option("--exact/--partial", default=True, help=_("Exact match or partial search"))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help=_("Output format"),
)
@click.option("--output", "-o", type=click.Path(), help=_("Save output to file"))
@click.pass_context
def search(
    ctx: click.Context,
    parcel_number: str,
    municipality: str,
    exact: bool,
    output_format: str,
    output: str | None,
) -> None:
    """
    Quick search for parcels with basic information.

    \\b
    Examples:
      cadastral search 103/2 --municipality SAVAR
      cadastral search 103/2 -m 334979
      cadastral search 114 -m 334979 --partial
    """
    try:
        with CadastralAPIClient() as client:
            # Resolve municipality - localized status message
            with console.status(
                _("Resolving municipality {muni}...").format(muni=municipality)
            ):
                municipality_code = _resolve_municipality(client, municipality)

            # Search for parcel - localized status message
            with console.status(
                _("Searching for parcel {num}...").format(num=parcel_number)
            ):
                parcel = client.get_parcel_by_number(
                    parcel_number, municipality_code, exact_match=exact
                )

            if not parcel:
                # Localized error message
                print_error(
                    _("Parcel '{num}' not found in municipality {muni}").format(
                        num=parcel_number, muni=municipality
                    )
                )

                # Localized suggestions
                console.print(_("\nSuggestions:"), style="yellow")
                console.print(
                    _(
                        "  • Try partial search: cadastral search {num} -m {muni} --partial"
                    ).format(num=parcel_number, muni=municipality)
                )
                console.print(_("  • Check parcel number format"))
                console.print(_("  • View on map: https://oss.uredjenazemlja.hr/map"))
                raise SystemExit(1)

            # Localized table headers for display
            data = {
                _("Parcel Number"): parcel.parcel_number,
                _("Municipality"): f"{parcel.municipality_name} ({parcel.municipality_reg_num})",
                _("Address"): parcel.address or _("N/A"),
                _("Area"): f"{parcel.area_numeric:,} m²"
                if parcel.area_numeric
                else _("N/A"),
                _("Land Use"): ", ".join(parcel.land_use_summary.keys())
                if parcel.land_use_summary
                else _("N/A"),
                _("Building Permitted"): _("Yes")
                if parcel.has_building_right
                else _("No"),
                # Using ngettext for plural forms
                _("Owners"): ngettext(
                    "{count} owner", "{count} owners", parcel.total_owners
                ).format(count=parcel.total_owners)
                if parcel.total_owners
                else _("Unknown"),
            }

            if output_format == "table":
                from ..formatters import format_table

                console.print(format_table(data), highlight=False)
                # Localized hint
                console.print(
                    _(
                        "\n💡 For full details: cadastral get-parcel {num} -m {code}"
                    ).format(num=parcel_number, code=municipality_code),
                    style="dim",
                )
            else:
                # JSON/CSV export - keys stay in English (API standard)
                export_data = {
                    "parcel_number": parcel.parcel_number,
                    "municipality_code": parcel.municipality_reg_num,
                    "municipality_name": parcel.municipality_name,
                    "address": parcel.address,
                    "area_m2": parcel.area_numeric,
                    "land_use": list(parcel.land_use_summary.keys()),
                    "building_permitted": parcel.has_building_right,
                    "total_owners": parcel.total_owners,
                    "parcel_id": parcel.parcel_id,
                }
                print_output(export_data, format=output_format, file=output)

    except ParcelNotFoundError as e:
        print_error(str(e))
        raise SystemExit(1)
    except MunicipalityNotFoundError as e:
        print_error(str(e))
        console.print(_("\nSuggestions:"), style="yellow")
        console.print(
            _(
                "  • Search for municipalities: cadastral search-municipality {term}"
            ).format(term=municipality)
        )
        console.print(_("  • Use municipality code instead: --municipality 334979"))
        console.print(_("  • List all municipalities: cadastral list-municipalities"))
        raise SystemExit(1)
    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=e))
        raise SystemExit(1)


def _resolve_municipality(client: CadastralAPIClient, municipality: str) -> str:
    """
    Resolve municipality name to code.

    Args:
        client: API client instance
        municipality: Municipality name or code

    Returns:
        Municipality registration number (code)

    Raises:
        MunicipalityNotFoundError: If municipality not found
    """
    # If it's already a numeric code, return it
    if municipality.isdigit():
        return municipality

    # Search for municipality by name
    results = client.search_municipality(search_term=municipality.upper())

    if not results:
        raise MunicipalityNotFoundError(
            _("Municipality '{muni}' not found").format(muni=municipality)
        )

    if len(results) == 1:
        return results[0].municipality_reg_num

    # Multiple results - try exact match
    for result in results:
        if result.municipality_name.upper() == municipality.upper():
            return result.municipality_reg_num

    # Ambiguous - show suggestions with localized message
    console.print(
        _("\n⚠️  Multiple municipalities found for '{term}':").format(term=municipality),
        style="yellow bold",
    )
    console.print()

    from rich.table import Table

    table = Table(show_header=True, box=None, padding=(0, 2))
    table.add_column(_("Code"), style="bold")
    table.add_column(_("Name"))
    table.add_column(_("Office"))

    for result in results[:10]:  # Show first 10
        table.add_row(
            result.municipality_reg_num,
            result.municipality_name,
            str(result.institution_id),
        )

    console.print(table)

    if len(results) > 10:
        console.print(
            _("\n... and {count} more").format(count=len(results) - 10), style="dim"
        )

    console.print(
        _("\n💡 Use specific code: --municipality {code}").format(
            code=results[0].municipality_reg_num
        ),
        style="dim",
    )

    raise MunicipalityNotFoundError(
        _("Please specify municipality code to avoid ambiguity")
    )


# Key Points for Localization:
#
# 1. Import `_` and `ngettext` from i18n module
# 2. Wrap all user-facing strings in _()
# 3. Use named placeholders: {name} not %s or {}
# 4. Keep command/option names in English
# 5. Keep JSON/CSV keys in English
# 6. Localize table headers for display
# 7. Use ngettext() for plurals
# 8. Keep technical terms in English (wkt, geojson, etc.)
# 9. Localize error messages, suggestions, hints
# 10. Test both languages thoroughly
