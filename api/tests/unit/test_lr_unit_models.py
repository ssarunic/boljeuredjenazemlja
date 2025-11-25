#!/usr/bin/env python3.12
"""Test Land Registry Unit (LR unit) Pydantic models validation."""

from __future__ import annotations

import json
from pathlib import Path

# Sample LR unit response from mock server
lr_unit_response_data = {
    "lrUnitId": 13122553,
    "lrUnitNumber": "769",
    "mainBookId": 21277,
    "mainBookName": "TESTMUNICIPALITY",
    "cadastreMunicipalityId": 2387,
    "institutionId": 284,
    "institutionName": "Test Land Registry Office",
    "status": "0",
    "statusName": "Aktivan",
    "verificated": True,
    "condominiums": False,
    "lrUnitTypeId": 1,
    "lrUnitTypeName": "VLASNIČKI",
    "lastDiaryNumber": "Z-27986/2025",
    "activePlumbs": [],
    "ownershipSheetB": {
        "lrUnitShares": [
            {
                "description": "1. Suvlasnički dio: 4/8",
                "lrOwners": [
                    {
                        "lrOwnerId": 60930291,
                        "name": "Test Owner A",
                        "lrEntry": {
                            "description": "Zaprimljeno 05.04.2012.g. pod brojem Z-3983/2012<br><br>UKNJIŽBA, PRAVO VLASNIŠTVA",
                            "orderNumber": "1.1"
                        }
                    }
                ],
                "lrUnitShareId": 46503704,
                "subSharesAndEntries": [],
                "status": 0,
                "orderNumber": "1"
            },
            {
                "description": "2. Suvlasnički dio: 1/8",
                "lrOwners": [
                    {
                        "lrOwnerId": 60930293,
                        "name": "Test Owner B",
                        "address": "Test Street 123, Test City",
                        "taxNumber": "12345678901",
                        "lrEntry": {
                            "description": "Zaprimljeno 05.04.2012.g. pod brojem Z-3983/2012",
                            "orderNumber": "2.1"
                        }
                    }
                ],
                "lrUnitShareId": 46503705,
                "subSharesAndEntries": [],
                "status": 0,
                "orderNumber": "2"
            }
        ],
        "lrEntries": []
    },
    "possessionSheetA1": {
        "cadParcels": [
            {
                "parcelId": 6564837,
                "parcelNumber": "118/4",
                "cadMunicipalityId": 2387,
                "cadMunicipalityRegNum": "334979",
                "cadMunicipalityName": "TESTMUNICIPALITY",
                "institutionId": 114,
                "address": "TEST FIELD",
                "area": "409",
                "buildingRemark": 0,
                "detailSheetNumber": "4",
                "hasBuildingRight": False,
                "parcelParts": [
                    {
                        "parcelPartId": 74358714,
                        "name": "MASLINJAK",
                        "area": "409",
                        "possessionSheetId": 14823991,
                        "possessionSheetNumber": "769",
                        "building": False
                    }
                ],
                "possessionSheets": [],
                "isAdditionalDataSet": False,
                "legalRegime": False,
                "graphic": True,
                "alphaNumeric": True,
                "status": 0,
                "resourceCode": 0,
                "isHarmonized": False
            },
            {
                "parcelId": 6565030,
                "parcelNumber": "279/6",
                "cadMunicipalityId": 2387,
                "cadMunicipalityRegNum": "334979",
                "cadMunicipalityName": "TESTMUNICIPALITY",
                "institutionId": 114,
                "address": "TEST LOCATION",
                "area": "1890",
                "buildingRemark": 0,
                "detailSheetNumber": "1",
                "hasBuildingRight": False,
                "parcelParts": [
                    {
                        "parcelPartId": 74358720,
                        "name": "MASLINJAK",
                        "area": "890",
                        "possessionSheetId": 14823991,
                        "possessionSheetNumber": "769",
                        "building": False
                    },
                    {
                        "parcelPartId": 74358721,
                        "name": "PAŠNJAK",
                        "area": "1000",
                        "possessionSheetId": 14823991,
                        "possessionSheetNumber": "769",
                        "building": False
                    }
                ],
                "possessionSheets": [],
                "isAdditionalDataSet": False,
                "legalRegime": False,
                "graphic": True,
                "alphaNumeric": True,
                "status": 0,
                "resourceCode": 0,
                "isHarmonized": False
            }
        ]
    },
    "possessionSheetA2": {
        "lrEntries": []
    },
    "encumbranceSheetC": {
        "lrEntryGroups": [
            {
                "description": "1. Na suvlasnički dio: 1 (4/8)",
                "shareOrderNumber": "1",
                "lrEntries": [
                    {
                        "description": "Zaprimljeno 05.05.2016.g. pod brojem Z-9139/2016<br><br>ZABILJEŽBA, TRAŽBINA SOCIJALNE POMOĆI",
                        "lrEntryId": 93358400,
                        "orderNumber": "1.1"
                    }
                ]
            }
        ]
    }
}


