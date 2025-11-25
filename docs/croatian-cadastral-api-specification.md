# Croatian Cadastral System API Specification

## Overview
The Croatian cadastral system (Uređena zemlja) provides public APIs for accessing parcel information, ownership data, and possession sheets (Posjedovni list). The system is accessible at `https://oss.uredjenazemlja.hr/oss/public`.

## Base Information
- **Base URL:** `https://oss.uredjenazemlja.hr/oss/public`
- **Authentication:** None required (public APIs)
- **Rate Limiting:** Recommended 0.5-1 second between requests
- **Response Format:** JSON

## Required Headers
```
Accept: application/json, text/plain, */*
User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15
```

## API Endpoints

### 1. Municipality Search
**Purpose:** Get municipality registration numbers for parcel searches

**Endpoint:** `GET /search-cad-parcels/municipalities`

**Status:** ✅ **WORKING**

**Parameters:**
- `search` (string, optional): Municipality name or registration code
- `officeId` (string, optional): Filter by cadastral office ID (institutionId)
- `departmentId` (string, optional): Filter by department ID

**Example Requests:**
```
# Search by name
GET /oss/public/search-cad-parcels/municipalities?search=SAVAR

# Search by code
GET /oss/public/search-cad-parcels/municipalities?search=334979

# Filter by cadastral office (returns 162 municipalities for Zadar office)
GET /oss/public/search-cad-parcels/municipalities?officeId=114

# Filter by office and department (returns 66 municipalities)
GET /oss/public/search-cad-parcels/municipalities?officeId=114&departmentId=116

# Combine search with filters
GET /oss/public/search-cad-parcels/municipalities?search=SAVAR&officeId=114
```

**Actual Response:**
```json
[
  {
    "key1": "2387",
    "value1": "334979 SAVAR",
    "key2": "334979",
    "value2": "114",
    "value3": "116",
    "displayValue1": "334979 SAVAR, ZADAR, PUK ZADAR"
  }
]
```

**Key Fields:**
- `key1` (string): Municipality internal ID (cadMunicipalityId) - used in some responses
- `value1` (string): Municipality code + name combined
- `key2` (string): **Municipality registration number** - Use this for parcel searches
- `value2` (string): Cadastral office ID (institutionId) - matches `officeId` parameter
- `value3` (string): Department ID - matches `departmentId` parameter
- `displayValue1` (string): Full display name with court information

**Known Municipality Codes:**
- SAVAR: `334979` (Court: Zadar, ID: 114)
- LUKA: `334731` (Court: Zadar, ID: 114)

**Important Notes:**
- All parameters are optional - can be used independently or combined
- Search works with both municipality name and registration code
- Partial name searches return multiple results (e.g., "LUKA" returns 16 municipalities)
- Use `key2` value as `municipalityRegNum` parameter for parcel searches
- Filtering by `officeId=114` returns 162 municipalities in Zadar cadastral office
- Filtering by `officeId=114&departmentId=116` narrows to 66 municipalities in that department
- The `value2` and `value3` fields in responses correspond to the filter parameters
- The old `/search-municipalities` endpoint returns 404 - do not use

### 2. Cadastral Offices List
**Purpose:** List all cadastral offices (Područni uredi za katastar) in Croatia

**Endpoint:** `GET /search-cad-parcels/offices`

**Status:** ✅ **WORKING**

**Parameters:** None

**Example Request:**
```
GET /oss/public/search-cad-parcels/offices
```

**Actual Response:**
```json
[
  {
    "id": "35",
    "name": "PODRUČNI URED ZA KATASTAR KRAPINA"
  },
  {
    "id": "114",
    "name": "PODRUČNI URED ZA KATASTAR ZADAR"
  },
  {
    "id": "130",
    "name": "PODRUČNI URED ZA KATASTAR ŠIBENIK"
  }
  // ... 21 offices total
]
```

**Response Fields:**
- `id` (string): Cadastral office ID - matches `institutionId` from other endpoints
- `name` (string): Full name of cadastral office

**Important Notes:**
- Returns all 21 cadastral offices in Croatia
- The `id` field corresponds to:
  - `value2` in municipality search responses (Institution/Court ID)
  - `institutionId` in parcel information responses
- Useful for mapping office IDs to human-readable names
- No pagination - returns complete list

**Known Office IDs:**
- Zadar: `114`
- Šibenik: `130`
- Krapina: `35`

### 3. Municipality GIS Data Download (ATOM Feed)
**Purpose:** Download GIS spatial data (parcel boundaries) for a municipality

**Endpoint:** `GET /atom/ko-{municipalityRegNum}.zip`

