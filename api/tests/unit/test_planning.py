"""Spatial-plan building areas: geometry helpers, zone models, parcel matching, mirrors."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from cadastral_api import CadastralAPIError, ErrorType, ParcelGeometry, PlanningWFSClient
from cadastral_api.gis.geometry_ops import (
    overlap_fraction,
    point_in_polygon,
    ring_area,
    rings_intersect,
    sample_points,
)
from cadastral_api.models.planning_entities import (
    BUILDING_AREAS_DISCLAIMER,
    PlanGeneration,
    PlanningDataset,
    PlanningZone,
    ZoneKind,
    ZoningStatus,
)
from cadastral_api.planning.wfs_client import match_parcel, validate_min_overlap

# The mock server's synthetic 40 x 30 m parcel 103/2 in SAVAR.
PARCEL = ParcelGeometry(
    cestica_id="6564817",
    broj_cestice="103/2",
    povrsina_graficka=1200.0,
    maticni_broj_ko="334979",
    coordinates=[
        {"x": 380596.77, "y": 4880892.83},
        {"x": 380636.77, "y": 4880892.83},
        {"x": 380636.77, "y": 4880922.83},
        {"x": 380596.77, "y": 4880922.83},
        {"x": 380596.77, "y": 4880892.83},
    ],
)
RING = [(c.x, c.y) for c in PARCEL.coordinates]


def _rect(x0: float, y0: float, x1: float, y1: float) -> list[list[float]]:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]


def _feature(fid: str, ring: list[list[float]], **props: Any) -> dict[str, Any]:
    return {
        "type": "Feature",
        "id": fid,
        "geometry": {"type": "Polygon", "coordinates": [ring]},
        "properties": props,
    }


DETACHED_T2 = _feature(
    "Gradj_podrucje_izvan_naselja.1",
    _rect(380500, 4880850, 380616.77, 4880925),  # left half of the parcel
    jls_mb="03794",
    jls_ime="SALI",
    plan_naziv="PPUO SALI - III. ID",
    ozn_ispu="HR-ISPU-PPGO-03794-R05",
    ozn_namjen="T2",
    namjena="GOSPODARSKA - UGOSTITELJSKO TURISTIČKA (TURISTIČKO NASELJE)",
    naz_vl="SAVAR - UVALA ILO",
    az_oznaka="T",
    pov=10000.0,
)
SETTLEMENT = _feature(
    "Gradj_podrucje_naselje.1",
    _rect(380500, 4880850, 380700, 4881000),  # whole parcel
    jls_mb="03794",
    jls_ime="SALI",
    plan_naziv="PPUO SALI - III. ID",
    ozn_ispu="HR-ISPU-PPGO-03794-R05",
    ozn_namjen="GPN",
    pov=30000.0,
)
SLIVER = _feature(
    "Gradj_podrucje_izvan_naselja.2",
    _rect(380636.5, 4880892.83, 380700, 4880922.83),  # 0.27 m strip along the east edge
    ozn_namjen="G",
    namjena="GROBLJE",
)
DATASET = PlanningDataset(name="test", state="today", source_url="http://x/planning/wfs")


# ---------------------------------------------------------------------------
# geometry_ops
# ---------------------------------------------------------------------------


def test_ring_area_is_the_rectangle_area() -> None:
    assert ring_area(RING) == pytest.approx(1200.0)


def test_point_in_polygon_respects_holes() -> None:
    outer = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
    hole = [(4, 4), (6, 4), (6, 6), (4, 6), (4, 4)]
    assert point_in_polygon(1, 1, [outer, hole])
    assert not point_in_polygon(5, 5, [outer, hole])
    assert not point_in_polygon(11, 5, [outer, hole])


def test_rings_intersect_detects_containment_partial_overlap_and_disjoint() -> None:
    big = [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)]
    small = [(10, 10), (20, 10), (20, 20), (10, 20), (10, 10)]
    crossing = [(90, 90), (110, 90), (110, 110), (90, 110), (90, 90)]
    far = [(200, 200), (210, 200), (210, 210), (200, 210), (200, 200)]
    assert rings_intersect(big, small) and rings_intersect(small, big)
    assert rings_intersect(big, crossing)
    assert not rings_intersect(big, far)


def test_overlap_fraction_of_a_half_covered_rectangle_is_one_half() -> None:
    assert len(sample_points(RING, 40)) == 1600
    half = [[(380500, 4880850), (380616.77, 4880850), (380616.77, 4880925), (380500, 4880925)]]
    assert overlap_fraction(RING, [half], grid=40) == pytest.approx(0.5, abs=0.02)
    assert overlap_fraction(RING, [half], grid=0) == 0.0


# ---------------------------------------------------------------------------
# PlanningZone
# ---------------------------------------------------------------------------


def test_zone_from_detached_feature_keeps_designation_and_provenance() -> None:
    zone = PlanningZone.from_feature(DETACHED_T2, ZoneKind.DETACHED)
    assert zone.feature_id == "Gradj_podrucje_izvan_naselja.1"
    assert zone.designation_code == "T2"
    assert zone.designation_class == "T"
    assert zone.designation_class_label == "tourism and hospitality"
    assert zone.zone_name == "SAVAR - UVALA ILO"
    assert zone.plan_id == "HR-ISPU-PPGO-03794-R05"
    assert zone.generation is PlanGeneration.OLD
    assert zone.label() == (
        "T2 GOSPODARSKA - UGOSTITELJSKO TURISTIČKA (TURISTIČKO NASELJE) (SAVAR - UVALA ILO)"
    )
    assert zone.bounds == (380500.0, 4880850.0, 380616.77, 4880925.0)


def test_settlement_feature_defaults_to_gpn_and_derives_the_class() -> None:
    feature = dict(SETTLEMENT)
    feature["properties"] = {k: v for k, v in SETTLEMENT["properties"].items() if k != "ozn_namjen"}
    zone = PlanningZone.from_feature(feature, ZoneKind.SETTLEMENT)
    assert zone.designation_code == "GPN"
    assert zone.designation_class == "GPN"
    infra = PlanningZone.from_feature(
        _feature("x", _rect(0, 0, 1, 1), ozn_namjen="IS5"), ZoneKind.DETACHED
    )
    assert infra.designation_class == "IS"


def test_zone_geojson_is_a_polygon_feature_with_attributes() -> None:
    feature = PlanningZone.from_feature(DETACHED_T2, ZoneKind.DETACHED).to_geojson()
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"]["designation_code"] == "T2"
    assert feature["properties"]["srs"] == "EPSG:3765"
    assert "polygons" not in feature["properties"]


# ---------------------------------------------------------------------------
# match_parcel
# ---------------------------------------------------------------------------


def test_match_parcel_sorts_by_overlap_and_drops_slivers() -> None:
    zones = [
        PlanningZone.from_feature(DETACHED_T2, ZoneKind.DETACHED),
        PlanningZone.from_feature(SETTLEMENT, ZoneKind.SETTLEMENT),
        PlanningZone.from_feature(SLIVER, ZoneKind.DETACHED),
    ]
    zoning = match_parcel(PARCEL, zones, DATASET)
    assert zoning.status is ZoningStatus.INSIDE_SETTLEMENT
    assert zoning.in_building_area
    assert [m.zone.designation_code for m in zoning.matches] == ["GPN", "T2"]
    assert zoning.matches[0].overlap_fraction == 1.0
    assert zoning.matches[0].overlap_m2 == 1200.0
    assert zoning.matches[1].overlap_fraction == pytest.approx(0.5, abs=0.02)
    assert zoning.plans == ["PPUO SALI - III. ID"]
    assert zoning.dataset.disclaimer == BUILDING_AREAS_DISCLAIMER
    assert zoning.summary()["designation_code"] == "GPN"


def test_match_parcel_outside_everything() -> None:
    zoning = match_parcel(PARCEL, [], DATASET)
    assert zoning.status is ZoningStatus.OUTSIDE
    assert not zoning.in_building_area
    assert zoning.buildability == "unknown"
    assert zoning.matches == [] and zoning.plans == [] and zoning.intersecting_zones == 0


def test_sliver_intersection_is_reported_not_hidden() -> None:
    sliver = [PlanningZone.from_feature(SLIVER, ZoneKind.DETACHED)]
    zoning = match_parcel(PARCEL, sliver, DATASET)
    assert zoning.status is ZoningStatus.TOUCHES_BELOW_THRESHOLD
    assert not zoning.in_building_area
    assert zoning.matches == []
    assert [m.zone.designation_code for m in zoning.below_threshold] == ["G"]
    assert zoning.intersecting_zones == 1
    assert zoning.summary()["intersecting_zones"] == 1


def test_plans_include_the_plans_of_below_threshold_zones() -> None:
    sliver = dict(SLIVER)
    sliver["properties"] = {**SLIVER["properties"], "plan_naziv": "UPU KAMP - I. ID"}
    zones = [
        PlanningZone.from_feature(SETTLEMENT, ZoneKind.SETTLEMENT),
        PlanningZone.from_feature(sliver, ZoneKind.DETACHED),
    ]
    zoning = match_parcel(PARCEL, zones, DATASET)
    assert zoning.plans == ["PPUO SALI - III. ID", "UPU KAMP - I. ID"]


def test_boundary_only_contact_never_counts_even_at_zero_threshold() -> None:
    touching = PlanningZone.from_feature(
        _feature("t", _rect(380636.77, 4880892.83, 380700, 4880922.83), ozn_namjen="T2"),
        ZoneKind.DETACHED,
    )
    zoning = match_parcel(PARCEL, [touching], DATASET, min_overlap=0.0)
    assert zoning.status is ZoningStatus.TOUCHES_BELOW_THRESHOLD
    assert not zoning.in_building_area
    assert zoning.below_threshold[0].overlap_fraction == 0.0


@pytest.mark.parametrize("bad", [-0.01, 1.01, float("nan"), float("inf")])
def test_min_overlap_must_be_a_finite_share(bad: float) -> None:
    with pytest.raises(ValueError):
        match_parcel(PARCEL, [], DATASET, min_overlap=bad)


def test_detached_only_match_gives_detached_status() -> None:
    zones = [PlanningZone.from_feature(DETACHED_T2, ZoneKind.DETACHED)]
    zoning = match_parcel(PARCEL, zones, DATASET)
    assert zoning.status is ZoningStatus.DETACHED_ZONE


# ---------------------------------------------------------------------------
# PlanningWFSClient: URL resolution and mirror rotation
# ---------------------------------------------------------------------------


class FakeClient:
    """Stands in for httpx.Client: answers per URL from ``responses``."""

    responses: dict[str, Any] = {}
    calls: list[str] = []

    def __init__(self, **kwargs: Any) -> None:
        pass

    def get(self, url: str, params: dict[str, str] | None = None) -> httpx.Response:
        FakeClient.calls.append(url)
        answer = FakeClient.responses[url]
        request = httpx.Request("GET", url, params=params)
        if isinstance(answer, Exception):
            raise answer
        status, body = answer
        if isinstance(body, str):
            return httpx.Response(status, text=body, request=request)
        return httpx.Response(status, content=json.dumps(body).encode(), request=request)

    def close(self) -> None:
        pass


@pytest.fixture
def fake_http(monkeypatch: pytest.MonkeyPatch) -> type[FakeClient]:
    FakeClient.responses = {}
    FakeClient.calls = []
    monkeypatch.setattr("cadastral_api.planning.wfs_client.httpx.Client", FakeClient)
    return FakeClient


EMPTY = {"type": "FeatureCollection", "numberMatched": 0, "numberReturned": 0, "features": []}


def test_default_url_derives_from_the_api_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CADASTRAL_PLANNING_WFS_URLS", raising=False)
    client = PlanningWFSClient(api_base_url="http://localhost:8000/")
    assert client.base_urls == ["http://localhost:8000/planning/wfs"]
    client.close()


def test_env_lists_several_mirrors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CADASTRAL_PLANNING_WFS_URLS", "http://a/wfs, http://b/wfs/")
    client = PlanningWFSClient()
    assert client.base_urls == ["http://a/wfs", "http://b/wfs"]
    client.close()


def test_gateway_error_and_timeout_move_to_the_next_mirror(fake_http: type[FakeClient]) -> None:
    fake_http.responses = {
        "http://a/wfs": (502, "<html>502 Proxy Error</html>"),
        "http://b/wfs": httpx.ConnectTimeout("slow"),
        "http://c/wfs": (200, {**EMPTY, "features": [DETACHED_T2]}),
    }
    client = PlanningWFSClient(["http://a/wfs", "http://b/wfs", "http://c/wfs"], rate_limit=0)
    wkt = "POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))"
    zones = client.zones_intersecting(wkt, kinds=[ZoneKind.DETACHED])
    assert [z.designation_code for z in zones] == ["T2"]
    assert fake_http.calls == ["http://a/wfs", "http://b/wfs", "http://c/wfs"]
    _, provenance = client.zones_intersecting_with_provenance(wkt, kinds=[ZoneKind.DETACHED])
    dataset = client.dataset(provenance)
    assert dataset.source_url == "http://c/wfs"  # the mirror that answered, not the first
    assert dataset.retrieved_at == provenance[0].retrieved_at and dataset.state is None
    assert dataset.state_note and "2016" in dataset.state_note
    assert client.dataset().retrieved_at is None  # nothing is remembered on the client


def test_provenance_is_per_operation_not_shared_between_threads(
    fake_http: type[FakeClient],
) -> None:
    """Two concurrent lookups each report the mirror that answered them."""
    import threading

    gate = threading.Barrier(2, timeout=10)
    gated_once = threading.Event()

    class PerThread(FakeClient):
        def get(self, url: str, params: dict[str, str] | None = None) -> httpx.Response:
            name = threading.current_thread().name
            if name == "second" and url == "http://a/wfs":
                if not gated_once.is_set():
                    gated_once.set()
                    gate.wait()  # let the first thread finish before this mirror "fails"
                return httpx.Response(502, text="down", request=httpx.Request("GET", url))
            return super().get(url, params)

    fake_http.responses = {
        "http://a/wfs": (200, {**EMPTY, "features": [SETTLEMENT]}),
        "http://b/wfs": (200, {**EMPTY, "features": [DETACHED_T2]}),
    }
    client = PlanningWFSClient(["http://a/wfs", "http://b/wfs"], rate_limit=0)
    client.client = PerThread()
    results: dict[str, Any] = {}

    def run(name: str) -> None:
        results[name] = client.zoning_for_geometry(PARCEL)
        if name == "first":
            gate.wait()

    first = threading.Thread(target=run, args=("first",), name="first")
    second = threading.Thread(target=run, args=("second",), name="second")
    second.start()
    first.start()
    first.join(10)
    second.join(10)
    assert results["first"].dataset.source_url == "http://a/wfs"
    assert results["second"].dataset.source_url == "http://b/wfs"


def test_invalid_threshold_is_rejected_before_any_request(fake_http: type[FakeClient]) -> None:
    fake_http.responses = {"http://a/wfs": (200, EMPTY)}
    client = PlanningWFSClient(["http://a/wfs"], rate_limit=0)
    for bad in (-0.01, 1.01, float("nan"), True, "0.5"):
        with pytest.raises(ValueError):
            client.zoning_for_geometry(PARCEL, min_overlap=bad)  # type: ignore[arg-type]
    assert fake_http.calls == []


def test_validate_min_overlap_accepts_the_whole_closed_range() -> None:
    assert validate_min_overlap(0) == 0.0
    assert validate_min_overlap(1) == 1.0
    assert validate_min_overlap(0.02) == 0.02


def test_all_mirrors_down_is_a_connection_error(fake_http: type[FakeClient]) -> None:
    fake_http.responses = {"http://a/wfs": (503, "down"), "http://b/wfs": (504, "down")}
    client = PlanningWFSClient(["http://a/wfs", "http://b/wfs"], rate_limit=0)
    with pytest.raises(CadastralAPIError) as exc_info:
        client.find_zones(municipality_code="03794")
    assert exc_info.value.error_type is ErrorType.CONNECTION
    assert "http://b/wfs: HTTP 504" in exc_info.value.details["mirrors"]


def test_wfs_exception_is_an_invalid_response_not_a_retry(fake_http: type[FakeClient]) -> None:
    fake_http.responses = {
        "http://a/wfs": (400, "<ows:ExceptionReport>Feature type unknown</ows:ExceptionReport>"),
        "http://b/wfs": (200, EMPTY),
    }
    client = PlanningWFSClient(["http://a/wfs", "http://b/wfs"], rate_limit=0)
    with pytest.raises(CadastralAPIError) as exc_info:
        client.find_zones(designation_code="T2")
    assert exc_info.value.error_type is ErrorType.INVALID_RESPONSE
    assert fake_http.calls == ["http://a/wfs"]


def test_find_zones_builds_a_cql_filter_with_escaped_quotes(fake_http: type[FakeClient]) -> None:
    captured: dict[str, str] = {}

    class Recording(FakeClient):
        def get(self, url: str, params: dict[str, str] | None = None) -> httpx.Response:
            captured.update(params or {})
            return super().get(url, params)

    fake_http.responses = {"http://a/wfs": (200, EMPTY)}
    client = PlanningWFSClient(["http://a/wfs"], rate_limit=0)
    client.client = Recording()
    client.find_zones(municipality_code="03794", designation_code="T'2", count=5, start_index=10)
    assert captured["cql_filter"] == "jls_mb='03794' AND ozn_namjen='T''2'"
    assert captured["count"] == "5" and captured["startIndex"] == "10"
    assert captured["typeNames"].endswith("Gradj_podrucje_izvan_naselja")
