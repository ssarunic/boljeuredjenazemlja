# Parcel Locator Specification: Parcel by Address and by Point

Research for two new lookups, `find_parcel_by_address` and `find_parcel_by_point`,
in the SDK, the CLI and the MCP server. Every endpoint below was probed on
2026-09-14; timings are single measurements from one client and will vary.
Nothing in this document is implemented yet.

## Scope Notice

This project is a demonstration. The defaults and the mock server stay the only
targets of the code; the services below belong to the Državna geodetska uprava
(DGU) and to Grad Zagreb, and whoever points the code at them must first verify
that they may (terms of use, data-protection law) and does so at their own risk.
Section 8 records what the terms say. House-number points and parcel numbers are
registry data, not personal data, but the parcel they lead to has possessors and
owners: keep captured responses out of the repository or redact them
(`scripts/redact_capture.py`).

## 1. Summary and Recommendation

Both lookups can be built on two open INSPIRE download services of the DGU plus,
for Zagreb, the city's ArcGIS server. No new dependency is needed.

| Step | Nationwide source | Latency seen | Zagreb source | Latency seen |
|---|---|---|---|---|
| address -> point, parcel number, k.o. name | INSPIRE Addresses WFS (`ad:AD.Address`) | 1.2-2.5 s | `KBR_kućni_broj` layer (gives k.o. MB directly) | 1.5-1.7 s |
| point -> k.o. registration number (MB) | INSPIRE Cadastral Zoning (`cp:CadastralZoning`, BBOX) | 0.4 s | not needed | |
| point -> parcel (number, OSS parcel id) | INSPIRE Cadastral Parcels WFS (`cp:CadastralParcel`, INTERSECTS) | 13.6-15 s | `KČ_DKP/MapServer/12` point query | 1-2 s |

Three facts make the design simple:

1. The INSPIRE parcel `localId` (`CP.6564817`), Zagreb's `OBJECTID_ZIS` (`41086563`)
   and the OSS public API's parcel id (`parcelId`/`key1`) are the same number. A
   point lookup therefore ends in `get_parcel_info(parcel_id)` without a
   parcel-number search.
2. The Addresses WFS is a flat feature type whose attributes include the parcel the
   house number stands on (`broj_cestice`, with the cadastre's `*` prefix for
   building parcels) and the cadastral municipality name. An address lookup needs
   no spatial query at all: address -> (k.o. name, parcel number) -> the existing
   `find_parcel` -> parcel id.
3. Cadastral municipality names are not unique (10 "Novo Selo", 5 "Sveti Petar"),
   but one 0.4 s BBOX request on `cp:CadastralZoning` at the address point returns
   the k.o. label `334979-SAVAR`, i.e. the registration number. Use it always; it is
   cheaper than reasoning about ambiguity.

Recommended shape:

- `find_parcel_by_address(text | street + house_number [+ settlement])`:
  Addresses WFS -> candidates -> zoning BBOX for the MB -> `find_parcel(number, MB)`.
  Falls back to `find_parcel_by_point` on the address point when `broj_cestice`
  is empty. Zagreb needs no special path here: the DGU layer covers it with the
  same points (Ilica 1 is 459271.67, 5074920.58 in both).
- `find_parcel_by_point(x, y, crs)`: Zagreb ArcGIS when the point lies in the city's
  service extent (1-2 s), otherwise the INSPIRE parcel WFS with a 60 s timeout, run
  off the event loop like `get_parcel_zoning`. A later optimisation is the local
  route: zoning BBOX -> MB -> the ATOM GML already cached by `GISCache` ->
  `point_in_polygon` over the k.o. (milliseconds after the first download).

Sources looked at and rejected: the OSS public JSON API has no address endpoint
(the web app's "Adresni registar" lives under `/private/...` routes and the
token-protected `OssWebServices` GeoServer; the token in the site's `env.js` is not
ours to use); the ISPU geoportal's `search-text` suggests addresses nationwide but
no anonymous endpoint that turns a hit into coordinates was found; `katastar.hr`
does not resolve; `geoportal.dgu.hr/api/search` answers 401.

## 2. Coordinate Reference System

