"""Every fetched record says which register answered, from where and when.

The provenance is stamped by the client after the fetch, like
``lr_unit_derived_from_links``; a record built from a file has none.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import httpx

from cadastral_api import CadastralAPIClient, LandRegistryUnitDetailed, ParcelInfo
from cadastral_api.models.provenance import Provenance, now_utc_iso

FIXTURES = Path(__file__).resolve().parents[2] / "src" / "cadastral_api" / "tests" / "fixtures"
ISO_UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\+00:00$")
_FIXTURE_FOR_PATH = {
    "/lr/lr-unit": "lr_unit_lrparcels.json",
    "/cad/parcel-info": "parcel_info_direct.json",
}


def _serve(request: httpx.Request) -> httpx.Response:
    name = _FIXTURE_FOR_PATH[request.url.path]
    return httpx.Response(200, json=json.loads((FIXTURES / name).read_text()))


def _client() -> CadastralAPIClient:
    client = CadastralAPIClient(base_url="http://mock", rate_limit=0)
    client.client = httpx.Client(base_url="http://mock", transport=httpx.MockTransport(_serve))
    return client


def test_parcel_info_is_stamped_with_cadastre_provenance() -> None:
    parcel = _client().get_parcel_info("6564817")
    assert isinstance(parcel.provenance, Provenance)
    assert parcel.provenance.register == "cadastre"
    assert parcel.provenance.source_url == "http://mock/cad/parcel-info?parcelId=6564817"
    assert ISO_UTC.match(parcel.provenance.retrieved_at)


def test_lr_unit_is_stamped_with_land_registry_provenance() -> None:
    unit = _client().get_lr_unit_detailed("449", 21277)
    assert unit.provenance is not None
    assert unit.provenance.register == "land_registry"
    assert unit.provenance.source_url == (
        "http://mock/lr/lr-unit?lrUnitNumber=449&mainBookId=21277&historicalOverview=false"
    )
    assert ISO_UTC.match(unit.provenance.retrieved_at)


def test_a_record_built_from_a_file_has_no_provenance() -> None:
    raw = json.loads((FIXTURES / "parcel_info_direct.json").read_text())
    assert ParcelInfo.model_validate(raw).provenance is None
    raw = json.loads((FIXTURES / "lr_unit_lrparcels.json").read_text())
    unit = LandRegistryUnitDetailed.model_validate(raw[0] if isinstance(raw, list) else raw)
    assert unit.provenance is None


def test_provenance_is_part_of_the_json_dump() -> None:
    dumped = _client().get_parcel_info("6564817").model_dump(mode="json")
    assert dumped["provenance"]["register"] == "cadastre"
    assert set(dumped["provenance"]) == {"register", "source_url", "retrieved_at"}


def test_now_utc_iso_is_second_precision_utc() -> None:
    assert ISO_UTC.match(now_utc_iso())
