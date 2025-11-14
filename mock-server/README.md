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

Test data is located in the `data/` directory:
- `municipalities.json` - Sample municipalities
- `offices.json` - Sample cadastral offices
- `parcels/` - Sample parcel data

## License

MIT
