"""Croatian Cadastral System (Ureena zemlja) API Client."""

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
    Party,
    Plumb,
    PossessionSheet,
    PossessionSheetSearchResult,
    Possessor,
    build_map_url,
)
from .utils import display_parcel_number, normalize_parcel_number

__version__ = "0.1.0"

__all__ = [
    # Client
    "CadastralAPIClient",
    # Exceptions
    "CadastralAPIError",
    "ErrorType",
    # GIS
    "GISCache",
    "GMLParser",
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
    # Helpers
    "display_parcel_number",
    "normalize_parcel_number",
]
