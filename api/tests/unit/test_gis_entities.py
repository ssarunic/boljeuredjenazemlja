"""ParcelGeometry: map link and GeoJSON export."""

from cadastral_api import ParcelGeometry, build_map_url
from cadastral_api.models.gis_entities import MAP_LAYERS

# The mock server's synthetic 40 x 30 m parcel 103/2 in SAVAR.
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


def test_map_url_is_centred_on_the_parcel_at_zoom_19() -> None:
    assert GEOMETRY.map_url() == (
        "https://oss.uredjenazemlja.hr/map?center=380616.77,4880907.83&zoom=19"
        f"&layers={MAP_LAYERS}"
    )


def test_map_url_zoom_is_configurable() -> None:
    assert "&zoom=20&" in GEOMETRY.map_url(zoom=20)


def test_map_url_rounds_to_centimetres() -> None:
    url = build_map_url((380616.7749, 4880907.8251))
    assert "center=380616.77,4880907.83&" in url


def test_build_map_url_without_center_is_the_plain_viewer() -> None:
    assert build_map_url() == f"https://oss.uredjenazemlja.hr/map?layers={MAP_LAYERS}"


def test_to_geojson_feature_carries_properties_and_map_url() -> None:
    feature = GEOMETRY.to_geojson(zoom=20)

    assert feature["type"] == "Feature"
    assert feature["geometry"] == {
        "type": "Polygon",
        "coordinates": [GEOMETRY.to_geojson_coords()],
    }
    assert feature["properties"] == {
        "parcel_number": "103/2",
        "municipality": "334979",
        "area_m2": 1200.0,
        "srs": "EPSG:3765",
        "map_url": GEOMETRY.map_url(zoom=20),
    }


def test_model_dump_does_not_include_map_url() -> None:
    # The link is derived; callers add it explicitly (the MCP tool does).
    assert "map_url" not in GEOMETRY.model_dump()
