"""#4: co-owners nested in condominium sub-shares must be counted and listed.

Previously OwnershipSheetB.get_current_owners() (and therefore num_owners,
owner_rows, and the MCP total_owners) only counted direct share.owners, missing
the co-owners of shared apartments (etažno vlasništvo).
"""

from cadastral_api.models.entities import OwnershipSheetB

# One directly-owned apartment + one apartment co-owned via two sub-shares.
SHEET_B = {
    "lrUnitShares": [
        {
            "lrUnitShareId": 1,
            "description": "16. Suvlasnički dio: 1/4651 ETAŽNO VLASNIŠTVO (E-16)",
            "orderNumber": "16",
            "status": 0,
            "condominiumNumber": "E-16",
            "lrOwners": [{"name": "Owner X", "taxNumber": "10000000000"}],
            "subSharesAndEntries": [],
        },
        {
            "lrUnitShareId": 2,
            "description": "22. Suvlasnički dio: 61/4651 ETAŽNO VLASNIŠTVO (E-22)",
            "orderNumber": "22",
            "status": 0,
            "condominiumNumber": "E-22",
            "lrOwners": [],  # no direct owner; co-owned via sub-shares
            "subSharesAndEntries": [
                {
                    "lrUnitShareId": 21,
                    "description": "22.3. Suvlasnički dio etaže: 1/2",
                    "orderNumber": "3",
                    "status": 0,
                    "lrOwners": [{"name": "Co-Owner A", "taxNumber": "11111111111"}],
                    "subSharesAndEntries": [],
                },
                {
                    "lrUnitShareId": 22,
                    "description": "22.7. Suvlasnički dio etaže: 1/2",
                    "orderNumber": "7",
                    "status": 0,
                    "lrOwners": [{"name": "Co-Owner B", "taxNumber": "22222222222"}],
                    "subSharesAndEntries": [],
                },
            ],
        },
    ]
}


def _sheet() -> OwnershipSheetB:
    return OwnershipSheetB.model_validate(SHEET_B)


def test_get_current_owners_includes_sub_share_co_owners() -> None:
    names = {o.name for o in _sheet().get_current_owners()}
    assert names == {"Owner X", "Co-Owner A", "Co-Owner B"}


def test_owner_rows_lists_co_owners_with_their_sub_share_fraction() -> None:
    rows = _sheet().owner_rows()
    assert len(rows) == 3
    by_name = {r["name"]: r for r in rows}

    # Direct owner carries the apartment's own share.
    assert by_name["Owner X"]["share"] == {"num": 1, "den": 4651, "decimal": 1 / 4651}
    assert by_name["Owner X"]["condominium_number"] == "E-16"

    # Co-owner carries the sub-share fraction (1/2 of apartment E-22), and the
    # condominium number propagates from the parent apartment share.
    co_a = by_name["Co-Owner A"]
    assert co_a["share"] == {"num": 1, "den": 2, "decimal": 0.5}
    assert co_a["condominium_number"] == "E-22"
