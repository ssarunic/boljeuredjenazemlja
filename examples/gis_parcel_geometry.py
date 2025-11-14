#!/usr/bin/env python3
"""
GIS parcel geometry example for Croatian Cadastral API client.

Demonstrates downloading and using parcel boundary geometries.
"""

import sys
from pathlib import Path

# Add src to path for local development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cadastral_api import CadastralAPIClient


def main() -> None:
    """Demonstrate GIS geometry features."""
    print("Croatian Cadastral API - GIS Geometry Example")
    print("=" * 80)

    with CadastralAPIClient() as client:
        # Example 1: Get parcel geometry
        print("\n1. Getting parcel geometry for 103/2 in SAVAR")
        print("-" * 80)

        geometry = client.get_parcel_geometry("103/2", "334979")

        if geometry:
            print(f"✓ Found parcel: {geometry.broj_cestice}")
            print(f"  Parcel ID: {geometry.cestica_id}")
            print(f"  Municipality: {geometry.maticni_broj_ko}")
            print(f"  Area (GIS): {geometry.povrsina_graficka} m²")
            print(f"  Coordinate system: {geometry.srs_name}")
            print(f"  Number of vertices: {geometry.coordinate_count}")

            # Bounding box
            min_x, min_y, max_x, max_y = geometry.bounds
            print(f"\n  Bounding box:")
            print(f"    Min X: {min_x:,.2f}")
            print(f"    Min Y: {min_y:,.2f}")
            print(f"    Max X: {max_x:,.2f}")
            print(f"    Max Y: {max_y:,.2f}")
            print(f"    Width: {max_x - min_x:,.2f} m")
            print(f"    Height: {max_y - min_y:,.2f} m")

            # First few coordinates
            print(f"\n  First 5 coordinates:")
            for i, coord in enumerate(geometry.coordinates[:5]):
                print(f"    {i+1}. {coord}")

            # Export formats
            print(f"\n  Export formats:")
            print(f"    WKT: {geometry.to_wkt()[:100]}...")
            print(f"    GeoJSON coords: {len(geometry.to_geojson_coords())} points")

        else:
            print("✗ Parcel not found")

        # Example 2: Compare API data with GIS data
        print("\n\n2. Comparing API data vs GIS data")
        print("-" * 80)

        # Get API data
        api_data = client.get_parcel_by_number("103/2", "334979")
        gis_data = client.get_parcel_geometry("103/2", "334979")

        if api_data and gis_data:
            print(f"Parcel number: {api_data.parcel_number} (API) vs {gis_data.broj_cestice} (GIS)")
            print(f"Area: {api_data.area_numeric} m² (API) vs {gis_data.povrsina_graficka} m² (GIS)")

            area_diff = abs(api_data.area_numeric - gis_data.povrsina_graficka)
            area_diff_pct = (area_diff / api_data.area_numeric) * 100
            print(f"Area difference: {area_diff:.2f} m² ({area_diff_pct:.2f}%)")

        # Example 3: Multiple parcels
        print("\n\n3. Getting geometries for multiple parcels")
        print("-" * 80)

        parcel_numbers = ["103/2", "103/3", "114"]

        for parcel_num in parcel_numbers:
            geom = client.get_parcel_geometry(parcel_num, "334979")
            if geom:
                print(f"✓ {parcel_num:10s} - {geom.povrsina_graficka:8.2f} m² - {geom.coordinate_count:3d} vertices")
            else:
                print(f"✗ {parcel_num:10s} - Not found")

        # Example 4: Cache information
        print("\n\n4. GIS Cache Information")
        print("-" * 80)

        cache_dir = client.gis_cache.cache_dir
        print(f"Cache directory: {cache_dir}")

        if client.gis_cache.is_cached("334979"):
            print("✓ Municipality 334979 (SAVAR) is cached")
            zip_path = client.gis_cache.get_zip_path("334979")
            gml_path = client.gis_cache.get_gml_path("334979", "katastarske_cestice.gml")

            import os
            zip_size = os.path.getsize(zip_path) if zip_path.exists() else 0
            gml_size = os.path.getsize(gml_path) if gml_path.exists() else 0

            print(f"  ZIP file: {zip_size / 1024:.1f} KB")
            print(f"  GML file: {gml_size / 1024 / 1024:.1f} MB")

        # To clear cache (uncomment if needed):
        # client.gis_cache.clear_municipality("334979")
        # client.gis_cache.clear_all()

    print("\n" + "=" * 80)
    print("GIS geometry example completed!")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