**Status:** ✅ **WORKING - NO AUTHENTICATION REQUIRED**

**URL Pattern:**
```
https://oss.uredjenazemlja.hr/oss/public/atom/ko-{municipalityRegNum}.zip
```

**Example URLs:**
```
# SAVAR municipality (334979) - 224 KB
https://oss.uredjenazemlja.hr/oss/public/atom/ko-334979.zip

# LUKA municipality (334731)
https://oss.uredjenazemlja.hr/oss/public/atom/ko-334731.zip
```

**Response:**
- ZIP file containing GML files with cadastral data
- File contents (example from SAVAR):
  - `katastarske_cestice.gml` - Cadastral parcels (~1.4 MB)
  - `katastarske_opcine.gml` - Cadastral municipalities
  - `nacini_uporabe_zemljista.gml` - Land use types
  - `nacini_uporabe_zgrada.gml` - Building use types

**Important Notes:**
- ✅ **No authentication required** - direct download works
- This is an INSPIRE directive-compliant ATOM feed service
- Part of European spatial data infrastructure requirements
- Each municipality has its own ZIP file
- Files range from ~200KB to several MB depending on municipality size
- GML files use INSPIRE-compliant schemas
- The `ko-` prefix stands for "katastarska općina" (cadastral municipality)
- Suitable for automated bulk downloads

**Programmatic Access:**
```python
import urllib.request

# Direct download - no authentication needed
url = f"https://oss.uredjenazemlja.hr/oss/public/atom/ko-{municipality_code}.zip"
urllib.request.urlretrieve(url, f"municipality_{municipality_code}.zip")

# Or with requests/httpx
import httpx
response = httpx.get(url)
with open(f"municipality_{municipality_code}.zip", "wb") as f:
    f.write(response.content)
```

### 4. Parcel Number Search
**Purpose:** Search for parcel IDs using parcel number and municipality

**Endpoint:** `GET /search-cad-parcels/parcel-numbers`

**Parameters:**
- `search` (string): Parcel number (e.g., "35/1", "1072/12", "114")
- `municipalityRegNum` (string): Municipality registration number

**Example Request:**
```
GET /oss/public/search-cad-parcels/parcel-numbers?search=103/2&municipalityRegNum=334979
```

**Actual Response:**
```json
[
  {
    "key1": "6564817",
    "value1": "103/2",
    "key2": null,
    "value2": null,
    "value3": null,
    "displayValue1": null
  }
]
```

**Key Fields:**
- `key1` (string): **Parcel ID** - Required for detailed info requests
- `value1` (string): Parcel number (confirmed)
- `key2` (null): Purpose unknown, always null in tested responses
- `value2` (null): Purpose unknown, always null in tested responses
- `value3` (null): Purpose unknown, always null in tested responses
- `displayValue1` (null): Purpose unknown, always null in tested responses

**Important Notes:**
- Response structure differs from initial documentation
- Only `key1` (parcelId) and `value1` (parcelNumber) contain data
- No `municipalityName` or `address` fields in search response
- Partial parcel number searches return multiple results (e.g., "114" returns 114, 1140/1, 1140/2, 1141, etc.)

### 5. Parcel Detailed Information
**Purpose:** Get complete parcel information including ownership data

**Endpoint:** `GET /cad/parcel-info`

**Parameters:**
- `parcelId` (string): Parcel ID obtained from parcel search

**Example Request:**
```
GET /oss/public/cad/parcel-info?parcelId=6564817
```

**Actual Response Structure (Complete):**
```json
{
  "parcelId": 6564817,
  "parcelNumber": "103/2",
  "cadMunicipalityId": 2387,
  "cadMunicipalityRegNum": "334979",
  "cadMunicipalityName": "SAVAR",
  "institutionId": 114,
  "address": "POLJE",
  "area": "1200",
  "buildingRemark": 0,
  "detailSheetNumber": "4",
  "hasBuildingRight": false,
  "parcelParts": [
    {
      "parcelPartId": 74357391,
      "name": "MASLINJAK",
      "area": "1200",
      "possessionSheetId": 14823725,
      "possessionSheetNumber": "657",
      "building": false
    }
  ],
  "possessionSheets": [
    {
      "possessionSheetId": 14823725,
      "possessionSheetNumber": "657",
      "cadMunicipalityId": 2387,
      "possessors": [
        {
          "name": "ŠARUNIĆ AUGUSTIN, BOŽO",
          "address": "PUT SKALICA 1, SPLIT"
        },
        {
          "name": "ŠARUNIĆ ANTE, P. BOŽE",
          "address": "SAVAR"
        }
      ]
    }
  ],
  "lrUnit": {
    "lrUnitId": 13122441,
    "lrUnitNumber": "657",
    "mainBookId": 21277,
    "status": "0",
    "verificated": false,
    "condominiums": false
  },
  "isAdditionalDataSet": false,
  "legalRegime": false,
  "graphic": true,
  "alphaNumeric": true,
  "status": 0,
  "resourceCode": 0,
  "isHarmonized": true
}
```

