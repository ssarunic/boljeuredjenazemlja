# Cadastral CLI

Command-line interface for the Croatian Cadastral System API.

## Features

- Rich terminal interface with formatted tables
- Multiple output formats (table, JSON, CSV, WKT, GeoJSON)
- Batch processing support
- Internationalization (Croatian, English)
- Interactive parcel search and information retrieval

## Installation

```bash
cd cli
pip install -e .
```

## Quick Start

```bash
# Search for a parcel
cadastral search 103/2 --municipality SAVAR

# Get detailed parcel information with owners
cadastral get-parcel 103/2 -m 334979 --show-owners

# Get land registry unit information
cadastral get-lr-unit --from-parcel 279/6 -m SAVAR --all

# Batch processing
cadastral batch-fetch "103/2,45,396/1" --municipality SAVAR

# Get parcel geometry
cadastral get-geometry 103/2 -m 334979 --format wkt
```

## Documentation

- [Command Reference](docs/command-reference.md)

## License

MIT
