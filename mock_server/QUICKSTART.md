# Quick Start Guide - Mock Cadastral API Server

## Start the Server

```bash
cd mock_server
python3 main.py
```

The server will start on http://localhost:8000

## Test the Server

### Check server status
```bash
curl http://localhost:8000
```

### Test all endpoints

**1. List Cadastral Offices**
```bash
curl "http://localhost:8000/search-cad-parcels/offices" | python3 -m json.tool
```

**2. Search Municipalities**
```bash
# By name
curl "http://localhost:8000/search-cad-parcels/municipalities?search=SAVAR" | python3 -m json.tool

# By office ID
curl "http://localhost:8000/search-cad-parcels/municipalities?officeId=114" | python3 -m json.tool
```

**3. Search for Parcels**
```bash
# Exact match
curl "http://localhost:8000/search-cad-parcels/parcel-numbers?search=103/2&municipalityRegNum=334979" | python3 -m json.tool

# Partial match (returns 114, 1140/1, 1141)
curl "http://localhost:8000/search-cad-parcels/parcel-numbers?search=114&municipalityRegNum=334979" | python3 -m json.tool
```

**4. Get Detailed Parcel Info**
```bash
curl "http://localhost:8000/cad/parcel-info?parcelId=6564817" | python3 -m json.tool
```

## Use with CLI Client

Update your `.env` file or set environment variable:

```bash
export CADASTRAL_API_BASE_URL=http://localhost:8000
```

Then use the CLI normally:

```bash
cadastral list-offices
cadastral search 103/2 -m SAVAR
cadastral get-parcel 103/2 -m 334979 --show-owners
```

## Test Data

### SAVAR (334979)
- 103/2 - Olive grove, 1200 m², 2 owners
- 45 - Pasture, 981 m², 2 sheets with 1/1 ownership
- 396/1 - Forest, 2077 m², 18 owners
- 114 - Arable land, 845 m², 2 owners with 1/2 each
- 1140/1 - Orchard, 1523 m², 3 owners with fractions
- Plus 5 more parcels

### LUKA (334731)
- 23 - Arable land with building, 756 m²
- 67/2 - Olive grove, 1423 m²
- 145 - Mixed use, 2789 m²
- Plus 4 more parcels

## API Documentation

Visit these URLs while the server is running:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Stop the Server

Press `CTRL+C` in the terminal where it's running, or:

```bash
pkill -f "python3 main.py"
```

## Troubleshooting

**Port already in use:**
```bash
# Check what's using port 8000
lsof -i :8000

# Kill it or use different port
uvicorn main:app --port 8001
```

**Missing dependencies:**
```bash
pip install fastapi uvicorn
```

**Data not loading:**
```bash
# Verify files exist
ls -la data/
ls -la data/parcels/
```