**Complete Field Documentation:**

#### Root Level Fields:
- `parcelId` (integer): Unique parcel identifier
- `parcelNumber` (string): Cadastral parcel number
- `cadMunicipalityId` (integer): Municipality internal ID
- `cadMunicipalityRegNum` (string): Municipality registration number
- `cadMunicipalityName` (string): Municipality name
- `institutionId` (integer): Cadastral institution/office ID
- `address` (string): Parcel location/address
- `area` (string): Total parcel area in m² (note: string, not number)
- `buildingRemark` (integer): Building remark code
- `detailSheetNumber` (string): Detail sheet number
- `hasBuildingRight` (boolean): Whether building is permitted
- `isAdditionalDataSet` (boolean): Additional data availability flag
- `legalRegime` (boolean): Legal regime indicator
- `graphic` (boolean): Graphical data available
- `alphaNumeric` (boolean): Alphanumeric data available
- `status` (integer): Parcel status code
- `resourceCode` (integer): Resource code
- `isHarmonized` (boolean): Data harmonization status

### 4. Land Registry Main Books Search
**Purpose:** Search for land registry main books (Zemljišne knjige - glavne knjige)

**Endpoint:** `GET /search-lr-parcels/main-books`

**Status:** ✅ **WORKING**

**Parameters:**
- `search` (string, optional): Search term for filtering results
- `officeId` (string, optional): Filter by cadastral office ID
- `institutionName` (string, optional): Filter by institution name

**Example Requests:**
```
# Get all main books (returns thousands of results)
GET /oss/public/search-lr-parcels/main-books?search=&officeId=&institutionName=

# Filter by cadastral office
GET /oss/public/search-lr-parcels/main-books?search=&officeId=225&institutionName=

# Search by name
GET /oss/public/search-lr-parcels/main-books?search=ZAPREŠIĆ&officeId=&institutionName=
```

**Actual Response:**
```json
[
  {
    "key1": "21780",
    "value1": "ZAPREŠIĆ",
    "key2": "291",
    "value2": "ZAPREŠIĆ",
    "value3": null,
    "displayValue1": "ZAPREŠIĆ, ZAPREŠIĆ"
  },
  {
    "key1": "21781",
    "value1": "PLUSKA",
    "key2": "291",
    "value2": "ZAPREŠIĆ",
    "value3": null,
    "displayValue1": "PLUSKA, ZAPREŠIĆ"
  },
  {
    "key1": "21812",
    "value1": "DONJA KUPČINA",
    "key2": "225",
    "value2": "JASTREBARSKO",
    "value3": null,
    "displayValue1": "DONJA KUPČINA, JASTREBARSKO"
  }
]
```

**Response Fields:**
- `key1` (string): Main book ID (primary identifier)
- `value1` (string): Main book name/location
- `key2` (string): Court/Institution ID
- `value2` (string): Court/Institution name
- `value3` (null): Reserved field, always null
- `displayValue1` (string): Full display name "{value1}, {value2}"

**Important Notes:**
- Returns land registry main books, not cadastral municipalities
- The `key2` field represents the court jurisdiction ID
- Empty search parameters return complete list (very large response)
- Useful for finding which land registry court covers a specific area
- The main book ID (`key1`) is referenced in parcel info responses as `lrUnit.mainBookId`
- Multiple main books can exist under the same court (e.g., ZAPREŠIĆ court has ZAPREŠIĆ, PLUSKA, LADUČ, etc.)

**Relationship to Parcel Data:**
- Main books are part of the land registry system (Zemljišne knjige)
- Each parcel's `lrUnit.mainBookId` references a main book from this endpoint
- Different from cadastral municipalities - main books are for legal ownership records
- Court ID (`key2`) may differ from cadastral office ID (`institutionId`)

**Known Court IDs:**
- ZAPREŠIĆ: `291`
- JASTREBARSKO: `225`
- ZADAR: `284` (land registry court, different from cadastral office ID 114)
- OSIJEK: `247`
- SISAK: `265`

### 5. Land Registry Books of Deposit Companies (DC) Search
**Purpose:** Search for land registry books of deposit companies (Knjige zemlje u vlasništvu društva s ograničenom odgovornošću - "books-of-dc")

