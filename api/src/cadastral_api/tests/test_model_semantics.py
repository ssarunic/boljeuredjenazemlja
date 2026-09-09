"""Model semantics that used to invent facts: share status, missing areas, link
ambiguity, possessor wording, exact share totals."""

import json
from fractions import Fraction
from pathlib import Path

import pytest

from cadastral_api.client.api_client import CadastralAPIClient
from cadastral_api.exceptions import CadastralAPIError, ErrorType
from cadastral_api.models.entities import (
    EncumbranceSheetC,
    LandRegistryUnitDetailed,
    LREntry,
    LRShare,
    LRUnitParcel,
    OwnershipSheetB,
    ParcelInfo,
    PossessionSheet,
    ShareStatus,
)

FIXTURES = Path(__file__).parent / "fixtures"


def _share(status: int, description: str = "1. Suvlasnički dio: 1/3") -> LRShare:
    return LRShare.model_validate(
        {"lrUnitShareId": 1, "description": description, "orderNumber": "1", "status": status}
    )


def test_share_status_maps_zero_to_active_and_the_rest_to_historical() -> None:
    assert _share(0).share_status is ShareStatus.ACTIVE
    assert _share(1).share_status is ShareStatus.HISTORICAL
    assert _share(7).share_status is ShareStatus.HISTORICAL


def test_entry_kinds_and_deletion_flag() -> None:
    entry = LREntry.model_validate(
        {"description": "Briše se zabilježba spora upisana pod Z-1/2020", "orderNumber": "1.1"}
    )
    assert entry.action_type == "zabilježba"
    assert entry.deletes_prior_entry is True
    plain = LREntry.model_validate(
        {"description": "UKNJIŽBA, PRAVO VLASNIŠTVA", "orderNumber": "1.2"}
    )
    assert plain.action_type == "uknjižba"
    assert plain.deletes_prior_entry is False


def test_lean_unit_parcel_does_not_invent_facts() -> None:
    parcel = LRUnitParcel.model_validate({"parcelId": 1, "parcelNumber": "1/1"})
    assert parcel.area is None and parcel.area_numeric is None
    assert parcel.is_harmonized is None and parcel.graphic is None and parcel.status is None
    broken = LRUnitParcel.model_validate({"parcelId": 1, "parcelNumber": "1/1", "area": "n/a"})
    assert broken.area_numeric is None


def test_total_area_treats_missing_area_as_zero() -> None:
    raw = json.loads((FIXTURES / "lr_unit_lrparcels.json").read_text(encoding="utf-8"))
    unit = LandRegistryUnitDetailed.model_validate(raw[0])
    unit.possessory_sheet_a1.cad_parcels.append(
        LRUnitParcel.model_validate({"parcelId": 2, "parcelNumber": "2/2"})
    )
    assert unit.possessory_sheet_a1.total_area() == 3291


def test_link_resolution_refuses_to_pick_between_disagreeing_links() -> None:
    parcel = ParcelInfo.model_validate(
        json.loads((FIXTURES / "parcel_info_linked.json").read_text(encoding="utf-8"))
    )
    assert parcel.lr_unit is None
    other = parcel.lr_units_from_parcel_links[0].model_copy(
        update={"lr_unit_number": "999", "lr_unit_id": 1}
    )
    parcel.lr_units_from_parcel_links.append(other)
    assert [u.lr_unit_number for u in parcel.lr_unit_candidates()] == ["449", "999"]
    with pytest.raises(CadastralAPIError) as exc:
        CadastralAPIClient._resolve_lr_unit_ref(parcel)
    assert exc.value.error_type is ErrorType.LR_UNIT_NOT_FOUND
    assert exc.value.details["reason"] == "lr_unit_ambiguous"
    assert "449/21277" in exc.value.details["candidates"]


def test_direct_unit_wins_over_disagreeing_links() -> None:
    parcel = ParcelInfo.model_validate(
        json.loads((FIXTURES / "parcel_info_linked.json").read_text(encoding="utf-8"))
    )
    parcel.lr_unit = parcel.lr_units_from_parcel_links[0].model_copy(
        update={"lr_unit_number": "5", "lr_unit_id": 2}
    )
    assert CadastralAPIClient._resolve_lr_unit_ref(parcel) == ("5", 21277)


def test_total_possessors_replaces_total_owners() -> None:
    parcel = ParcelInfo.model_validate(
        json.loads((FIXTURES / "parcel_info_linked.json").read_text(encoding="utf-8"))
    )
    assert parcel.total_possessors == 119
    assert "total_possessors" in parcel.model_dump()
    assert not hasattr(parcel, "total_owners")


def test_share_totals_are_exact() -> None:
    sheet = OwnershipSheetB.model_validate(
        {"lrUnitShares": [_share(0).model_dump(by_alias=True) for _ in range(3)]}
    )
    assert sheet.total_ownership_fraction() == Fraction(1)
    assert sheet.total_ownership_accounted() == 1.0
    possession = PossessionSheet.model_validate(
        {
            "possessionSheetId": 1,
            "possessionSheetNumber": "1",
            "cadMunicipalityId": 1,
            "possessors": [{"name": f"P{i}", "ownership": "1/3"} for i in range(3)],
        }
    )
    assert possession.total_ownership == 1.0


def test_has_entries_is_the_honest_name() -> None:
    sheet = EncumbranceSheetC.model_validate({"lrEntryGroups": []})
    assert sheet.has_entries() is False
    assert not hasattr(sheet, "has_encumbrances")
    raw = json.loads((FIXTURES / "lr_unit_encumbrances.json").read_text(encoding="utf-8"))
    unit = LandRegistryUnitDetailed.model_validate(raw[0])
    assert unit.has_sheet_c_entries() is True
    assert unit.summary()["has_sheet_c_entries"] is True
