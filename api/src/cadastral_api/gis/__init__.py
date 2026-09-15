"""GIS data access layer with local caching."""

from .cache import GISCache
from .parser import GMLParser
from .spatial_index import IndexedParcel, Neighbour, ParcelIndex, RadiusHit

__all__ = ["GISCache", "GMLParser", "IndexedParcel", "Neighbour", "ParcelIndex", "RadiusHit"]