**Endpoint:** `GET /search-lr-parcels/books-of-dc`

**Status:** ✅ **WORKING**

**Parameters:**
- `search` (string, optional): Search term for filtering results
- `officeId` (string, optional): Filter by cadastral office ID
- `institutionName` (string, optional): Filter by institution name

**Example Requests:**
```
# Get all books of DC (returns thousands of results)
GET /oss/public/search-lr-parcels/books-of-dc?search=&officeId=&institutionName=

# Filter by land registry office
GET /oss/public/search-lr-parcels/books-of-dc?search=&officeId=201&institutionName=

# Search by name
GET /oss/public/search-lr-parcels/books-of-dc?search=BELI+MANASTIR&officeId=&institutionName=
```

**Actual Response:**
```json
[
  {
    "key1": "30268",
    "value1": "BELI MANASTIR",
    "key2": "201",
    "value2": "Zemljišnoknjižni odjel Beli Manastir",
    "value3": null,
    "displayValue1": "BELI MANASTIR, Zemljišnoknjižni odjel Beli Manastir"
  },
  {
    "key1": "30221",
    "value1": "ČEMINAC",
    "key2": "201",
    "value2": "Zemljišnoknjižni odjel Beli Manastir",
    "value3": null,
    "displayValue1": "ČEMINAC, Zemljišnoknjižni odjel Beli Manastir"
  },
  {
    "key1": "30327",
    "value1": "BUJE",
    "key2": "204",
    "value2": "Zemljišnoknjižni odjel Buje - Buie",
    "value3": null,
    "displayValue1": "BUJE, Zemljišnoknjižni odjel Buje - Buie"
  }
]
```

**Response Fields:**
- `key1` (string): Book of DC ID (primary identifier)
- `value1` (string): Book location/name
- `key2` (string): Land registry office ID
- `value2` (string): Land registry office name (full name with "Zemljišnoknjižni odjel" prefix)
- `value3` (null): Reserved field, always null
- `displayValue1` (string): Full display name "{value1}, {value2}"

**Important Notes:**
- Returns land registry books specifically for deposit companies (društva s ograničenom odgovornošću)
- Different from main books (`/main-books`) - these are specialized books for corporate/company ownership
- The `key2` field represents the land registry court/office ID
- Empty search parameters return complete list (very large response - thousands of entries)
- The `value2` field uses full names like "Zemljišnoknjižni odjel Beli Manastir" (Land Registry Department)
- Multiple books can exist under the same land registry office

**Relationship to Other Endpoints:**
- Related to `/search-lr-parcels/main-books` but for corporate/company ownership records
- The office IDs (`key2`) match those from main books endpoint
- Part of the land registry (zemljišne knjige) system, not the cadastral (katastar) system

**Known Land Registry Office IDs:**
- Beli Manastir: `201`
- Buje - Buie: `204`
- Crikvenica: `206`
- Daruvar: `209`
- Gospić: `220`
- Imotski: `222`
- Ivanić Grad: `224`
- Karlovac: `226`
- Knin: `289`
- Korčula: `229`
- Krapina: `230`
- Krk: `232`
- Labin: `234`
- Mali Lošinj: `237`
- Našice: `239`
- Osijek: `247`
- Požega: `256`
- Rab: `259`
- Rovinj - Rovigno: `261`
- Sesvete: `263`
- Sinj: `264`
- Slatina: `266`
- Split: `269`
- Supetar: `271`
- Šibenik: `273`

### 6. Land Registry File Status
**Purpose:** Get status information for a specific land registry file (spis)

**Endpoint:** `POST /lr/file-status`

**Status:** ✅ **WORKING**

**Method:** POST (requires JSON request body)

**Request Body:**
```json
{
  "fileId": 44682477
}
```

**Parameters:**
- `fileId` (integer, required): The land registry file ID

**Example Request:**
```bash
POST /oss/public/lr/file-status
Content-Type: application/json

{
  "fileId": 44682477
}
```

**Actual Response:**
```json
{
  "fileId": 44682477,
  "lrFileNumber": "Z-27985/2025",
  "institution": {
    "institutionId": 284,
    "institutionName": "Zemljišnoknjižni odjel Zadar"
  },
  "statusDescription": "AUTOMATSKA OBRADA PODATAKA",
  "applicationContent": "Pojedinačno prevođenje u BZP Automatsko prevođenje u BZP",
  "infoDate": "2025-11-10T18:42:42.000+01:00",
  "receivingDate": "2025-09-01T17:00:00.000+02:00",
  "solvingDate": "2025-09-01",
  "executionDate": "2025-09-01T17:00:26.000+02:00"
}
```