# Sample condominium LR unit response data
condominium_lr_unit_data = {
    "lrUnitId": 6644000,
    "lrUnitNumber": "13998",
    "mainBookId": 30783,
    "mainBookName": "SPLIT",
    "cadastreMunicipalityId": 2518,
    "institutionId": 269,
    "institutionName": "Zemljišnoknjižni odjel Split",
    "status": "0",
    "statusName": "Aktivan",
    "verificated": True,
    "condominiums": False,  # API returns False even for condominiums!
    "lrUnitTypeId": 3,
    "lrUnitTypeName": "ETAŽNO VLASNIŠTVO S ODREĐENIM OMJERIMA",
    "lastDiaryNumber": "Z-47245/2025",
    "activePlumbs": [],
    "ownershipSheetB": {
        "lrUnitShares": [
            {
                "description": "16. Suvlasnički dio: 61/4651 ETAŽNO VLASNIŠTVO (E-16)",
                "lrOwners": [
                    {
                        "lrOwnerId": 43484805,
                        "name": "Test Owner",
                        "address": "Test Address",
                        "taxNumber": "12345678901",
                        "lrEntry": {
                            "description": "UKNJIŽBA, PRAVO VLASNIŠTVA",
                            "orderNumber": "16.4"
                        }
                    }
                ],
                "lrUnitShareId": 32618214,
                "condominiumNumber": "E-16",
                "condominiums": [
                    "STAN na PR (prizemlju), označen br. 1, površine 61,27 m2, koji se sastoji od dvije sobe, kuhinje, blagovaonice, kupaonice, hodnika i lođe, s pripadajućom drvarnicom."
                ],
                "subSharesAndEntries": [],
                "status": 0,
                "orderNumber": "16"
            },
            {
                # Share with nested co-owners (no direct lrOwners)
                "description": "22. Suvlasnički dio: 61/4651 ETAŽNO VLASNIŠTVO (E-22)",
                "lrUnitShareId": 32618220,
                "condominiumNumber": "E-22",
                "condominiums": [
                    "STAN na II. (drugom) katu, označen br. 7, površine 61,25 m2"
                ],
                "subSharesAndEntries": [
                    {
                        "description": "22.3. Suvlasnički dio etaže: 1/2",
                        "lrOwners": [
                            {
                                "lrOwnerId": 41225328,
                                "name": "Co-Owner A",
                                "address": "Address A",
                                "taxNumber": "11111111111",
                                "lrEntry": {
                                    "description": "UKNJIŽBA",
                                    "orderNumber": "22.3.1"
                                }
                            }
                        ],
                        "lrUnitShareId": 32619507,
                        "subSharesAndEntries": [],
                        "status": 0,
                        "orderNumber": "3"
                    },
                    {
                        "description": "22.7. Suvlasnički dio etaže: 1/2",
                        "lrOwners": [
                            {
                                "lrOwnerId": 44824166,
                                "name": "Co-Owner B",
                                "address": "Address B",
                                "taxNumber": "22222222222",
                                "lrEntry": {
                                    "description": "UKNJIŽBA",
                                    "orderNumber": "22.7.1"
                                }
                            }
                        ],
                        "lrUnitShareId": 34670862,
                        "subSharesAndEntries": [],
                        "status": 0,
                        "orderNumber": "7"
                    }
                ],
                "status": 0,
                "orderNumber": "22"
            }
        ],
        "lrEntries": []
    },
    "possessionSheetA1": {
        "cadParcels": []
    },
    "possessionSheetA2": {
        "lrEntries": []
    },
    "encumbranceSheetC": {
        "lrEntryGroups": []
    }
}


