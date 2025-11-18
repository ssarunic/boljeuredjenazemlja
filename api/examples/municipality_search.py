#!/usr/bin/env python3
"""
Municipality search example for Croatian Cadastral API client.

Demonstrates the newly discovered municipality search endpoint.
"""

import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cadastral_api import CadastralAPIClient, CadastralAPIError, ErrorType


def search_and_display(search_term: str) -> None:
    """
    Find municipalities and display results.

    Args:
        search_term: Municipality name or registration code
    """
    print(f"\n{'='*80}")
    print(f"Finding: '{search_term}'")
    print(f"{'='*80}\n")

    with CadastralAPIClient() as client:
        try:
            results = client.find_municipality(search_term)

            print(f"Found {len(results)} result(s):\n")

            for i, result in enumerate(results, 1):
                print(f"{i}. {result.municipality_name}")
                print(f"   Registration Number: {result.municipality_reg_num}")
                print(f"   Municipality ID: {result.municipality_id}")
                print(f"   Institution ID: {result.institution_id}")
                print(f"   Full Info: {result.display_value}")
                print()

        except CadastralAPIError as e:
            if e.error_type == ErrorType.MUNICIPALITY_NOT_FOUND:
                search = e.details.get("search_term", search_term)
                print(f"❌ Municipality '{search}' not found")
            else:
                print(f"❌ API Error ({e.error_type.value})")
                if e.cause:
                    print(f"   Caused by: {e.cause}")
        except Exception as e:
            print(f"❌ Error: {e}")
            raise


def main() -> None:
    """Run municipality find examples."""
    print("Croatian Cadastral API - Municipality Find Example")
    print("=" * 80)

    # Test different search patterns
    search_terms = [
        "SAVAR",  # Exact name
        "334979",  # By code
        "LUKA",  # Partial name (returns multiple)
        "ZADAR",  # City name
        "334731",  # LUKA by code
    ]

    for term in search_terms:
        search_and_display(term)

    print(f"\n{'='*80}")
    print("Municipality find examples completed!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