**Response Fields:**
- `fileId` (integer): Land registry file ID (matches request)
- `lrFileNumber` (string): File reference number (e.g., "Z-27985/2025")
- `institution` (object): Land registry office information
  - `institutionId` (integer): Office ID (matches those from `/search-lr-parcels` endpoints)
  - `institutionName` (string): Full office name
- `statusDescription` (string): Current status of the file (e.g., "AUTOMATSKA OBRADA PODATAKA")
- `applicationContent` (string): Description of the application/request content
- `infoDate` (string, ISO 8601): Last information update timestamp
- `receivingDate` (string, ISO 8601): Date when file was received
- `solvingDate` (string, ISO date): Date when file was resolved/processed
- `executionDate` (string, ISO 8601): Date and time when action was executed

**Important Notes:**
- This is a POST endpoint, not GET
- Requires Content-Type: application/json header
- Returns information about land registry administrative files (spis)
- File IDs are likely obtained from other land registry endpoints
- Institution ID (284) corresponds to "Zemljišnoknjižni odjel Zadar" (Zadar Land Registry Office)
- Timestamps include timezone information (e.g., +01:00 for CET, +02:00 for CEST)
- Status descriptions are in Croatian

**Common Status Values:**
- `AUTOMATSKA OBRADA PODATAKA` - Automatic data processing
- (Other statuses to be documented as discovered)

**Relationship to Other Endpoints:**
- The `institutionId` (284) matches land registry office IDs from:
  - `/search-lr-parcels/main-books`
  - `/search-lr-parcels/books-of-dc`
- Part of the land registry (zemljišne knjige) administrative system
- Tracks processing status of land registry applications and changes

**Use Cases:**
- Track status of land registry applications
- Monitor processing of ownership transfer requests
- Check execution dates for completed land registry actions
- Audit land registry file processing

### 7. Possession Sheet Search
**Purpose:** Search for possession sheet numbers

**Endpoint:** `GET /search-cad-parcels/possession-sheet-numbers`

**Parameters:**

- `search` (string): Possession sheet number
- `municipalityRegNum` (string): Municipality registration number

**Example Request:**
```
GET /oss/public/search-cad-parcels/possession-sheet-numbers?search=12345&municipalityRegNum=334979
```

### 8. Land Registry Unit Detailed Information

**Purpose:** Get complete land registry unit (zemljišnoknjižni uložak) with ownership sheets

**Endpoint:** `GET /lr/lr-unit-data`

**Status:** ✅ **WORKING**

**Parameters:**

- `lrUnitNumber` (string): Land registry unit number (e.g., "769")
- `mainBookId` (integer): Main book ID (e.g., 21277)

**Example Request:**
```
GET /oss/public/lr/lr-unit-data?lrUnitNumber=13998&mainBookId=30783
```

**Response Structure:**
The response contains detailed information organized into three "sheets":

- **Sheet A (possessionSheetA1)**: List of all parcels in the unit
- **Sheet B (ownershipSheetB)**: Ownership information with shares
- **Sheet C (encumbranceSheetC)**: Encumbrances (mortgages, liens, easements)

**Example Response (Condominium Unit):**
```json
{
  "lrUnitId": 6644000,
  "lrUnitNumber": "13998",
  "mainBookId": 30783,
  "mainBookName": "SPLIT",
  "institutionId": 269,
  "institutionName": "Zemljišnoknjižni odjel Split",
  "status": "0",
  "statusName": "Aktivan",
  "condominiums": false,
  "lrUnitTypeId": 3,
  "lrUnitTypeName": "ETAŽNO VLASNIŠTVO S ODREĐENIM OMJERIMA",
  "lastDiaryNumber": "Z-47245/2025",
  "ownershipSheetB": {
    "lrUnitShares": [...]
  },
  "possessionSheetA1": {
    "cadParcels": [...]
  },
  "encumbranceSheetC": {
    "lrEntryGroups": [...]
  }
}
```

#### Ownership Sheet B - LRShare Object

Each share in `ownershipSheetB.lrUnitShares` represents an ownership portion:

```json
{
  "lrUnitShareId": 32618214,
  "description": "16. Suvlasnički dio: 61/4651 ETAŽNO VLASNIŠTVO (E-16)",
  "condominiumNumber": "E-16",
  "condominiums": ["STAN na PR (prizemlju), označen br. 1, površine 61,27 m2..."],
  "lrOwners": [...],
  "subSharesAndEntries": [...],
  "status": 0,
  "orderNumber": "16"
}
```

**Standard Fields:**

