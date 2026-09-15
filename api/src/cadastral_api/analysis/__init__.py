"""Composition over the registers: pure functions on the SDK models, no I/O.

The client fetches records; this package reads across them: whether two
person records are the same person, whether the areas the registers give a
parcel agree, and whether the cadastre possessors are the land-registry
owners. Nothing here makes a request.
"""

from .area_check import DEFAULT_AREA_TOLERANCE, AreaCheck, check_area
from .persons import (
    PartyTypeInference,
    PersonKey,
    count_distinct_persons,
    infer_party_type,
    person_key,
    same_person,
)
from .registers import (
    MatchedPerson,
    PersonRecord,
    RegisterComparison,
    compare_registers,
    owner_records,
    possessor_records,
)

__all__ = [
    "AreaCheck",
    "DEFAULT_AREA_TOLERANCE",
    "MatchedPerson",
    "PartyTypeInference",
    "PersonKey",
    "PersonRecord",
    "RegisterComparison",
    "check_area",
    "compare_registers",
    "count_distinct_persons",
    "infer_party_type",
    "owner_records",
    "person_key",
    "possessor_records",
    "same_person",
]
