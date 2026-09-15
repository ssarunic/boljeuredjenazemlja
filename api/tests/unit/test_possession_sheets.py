"""Possession sheets: by id, by number, the parcels of a sheet, the municipality id."""

from __future__ import annotations

import json

import httpx
import pytest

from cadastral_api import CadastralAPIClient, SearchedParcel
from cadastral_api.exceptions import CadastralAPIError, ErrorType

SHEET = {
    "possessionSheetId": 16179481,
    "possessionSheetNumber": "877",
    "cadMunicipalityId": 2387,
    "cadMunicipalityRegNum": "334979",
    "cadMunicipalityName": "SAVAR",
    "possessionSheetTypeId": 1,
    "possessors": [
        {"name": "Posjednik 1", "ownership": "1/4", "address": "Adresa 1"},
        {"name": "POSJEDNIK 1", "ownership": "1/4", "address": None},
        {"name": "Posjednik 2", "ownership": "1/2", "address": None},
    ],
}
MUNICIPALITIES = [
    {"key1": "2387", "value1": "334979 SAVAR", "key2": "334979", "value2": "114",
     "value3": "116", "displayValue1": "334979 SAVAR, ZADAR, PUK ZADAR"},
]
NON_HARMONIZED = {
    "parcelId": 6564741, "parcelNumber": "1122/1", "cadMunicipalityId": 2387,
    "cadMunicipalityRegNum": "334979", "cadMunicipalityName": "SAVAR", "institutionId": 114,
    "address": "SAVAR", "area": "1618", "buildingRemark": 0, "detailSheetNumber": "3",
    "hasBuildingRight": False, "isHarmonized": False, "lastChangeLog": "18/2025",
    "lastChangeLogFileNum": "UP/I 932-07/2026-02/1217", "lastElaborateNumber": None,
    "parcelParts": [{"parcelPartId": 1, "name": "PAŠNJAK", "area": "1618", "building": False}],
    "possessionSheet": SHEET,
    "parcelLinks": [{"parcelId": 1, "parcelNumber": "1122/1", "area": "3291",
                     "lrUnit": {"lrUnitId": 9, "lrUnitNumber": "449", "mainBookId": 21277,
                                "mainBookName": "SAVAR", "status": "A", "verificated": True,
                                "condominiums": False}, "parcelParts": []}],
}
HARMONIZED = {
    "parcelId": 6564817, "parcelNumber": "103/2", "cadMunicipalityId": 2387,
    "cadMunicipalityRegNum": "334979", "area": "1200", "buildingRemark": 0,
    "isHarmonized": True, "parcelParts": [{"name": "MASLINJAK", "area": "1200", "building": False}],
    "lrUnit": {"lrUnitId": 10, "lrUnitNumber": "657", "mainBookId": 21277, "mainBookName": "SAVAR",
               "status": "A", "verificated": True, "condominiums": False,
               "ownershipSheetB": {"lrUnitShares": [
                   {"lrUnitShareId": 1, "orderNumber": "1", "description": "1/1", "status": 0,
                    "lrOwners": [{"name": "Vlasnik 1", "address": None, "taxNumber": None}]}
               ], "lrEntries": []}},
}


def _client(records: list[dict] | None = None, sheet: dict | None = SHEET):
    posted: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path == "/search-cad-parcels/municipalities":
            return httpx.Response(200, json=MUNICIPALITIES)
        if path in ("/cad/possession-sheet", "/cad/possession-sheet-by-number"):
            return httpx.Response(200, json=sheet or {})
        if path == "/cad/cad-parcels-search-data":
            data = {"possessionSheetNumber": "877", "municipalityNumber": "334979"}
            return httpx.Response(200, json=data)
        if path == "/cad/search-parcels":
            posted.append(json.loads(request.content))
            return httpx.Response(200, json=records if records is not None else [NON_HARMONIZED])
        raise AssertionError(path)

    client = CadastralAPIClient(base_url="http://mock", rate_limit=0, unknown_fields="error")
    client.client = httpx.Client(base_url="http://mock", transport=httpx.MockTransport(handler))
    return client, posted


