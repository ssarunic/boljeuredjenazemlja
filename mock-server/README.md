# Mock Cadastral API Server

FastAPI-based mock server for testing the Croatian Cadastral System API client.

## Features

- Mock implementation of all cadastral API endpoints
- Test data for municipalities, offices, and parcels
- Fast local development and testing
- No external API dependencies

## Quick Start

```bash
cd mock-server
pip install -r requirements.txt
python src/main.py
```

The server will start on `http://localhost:8000`.

## Configuration

Configure your API client to use the mock server:

```bash
export CADASTRAL_API_BASE_URL=http://localhost:8000
```

## Test Data

Test data is located in the `data/` directory. Most of it is a redacted copy of
real responses (k.o. Savar sample, September 2026) produced by
`scripts/redact_capture.py`: every key, type and shape is as the public API
sends it, while names, addresses and OIBs are deterministic placeholders
("Vlasnik 12", "Adresa 12", synthetic OIBs) and personal names in entry texts
are `N.N.`.

- `offices.json` - The 21 cadastral offices
- `municipalities.json` - Municipalities (SAVAR and LUKA plus decoys)
- `main-books.json`, `books-of-dc.json` - Land registry main books and books of deposited contracts (KPU)
- `parcels/334979.json` - 68 parcels of k.o. Savar: 59 redacted real ones in all three shapes (direct `lrUnit`, linked via `parcelLinks`, cadastre-only building parcels `*35/1`) plus the hand-made demo parcels 103/2, 45, 396/1, ...
- `parcels/334731.json` - Hand-made parcels of k.o. Luka
- `lr-units/<mainBookId>-<unit>.json` - 17 units of main book 21277 (SAVAR), the Split condominium 13998/30783 and the hand-made unit 657
- `lr-file-status/` - Plomba (file) status records

Possession sheets for `/search-cad-parcels/possession-sheet-numbers` are derived
from the parcels at startup. The parcel search reproduces the observed public
behaviour: prefix match, a leading asterisk as wildcard, `35/1 ZGR` for the
building parcel `*35/1`.

To refresh the data, run `scripts/capture_api_sample.py --base-url <server>
<raw-dir>` (only against a server you have the rights to use; see
`docs/legal.md`) and then `scripts/redact_capture.py <raw-dir> --write`.

## License

MIT

## GIS geometry fixture

`data/geometry/<municipality>.zip` is served by `/atom/ko-<municipality>.zip`.
The included `334979.zip` holds a small synthetic `katastarske_cestice.gml`
(parcels 103/2, 45 and 396/1 of SAVAR, drawn as rectangles whose areas match
`data/parcels/334979.json`). It exists so that `get-geometry` and
`download-gis` work offline against the mock server, and so that the
documentation build can capture their output.
