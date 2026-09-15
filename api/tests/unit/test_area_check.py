"""The areas the registers give one parcel, compared."""

from __future__ import annotations

from cadastral_api.analysis import DEFAULT_AREA_TOLERANCE, check_area


def test_three_agreeing_areas_are_no_mismatch() -> None:
    check = check_area(cadastre_m2=1200, land_registry_m2=1200, gis_m2=1215.4)
    assert check.compared == ["cadastre", "land_registry", "gis"]
    assert check.max_difference_m2 == 15.4
    assert check.max_difference_fraction == round(15.4 / 1215.4, 4)
    assert check.mismatch is False
    assert check.tolerance_fraction == DEFAULT_AREA_TOLERANCE
    assert check.note is None


def test_a_difference_above_the_tolerance_is_flagged() -> None:
    check = check_area(cadastre_m2=1200, gis_m2=1100.0)
    assert check.compared == ["cadastre", "gis"]
    assert check.land_registry_m2 is None
    assert check.max_difference_m2 == 100.0
    assert check.max_difference_fraction == round(100 / 1200, 4)
    assert check.mismatch is True


def test_the_tolerance_is_a_parameter() -> None:
    assert check_area(cadastre_m2=1000, gis_m2=1040.0).mismatch is False
    assert check_area(cadastre_m2=1000, gis_m2=1040.0, tolerance=0.02).mismatch is True


def test_one_or_no_area_is_nothing_to_compare() -> None:
    one = check_area(cadastre_m2=1200, note="land-register area not on the record")
    assert one.compared == ["cadastre"]
    assert one.mismatch is False
    assert one.max_difference_m2 is None
    assert one.note == (
        "only one area is known, nothing to compare; land-register area not on the record"
    )
    none = check_area()
    assert none.compared == [] and none.mismatch is False
    assert none.note == "no area is known, nothing to compare"


def test_non_positive_areas_count_as_unknown() -> None:
    check = check_area(cadastre_m2=0, land_registry_m2=-5, gis_m2=1200.0)
    assert check.compared == ["gis"]
    assert check.cadastre_m2 is None and check.land_registry_m2 is None
