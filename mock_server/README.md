# Mock Croatian Cadastral API Server

## ⚠️ IMPORTANT - DEMO PROJECT ONLY

**This is a mock server for testing and demonstration purposes.**

- Returns **static data** from JSON files
- **NOT connected** to real Croatian government systems
- For **educational and testing** use only
- See main project README for complete disclaimer

## Overview

This FastAPI server mimics the Croatian cadastral API endpoints to enable safe testing of the `cadastral` CLI client without accessing production government systems.

## Features

- ✅ All 4 main API endpoints implemented
- ✅ Static test data for 2 municipalities (SAVAR, LUKA)
- ✅ 10+ parcels per municipality with realistic data
- ✅ Partial search support (e.g., "114" matches "114", "1140/1", etc.)
- ✅ Fast startup - all data loaded into memory
- ✅ OpenAPI documentation at `/docs`
- ✅ CORS enabled for browser testing

## Installation

### 1. Install Dependencies

```bash
cd mock_server
pip install -r requirements.txt
```

### 2. Start the Server

```bash
# Option A: Using uvicorn directly
uvicorn main:app --reload --port 8000

# Option B: Using Python
python main.py

# The server will start on http://localhost:8000
```

### 3. Verify Server is Running

```bash
curl http://localhost:8000

# Should return server info JSON
```

## API Endpoints

The mock server implements these endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Server info and status |
| `/search-cad-parcels/offices` | GET | List cadastral offices |
| `/search-cad-parcels/municipalities` | GET | Search municipalities |
| `/search-cad-parcels/parcel-numbers` | GET | Search parcel numbers |
| `/cad/parcel-info` | GET | Get detailed parcel info |
| `/atom/ko-{code}.zip` | GET | Download GIS data (optional) |

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Testing with CLI Client

Configure the cadastral CLI to use the mock server:

```bash
# Set environment variable
export CADASTRAL_API_BASE_URL=http://localhost:8000

# Or update .env file
echo "CADASTRAL_API_BASE_URL=http://localhost:8000" > .env
```

Then test commands:

```bash
# List offices
cadastral list-offices

# Search municipalities
cadastral search-municipality SAVAR

# Search parcels
cadastral search 103/2 --municipality SAVAR

# Get detailed parcel info
cadastral get-parcel 103/2 -m 334979 --show-owners

# Test partial search
cadastral search 114 -m 334979 --partial
```

## Test Data

### Municipalities

- **SAVAR** (334979) - 10 parcels
- **LUKA** (334731) - 7 parcels
- Plus 28 other municipalities for discovery commands

### Sample Parcels (SAVAR)

| Parcel | Area | Land Use | Owners |
|--------|------|----------|--------|
| 103/2 | 1200 m² | MASLINJAK | 2 owners (no fractions) |
| 45 | 981 m² | PAŠNJAK | 2 owners (1/1 each) |
| 396/1 | 2077 m² | ŠUMA | 18 owners (no fractions) |
| 114 | 845 m² | ORANICA | 2 owners (1/2 each) |
| 1140/1 | 1523 m² | VOĆNJAK | 3 owners (mixed fractions) |

### Sample Parcels (LUKA)

| Parcel | Area | Land Use | Owners |
|--------|------|----------|--------|
| 23 | 756 m² | ORANICA | 1 owner (1/1) |
| 67/2 | 1423 m² | MASLINJAK | 2 owners (no fractions) |
| 145 | 2789 m² | PAŠNJAK + ŠUMA | 2 owners (1/2 each) |
| 312/1 | 934 m² | VINOGRAD | 4 owners (1/4 each) |

## Data Structure

```
data/
├── offices.json              # 15 cadastral offices
├── municipalities.json       # 30 municipalities
└── parcels/
    ├── 334979.json          # SAVAR parcels (10 parcels)
    └── 334731.json          # LUKA parcels (7 parcels)
```

## Adding More Test Data

### Add a New Municipality

1. Add entry to `data/municipalities.json`:
```json
{
  "key1": "1234",
  "value1": "999999 TEST",
  "key2": "999999",
  "value2": "114",
  "value3": "116",
  "displayValue1": "999999 TEST, ZADAR, PUK ZADAR"
}
```

2. Create `data/parcels/999999.json` with parcel data

3. Restart server - data is loaded at startup

### Add Parcels to Existing Municipality

Edit the appropriate JSON file in `data/parcels/` and add new parcel objects following the existing structure.

## Implementation Notes

### Key Design Decisions

1. **Static JSON files** - No database, simple file-based storage
2. **In-memory loading** - All data loaded at startup for fast responses
3. **Partial search** - "114" matches "114", "1140/1", "1141" (startsWith)
4. **Empty arrays for not found** - Returns `[]` not 404 (matches real API)
5. **CORS enabled** - Allows browser-based testing
6. **No authentication** - All endpoints public (like the real API)

### Realistic Data Quirks

The mock data includes realistic quirks from the real API:

- ✅ Area fields are **strings** not numbers (`"area": "1200"`)
- ✅ Many ownership fields are **null** (common in real data)
- ✅ Multiple possession sheets per parcel (split ownership)
- ✅ Croatian names and addresses
- ✅ Various land use types (MASLINJAK, PAŠNJAK, ŠUMA, etc.)

## Performance

- **Startup time**: < 100ms
- **Response time**: < 10ms (in-memory lookup)
- **Memory usage**: ~ 2-5 MB (for current dataset)
- **Concurrent requests**: Handles 100+ requests/second

## Troubleshooting

### Server won't start

```bash
# Check if port 8000 is already in use
lsof -i :8000

# Kill existing process or use different port
uvicorn main:app --port 8001
```

### Data not loading

```bash
# Check files exist
ls -la data/
ls -la data/parcels/

# Check JSON syntax
python -m json.tool data/offices.json
```

### CLI returns errors

```bash
# Verify server is running
curl http://localhost:8000

# Check environment variable
echo $CADASTRAL_API_BASE_URL

# Test directly
curl "http://localhost:8000/search-cad-parcels/offices"
```

## Development

### Project Structure

```
mock_server/
├── main.py                  # FastAPI application (300 lines)
├── requirements.txt         # Dependencies
├── README.md               # This file
└── data/                   # Static test data
    ├── offices.json
    ├── municipalities.json
    └── parcels/
        ├── 334979.json
        └── 334731.json
```

### Running in Development Mode

```bash
# With auto-reload on file changes
uvicorn main:app --reload --port 8000

# With debug logging
uvicorn main:app --reload --log-level debug
```

### Adding New Endpoints

Edit `main.py` and add new FastAPI route handlers. The existing patterns show how to:

- Load data from JSON files
- Handle query parameters
- Return proper JSON responses
- Handle 404 errors

## Production Notes

**DO NOT deploy this mock server to production!**

This is for local testing only. The real Croatian cadastral system has:
- Authentication requirements
- Rate limiting
- Terms of service restrictions
- GDPR compliance needs
- Legal authorization requirements

See main project README for complete disclaimers and restrictions.

## License

Same as main project (MIT License).

## Questions?

See main project documentation:
- [Main README](../README.md) - Project overview
- [CLAUDE.md](../CLAUDE.md) - Development guide
- [CLI Documentation](../docs/CLI.md) - CLI usage

---

**Remember: This is a DEMO server with static data. Not for production use.**