- `lrUnitShareId` (integer): Unique share identifier
- `description` (string): Full share description with fraction
- `lrOwners` (array): Direct owners of this share (see Party object below)
- `subSharesAndEntries` (array): Nested co-ownership entries (for shared apartments)
- `status` (integer): Status code (0 = active)
- `orderNumber` (string): Order number in the ownership sheet

**Condominium-specific Fields:**

- `condominiumNumber` (string, optional): Apartment identifier (e.g., "E-16", "E-35")
- `condominiums` (array of strings, optional): Detailed apartment descriptions including:
  - Floor level (e.g., "na III. (trećem) katu")
  - Unit number (e.g., "označen br. 13")
  - Area (e.g., "površine 59,08 m2")
  - Room composition

**Example Apartment Description:**
```
"STAN na III. (trećem) katu, označen br. 13, površine 59,08 m2, koji se sastoji od dvije sobe, kuhinje, kupaonice, hodnika i lođe, s pripadajućom drvarnicom."
```

#### Nested Co-ownership (subSharesAndEntries)

For condominiums with shared apartments (e.g., married couples), ownership is nested:

```json
{
  "description": "22.3. Suvlasnički dio etaže: 1/2",
  "lrOwners": [
    {
      "lrOwnerId": 41225328,
      "name": "Co-Owner A",
      "address": "Address A",
      "taxNumber": "11111111111"
    }
  ],
  "subSharesAndEntries": [],
  "status": 0,
  "orderNumber": "3"
}
```

**Note:** When a share has no direct `lrOwners` but has `subSharesAndEntries`, the actual owners are found in the nested entries.

#### Party (lrOwners) Object

```json
{
  "lrOwnerId": 43484805,
  "name": "Test Owner",
  "address": "Test Address",
  "taxNumber": "12345678901",
  "lrEntry": {
    "description": "UKNJIŽBA, PRAVO VLASNIŠTVA",
    "orderNumber": "16.4"
  }
}
```

**Fields:**

- `lrOwnerId` (integer): Unique owner identifier
- `name` (string): Owner's full name
- `address` (string, optional): Owner's address
- `taxNumber` (string, optional): OIB (Croatian tax identification number)
- `lrEntry` (object, optional): Registration entry details

#### Detecting Condominiums

**⚠️ Important:** The `condominiums` boolean field at the unit level is **unreliable** (often `false` for actual condominiums).

**Reliable detection method:**
```python
def is_condominium(lr_unit):
    return "ETAŽN" in lr_unit.get("lrUnitTypeName", "").upper()
```

**Condominium unit types:**

- `ETAŽNO VLASNIŠTVO S ODREĐENIM OMJERIMA` - Condominium with defined shares
- `ETAŽNI` - Simple condominium

## Data Structure Details

### Nested Object Structures

#### ParcelPart Object
Describes land use classification and area for each part of the parcel:

```json
{
  "parcelPartId": 74357391,
  "name": "MASLINJAK",
  "area": "1200",
  "possessionSheetId": 14823725,
  "possessionSheetNumber": "657",
  "lastChangeLogNumber": "22/2025",
  "building": false
}
```

**Fields:**
- `parcelPartId` (integer): Unique identifier for this parcel part
- `name` (string): Land use type (see common types below)
- `area` (string): Area in square meters (note: string type)
- `possessionSheetId` (integer): Link to possession sheet
- `possessionSheetNumber` (string): Possession sheet reference number
- `lastChangeLogNumber` (string, optional): Last change log entry
- `building` (boolean): Whether this part contains buildings

**Common Land Use Types:**
- `PAŠNJAK` - Pasture
- `ORANICA` - Arable land
- `ŠUMA` - Forest
- `VOĆNJAK` - Orchard
- `VINOGRAD` - Vineyard
- `MASLINJAK` - Olive grove

#### PossessionSheet Object
Contains ownership information for the parcel:

```json
{
  "possessionSheetId": 14823725,
  "possessionSheetNumber": "657",
  "cadMunicipalityId": 2387,
  "cadMunicipalityRegNum": "334979",
  "cadMunicipalityName": "SAVAR",
  "possessionSheetTypeId": 1,
  "possessors": [...]
}
```

**Fields:**
- `possessionSheetId` (integer): Unique identifier
- `possessionSheetNumber` (string): Sheet reference number
- `cadMunicipalityId` (integer): Municipality ID
- `cadMunicipalityRegNum` (string, optional): Municipality registration number
- `cadMunicipalityName` (string, optional): Municipality name
- `possessionSheetTypeId` (integer, optional): Type of possession sheet
- `possessors` (array): List of owners (see Possessor object)

#### Possessor Object
Individual owner information:

