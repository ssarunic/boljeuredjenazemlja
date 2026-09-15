"""Do the areas the registers give one parcel agree?

The cadastre record carries the parcel's area; the land register carries its
own (sheet A of the unit, or the parcel link on the cadastre record); the
cadastral map gives a graphical area computed from the outline. They differ
routinely: the land register often still holds an old survey, and a graphical
area differs from a surveyed one by a per cent or two. A difference above the
tolerance is flagged so that the reader checks which register is current
before quoting a size.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

#: Relative difference between two areas above which they are flagged.
DEFAULT_AREA_TOLERANCE = 0.05
#: Differences below this many m2 are noise, whatever the share of the parcel.
DEFAULT_AREA_MIN_DIFFERENCE_M2 = 20.0


class AreaCheck(BaseModel):
    """The areas known for one parcel and whether they agree."""

    cadastre_m2: int | None = Field(default=None, description="Area on the cadastre record")
    land_registry_m2: int | None = Field(
        default=None, description="Area the land register holds for the parcel"
    )
    gis_m2: float | None = Field(
        default=None, description="Graphical area of the parcel outline on the cadastral map"
    )
    compared: list[str] = Field(
        default_factory=list, description="Which of the three areas were available"
    )
    max_difference_m2: float | None = Field(
        default=None, description="Largest difference between two of the areas, in m2"
    )
    max_difference_fraction: float | None = Field(
        default=None, description="That difference as a share of the largest area"
    )
    tolerance_fraction: float = Field(description="Share above which the areas are flagged")
    min_difference_m2: float = Field(
        default=0.0,
        description="Differences below this many m2 are never flagged (digitisation noise)",
    )
    mismatch: bool = Field(
        description="True when the largest difference exceeds the tolerance and the floor"
    )
    note: str | None = Field(default=None, description="Why an area is missing, or a caveat")


def check_area(
    cadastre_m2: int | None = None,
    land_registry_m2: int | None = None,
    gis_m2: float | None = None,
    tolerance: float = DEFAULT_AREA_TOLERANCE,
    note: str | None = None,
    min_difference_m2: float = DEFAULT_AREA_MIN_DIFFERENCE_M2,
) -> AreaCheck:
    """Compare whichever of the three areas are known (pure; nothing is fetched).

    With fewer than two areas there is nothing to compare: ``mismatch`` is
    False and the note says so. Non-positive values count as unknown. A
    mismatch needs the difference above ``tolerance`` and above
    ``min_difference_m2``: 5 % of a 60 m2 building parcel is 3 m2, which
    ordinary digitisation noise trips.
    """
    known: dict[str, float] = {}
    if cadastre_m2 is not None and cadastre_m2 > 0:
        known["cadastre"] = float(cadastre_m2)
    if land_registry_m2 is not None and land_registry_m2 > 0:
        known["land_registry"] = float(land_registry_m2)
    if gis_m2 is not None and gis_m2 > 0:
        known["gis"] = float(gis_m2)

    difference: float | None = None
    fraction: float | None = None
    if len(known) >= 2:
        values = list(known.values())
        difference = round(max(values) - min(values), 1)
        fraction = round(difference / max(values), 4)
    else:
        missing = "only one area is known" if known else "no area is known"
        note = f"{missing}, nothing to compare" + (f"; {note}" if note else "")

    return AreaCheck(
        cadastre_m2=cadastre_m2 if "cadastre" in known else None,
        land_registry_m2=land_registry_m2 if "land_registry" in known else None,
        gis_m2=gis_m2 if "gis" in known else None,
        compared=list(known),
        max_difference_m2=difference,
        max_difference_fraction=fraction,
        tolerance_fraction=tolerance,
        min_difference_m2=min_difference_m2,
        mismatch=(
            fraction is not None
            and difference is not None
            and fraction > tolerance
            and difference > min_difference_m2
        ),
        note=note,
    )
