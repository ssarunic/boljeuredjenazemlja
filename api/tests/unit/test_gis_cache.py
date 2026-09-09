"""GIS cache: a ZIP downloaded from one server must never be served for another.

The cache is keyed by municipality code only, so without the source marker a
ZIP fetched from the mock server (synthetic geometry) would be reused by any
later client regardless of its base URL. These tests pin the marker behaviour.
"""

import io
import zipfile
from pathlib import Path

import httpx
import pytest

from cadastral_api.gis.cache import GISCache

MOCK_URL = "http://mock:8000"
OTHER_URL = "http://other:9000"
GML_NAME = "katastarske_cestice.gml"


def _zip_bytes(gml: bytes) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(GML_NAME, gml)
    return buf.getvalue()


class FakeClient:
    """Stands in for httpx.Client: serves ``payload`` and records requested URLs."""

    calls: list[str] = []
    payload: bytes = b""
    status: int = 200

    def __init__(self, *args: object, **kwargs: object) -> None:
        pass

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *exc: object) -> bool:
        return False

    def get(self, url: str) -> httpx.Response:
        FakeClient.calls.append(url)
        return httpx.Response(
            FakeClient.status,
            content=FakeClient.payload,
            request=httpx.Request("GET", url),
        )


@pytest.fixture
def fake_http(monkeypatch: pytest.MonkeyPatch) -> type[FakeClient]:
    FakeClient.calls = []
    FakeClient.payload = _zip_bytes(b"<gml>mock</gml>")
    FakeClient.status = 200
    monkeypatch.setattr("cadastral_api.gis.cache.httpx.Client", FakeClient)
    return FakeClient


def test_download_writes_source_marker(tmp_path: Path, fake_http: type[FakeClient]) -> None:
    cache = GISCache(tmp_path, base_url=MOCK_URL + "/")

    gml = cache.get_parcel_data("334979")

    assert fake_http.calls == [f"{MOCK_URL}/atom/ko-334979.zip"]
    assert gml.read_bytes() == b"<gml>mock</gml>"
    assert cache.get_source("334979") == MOCK_URL
    assert cache.get_source_path("334979").read_text(encoding="utf-8") == MOCK_URL + "\n"
    assert cache.is_cached("334979")


def test_same_server_reuses_cache(tmp_path: Path, fake_http: type[FakeClient]) -> None:
    cache = GISCache(tmp_path, base_url=MOCK_URL)
    cache.get_parcel_data("334979")

    GISCache(tmp_path, base_url=MOCK_URL).get_parcel_data("334979")

    assert len(fake_http.calls) == 1


def test_other_server_redownloads_and_drops_stale_gml(
    tmp_path: Path, fake_http: type[FakeClient]
) -> None:
    GISCache(tmp_path, base_url=MOCK_URL).get_parcel_data("334979")
    fake_http.payload = _zip_bytes(b"<gml>other</gml>")

    other = GISCache(tmp_path, base_url=OTHER_URL)
    assert not other.is_cached("334979")
    gml = other.get_parcel_data("334979")

    assert fake_http.calls[-1] == f"{OTHER_URL}/atom/ko-334979.zip"
    assert gml.read_bytes() == b"<gml>other</gml>"
    assert other.get_source("334979") == OTHER_URL


def test_cache_without_marker_is_refreshed(tmp_path: Path, fake_http: type[FakeClient]) -> None:
    # A cache written by an earlier version: ZIP and extracted GML, no marker.
    muni_dir = tmp_path / "ko-334979"
    muni_dir.mkdir()
    (muni_dir / "ko-334979.zip").write_bytes(_zip_bytes(b"<gml>legacy</gml>"))
    (muni_dir / GML_NAME).write_bytes(b"<gml>legacy</gml>")

    cache = GISCache(tmp_path, base_url=MOCK_URL)
    assert cache.get_source("334979") is None
    assert not cache.is_cached("334979")

    gml = cache.get_parcel_data("334979")

    assert len(fake_http.calls) == 1
    assert gml.read_bytes() == b"<gml>mock</gml>"
    assert cache.is_cached("334979")


def test_force_redownloads(tmp_path: Path, fake_http: type[FakeClient]) -> None:
    cache = GISCache(tmp_path, base_url=MOCK_URL)
    cache.download_municipality("334979")

    cache.download_municipality("334979", force=True)

    assert len(fake_http.calls) == 2


def test_failed_download_keeps_previous_files_but_serves_nothing(
    tmp_path: Path, fake_http: type[FakeClient]
) -> None:
    GISCache(tmp_path, base_url=MOCK_URL).get_parcel_data("334979")
    fake_http.status = 503

    other = GISCache(tmp_path, base_url=OTHER_URL)
    with pytest.raises(httpx.HTTPStatusError):
        other.get_parcel_data("334979")

    # The mock-server copy is untouched for the mock client...
    assert GISCache(tmp_path, base_url=MOCK_URL).is_cached("334979")
    # ...and still not considered cached for the other one.
    assert not other.is_cached("334979")