```json
{
  "name": "ŠARUNIĆ AUGUSTIN, BOŽO",
  "ownership": "1/1",
  "address": "PUT SKALICA 1, SPLIT"
}
```

**Fields:**

- `name` (string): Owner's full name
- `ownership` (string, **optional**): Ownership fraction (e.g., "1/1", "1/4")
  - ⚠️ **Note:** This field is frequently missing in API responses
  - When present, format is always "numerator/denominator"
- `address` (string): Owner's address

**Condominium-specific fields** (appear for possessors in condominium units):

- `condominiumShareNumber` (string, optional): Apartment/unit number in the condominium (e.g., "35", "0" for common areas)
- `condominiumShareOwnership` (string, optional): Share of common areas (e.g., "61/4651")

**Example condominium possessor:**

```json
{
  "name": "GRAD SPLIT",
  "ownership": "1/1",
  "address": "SPLIT, OBALA KNEZA BRANIMIRA 17",
  "condominiumShareNumber": "0",
  "condominiumShareOwnership": "4531/4651"
}
```

**Important:** Many parcels have possessors without the `ownership` field. Handle this as optional in code.

#### LandRegistryUnit (lrUnit) Object
Land registry book information:

```json
{
  "lrUnitId": 13122441,
  "lrUnitNumber": "657",
  "mainBookId": 21277,
  "mainBookName": "SAVAR",
  "cadastreMunicipalityId": 2387,
  "institutionId": 284,
  "institutionName": "Zemljišnoknjižni odjel Zadar",
  "status": "0",
  "statusName": "Aktivan",
  "verificated": false,
  "condominiums": false,
  "lrUnitTypeId": 1,
  "lrUnitTypeName": "VLASNIČKI"
}
```

**Fields:**
- `lrUnitId` (integer): Unique land registry unit ID
- `lrUnitNumber` (string): Registry unit number
- `mainBookId` (integer): Main book ID
- `mainBookName` (string, optional): Main book name
- `cadastreMunicipalityId` (integer, optional): Municipality ID
- `institutionId` (integer, optional): Land registry institution ID
- `institutionName` (string, optional): Institution name (e.g., "Zemljišnoknjižni odjel Zadar")
- `status` (string): Status code
- `statusName` (string, optional): Status name (e.g., "Aktivan")
- `verificated` (boolean): Verification status
- `condominiums` (boolean): Condominium flag (⚠️ **unreliable** - often `false` for actual condominiums)
- `lrUnitTypeId` (integer, optional): Type ID
- `lrUnitTypeName` (string, optional): Type name (see Unit Types below)

**Unit Types (lrUnitTypeName):**

- `VLASNIČKI` - Standard ownership (single owner or co-owners)
- `ETAŽNO VLASNIŠTVO S ODREĐENIM OMJERIMA` - Condominium with defined shares (apartments)
- `ETAŽNI` - Condominium (etažno vlasništvo)

**⚠️ Important:** To detect condominiums, check `lrUnitTypeName` containing "ETAŽN" rather than the `condominiums` boolean flag, which is unreliable.

**Note:** Many fields in lrUnit are optional and only appear in certain contexts.

#### ParcelLink Object
Links to related or historical parcels:

```json
{
  "parcelId": 5775798,
  "parcelNumber": "45",
  "address": "VRT",
  "area": "981",
  "lrUnit": {...},
  "parcelParts": []
}
```

**Fields:**
- `parcelId` (integer): Linked parcel ID
- `parcelNumber` (string): Linked parcel number
- `address` (string): Linked parcel address
- `area` (string): Linked parcel area
- `lrUnit` (object): Land registry unit information
- `parcelParts` (array): Parcel parts (usually empty)

**Arrays:**
- `parcelLinks` (array, optional): List of linked parcels
- `lrUnitsFromParcelLinks` (array, optional): Extended lrUnit information from linked parcels

## Usage Workflow

### Complete Parcel Information Retrieval
1. **Get Municipality Code** (if not known):
   ```
   GET /search-cad-parcels/municipalities?search=MUNICIPALITYNAME
   ```
   Extract `key2` from response as `municipalityRegNum`

2. **Search for Parcel ID**:
   ```
   GET /search-cad-parcels/parcel-numbers?search=PARCELNUMBER&municipalityRegNum=MUNICIPALITYCODE
   ```
   Extract `key1` from response as `parcelId`

3. **Get Detailed Information**:
   ```
   GET /cad/parcel-info?parcelId=PARCELID
   ```

