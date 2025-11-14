#!/usr/bin/env python3.12
"""Debug script to check what the API is returning."""

import httpx
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("CADASTRAL_API_BASE_URL", "http://localhost:8000")
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
}

print(f"Testing API: {BASE_URL}\n")

# Step 1: Get municipality
print("Step 1: Searching for municipality 'SAVAR'...")
try:
    response = httpx.get(
        f"{BASE_URL}/search-cad-parcels/municipalities",
        params={"search": "SAVAR"},
        headers=HEADERS,
        timeout=10.0,
    )
    print(f"Status: {response.status_code}")
    print(f"Response type: {response.headers.get('content-type')}")
    print(f"Response length: {len(response.content)} bytes")
    print(f"Response text (first 500 chars):\n{response.text[:500]}")
    print()

    if response.status_code == 200:
        data = response.json()
        if data:
            municipality_reg_num = data[0].get('key1')
            print(f"Municipality code: {municipality_reg_num}\n")

            # Step 2: Search for parcel
            print(f"Step 2: Searching for parcel '1122/1' in municipality {municipality_reg_num}...")
            response2 = httpx.get(
                f"{BASE_URL}/search-cad-parcels/parcel-numbers",
                params={"search": "1122/1", "municipalityRegNum": municipality_reg_num},
                headers=HEADERS,
                timeout=10.0,
            )
            print(f"Status: {response2.status_code}")
            print(f"Response type: {response2.headers.get('content-type')}")
            print(f"Response length: {len(response2.content)} bytes")
            print(f"Response text (first 1000 chars):\n{response2.text[:1000]}")
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