All three services take and return EPSG:3765 (HTRS96/TM). Users and AI agents will
often have WGS84 (EPSG:4326). The datum shift between the two is null, so a
Transverse Mercator forward formula (GRS80, central meridian 16.5°, scale 0.9999,
false easting 500 000, false northing 0) with the standard series is exact to the
millimetre; a 30-line pure-Python implementation round-trips
(15.9765, 45.8132) -> (459315.80, 5074948.95) -> (15.9765, 45.8132) and puts the
DGU point of Ilica 1 at 45.81294 N, 15.97593 E. `pyproj` is not needed. Accept
`crs` as `EPSG:3765` (default) or `EPSG:4326` and reject others.

## 3. INSPIRE Addresses WFS (DGU)

```text
https://geoportal.dgu.hr/services/inspire/ad/wfs?service=WFS&version=2.0.0&request=GetCapabilities
```

GeoServer, WFS 2.0.0, one feature type `ad:AD.Address` (title "Adrese INSPIRE"),
1 682 273 features, `CountDefault` 1 000 000, paging, EPSG:3765 only, output
`application/json`, GML 3.2 and the usual GeoServer formats. `ows:Fees` and
`ows:AccessConstraints` are `NONE`. The type is not the INSPIRE AD application
schema but a flat national table (DescribeFeatureType):

