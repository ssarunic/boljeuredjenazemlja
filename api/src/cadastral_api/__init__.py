"""Croatian Cadastral System (Ureena zemlja) API Client."""

from .client import CadastralAPIClient
from .exceptions import CadastralAPIError, ErrorType
from .gis import GISCache, GMLParser
from .models import (
    CadastralOffice,
    Coordinate,
    FileStatus,
    LandRegistryUnit,
    MunicipalitySearchResult,
    ParcelGeometry,
    ParcelInfo,
    ParcelLink,
    ParcelPart,
    ParcelSearchResult,
    Plumb,
    PossessionSheet,
    Possessor,
)

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
    "CadastralOffice",
    "Coordinate",
    "FileStatus",
    "LandRegistryUnit",
    "MunicipalitySearchResult",
    "ParcelGeometry",
    "ParcelInfo",
    "ParcelLink",
    "ParcelPart",
    "ParcelSearchResult",
    "Plumb",
    "Possessor",
    "PossessionSheet",
]
