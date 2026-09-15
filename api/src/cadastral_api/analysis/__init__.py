"""Composition over the registers: pure functions on the SDK models, no I/O.

The client fetches records; this package reads across them: whether two
person records are the same person, whether the areas the registers give a
parcel agree, and (in later steps) whether the cadastre possessors are the
land-registry owners. Nothing here makes a request.
"""

from .area_check import DEFAULT_AREA_TOLERANCE, AreaCheck, check_area
from .persons import PersonKey, count_distinct_persons, person_key, same_person

__all__ = [
    "AreaCheck",
    "DEFAULT_AREA_TOLERANCE",
    "PersonKey",
    "check_area",
    "count_distinct_persons",
    "person_key",
    "same_person",
]
