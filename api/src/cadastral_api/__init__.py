"""Croatian Cadastral System (Ureena zemlja) API Client."""

from .analysis import AreaCheck, check_area, count_distinct_persons, person_key, same_person
from .client import CadastralAPIClient
from .exceptions import CadastralAPIError, ErrorType
from .gis import GISCache, GMLParser
from .models import (
    BookOfDCSearchResult,
    CadastralOffice,
    Coordinate,
    FileStatus,
    LandRegistryUnit,
    LandRegistryUnitDetailed,
    LRUnitType,
    MainBookSearchResult,
    MunicipalitySearchResult,
    ParcelGeometry,
    ParcelInfo,
    ParcelLink,
    ParcelPart,
    ParcelSearchResult,
    ParcelZoning,
    Party,
    PlanGeneration,
    PlanningZone,
    Plumb,
    PossessionSheet,
    PossessionSheetSearchResult,
    Possessor,
    Provenance,
    ZoneKind,
    ZoneMatch,
    ZoningStatus,
    build_map_url,
)
from .planning import PlanningWFSClient
from .utils import display_parcel_number, normalize_parcel_number

__version__ = "0.2.0"

__all__ = [
    # Client
    "CadastralAPIClient",
    # Exceptions
    "CadastralAPIError",
    "ErrorType",
    # GIS
    "GISCache",
    "GMLParser",
    # Spatial plans
    "PlanningWFSClient",
    "ParcelZoning",
    "PlanGeneration",
    "PlanningZone",
    "ZoneKind",
    "ZoneMatch",
    "ZoningStatus",
    # Models
    "BookOfDCSearchResult",
    "CadastralOffice",
    "Coordinate",
    "FileStatus",
    "LandRegistryUnit",
    "LandRegistryUnitDetailed",
    "LRUnitType",
    "MainBookSearchResult",
    "MunicipalitySearchResult",
    "ParcelGeometry",
    "build_map_url",
    "ParcelInfo",
    "ParcelLink",
    "ParcelPart",
    "ParcelSearchResult",
    "Party",
    "Plumb",
    "Possessor",
    "PossessionSheet",
    "PossessionSheetSearchResult",
    "Provenance",
    # Analysis (pure functions over the models)
    "AreaCheck",
    "check_area",
    "count_distinct_persons",
    "person_key",
    "same_person",
    # Helpers
    "display_parcel_number",
    "normalize_parcel_number",
]
