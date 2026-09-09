"""get_parcel_geometry: missing parcel is an error, found parcel carries a map link.

The SDK returns None when the parcel is not in the municipality's GML file.
The tool used to call ``to_geojson`` / ``to_wkt`` / ``model_dump`` on that
None and surface ``'NoneType' object has no attribute ...`` to the agent.
"""

import asyncio
from unittest.mock import MagicMock

import pytest
from cadastral_api import ParcelGeometry

from cadastral_mcp.tools import CadastralTools

GEOMETRY = ParcelGeometry(
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
MAP_URL_19 = "https://oss.uredjenazemlja.hr/map?center=380616.77,4880907.83&zoom=19&layers="


def _tools(geometry: ParcelGeometry | None) -> CadastralTools:
    client = MagicMock()
    client.get_parcel_geometry.return_value = geometry
    tools = CadastralTools(client)

    async def resolve(name_or_code: str) -> str:
        return "334979"

    tools._resolve_municipality = resolve  # type: ignore[method-assign]
    return tools


@pytest.mark.parametrize("fmt", ["geojson", "wkt", "dict"])
def test_missing_parcel_raises_clear_error(fmt: str) -> None:
    tools = _tools(None)

    with pytest.raises(ValueError) as exc_info:
        asyncio.run(tools.get_parcel_geometry("114", "SAVAR", format=fmt))

    message = str(exc_info.value)
    assert "114" in message
    assert "SAVAR" in message
    assert "334979" in message
    assert "NoneType" not in message


def test_geojson_output_is_a_feature_with_map_url() -> None:
    feature = asyncio.run(_tools(GEOMETRY).get_parcel_geometry("103/2", "SAVAR"))

    assert feature["type"] == "Feature"
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"]["parcel_number"] == "103/2"
    assert feature["properties"]["map_url"].startswith(MAP_URL_19)


def test_dict_output_keeps_model_fields_and_adds_map_url() -> None:
    data = asyncio.run(_tools(GEOMETRY).get_parcel_geometry("103/2", "SAVAR", format="dict"))

    assert data["broj_cestice"] == "103/2"
    assert data["povrsina_graficka"] == 1200.0
    assert len(data["coordinates"]) == 5
    assert data["map_url"].startswith(MAP_URL_19)


def test_zoom_is_passed_through_to_the_map_url() -> None:
    tools = _tools(GEOMETRY)

    data = asyncio.run(tools.get_parcel_geometry("103/2", "SAVAR", format="dict", zoom=20))
    feature = asyncio.run(tools.get_parcel_geometry("103/2", "SAVAR", zoom=20))

    assert "&zoom=20&" in data["map_url"]
    assert "&zoom=20&" in feature["properties"]["map_url"]


def test_wkt_output_is_the_bare_polygon() -> None:
    wkt = asyncio.run(_tools(GEOMETRY).get_parcel_geometry("103/2", "SAVAR", format="wkt"))

    assert wkt.startswith("POLYGON((")
    assert "map" not in wkt


def _search_tools(geometry_or_error: object) -> CadastralTools:
    client = MagicMock()
    hit = MagicMock()
    hit.parcel_id = "6564817"
    hit.parcel_number = "103/2"
    client.find_parcel.return_value = [hit]
    if isinstance(geometry_or_error, Exception):
        client.get_parcel_geometry.side_effect = geometry_or_error
    else:
        client.get_parcel_geometry.return_value = geometry_or_error
    tools = CadastralTools(client)

    async def resolve(name_or_code: str) -> str:
        return "334979"

    tools._resolve_municipality = resolve  # type: ignore[method-assign]
    return tools


def test_find_parcel_includes_map_url_when_geometry_is_available() -> None:
    result = asyncio.run(_search_tools(GEOMETRY).search_parcel("103/2", "SAVAR"))

    assert result["parcel_id"] == "6564817"
    assert result["map_url"].startswith(MAP_URL_19)


def test_find_parcel_omits_map_url_when_parcel_is_not_in_gml() -> None:
    result = asyncio.run(_search_tools(None).search_parcel("103/2", "SAVAR"))

    assert result["success"] is True
    assert "map_url" not in result


def test_find_parcel_survives_gis_download_failure() -> None:
    result = asyncio.run(
        _search_tools(RuntimeError("download failed")).search_parcel("103/2", "SAVAR")
    )

    assert result["success"] is True
    assert "map_url" not in result