| Attribute | Type | Example (Ilica 1, Zagreb) | Note |
|---|---|---|---|
| `inspire_id` | string | `HR.DGU.RPJ:KB.0022075271` | RPJ house-number id |
| `zgrada_id` | long | 2142892445 | building id (Zagreb's `ZG_ID` differs by one) |
| `kucni_broj` | string | `1`, `65A` | full house number |
| `broj` | int | 1 | numeric part |
| `podbroja_alfa` / `podbroj_num` | string / int | `A` / null | suffix |
| `rotacija` | double | -177.86 | label rotation |
| `geometry` | Point | 459271.67 5074920.58 | EPSG:3765 |
| `broj_cestice` | string, nullable | `2270`, `*59`, `*510/5` | parcel under the house number; `*` = building parcel |
| `ostale_vezane_cestice` | string, nullable | `443/2` | other parcels linked to the number |
| `katastarska_opcina` | string | `Centar Novi`, `Savar` | k.o. name, mixed case |
| `katastarska_opcina_id` | long | 2184015255, 1023781 | RPJ id, not the MB |
| `ulica` | string | `Ilica`, `Trg bana Josipa Jelačića` | official spelling with diacritics |
| `naselje`, `naselje_id` | string, long | `Zagreb`, 72150 | settlement |
| `postanski_ured`, `postanski_ured_id`, `postanski_broj` | | `Zagreb`, 2195037037, 10000 | |
| `ulica_id`, `ulica_redni_broj` | long | 721501047, 1047 | |

Filters that worked (`cql_filter`, GET, `count` small):

```text
ulica ILIKE 'Ilica' AND kucni_broj='1' AND naselje ILIKE 'Zagreb'      -> 1 feature, 1.6 s
katastarska_opcina ILIKE 'Savar'                                          -> 122 features, 2.5 s
naselje ILIKE 'Savar' AND kucni_broj='5'                                  -> parcel 753
strToLowerCase(ulica) LIKE '%ilica%' AND broj=1                           -> works (functions allowed)
ulica ILIKE '%jelacica%' AND naselje='Zagreb' AND kucni_broj='1'          -> 0 features
ulica ILIKE '%jela_i_a%' AND naselje='Zagreb' AND kucni_broj='1'          -> Trg bana Josipa Jelačića 1, k.o. Centar, parcel 1858
```

Diacritics: the data carry č ć š ž đ; users often do not. Replacing every letter
that could carry a diacritic (c, s, z, d and their upper-case forms) by the
single-character wildcard `_` in an `ILIKE` pattern matches both spellings; a
literal apostrophe is doubled as in `PlanningWFSClient._cql_literal`. Rank the
returned candidates by exact street match, then settlement.

Free-text parsing for the MCP tool: the last whitespace-separated token that
starts with a digit is the house number (`1`, `65A`, `12B`), the text before it is
the street, and anything after a comma is the settlement. When the settlement is
missing, return every candidate (Ilica 1 exists once; "Ulica bana Jelačića 1"
exists in many towns) and let the agent or user pick; never choose silently when
`numberMatched` > 1 and the settlements differ.

Villages without street names use the settlement name as the street (`ulica` =
`naselje` = `Savar`), so search `ulica` first and fall back to `naselje` when the
street query is empty.

## 4. INSPIRE Cadastral Parcels WFS (DGU)

```text
https://api.uredjenazemlja.hr/services/inspire/cp/wfs?service=WFS&version=2.0.0&request=GetCapabilities
```

GeoServer, WFS 2.0.0, INSPIRE CP 4.0 application schema (complex features),
types `cp:CadastralParcel` and `cp:CadastralZoning` (3495 zonings = cadastral
municipalities), EPSG:3765 only, `CountDefault` 1000, paging, JSON output,
`ows:Fees` and `ows:AccessConstraints` `NONE`, provider Državna geodetska uprava.
The earlier note in `spatial-planning-api-specification.md` section 9.2 that
GetFeature never answered is superseded: it answers, slowly.

### 4.1 Parcel at a point

```text
GET .../cp/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=cp:CadastralParcel
    &count=1&outputFormat=application/json
    &cql_filter=INTERSECTS(geometry,POINT(380615 4880910))
```

```json
{"type":"Feature","id":"CP.6564817",
 "geometry":{"type":"Polygon","coordinates":[[[380593.89,4880915.63], "..."]]},
 "properties":{"areaValue":{"value":1200,"@uom":"m2"},
   "beginLifespanVersion":"2025-09-01T10:00:00Z",
   "inspireId":{"localId":"CP.6564817","namespace":"HR.DGU.CP"},
   "label":"103/2","nationalCadastralReference":"334979-103/2",
   "referencePoint":{"type":"Point","coordinates":[380615.35,4880910.04]}}}
```

- `nationalCadastralReference` is `<MB>-<parcel number>`; `label` is the number
  alone (building parcels presumably `*35/1` as in the ATOM GML; not observed).
- `localId` minus `CP.` equals the OSS parcel id (`6564817` is parcel 103/2 in
  the mock data; `41086563` is Centar Novi 2270 both here and in Zagreb's DKP).
- Latency: 13.6 s, 13.8 s, 14.2 s, 15.0 s for four different points with
  `count=1`; a lookup by `nationalCadastralReference='334979-103/2'` took 36 s.
  The plain BBOX form (`bbox=minx,miny,maxx,maxy,urn:ogc:def:crs:EPSG::3765`)
  is no faster (13.5 s). `propertyName` is refused for these complex features
  ("Requested property ... is not available"). `resultType=hits` answers quickly
  but only with a count. Any client must use a timeout of at least 60 s and,
  in the MCP server, run the call in a thread.
- A parcel boundary polygon comes back with the feature, so this endpoint is also a
  substitute for the ATOM download in `get_parcel_geometry`; out of scope here.

### 4.2 Cadastral municipality at a point

```text
GET .../cp/wfs?service=WFS&version=2.0.0&request=GetFeature&typeNames=cp:CadastralZoning
    &count=5&outputFormat=application/json
    &bbox=380619,4880899,380621,4880901,urn:ogc:def:crs:EPSG::3765
```

Answers in 0.36-0.44 s with the k.o. MultiPolygons whose envelopes overlap the
box: `label` `334979-SAVAR`, `nationalCadastalZoningReference` (sic, the schema's
spelling) `334979`, `name.GeographicalName.spelling.text` `SAVAR`,
`beginLifespanVersion`. BBOX is an envelope test, so a point near a boundary
returns two or more zonings (the test above returned BRBINJ and SAVAR); finish with
`point_in_polygon` from `gis/geometry_ops.py` on the returned rings. An `INTERSECTS`
CQL filter on this type timed out at 90 s: use BBOX. Filtering by
`nationalCadastalZoningReference='334979'` returns the k.o. polygon in 0.35 s.

### 4.3 WMS twin

`https://api.uredjenazemlja.hr/services/inspire/cp_wms/wms` (layers
`CP.CadastralParcel`, `CP.CadastralZoning`); GetFeatureInfo requires a `STYLES`
parameter (probably `CP.CadastralParcel.Default`) and was not timed. Not needed.

## 5. Grad Zagreb ArcGIS Server

```text
https://arcportal.zagreb.hr/server/rest/services/DKPiRPJ?f=pjson
```

ArcGIS Server 10.9.1, folder `DKPiRPJ` (digitalni katastarski plan i registar
prostornih jedinica). Its MapServer layers answer anonymously; the
`katastarska_čestica/FeatureServer` answers `499 Token Required`. The service
description reads "DKP digitalni katastarski plan - dnevna replika podataka iz ZIS
sustava RH", i.e. a daily replica of the same national system the OSS API reads.
No copyright text or terms are published on the services (section 8).

| Service / layer | Geometry | Fields of interest | Notes |
|---|---|---|---|
| `KČ_DKP/MapServer/12` "katastarska čestica" | polygon | `KO` (MB, int), `KO_NAZIV`, `BROJ_KC`, `KC_BROJ`, `KC_PODBROJ`, `OZNAKA` ("CENTAR NOVI 2270"), `POVRSINA_KNJIZNA`, `POVRSINA_R`, `OBJECTID_ZIS` (= OSS parcel id), `PROMJENA`, `NAPOMENA` | Query, JSON/geoJSON/PBF, `maxRecordCount` 2000, advanced queries |
| `KBR_kućni_broj/MapServer/1` "KBR kućni broj" | point | `UL_IME`, `KB`, `KB_ST`, `KO_MB`, `KO_IME`, `KC_BR`, `NA_IME`, `ZG_ID`, `SRUSENO`, `JLS_IME`, `GC_IME` (gradska četvrt), `MO_IME` (mjesni odbor) | no advanced queries, "Pagination is not supported" (omit `resultRecordCount`); `returnCountOnly` works |
| `ulica_i_trg/MapServer/1` "ulica" | polyline | `UL_IME`, `UL_IME_HR`, `UL_JID`, `NA_IME` | street axes |
| `zgrada/MapServer/1` | polygon | `KO`, `VRSTA_UPORABE` | buildings |

Working requests:

```text
GET .../KBR_kućni_broj/MapServer/1/query?where=UL_IME='Ilica' AND KB='1'
    &outFields=UL_IME,KB,KO_MB,KO_IME,KC_BR,NA_IME&returnGeometry=true&f=json
-> {"UL_IME":"Ilica","KB":"1","KB_ST":"S","KO_MB":"339164","KO_IME":"Centar Novi",
    "KC_BR":"2270","NA_IME":"Zagreb","SRUSENO":"NE"}  point 459271.67 5074920.58   (1.6 s)

GET .../KČ_DKP/MapServer/12/query?geometry=459271.67,5074920.58&geometryType=esriGeometryPoint
    &inSR=3765&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json
-> {"KO":339164,"KO_NAZIV":"CENTAR NOVI","BROJ_KC":"2270","POVRSINA_KNJIZNA":531,
    "POVRSINA_R":533,"OBJECTID_ZIS":41086563}                                        (1-2 s)
```

`where` matching is case-sensitive and exact on this layer (`'ILICA'` finds
nothing, `LIKE '%Ilica%'` finds 767 house numbers). Street names follow the same
official spelling as the DGU layer. The city layer adds nothing the DGU address
layer lacks except `KO_MB`, which the zoning BBOX also supplies; keep it as an
optional fallback for addresses and use it primarily for the fast point lookup.

## 6. ISPU Geoportal Search (Suggestions Only)

`https://ispu.mgipu.hr/api/v1/gis/search-text?input=Ilica 1 Zagreb` returns grouped
hits; the "Adrese" group lists `{"id":"238843059","label":"ZAGREB, ILICA 1",
"source":"kucni_broj","hash":"jkE3b0Skg4"}` with settlement and county. It is a
good fuzzy suggester (179 hits for that input) but the follow-up call that maps a
hit to coordinates was not found (`info-lokacija-*` variants answer 404; the
bundle does not contain the paths) and the location flow sits behind the portal's
captcha. Use only if a type-ahead is ever wanted; not needed for the two tools.

## 7. Lookup Recipes

### 7.1 `find_parcel_by_point`

```text
input: x, y, crs (EPSG:3765 default | EPSG:4326)
1. Convert to EPSG:3765 if needed (section 2). Reject points outside the national
   extent of the ATOM feed (208311..744180, 4608970..5161550).
2. If a Zagreb ArcGIS URL is configured and the point is inside the KČ_DKP layer's
   extent (read once from the layer metadata): point query on layer 12 ->
   {municipality_code: KO, parcel_number: BROJ_KC, parcel_id: OBJECTID_ZIS}.
   Empty result or error -> continue.
3. INSPIRE parcel WFS, INTERSECTS, count=1, 60 s timeout ->
   {parcel_id: localId without "CP.", parcel_number: label,
    municipality_code: nationalCadastralReference before "-", polygon}.
4. get_parcel_info(parcel_id) for the full record (optional flag, as get_parcel does).
Later: zoning BBOX -> MB -> GISCache GML -> point_in_polygon (fast after first use).
```

Parcels are a partition of the territory, so exactly one is expected; return the
first and report `matches` when the service returns more (shared boundary). A point
on a k.o. boundary can select the neighbour's parcel; report the parcel's own
`municipality_code`, never the caller's assumption.

### 7.2 `find_parcel_by_address`

```text
input: text ("Ilica 1, Zagreb") or street + house_number [+ settlement]; max_candidates
1. Parse text (section 3). Build the ILIKE pattern with "_" for diacritic-able letters.
2. Addresses WFS: ulica ILIKE pattern AND kucni_broj = number [AND naselje ILIKE ...],
   count = max_candidates + 1. Empty -> retry with naselje in place of ulica
   (villages). Still empty -> not found.
3. For each candidate (or only the chosen one): zoning BBOX at the point ->
   municipality_code; keep the address layer's k.o. name for display.
4. If broj_cestice is present: find_parcel(broj_cestice, municipality_code) with the
   existing exact-match rules (the "*" prefix is already accepted). Also return
   ostale_vezane_cestice as linked parcel numbers, unresolved.
   If broj_cestice is null: find_parcel_by_point(point).
5. Return the address as matched (street, number, settlement, postal code), the
   point, the parcel reference and id, and the candidate list when > 1.
```

### 7.3 Result model (proposal)

```python
class ParcelLocation(BaseModel):
    parcel_id: int | None
    parcel_number: str
    municipality_code: str
    municipality_name: str | None
    point: Coordinate                  # EPSG:3765, the query point or the address point
    address: MatchedAddress | None     # street, house_number, settlement, postal_code, inspire_id
    linked_parcel_numbers: list[str]   # ostale_vezane_cestice
    source: str                        # "dgu-inspire-ad", "dgu-inspire-cp", "zagreb-dkp"
    source_url: str
    retrieved_at: str
    candidates: list[AddressCandidate] # when the address was ambiguous
    match_note: str | None
```

## 8. Terms of Use (verify before pointing the code at these servers)

- Both DGU WFS capabilities documents state `Fees NONE` and `AccessConstraints NONE`
  and answer anonymously. The DGU's announcement of the parcel service
  (dgu.gov.hr news 5591) says it is for registered users free of charge on
  accepting the terms; the 2019 announcement of address services (news 5035) said
  the Addresses WFS was for public-law bodies under a signed protocol, and the two
  NIPP register entries for addresses (ids 447 and 452) no longer exist. The 2019
  freedom-of-information answer to OpenStreetMap Croatia (imamopravoznati.org)
  records that DGU revised its terms to allow reuse of the network services'
  data with attribution, and the current dgu.gov.hr terms page allows reuse
  "uz navođenje izvora". The address service's status is the least clear of the
  three: make it configurable, default it to the mock, and attribute
  "Državna geodetska uprava" in every output that used it.
- Grad Zagreb publishes no terms or copyright text on `arcportal.zagreb.hr`; the
  same DKP is served on `gis.zagreb.hr` for other city apps. Treat as
  "verify with the city's cadastre office", off by default.
- Rate: keep the SDK's request spacing (0.375 s) on all three; the parcel WFS is
  slow enough that no extra throttling matters.

## 9. Implementation Plan

Mapped to the repository conventions (naming, i18n, output keys, docs, changelog,
mock, gates):

1. SDK `api/src/cadastral_api/locator/` with `address_wfs_client.py`,
   `parcel_wfs_client.py`, `zagreb_arcgis_client.py`, `crs.py` (TM formula) and
   `models/locator_entities.py`. Reuse the mirror-rotation, timeout, rate-limit
   and provenance pattern of `planning/wfs_client.py`. Environment:
   `CADASTRAL_ADDRESS_WFS_URLS`, `CADASTRAL_PARCEL_WFS_URLS`,
   `CADASTRAL_ZAGREB_ARCGIS_URL`, each defaulting to the mock
   (`<base>/inspire/ad/wfs`, `<base>/inspire/cp/wfs`,
   `<base>/zagreb/arcgis/rest/services/DKPiRPJ`).
2. `CadastralAPIClient.find_parcel_by_point()` and `.find_parcel_by_address()`
   composing section 7; `get_parcel_info` optional.
3. CLI `cadastral locate` (Croatian name per `specs/terminology.md` section 4,
   e.g. `uz lociraj`) with `--address TEXT` / `--point X,Y [--crs]`, table/json/csv,
   output keys registered in `output_keys.py` and `po/hr.po`.
4. MCP `find_parcel_by_address(text, settlement=None, max_candidates=5)` and
   `find_parcel_by_point(x, y, crs="EPSG:3765")` in `mcp/src/cadastral_mcp/server.py`,
   run through `asyncio.to_thread` like `get_parcel_zoning`, with the disclaimer
   and source attribution in the result.
5. Mock server routes imitating the three services with the Savar sample
   (k.o. 334979: addresses `Savar 5` -> 753, `Savar 65A` -> `*59` + 443/2) and one
   Zagreb building (Ilica 1 -> Centar Novi 2270, id 41086563), following the
   `/planning/wfs` implementation (GetCapabilities, GetFeature, CQL subset, BBOX).
6. Fixtures: redacted captures of one response per endpoint shape under
   `api/src/cadastral_api/tests/fixtures/`, extending `scripts/redact_capture.py`.
7. Tests: filter building (diacritics, apostrophes), free-text parsing, CRS
   round-trip, zoning disambiguation, fallbacks, MCP tool contract; gates
   `test_localized_cli.py`, `test_output_keys.py`, `test_i18n_coverage.py`,
   `test_docs_coverage.py`.
8. Docs: `docs/en/cli/locate.md`, MCP usage guide, SDK guide, README feature list,
   CHANGELOG `[Unreleased]`.

## 10. Verification Log (2026-09-14)

- Addresses WFS: GetCapabilities, DescribeFeatureType, five GetFeature filters (all
  200; 0.4-2.5 s); 1 682 273 features.
- Parcel WFS: GetCapabilities; four INTERSECTS point queries (13.6-15.0 s);
  one BBOX query (13.5 s, 5 parcels in a 10 m box); one lookup by reference (36 s);
  `propertyName` refused; zoning BBOX 0.36-0.44 s, zoning INTERSECTS timed out
  (90 s); zoning by reference 0.35 s.
- Zagreb: folder listing; layer metadata for KČ_DKP/12, KBR/1, ulica/1, zgrada/1;
  house-number query for Ilica 1; parcel point query at that point; FeatureServer
  `499 Token Required`.
- Identity checks: `CP.6564817` = mock `parcelId` 6564817 (103/2 Savar);
  `CP.41086563` = Zagreb `OBJECTID_ZIS` 41086563 (Centar Novi 2270).
- OSS municipality search: "Centar Novi" 1 hit, "Savar" 1, "Novo Selo" 10,
  "Sveti Petar" 5.
- Not found / not usable: OSS public address endpoint, ISPU hit-to-location call,
  `katastar.hr` (no DNS), `geoportal.dgu.hr/api/search` (401), INSPIRE AD on
  `api.uredjenazemlja.hr` (404), NIPP register entries 447 and 452 (gone).