# Sample possessor data with condominium fields
possessor_with_condominium_data = {
    "name": "GRAD SPLIT",
    "ownership": "1/1",
    "address": "SPLIT, OBALA KNEZA BRANIMIRA 17",
    "condominiumShareNumber": "0",
    "condominiumShareOwnership": "4531/4651"
}

def main():
    """Run LR unit model validation tests."""
    print("=" * 70)
    print("Testing Land Registry Unit Pydantic Models")
    print("=" * 70)
    print()

    # Try to import and validate
    try:
        import sys
        from pathlib import Path

        # Add API source to path
        api_src = Path(__file__).parent.parent.parent / "src"
        sys.path.insert(0, str(api_src))

        from cadastral_api.models.entities import LandRegistryUnitDetailed

        print("Test 1: Basic LR Unit Validation")
        print("-" * 70)
        lr_unit = LandRegistryUnitDetailed.model_validate(lr_unit_response_data)
        print(f"✓ Validation successful!")
        print(f"  LR Unit Number: {lr_unit.lr_unit_number}")
        print(f"  Main Book: {lr_unit.main_book_name}")
        print(f"  Institution: {lr_unit.institution_name}")
        print(f"  Status: {lr_unit.status_name}")
        print(f"  Unit Type: {lr_unit.lr_unit_type_name}")
        print()

        print("Test 2: Ownership Sheet B Validation")
        print("-" * 70)
        ownership = lr_unit.ownership_sheet_b
        print(f"✓ Ownership sheet parsed")
        print(f"  Total shares: {len(ownership.lr_unit_shares)}")

        for share in ownership.lr_unit_shares:
            if share.is_active:
                print(f"  Share {share.order_number}: {share.description}")
                for owner in share.owners:
                    print(f"    - {owner.name}")
                    if owner.address:
                        print(f"      Address: {owner.address}")
                    if owner.tax_number:
                        print(f"      OIB: {owner.tax_number}")
        print()

        print("Test 3: Parcel List (Sheet A) Validation")
        print("-" * 70)
        parcels = lr_unit.get_all_parcels()
        print(f"✓ Parcel list parsed")
        print(f"  Total parcels: {len(parcels)}")
        for parcel in parcels:
            print(f"  - {parcel.parcel_number}: {parcel.area_numeric} m² ({parcel.address or 'No address'})")
        print()

        print("Test 4: Encumbrance Sheet C Validation")
        print("-" * 70)
        has_encumbrances = lr_unit.has_encumbrances()
        print(f"✓ Encumbrance sheet parsed")
        print(f"  Has encumbrances: {has_encumbrances}")

        if has_encumbrances:
            for group in lr_unit.encumbrance_sheet_c.lr_entry_groups:
                print(f"  Group: {group.description}")
                for entry in group.lr_entries:
                    print(f"    - Entry {entry.order_number}: {entry.description[:60]}...")
        print()

        print("Test 5: Summary Statistics")
        print("-" * 70)
        summary = lr_unit.summary()
        print(f"✓ Summary generated")
        print(f"  Total parcels: {summary['total_parcels']}")
        print(f"  Total area: {summary['total_area_m2']} m²")
        print(f"  Number of owners: {summary['num_owners']}")
        print(f"  Has encumbrances: {summary['has_encumbrances']}")
        print()

        print("Test 6: Total Area Calculation")
        print("-" * 70)
        total_area = lr_unit.possessory_sheet_a1.total_area()
        print(f"✓ Total area calculated")
        print(f"  Total: {total_area} m²")
        print()

        # Test standard unit is not a condominium
        print("Test 7: Standard Unit is_condominium() Check")
        print("-" * 70)
        assert lr_unit.is_condominium() is False, "Standard unit should not be a condominium"
        print(f"✓ is_condominium() returns False for VLASNIČKI unit")
        print(f"  Unit type: {lr_unit.lr_unit_type_name}")
        print()

        # Test condominium-specific functionality
        print("Test 8: Condominium LR Unit Validation")
        print("-" * 70)
        condo_unit = LandRegistryUnitDetailed.model_validate(condominium_lr_unit_data)
        print(f"✓ Condominium unit validated")
        print(f"  Unit: {condo_unit.lr_unit_number}")
        print(f"  Type: {condo_unit.lr_unit_type_name}")
        print(f"  is_condominium(): {condo_unit.is_condominium()}")
        assert condo_unit.is_condominium() is True, "ETAŽNO VLASNIŠTVO should be detected as condominium"
        print()

        print("Test 9: Condominium Share Fields")
        print("-" * 70)
        first_share = condo_unit.ownership_sheet_b.lr_unit_shares[0]
        print(f"✓ First share parsed")
        print(f"  Condominium number: {first_share.condominium_number}")
        print(f"  Apartment description: {first_share.condominium_descriptions[0][:50]}...")
        print(f"  is_condominium_share(): {first_share.is_condominium_share()}")
        assert first_share.condominium_number == "E-16", "Condominium number should be E-16"
        assert first_share.is_condominium_share() is True, "Share with condominium number should be condominium share"
        print()

        print("Test 10: Nested Co-owners (subSharesAndEntries)")
        print("-" * 70)
        second_share = condo_unit.ownership_sheet_b.lr_unit_shares[1]
        print(f"✓ Share with nested co-owners parsed")
        print(f"  has_sub_owners(): {second_share.has_sub_owners()}")
        print(f"  Direct owners: {len(second_share.owners)}")
        print(f"  All owners (including nested): {len(second_share.get_all_owners())}")
        assert second_share.has_sub_owners() is True, "Share should have sub-owners"
        assert len(second_share.owners) == 0, "No direct owners expected"
        assert len(second_share.get_all_owners()) == 2, "Should have 2 co-owners from subSharesAndEntries"
        for owner in second_share.get_all_owners():
            print(f"  - {owner.name}")
        print()

        print("Test 11: Condominium Units Count")
        print("-" * 70)
        units_count = condo_unit.get_condominium_units_count()
        print(f"✓ Condominium units counted")
        print(f"  Number of units: {units_count}")
        assert units_count == 2, "Should have 2 condominium units in test data"
        print()

        print("Test 12: Possessor with Condominium Fields")
        print("-" * 70)
        from cadastral_api.models.entities import Possessor
        possessor = Possessor.model_validate(possessor_with_condominium_data)
        print(f"✓ Possessor with condominium fields validated")
        print(f"  Name: {possessor.name}")
        print(f"  Condominium share number: {possessor.condominium_share_number}")
        print(f"  Condominium share ownership: {possessor.condominium_share_ownership}")
        assert possessor.condominium_share_number == "0", "Condominium share number should be '0'"
        assert possessor.condominium_share_ownership == "4531/4651", "Condominium share ownership should be '4531/4651'"
        print()

        print("Test 13: Summary Includes Condominium Info")
        print("-" * 70)
        condo_summary = condo_unit.summary()
        print(f"✓ Summary generated for condominium unit")
        print(f"  is_condominium: {condo_summary['is_condominium']}")
        print(f"  condominium_units: {condo_summary.get('condominium_units', 'N/A')}")
        assert condo_summary["is_condominium"] is True, "Summary should indicate condominium"
        assert condo_summary.get("condominium_units") == 2, "Summary should have condominium_units"
        print()

        print("=" * 70)
        print("ALL TESTS PASSED ✓")
        print("=" * 70)
        return 0

    except Exception as e:
        print()
        print("=" * 70)
        print(f"✗ TEST FAILED: {type(e).__name__}")
        print("=" * 70)
        print(f"Error: {e}")
        print()
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