def test_sheet_by_id_and_by_number_with_provenance() -> None:
    client, _ = _client()
    sheet = client.get_possession_sheet(16179481)
    assert sheet.possession_sheet_number == "877" and len(sheet.possessors) == 3
    assert sheet.provenance is not None and sheet.provenance.register == "cadastre"
    assert sheet.provenance.source_url == "http://mock/cad/possession-sheet?possessionSheetId=16179481"
    by_number = client.get_possession_sheet_by_number("877", 2387)
    assert by_number.provenance.source_url.endswith(
        "/cad/possession-sheet-by-number?possessionSheetNumber=877&cadMunicipalityId=2387"
    )


def test_missing_sheet_is_a_typed_error() -> None:
    client, _ = _client(sheet=None)
    with pytest.raises(CadastralAPIError) as excinfo:
        client.get_possession_sheet(1)
    assert excinfo.value.error_type is ErrorType.POSSESSION_SHEET_NOT_FOUND
    with pytest.raises(CadastralAPIError) as excinfo:
        client.get_possession_sheet_by_number("999", 2387)
    assert excinfo.value.error_type is ErrorType.POSSESSION_SHEET_NOT_FOUND


def test_resolve_municipality_id_and_reverse_lookup() -> None:
    client, _ = _client()
    assert client.resolve_municipality_id("SAVAR") == 2387
    assert client.resolve_municipality_id("334979") == 2387
    data = client.lookup_possession_sheet_number(16179481)
    assert (data.possession_sheet_number, data.municipality_number) == ("877", "334979")


def test_search_parcels_sends_the_form_body_and_parses_both_shapes() -> None:
    client, posted = _client(records=[NON_HARMONIZED, HARMONIZED])
    records = client.search_parcels(cad_municipality_id=2387, possession_sheet_number="877")
    assert posted == [{"parcelId": "", "cadMunicipalityId": "2387", "parcelNumber": "",
                       "possessionSheetNumber": "877"}]
    plain, harmonized = records
    assert isinstance(plain, SearchedParcel)
    assert plain.possession_sheet is not None and len(plain.possession_sheet.possessors) == 3
    assert plain.possession_sheet.provenance is not None
    assert plain.resolved_lr_unit().lr_unit_number == "449"
    assert plain.area_numeric == 1618 and plain.land_use_summary == {"PAŠNJAK": 1618}
    assert plain.is_building_parcel is False and plain.parcel_number_display == "1122/1"
    assert harmonized.possession_sheet is None and harmonized.parcel_links is None
    assert harmonized.lr_unit is not None
    assert [row["name"] for row in harmonized.lr_unit.owner_rows()] == ["Vlasnik 1"]
    assert harmonized.resolved_lr_unit().lr_unit_number == "657"
    # The other two forms of the search.
    client.search_parcels(cad_municipality_id=2387, parcel_number="35/1.ZGR")
    assert posted[-1]["parcelNumber"] == "*35/1" and posted[-1]["possessionSheetNumber"] == ""
    client.search_parcels(parcel_id=6564817)
    assert posted[-1] == {"parcelId": "6564817", "cadMunicipalityId": "", "parcelNumber": "",
                          "possessionSheetNumber": ""}
    with pytest.raises(ValueError):
        client.search_parcels(cad_municipality_id=2387)


def test_search_parcels_empty_answer_is_an_empty_list() -> None:
    client, _ = _client(records=[])
    assert client.search_parcels(parcel_id=1) == []


