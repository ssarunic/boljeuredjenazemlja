# Croatian Cadastral API - Python SDK

Python SDK for accessing the Croatian Cadastral System (Uređena zemlja) API.

## Features

- Type-safe Pydantic V2 models with full validation
- GIS integration with parcel geometry parsing
- Local caching of GML files
- Automatic rate limiting
- Comprehensive error handling
- Internationalization support (Croatian, English)

## Installation

```bash
cd api
pip install -e .
```

## Quick Start

```python
from cadastral_api import CadastralAPIClient

with CadastralAPIClient() as client:
    # Search for a parcel
    parcels = client.search_parcels("103/2", "SAVAR")
    
    # Get detailed parcel information
    parcel = client.get_parcel_by_id(parcels[0].key1)
    
    # Get parcel geometry
    geometry = client.get_parcel_geometry("103/2", "334979")
    print(f"Area: {geometry.area} m²")
```

## Documentation

- [API Documentation](docs/)
- [Pydantic Entities Implementation](docs/pydantic-entities-implementation.md)
- [Examples](examples/)

## License

MIT