### Example Python Implementation
```python
import requests

class CadastralAPI:
    def __init__(self):
        self.headers = {
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15'
        }
        self.base_url = 'https://oss.uredjenazemlja.hr/oss/public'

    def search_municipality(self, municipality_name_or_code):
        url = f'{self.base_url}/search-cad-parcels/municipalities'
        params = {'search': municipality_name_or_code}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return data[0].get('key2') if data else None  # Return municipality reg number
        return None

    def search_parcel(self, parcel_number, municipality_code):
        url = f'{self.base_url}/search-cad-parcels/parcel-numbers'
        params = {
            'search': str(parcel_number),
            'municipalityRegNum': municipality_code
        }
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return data[0].get('key1') if data else None
        return None

    def get_parcel_info(self, parcel_id):
        url = f'{self.base_url}/cad/parcel-info'
        params = {'parcelId': parcel_id}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json()
        return None
```

## Error Handling

### Common HTTP Status Codes
- `200` - Success
- `404` - Parcel/Municipality not found
- `500` - Server error
- `503` - Service temporarily unavailable

### Best Practices
1. **Rate Limiting**: Wait 0.5-1 seconds between requests
2. **Timeout**: Set request timeout to 10 seconds
3. **Retry Logic**: Implement retry for 5xx errors
4. **Data Validation**: Always check if response data exists before accessing
5. **Error Logging**: Log failed requests with parcel numbers for debugging

## Map Integration

### Share URL Format
Parcels can be viewed on the interactive map using:
```
https://oss.uredjenazemlja.hr/map?cad_parcel_id=PARCELID
```

### Coordinate System
- **EPSG**: 3765 (HTRS96 / Croatia TM)
- **Units**: Meters
- **Coverage**: Croatia

## Related Services

### WFS INSPIRE Service
- **URL**: `https://oss.uredjenazemlja.hr/wfs`
- **Purpose**: Download cadastral geometries
- **Format**: GML

### ATOM Download Service
- **URL**: `https://catalog.uredjenazemlja.hr/katalogpodataka/atom-usluga-preuzimanja-dkp-a`
- **Purpose**: Bulk download of cadastral data by municipality
- **Format**: ZIP files containing GML data

## Notes

### Data Accuracy
- Ownership information is official and legally binding
- Data is updated regularly by cadastral offices
- Some older parcels may have incomplete ownership records

### Privacy Considerations
- All accessed data is public information
- No authentication required as per Croatian law
- Ownership information is publicly available

### Performance Considerations
- Complex parcels (>100 owners) may take longer to process
- Large municipalities may have slower response times
- Consider caching parcel IDs for repeated access

## Testing Data

### Verified Parcels in SAVAR Municipality (Code: 334979)
The following parcels have been tested and verified (Court: Zadar):

1. **Parcel 103/2** (ID: 6564817)
   - Address: POLJE
   - Area: 1,200 m²
   - Land use: MASLINJAK (Olive grove)
   - Possession sheet: 657
   - Owners: 2 (no ownership fractions listed)

2. **Parcel 103/3** (ID: 6564815)
   - Address: POLJE
   - Area: 439 m²
   - Land use: PAŠNJAK (Pasture)
   - Possession sheet: 657
   - Owners: 2 (no ownership fractions listed)

3. **Parcel 114** (ID: 6564826)
   - Address: POLJE
   - Area: 2,401 m²
   - Land use: PAŠNJAK (Pasture)
   - Possession sheet: 657
   - Owners: 2 (no ownership fractions listed)

4. **Parcel 45** (ID: 6564715)
   - Address: POLJE
   - Area: 981 m²
   - Land use: MASLINJAK (Olive grove) - split between 2 sheets
   - Possession sheets: 138, 43
   - Owners: 2 (with ownership fractions: "1/1" each on separate sheets)
   - Has parcel links to historical records

5. **Parcel 396/1** (ID: 6565198)
   - Address: ILO
   - Area: 2,077 m²
   - Land use: ŠUMA (Forest)
   - Possession sheet: 645
   - Owners: 18 (no ownership fractions listed)
   - Example of complex multi-owner parcel

### Key Observations:
- **Municipality search working**: Use `/search-cad-parcels/municipalities` endpoint (the old `/search-municipalities` returns 404)
- **Ownership fractions are inconsistent**: Only some parcels include the `ownership` field
- **Multiple possession sheets**: A single parcel can have multiple possession sheets (e.g., parcel 45)
- **Parcel links**: Some parcels have `parcelLinks` array with historical/related parcel information
- **String vs Integer types**: `area` is always string, `parcelId` can be string or integer
- **Municipality search supports both name and code**: Can search by "SAVAR" or "334979"

---

*Document created: November 6, 2025*
*Last updated: November 7, 2025*
*Based on Croatian cadastral system exploration and implementation with live API testing*