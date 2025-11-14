#!/usr/bin/env python3
"""
Basic usage example for Croatian Cadastral API client.

This script demonstrates how to search for parcels and retrieve detailed information
using verified test data from SAVAR municipality.
"""

import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cadastral_api import CadastralAPIClient, CadastralAPIError, ErrorType


def print_parcel_summary(parcel_number: str, municipality_code: str) -> None:
    """
    Search and display summary information for a parcel.

    Args:
        parcel_number: Parcel number to search
        municipality_code: Municipality registration number
    """
    print(f"\n{'='*80}")
    print(f"Searching for parcel: {parcel_number} in municipality {municipality_code}")
    print(f"{'='*80}\n")

    with CadastralAPIClient() as client:
        try:
            # Search for parcel
            search_results = client.search_parcel(parcel_number, municipality_code)
            print(f"Found {len(search_results)} result(s):")
            for result in search_results:
                print(f"  - Parcel {result.parcel_number} (ID: {result.parcel_id})")

            # Get detailed info for exact match
            parcel_info = client.get_parcel_by_number(
                parcel_number, municipality_code, exact_match=True
            )

            if not parcel_info:
                print(f"\n❌ No exact match found for parcel {parcel_number}")
                return

            # Display parcel information
            print(f"\n📍 Parcel Details:")
            print(f"   Number: {parcel_info.parcel_number}")
            print(f"   ID: {parcel_info.parcel_id}")
            print(f"   Municipality: {parcel_info.cad_municipality_name}")
            print(f"   Address: {parcel_info.address}")
            print(f"   Area: {parcel_info.area_numeric:,} m²")
            print(f"   Building permitted: {'Yes' if parcel_info.has_building_right else 'No'}")

            # Land use information
            print(f"\n🌾 Land Use:")
            for land_type, area in parcel_info.land_use_summary.items():
                print(f"   {land_type}: {area:,} m²")

            # Ownership information
            print(f"\n👥 Ownership ({parcel_info.total_owners} owner(s)):")
            for sheet in parcel_info.possession_sheets:
                print(f"   Possession Sheet: {sheet.possession_sheet_number}")
                for possessor in sheet.possessors:
                    ownership_str = (
                        f" ({possessor.ownership})"
                        if possessor.ownership
                        else " (fraction not specified)"
                    )
                    print(f"     • {possessor.name}{ownership_str}")
                    print(f"       Address: {possessor.address}")

            # Map URL
            map_url = client.get_map_url(parcel_info.parcel_id)
            print(f"\n🗺️  View on map: {map_url}")

        except CadastralAPIError as e:
            if e.error_type == ErrorType.PARCEL_NOT_FOUND:
                parcel_num = e.details.get("parcel_number", parcel_number)
                muni_code = e.details.get("municipality_reg_num", municipality_code)
                print(f"❌ Parcel '{parcel_num}' not found in municipality '{muni_code}'")
            else:
                print(f"❌ API Error ({e.error_type.value})")
                if e.cause:
                    print(f"   Caused by: {e.cause}")
        except Exception as e:
            print(f"❌ Error: {e}")
            raise


def main() -> None:
    """Run example queries for verified test parcels."""
    print("Croatian Cadastral API Client - Basic Usage Example")
    print("=" * 80)

    # SAVAR municipality code
    MUNICIPALITY_CODE = "334979"

    # Test parcels (verified in SAVAR, Court: Zadar)
    test_parcels = [
        "103/2",  # Simple parcel with 2 owners, no ownership fractions
        "45",  # Parcel with ownership fractions and parcel links
        "396/1",  # Complex parcel with 18 owners
    ]

    print("\nTesting with verified parcels from SAVAR municipality...")

    for parcel_number in test_parcels:
        print_parcel_summary(parcel_number, MUNICIPALITY_CODE)

    print(f"\n{'='*80}")
    print("Example completed successfully!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
