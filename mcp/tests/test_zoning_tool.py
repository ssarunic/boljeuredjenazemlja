"""get_parcel_zoning: dictionary with summary, geometry only on request, clear errors."""

import asyncio
from unittest.mock import MagicMock

import pytest
from cadastral_api import CadastralAPIError, ErrorType
from cadastral_api.models.planning_entities import (
    ParcelZoning,
    PlanningDataset,
    PlanningZone,
    ZoneKind,
    ZoneMatch,
    ZoningStatus,
)

from cadastral_mcp.tools import CadastralTools

ZONE = PlanningZone(
    feature_id="Gradj_podrucje_izvan_naselja.11",
    zone_kind=ZoneKind.DETACHED,
    designation_code="T2",
    designation="GOSPODARSKA - UGOSTITELJSKO TURISTIČKA (TURISTIČKO NASELJE)",
    zone_name="SAVAR - UVALA ILO",
    plan_name="PPUO SALI - III. ID",
    plan_id="HR-ISPU-PPGO-03794-R05",
    polygons=[[[{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 1, "y": 1}, {"x": 0, "y": 0}]]],
)
ZONING = ParcelZoning(
    parcel_number="103/2",
    municipality_code="334979",
    parcel_area_m2=1200.0,
    status=ZoningStatus.DETACHED_ZONE,
    in_building_area=True,
    matches=[ZoneMatch(zone=ZONE, overlap_fraction=0.5, overlap_m2=600.0)],
    plans=["PPUO SALI - III. ID"],
    dataset=PlanningDataset(name="test"),
)


BELOW_ONLY = ParcelZoning(
    parcel_number="103/2",
    municipality_code="334979",
    status=ZoningStatus.TOUCHES_BELOW_THRESHOLD,
    in_building_area=False,
    below_threshold=[ZoneMatch(zone=ZONE, overlap_fraction=0.01, overlap_m2=12.0)],
    intersecting_zones=1,
    plans=["PPUO SALI - III. ID"],
    dataset=PlanningDataset(name="test"),
)


def _tools(zoning: ParcelZoning | None, error: Exception | None = None) -> CadastralTools:
    client = MagicMock()
    if error is not None:
        client.get_parcel_zoning.side_effect = error
    else:
        client.get_parcel_zoning.return_value = zoning
    tools = CadastralTools(client)

    def resolve(name_or_code: str) -> str:
        return "334979"

    tools._resolve_municipality = resolve  # type: ignore[method-assign]
    return tools


def test_result_carries_summary_status_and_disclaimer_without_geometry() -> None:
    result = asyncio.run(_tools(ZONING).get_parcel_zoning("103/2", "SAVAR"))
    assert result["status"] == "detached_zone"
    assert result["summary"]["designation_code"] == "T2"
    assert result["matches"][0]["zone"]["zone_name"] == "SAVAR - UVALA ILO"
    assert "polygons" not in result["matches"][0]["zone"]
    assert "interpretation" in result["dataset"]["disclaimer"]
    assert result["generation_note"].startswith("Designation codes")
    assert result["buildability"] == "unknown"
    assert result["summary"]["buildability"] == "unknown"


@pytest.mark.parametrize("bad", [-0.01, 1.5, float("nan")])
def test_min_overlap_outside_zero_to_one_is_rejected(bad: float) -> None:
    with pytest.raises(ValueError):
        asyncio.run(_tools(ZONING).get_parcel_zoning("103/2", "SAVAR", min_overlap=bad))


def test_below_threshold_zones_lose_their_polygons_too() -> None:
    result = asyncio.run(_tools(BELOW_ONLY).get_parcel_zoning("103/2", "SAVAR"))
    assert result["status"] == "touches_below_threshold"
    assert result["matches"] == []
    assert result["below_threshold"][0]["zone"]["designation_code"] == "T2"
    assert "polygons" not in result["below_threshold"][0]["zone"]
    assert result["plans"] == ["PPUO SALI - III. ID"]
    with_geometry = asyncio.run(
        _tools(BELOW_ONLY).get_parcel_zoning("103/2", "SAVAR", include_geometry=True)
    )
    assert "polygons" in with_geometry["below_threshold"][0]["zone"]


def test_invalid_threshold_is_rejected_before_the_client_is_called() -> None:
    tools = _tools(ZONING)
    with pytest.raises(ValueError):
        asyncio.run(tools.get_parcel_zoning("103/2", "SAVAR", min_overlap=2))
    tools.client.get_parcel_zoning.assert_not_called()


def test_geometry_is_included_on_request() -> None:
    result = asyncio.run(_tools(ZONING).get_parcel_zoning("103/2", "SAVAR", include_geometry=True))
    assert result["matches"][0]["zone"]["polygons"][0][0][0] == {"x": 0.0, "y": 0.0}


def test_missing_geometry_raises_clear_error() -> None:
    with pytest.raises(ValueError) as exc_info:
        asyncio.run(_tools(None).get_parcel_zoning("114", "SAVAR"))
    message = str(exc_info.value)
    assert "114" in message and "334979" in message and "NoneType" not in message


def test_api_error_is_reported_as_value_error() -> None:
    error = CadastralAPIError(ErrorType.CONNECTION, details={"reason": "all_mirrors_failed"})
    with pytest.raises(ValueError) as exc_info:
        asyncio.run(_tools(None, error).get_parcel_zoning("103/2", "SAVAR"))
    assert "building areas" in str(exc_info.value)


def test_wfs_failure_names_the_endpoint_and_the_setting() -> None:
    # The default endpoint is the mock server's imitation of the WFS; on any
    # other cadastre server it is a 404, and the message must say what to set.
    error = CadastralAPIError(
        ErrorType.CONNECTION,
        details={"endpoint": "https://oss.example.hr/oss/public/planning/wfs", "status_code": 404},
    )
    tools = _tools(None, error=error)
    tools.client.planning.base_urls = ["https://oss.example.hr/oss/public/planning/wfs"]
    with pytest.raises(ValueError) as excinfo:
        asyncio.run(tools.get_parcel_zoning("103/2", "SAVAR"))
    message = str(excinfo.value)
    assert "status_code=404" in message
    assert "https://oss.example.hr/oss/public/planning/wfs" in message
    assert "CADASTRAL_PLANNING_WFS_URLS" in message


def test_wfs_failure_on_a_configured_mirror_does_not_blame_the_setting() -> None:
    error = CadastralAPIError(ErrorType.CONNECTION, details={"reason": "all_mirrors_failed"})
    tools = _tools(None, error=error)
    tools.client.planning.base_urls = ["https://gis4.example.hr/srv1/x/wfs"]
    with pytest.raises(ValueError) as excinfo:
        asyncio.run(tools.get_parcel_zoning("103/2", "SAVAR"))
    assert "CADASTRAL_PLANNING_WFS_URLS" not in str(excinfo.value)
    assert "gis4.example.hr" in str(excinfo.value)
