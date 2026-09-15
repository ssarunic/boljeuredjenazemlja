"""Composition over the registers: pure functions on the SDK models, no I/O.

The client fetches records; this package reads across them: whether two
person records are the same person, whether the areas the registers give a
parcel agree, and whether the cadastre possessors are the land-registry
owners. Nothing here makes a request.
"""

from .area_check import DEFAULT_AREA_TOLERANCE, AreaCheck, check_area
from .assembly import (
    DEFAULT_WEIGHTS,
    AcquisitionScore,
    AssemblyAnalysis,
    AssemblyInput,
    PersonHolding,
    acquisition_score,
    build_assembly,
    resolve_weights,
)
from .export import matrix_csv, parcels_csv, parcels_geojson, persons_csv, rows_to_csv
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
    "AcquisitionScore",
    "AreaCheck",
    "AssemblyAnalysis",
    "AssemblyInput",
    "DEFAULT_WEIGHTS",
    "PersonHolding",
    "acquisition_score",
    "build_assembly",
    "matrix_csv",
    "parcels_csv",
    "parcels_geojson",
    "persons_csv",
    "resolve_weights",
    "rows_to_csv",
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