def test_get_possession_sheet_parcels_bundles_the_three_calls() -> None:
    client, posted = _client(records=[NON_HARMONIZED, HARMONIZED])
    result = client.get_possession_sheet_parcels("877", "SAVAR")
    assert result.sheet.possession_sheet_number == "877"
    assert [p.parcel_number for p in result.parcels] == ["1122/1", "103/2"]
    assert result.total_area_m2 == 2818
    assert result.maybe_truncated is False
    assert result.parcels_provenance.source_url == "http://mock/cad/search-parcels"
    assert posted[-1]["cadMunicipalityId"] == "2387"
    long_client, _ = _client(records=[NON_HARMONIZED] * 30)
    assert long_client.get_possession_sheet_parcels("877", "SAVAR").maybe_truncated is True


HARMONIZED_STUB_BY_NUMBER = {
    "possessionSheetNumber": "657", "cadMunicipalityId": 2387, "lrUnitId": 13122441,
    "possessors": [],
}
HARMONIZED_STUB_BY_ID = {
    "possessionSheetId": 14823725, "possessionSheetNumber": "657", "cadMunicipalityId": 2387,
    "cadMunicipalityRegNum": "334979", "cadMunicipalityName": "SAVAR", "lrUnitId": 13122441,
    "possessors": [],
}


def test_harmonized_sheet_stubs_parse_and_point_at_the_unit() -> None:
    client, _ = _client(records=[HARMONIZED], sheet=HARMONIZED_STUB_BY_NUMBER)
    sheet = client.get_possession_sheet_by_number("657", 2387)
    assert sheet.possession_sheet_id is None and sheet.lr_unit_id == 13122441
    assert sheet.possessors == [] and sheet.possessors_in_land_registry is True
    client, _ = _client(records=[HARMONIZED], sheet=HARMONIZED_STUB_BY_ID)
    assert client.get_possession_sheet(14823725).possessors_in_land_registry is True
    # A sheet with possessors is never "in the land registry".
    client, _ = _client(records=[NON_HARMONIZED])
    assert client.get_possession_sheet_parcels("877", "SAVAR").possessors_in_land_registry is False


def test_harmonized_sheet_parcels_bring_the_owners_from_the_inline_unit() -> None:
    client, _ = _client(records=[HARMONIZED, HARMONIZED], sheet=HARMONIZED_STUB_BY_NUMBER)
    result = client.get_possession_sheet_parcels("657", "SAVAR")
    assert result.possessors_in_land_registry is True
    assert result.lr_unit is not None and result.lr_unit.lr_unit_number == "657"
    # The same unit inlined on two parcels is read once.
    assert [row["name"] for row in result.owner_rows()] == ["Vlasnik 1"]
    assert result.owner_rows()[0]["register"] == "land_registry"
    plain, _ = _client(records=[NON_HARMONIZED])
    assert plain.get_possession_sheet_parcels("877", "SAVAR").owner_rows() == []


def test_harmonized_stub_is_backfilled_from_the_parcel_records() -> None:
    record = dict(HARMONIZED)
    record["cadMunicipalityName"] = "SAVAR"
    record["parcelParts"] = [
        {"name": "MASLINJAK", "area": "1200", "building": False,
         "possessionSheetId": 14823725, "possessionSheetNumber": "657"}
    ]
    client, _ = _client(records=[record], sheet=HARMONIZED_STUB_BY_NUMBER)
    result = client.get_possession_sheet_parcels("657", "SAVAR")
    sheet = result.sheet
    assert sheet.possession_sheet_id == 14823725
    assert sheet.cad_municipality_reg_num == "334979" and sheet.cad_municipality_name == "SAVAR"
    assert result.backfilled_from_parcels == (
        "possession_sheet_id", "cad_municipality_reg_num", "cad_municipality_name",
    )
    assert sheet.is_condominium is None and sheet.total_ownership is None
    # A full sheet is left alone.
    client, _ = _client(records=[NON_HARMONIZED])
    full = client.get_possession_sheet_parcels("877", "SAVAR")
    assert full.backfilled_from_parcels == () and full.sheet.is_condominium is False
