"""download_municipality_gis fills the cache and reports what it cached."""

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cadastral_mcp.tools import CadastralTools


def _tools(tmp_path: Path, cached: bool):
    zip_path = tmp_path / "ko-334979.zip"
    zip_path.write_bytes(b"x" * 1234)
    gml_path = tmp_path / "katastarske_cestice.gml"
    gml_path.write_text("<gml/>", encoding="utf-8")
    cache = MagicMock()
    cache.base_url = "http://localhost:8000"
    cache.is_cached.return_value = cached
    cache.download_municipality.return_value = zip_path
    cache.get_parcel_data.return_value = gml_path
    cache.get_source.return_value = "http://localhost:8000"
    client = MagicMock()
    client.gis_cache = cache
    tools = CadastralTools(client)

    async def resolve(name_or_code: str) -> str:
        return "334979"

    tools._resolve_municipality = resolve  # type: ignore[method-assign]
    return tools, cache


def test_download_reports_the_cached_files(tmp_path: Path) -> None:
    tools, cache = _tools(tmp_path, cached=False)
    with patch("cadastral_mcp.tools.GMLParser") as parser:
        parser.return_value.count_parcels.return_value = 1523
        result = asyncio.run(tools.download_municipality_gis("SAVAR"))
    assert result["municipality_code"] == "334979"
    assert result["download_url"] == "http://localhost:8000/atom/ko-334979.zip"
    assert result["already_cached"] is False
    assert result["zip_size_bytes"] == 1234
    assert result["parcel_count"] == 1523
    assert result["source"] == "http://localhost:8000"
    cache.download_municipality.assert_called_once_with("334979", False)


def test_force_redownloads_a_cached_municipality(tmp_path: Path) -> None:
    tools, cache = _tools(tmp_path, cached=True)
    with patch("cadastral_mcp.tools.GMLParser") as parser:
        parser.return_value.count_parcels.return_value = 1
        cached = asyncio.run(tools.download_municipality_gis("SAVAR"))
        forced = asyncio.run(tools.download_municipality_gis("SAVAR", force=True))
    assert cached["already_cached"] is True
    assert forced["already_cached"] is False
    cache.download_municipality.assert_called_with("334979", True)


def test_download_failure_is_a_clear_error(tmp_path: Path) -> None:
    tools, cache = _tools(tmp_path, cached=False)
    cache.download_municipality.side_effect = OSError("connection refused")
    with pytest.raises(ValueError) as excinfo:
        asyncio.run(tools.download_municipality_gis("SAVAR"))
    assert "334979" in str(excinfo.value)
    assert "connection refused" in str(excinfo.value)
