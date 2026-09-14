# Spatial Planning Data API Specification

Machine-readable sources of Croatian spatial-plan data (prostorni planovi: PPUO/PPUG,
GUP, UPU, DPU, county and state plans), the land-use and building-area designations
they carry, and the cadastre-side geometry endpoints needed to match them against
parcels and land-registry units.

Status: research specification. Every endpoint and example below was exercised on
2026-09-14 unless marked "not verified". Implemented so far: the building-areas WFS
(section 3) as `cadastral_api.planning.PlanningWFSClient` with mirror rotation,
`CadastralAPIClient.get_parcel_zoning`, the CLI command `get-zoning`, the MCP tool
`get_parcel_zoning` and the mock server's `/planning/wfs`. The raster WMS (section 2),
the regional services (section 5) and the catalogues (section 8) are documented only.

## Scope Notice

This project is an educational demonstration. All servers in this document are Croatian
government or municipal systems, or third-party vendor systems operated for them. Their
service metadata mostly declares no fees and no access constraints, but their data
disclaimers are strict (see section 3.6). Before pointing code at any of them, verify
that you have the right to use the server and its data (terms of service, data-protection
law); use at your own risk. The SDK default stays the mock server at `http://localhost:8000`.

Contents

1. Landscape and common conventions
2. Raster: county plan-sheet WMS (old-generation plans)
3. Vector: nationwide building-areas WFS
4. Vector: other ministry WFS services
5. Vector: regional and municipal services
6. ISPU geoportal internal JSON API (observed, undocumented)
7. eKatalog public JSON API
8. Catalogues and registers (NIPP, data.gov.hr)
9. Cadastre-side geometry endpoints for matching
10. New-generation plan model (Pravilnik NN 152/2023)
11. Matching recipe
12. Verification log and open items

## 1. Landscape and Common Conventions

### 1.1 Three tiers of plan data

| Tier | What exists | Structure | Public API |
|------|-------------|-----------|------------|
| Old-generation plans (almost all plans in force) | Georeferenced raster scans of the plan map sheets | One WMS layer per sheet, named by plan and sheet code | WMS only (section 2) |
| Building areas, nationwide | Vector polygons derived from those plans by the county spatial-planning institutes; state September 2024 (metadata still says 2016) | Two feature types with land-use code per polygon | WFS (section 3) |
| New-generation plans | Vector plans with polygons linked to provisions, made in ePlanovi Editor since 2024 | 26 thematic layers, coded themes (section 10) | None yet; ePlanovi is login-only |

Regional exceptions with their own vector land use are listed in section 5.

### 1.2 Owner and hosts

Owner: Ministarstvo prostornoga uređenja, graditeljstva i državne imovine (MPGI),
formerly MGIPU, hence the host names. Contact given in service metadata:
`ISPU-help@mpgi.hr` (older records `ISPU-help@mgipu.hr`).

| Host | Role |
|------|------|
| `ispu.mgipu.hr` | ISPU geoportal (Angular app) and its internal JSON API. `ispu.mpgi.hr` does not resolve. |
| `gis1.mgipu.hr` ... `gis4.mgipu.hr` | Four GeoServer mirrors behind an Apache proxy, path `/srv1/<workspace>/wms`, `/srv1/<workspace>/wfs` or `/srv1/<workspace>/ows`. Only whitelisted workspace paths answer; the generic paths `/srv1/wms`, `/srv1/ows`, `/srv1/web` and `/srv1/rest` return 404. |
| `katalog.mgipu.hr` | eKatalog prostornih planova (metadata registry) with a public JSON API (section 7). |
| `planovi.mgipu.hr`, `editor-ispu.gov.hr` | ePlanovi and ePlanovi Editor. Login only (NIAS). |
| `geoportal.nipp.hr`, `registri.nipp.hr` | National SDI catalogue (GeoNetwork CSW) and register API (section 8). |

Mirror behaviour: the four `gisN` hosts serve the same workspaces but any of them can
return `502 Proxy Error` (an HTML page, `text/html`) for minutes at a time. Observed
today: Zadar county (Z13) answered only on gis3 and gis4, Istria (Z18) only on gis1, gis2
and gis4. A client must treat 502 as "try the next mirror", not as an error.

### 1.3 Coordinate reference system

Every ministry service uses EPSG:3765 (HTRS96 / Croatia TM, metres) as its native CRS,
the same CRS as the DGU cadastral GML this repository already parses. WMS layers also
advertise EPSG:4326 and CRS:84; the WFS accepts `srsName=EPSG:4326` on output. HTRS96 to
WGS 84 is a null datum shift (EPSG:15967, 1 m stated accuracy), so pyproj converts
without grid files.

### 1.4 Identifiers

| Identifier | Format | Example | Where it appears |
|------------|--------|---------|------------------|
| Plan identifier (ISPU) | `HR-ISPU-<TYPE>-<JLS code 5 digits>-R<revision 2 digits>` | `HR-ISPU-PPGO-03794-R05` (PPUO Sali, third amendment) | WFS attribute `ozn_ispu`, eKatalog, geoportal search |
| Raster layer name | `HR_ISPU_<TYPE><n>_<JLS code>_R<rev>_<SHEET>_<x>_<y>[<suffix>]` | `HR_ISPU_PPGO_03794_R07_KN_1_1` | WMS layer `<Name>` |
| Plan type codes | `PPGO` (PPUO or PPUG), `GUP<n>`, `UPU<n>`, `DPU<n>`, `PUP<n>`, `PPZP` (county plan), `PPPPO` (special-feature area plan) | `UPU12`, `DPU1` | Layer names; `<n>` numbers the plans of that type within one JLS |
| Sheet codes | `KN` korištenje i namjena, `GP` građevinska područja, `IS` infrastrukturni sustavi, `ZP` uvjeti korištenja, uređenja i zaštite; rare `OK`, `NG` | `GP_4_10B` | Layer names; the numbers follow the 1998 Pravilnik sheet numbering |
| JLS code | 5-digit code of the grad/općina (šifra JLS) | `03794` = Općina Sali | Layer names, WFS `jls_mb` |
| County code | 2 digits, standard county order | `13` = Zadarska | WMS workspace `PPRasterZ13_Public`, WFS `zup_rb` (5 digits, `00013`) |
| Cadastral municipality | matični broj katastarske općine, 6 digits | `334979` = SAVAR | Geoportal API, cadastre GML |

County codes: 01 Zagrebačka, 02 Krapinsko-zagorska, 03 Sisačko-moslavačka,
04 Karlovačka, 05 Varaždinska, 06 Koprivničko-križevačka, 07 Bjelovarsko-bilogorska,
08 Primorsko-goranska, 09 Ličko-senjska, 10 Virovitičko-podravska, 11 Požeško-slavonska,
12 Brodsko-posavska, 13 Zadarska, 14 Osječko-baranjska, 15 Šibensko-kninska,
16 Vukovarsko-srijemska, 17 Splitsko-dalmatinska, 18 Istarska,
19 Dubrovačko-neretvanska, 20 Međimurska, 21 Grad Zagreb.

### 1.5 Errors

| Source | Shape |
|--------|-------|
| Apache proxy | HTTP 502, `text/html`, body `502 Proxy Error`; HTTP 404 `text/html` for non-whitelisted paths |
| GeoServer WFS | HTTP 400, `ows:ExceptionReport` XML with `exceptionCode` (`InvalidParameterValue`, `NoApplicableCode`) and `locator` |
| GeoServer WMS | `ServiceExceptionReport` XML by default; `EXCEPTIONS=application/json`, `INIMAGE` or `BLANK` are supported |
| ISPU JSON API | HTTP 403 with `{"succeeded": false, "message": "Neovlašten pristup resursima aplikacije.", "errors": null, "data": null}`; HTTP 204 with empty body for "not found" |
| eKatalog JSON API | HTTP 500 with a JSON string, e.g. `"Problem s metadata zahtjevom"`; HTTP 400 `"Nedostaje parametar url"` |

### 1.6 Rate limits and terms

No rate limits are published for any service. Service capabilities declare
`Fees: NONE` and `AccessConstraints: NONE`; the NIPP register says "Nema uvjeta za pristup
i korištenje" for the ministry services. The Uredba o ISPU (NN 115/2015) states that
access to the geoportal is public (čl. 10) and that ISPU data are taken free of charge
(čl. 8); the Zakon o prostornom uređenju (NN 155/2025, čl. 35) states that data in the
system are public. The data disclaimers still apply (section 3.6). Keep the SDK's
0.375 s throttle when talking to these servers.

## 2. Raster: County Plan-Sheet WMS

### 2.1 Endpoints

```text
https://gis{1,2,3,4}.mgipu.hr/srv1/PPRasterZ<NN>_Public/wms
https://gis{1,2,3,4}.mgipu.hr/srv1/PPRasterZ<NN>_Public/ows     (same service)
https://gis{1,2,3,4}.mgipu.hr/srv1/PPRasterPPPPO_Public/wms      (state-level plans)
```

`<NN>` is the county code. Layer counts observed today (one mirror each):

| Workspace | Layers | Workspace | Layers |
|-----------|--------|-----------|--------|
| Z01 | 1959 | Z11 | 419 |
| Z02 | 454 | Z12 | 404 on all mirrors (Brodsko-posavska runs its own WMS) |
| Z03 | 779 | Z13 | 2413 |
| Z04 | not reachable today | Z14 | not reachable today |
| Z05 | 487 | Z15 | 696 |
| Z06 | 304 | Z16 | 203 |
| Z07 | 345 | Z17 | 3247 |
| Z08 | 6 (Primorsko-goranska runs its own services) | Z18 | 738 |
| Z09 | 697 | Z19 | 1320 |
| Z10 | 409 | Z20 | not reachable today |
| | | Z21 | 898 |

Service: GeoServer, WMS 1.1.1 and 1.3.0. Contact organisation "MGIPU-Zavod za prostorni
razvoj". Fees NONE, AccessConstraints NONE. Every layer links an ISO 19115 metadata
record in the NIPP catalogue (section 8.1).

### 2.2 GetCapabilities

```http
GET /srv1/PPRasterZ13_Public/wms?service=WMS&request=GetCapabilities&version=1.3.0
```

Response: `text/xml`, `WMS_Capabilities`. One `<Layer queryable="1">` per sheet, with
`<Name>`, `<Title>` (plan name plus sheet, human-readable), `<Abstract>` (plan name plus
layer name), `<CRS>EPSG:3765</CRS>`, `<CRS>CRS:84</CRS>`, an `EX_GeographicBoundingBox`,
a `BoundingBox CRS="EPSG:3765"` (the sheet's extent, the only way to find which sheets
cover a point), a `MetadataURL` (CSW GetRecordById) and a `LegendURL`. Example layer block,
abbreviated:

```xml
<Layer queryable="1">
  <Name>HR_ISPU_PPGO_03794_R07_GP_4_5</Name>
  <Title>PPUO Sali - VI. ID  GP</Title>
  <Abstract>PPUO Sali - VI. ID  HR_ISPU_PPGO_03794_R07_GP_4_5</Abstract>
  <CRS>EPSG:3765</CRS>
  <CRS>CRS:84</CRS>
  <BoundingBox CRS="EPSG:3765" minx="380229.4" miny="4880281.0" maxx="382104.6" maxy="4882625.9"/>
  <MetadataURL type="ISO19115:2003">
    <Format>text/plain</Format>
    <OnlineResource xlink:href="http://geoportal.nipp.hr/geonetwork/srv/eng/csw?Service=CSW&amp;Request=GetRecordById&amp;Version=2.0.2&amp;outputSchema=http://www.isotc211.org/2005/gmd&amp;elementSetName=full&amp;id=9310e114-b20d-4282-a1dc-6bc1c1ef20be"/>
  </MetadataURL>
  <Style>
    <Name>raster</Name>
    <LegendURL width="20" height="20">
      <Format>image/png</Format>
      <OnlineResource xlink:href="https://gis4.mgipu.hr/srv1/PPRasterZ13_Public/ows?service=WMS&amp;version=1.3.0&amp;request=GetLegendGraphic&amp;format=image%2Fpng&amp;width=20&amp;height=20&amp;layer=HR_ISPU_PPGO_03794_R07_GP_4_5"/>
    </LegendURL>
  </Style>
</Layer>
```

Sheet-code distribution in Z13: IS 1032, KN 789, ZP 327, GP 265. Plan-type distribution:
PPGO 480, UPU 1511 (all `UPU<n>`), DPU 410, PUP 6, PPZP 6.

Layer titles carry the plan name as registered in ISPU, including amendment suffixes
(`- VI. ID`, `- IV. ID (službeno: Izmjene i dopune)`, `(pročišćeni tekst)`, `(ciljane)`).
The revision number in the layer name (`R07`) is the plan revision that produced the
sheet; several revisions of one plan can coexist in the capabilities.

The capabilities document is large (Z13: 2.4 MB, Z17 larger). Cache it per workspace.

### 2.3 GetMap

```http
GET /srv1/PPRasterZ13_Public/wms
    ?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap
    &LAYERS=HR_ISPU_PPGO_03794_R07_KN_1_1
    &CRS=EPSG:3765&BBOX=380100,4880500,381100,4881500
    &WIDTH=600&HEIGHT=600&FORMAT=image/png
```

| Parameter | Notes |
|-----------|-------|
| `LAYERS` | One or more layer names, comma-separated. Sheets of one plan can be stacked. |
| `CRS` / `SRS` | `EPSG:3765` (axis order x,y east,north in 1.3.0), `EPSG:4326` (lat,lon order in 1.3.0; lon,lat with `VERSION=1.1.1` and `SRS`), `CRS:84`. |
| `BBOX` | In CRS units. WMS 1.3.0 with EPSG:4326 expects `minlat,minlon,maxlat,maxlon`. |
| `FORMAT` | `image/png`, `image/png; mode=8bit`, `image/jpeg`, `image/gif`, `image/geotiff`, `image/geotiff8`, `application/pdf`, `image/svg`, `application/vnd.google-earth.kml+xml`, `application/vnd.google-earth.kmz`, `application/json;type=utfgrid`. |
| `TRANSPARENT` | `true` gives transparent background outside the sheet. |
| `STYLES` | Empty; only the default `raster` style exists. |

Response: the image (verified `image/png` 232 KB for the example, `image/jpeg` 42 KB for
a 1.1.1 request in EPSG:4326). Areas outside the sheet's bounding box are blank. Legend:
`REQUEST=GetLegendGraphic&LAYER=<name>&FORMAT=image/png` returns a 20 x 20 generic
raster icon, not the plan legend; the real legend is another sheet in the same workspace
or a page in the plan document.

### 2.4 GetFeatureInfo

Supported (`text/plain`, `text/html`, `application/json`, GML), but the layers are RGB
rasters, so the response contains pixel band values (`RED_BAND`, `GREEN_BAND`,
`BLUE_BAND`), not land-use attributes. Colour-to-legend matching is possible in principle
(the 1998 Pravilnik fixed the colours per designation) and fragile in practice (scan
quality, hatching, overprinted labels). Do not build on it.

### 2.5 Finding the sheets for a parcel

1. Fetch the county workspace capabilities.
2. Keep layers whose `BoundingBox CRS="EPSG:3765"` contains the parcel's bounding box.
3. Prefer the highest `R<rev>` of each plan and the `KN_1_1` sheet for land use, `GP_*`
   sheets for building areas (1:5000 scale, one sheet per settlement).

For the SAVAR parcel 103/2 (bbox around 380594-380640, 4880883-4880933) this yields
`HR_ISPU_PPGO_03794_R07_KN_1_1`, `..._GP_4_5`, `..._IS_3_2`, `..._IS_4_1`, `..._ZP_1_1`,
`..._ZP_1_6` (PPUO Sali, sixth amendment). Rendered, the parcel lies in the agricultural
hatch south of the yellow settlement building area of Savar.

## 3. Vector: Nationwide Building-Areas WFS

### 3.1 Endpoint

```text
https://gis4.mgipu.hr/srv1/GradjPodrucje_MGIPU_Public/wfs
```

Only gis4 was tested for this workspace; the other mirrors are expected to serve it as
well (untested). WFS 1.0.0, 1.1.0 and 2.0.0. GeoServer. Fees NONE, AccessConstraints
NONE. DefaultCRS `urn:ogc:def:crs:EPSG::3765`, OtherCRS EPSG:4326. Result paging
supported (`count`, `startIndex`, `next` links). No `CountDefault` cap is advertised; a
full attribute dump of 13 493 features succeeded in one request. No WMS is exposed for
this workspace on the proxy (`/wms` and `/ows` return 404); the geoportal renders it
through its own proxy.

NIPP register: <https://registri.nipp.hr/api/izvori/246/> (jedinstvena oznaka 0248),
metadata record `95f33449-c9ee-4714-a373-19a6f91d3af0`. The geoportal labels the layer
"Građevinska područja (rujan 2024.)"; the register abstract still says plans in force in
September 2016.

### 3.2 Feature types

| Type name | Features | Meaning |
|-----------|----------|---------|
| `GradjPodrucje_MGIPU_Public:Gradj_podrucje_naselje` | 89 911 | Građevinsko područje naselja (settlement building area), code `GPN` |
| `GradjPodrucje_MGIPU_Public:Gradj_podrucje_izvan_naselja` | 13 493 | Izdvojeno građevinsko područje izvan naselja (detached zone), with the land-use code |

Attributes (from DescribeFeatureType):

| Attribute | Type | In | Meaning | Example |
|-----------|------|----|---------|---------|
| `objectid_1` | int | naselje | Source object id, often null | `null` |
| `zup_rb` | string | both | County code, 5 digits | `00013` |
| `jls_mb` | string | both | JLS code, 5 digits | `03794` |
| `jls_st` | string | both | JLS status: `OP` općina, `GR` grad | `OP` |
| `jls_ime` | string | both | JLS name, upper case | `SALI` |
| `plan_naziv` | string | both | Source plan name | `PPUO SALI - III. ID` |
| `ozn_ispu` | string | both | Source plan ISPU identifier | `HR-ISPU-PPGO-03794-R05` |
| `izvor` | string | both | Source sheet number in the plan | `4.5.` |
| `mj_izvora` | string | both | Source scale | `1:5.000` |
| `znacaj` | int | izvan | Significance (0 local, 2 county/state; values observed 0 and 2) | `2` |
| `napomena` | string | both | Note, usually null | `null` |
| `namjena` | string | izvan | Designation, text as in the plan | `GOSPODARSKA - UGOSTITELJSKO TURISTIČKA (KAMP)` |
| `namjena_vl` | string | izvan | Designation detail | `UREĐENA MORSKA PLAŽA (KOPNENI DIO)` |
| `ozn_namjen` | string | both | Designation code (`GPN` in naselje) | `T3` |
| `naz_vl` | string | both | Zone name, usually `<settlement> - <locality>` | `VERUNIĆ - LUČICA` |
| `az_oznaka` | string | izvan | Aggregated code (first letter class) | `T` |
| `pov` | double | both | Area in m2 | `21209.417` |
| `shape_area`, `shape_length` | decimal | both | Source geometry measures | `21209.42`, `714.58` |
| `geom` | gml:GeometryPropertyType | both | Polygon or MultiPolygon, EPSG:3765 | |

Feature ids are `<type>.<n>`, e.g. `Gradj_podrucje_izvan_naselja.109142`, and are usable
with the `GetFeatureById` stored query.

### 3.3 Designation codes observed

Nationwide counts of `ozn_namjen` on the detached-zone type (top values; codes are the
county institutes' transcription of the old-plan legends and are not fully normalised):

| Code | Count | Designation |
|------|-------|-------------|
| `G` | 2439 | Groblje |
| `T2` | 250 | Ugostiteljsko-turistička, turističko naselje |
| `I1` | 198 | Proizvodna, pretežito industrijska |
| `T1` | 183 | Ugostiteljsko-turistička, hotel |
| `I+K`, `I, K`, `I,K` | 312 | Proizvodno-poslovna (three spellings) |
| `IS`, `IS5` | 303 | Površine infrastrukturnih sustava |
| `T3` | 146 | Ugostiteljsko-turistička, kamp |
| `M3`, `M4` | 188 | Mješovita |
| `K`, `K1`, `K2`, `K3` | 337 | Poslovna (uslužna, trgovačka, komunalno-servisna) |
| `N` | 123 | Posebna namjena |
| `R`, `R1`, `R3`, `R5`, `R6`, `R7` | 424 | Sport i rekreacija |
| `I`, `I2`, `I3`, `IH` | 700 | Proizvodna (zanatska, marikultura) |
| `E1` | 86 | Eksploatacija mineralnih sirovina |
| `D` | 46 | Javna i društvena |
| `X`, `+`, null | 400 | Unclassified |

The free-text `namjena` is `OSTALO` for many rows even when `ozn_namjen` is specific, so
derive the class from `ozn_namjen` (or `az_oznaka`) first and use `namjena` and
`namjena_vl` as labels.

### 3.4 Operations

GetCapabilities:

```http
GET /srv1/GradjPodrucje_MGIPU_Public/wfs?service=WFS&request=GetCapabilities
```

Output formats advertised for GetFeature: `application/json` (GeoJSON), `json`,
`application/gml+xml; version=3.2`, `gml32`, `gml3`, `GML2`, `text/xml; subtype=gml/3.2`,
`csv`, `text/csv`, `SHAPE-ZIP`, `KML`, `application/vnd.google-earth.kml+xml`.

DescribeFeatureType:

```http
GET /srv1/GradjPodrucje_MGIPU_Public/wfs?service=WFS&version=2.0.0
    &request=DescribeFeatureType&typeNames=GradjPodrucje_MGIPU_Public:Gradj_podrucje_izvan_naselja
```

Response: XML Schema with one `xsd:element` per attribute, as in the table above.

GetFeature parameters (WFS 2.0.0 KVP):

| Parameter | Notes |
|-----------|-------|
| `typeNames` | One of the two type names (namespace prefix required). |
| `outputFormat` | See above. `application/json` is the practical choice. |
| `count`, `startIndex` | Paging. The GeoJSON response carries `numberMatched`, `numberReturned` and a `links[]` entry with `rel: next`. |
| `sortBy` | Attribute name; append a space and `D` for descending (`sortBy=pov D`). |
| `propertyName` | Comma-separated attributes to return. Omit `geom` to get attribute-only responses (geometry is then `null`). |
| `bbox` | `minx,miny,maxx,maxy,EPSG:3765`. |
| `srsName` | Output CRS, e.g. `EPSG:4326` (lon,lat order in GeoJSON). |
| `cql_filter` | GeoServer ECQL: attribute comparisons (`jls_mb='03794' AND ozn_namjen='T3'`), `LIKE`, `IN`, and spatial predicates `INTERSECTS(geom, <WKT>)`, `WITHIN`, `DWITHIN(geom, <WKT>, 50, meters)`, `BBOX(geom, ...)`. WKT is in EPSG:3765 unless `srsName` says otherwise. |
| `filter` | FES 2.0 XML filter, alternative to `cql_filter`. |
| `resultType=hits` | Returns only `numberMatched` (XML). |
| `storedQuery_id=urn:ogc:def:query:OGC-WFS::GetFeatureById&id=<fid>` | Single feature by id. |

### 3.5 Examples

Attribute filter with paging and sorting:

```http
GET /srv1/GradjPodrucje_MGIPU_Public/wfs?service=WFS&version=2.0.0&request=GetFeature
    &typeNames=GradjPodrucje_MGIPU_Public:Gradj_podrucje_izvan_naselja
    &cql_filter=jls_mb='03794' AND ozn_namjen='T3'
    &outputFormat=application/json&count=2&startIndex=0&sortBy=pov
```

```json
{
  "type": "FeatureCollection",
  "totalFeatures": 4,
  "numberMatched": 4,
  "numberReturned": 2,
  "timeStamp": "2026-09-14T13:06:10.820Z",
  "links": [{"title": "next page", "type": "application/json", "rel": "next",
             "href": "https://gis4.mgipu.hr/srv1/GradjPodrucje_MGIPU_Public/wfs?REQUEST=GetFeature&...&STARTINDEX=2"}],
  "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::3765"}},
  "features": [
    {
      "type": "Feature",
      "id": "Gradj_podrucje_izvan_naselja.109142",
      "geometry": {"type": "Polygon", "coordinates": [[[369277.5811, 4890223.1612], [369249.65, 4890228.56], "..."]]},
      "geometry_name": "geom",
      "properties": {
        "zup_rb": "00013", "jls_mb": "03794", "jls_st": "OP", "jls_ime": "SALI",
        "plan_naziv": "PPUO SALI - III. ID", "ozn_ispu": "HR-ISPU-PPGO-03794-R05",
        "izvor": "4.10.", "mj_izvora": "1:5.000", "znacaj": 2, "napomena": null,
        "namjena": "GOSPODARSKA - UGOSTITELJSKO TURISTIČKA (KAMP)", "namjena_vl": null,
        "ozn_namjen": "T3", "naz_vl": "VERUNIĆ - LUČICA", "az_oznaka": "T",
        "pov": 21209.417007716984, "shape_area": 21209.42, "shape_length": 714.58
      }
    }
  ]
}
```

Spatial join for one parcel (WKT from the cadastral GML, EPSG:3765):

```http
GET /srv1/GradjPodrucje_MGIPU_Public/wfs?service=WFS&version=2.0.0&request=GetFeature
    &typeNames=GradjPodrucje_MGIPU_Public:Gradj_podrucje_naselje
    &cql_filter=INTERSECTS(geom, POLYGON ((380593.89 4880915.63, 380595.57 4880907.31, 380612.75 4880882.91, 380613.8 4880885.43, 380639.65 4880911.28, 380635.25 4880916.36, 380622.02 4880932.76, 380615.6 4880927.04, 380603.57 4880926.56, 380593.89 4880915.63)))
    &outputFormat=application/json&propertyName=jls_ime,plan_naziv,ozn_ispu,ozn_namjen,izvor,pov
```

Response for SAVAR 103/2: `numberMatched: 0` on both feature types (the parcel is outside
every building area). The same query with `bbox=378000,4879000,383000,4884000,EPSG:3765`
returns the four `GPN` polygons of Savar, Brbinj and Luka with `plan_naziv` "PPUO SALI -
III. ID". Note that `propertyName` must only name attributes that exist on the queried
type; naming `namjena` on the naselje type returns HTTP 400.

Reprojected output:

```http
GET ...&cql_filter=naz_vl='SAVAR - UVALA ILO'&srsName=EPSG:4326&outputFormat=application/json
```

```json
{"crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::4326"}},
 "features": [{"id": "Gradj_podrucje_izvan_naselja.109080",
               "geometry": {"type": "Polygon", "coordinates": [[[15.00677041, 44.06952012], "..."]]}}]}
```

CSV:

```http
GET ...&outputFormat=csv&propertyName=naz_vl,ozn_namjen,pov
```

```csv
FID,ozn_namjen,naz_vl,pov
Gradj_podrucje_izvan_naselja.109075,T3,ZAGLAV - EKO POSTAJA BARBAROŽA,30022.00806075
Gradj_podrucje_izvan_naselja.109077,T3,ZAGLAV - TRSTENICA,29102.45809997
```

Shapefile: `outputFormat=SHAPE-ZIP` returns `application/zip` with `.shp`, `.shx`, `.dbf`,
`.prj` (verified, 3.4 KB for four features).

Count only:

```http
GET ...&typeNames=GradjPodrucje_MGIPU_Public:Gradj_podrucje_izvan_naselja&resultType=hits
```

```xml
<wfs:FeatureCollection ... numberMatched="13493" numberReturned="0" timeStamp="..."/>
```

Error:

```xml
<ows:ExceptionReport version="2.0.0">
  <ows:Exception exceptionCode="InvalidParameterValue" locator="typeName">
    <ows:ExceptionText>Feature type GradjPodrucje_MGIPU_Public:Nope unknown</ows:ExceptionText>
  </ows:Exception>
</ows:ExceptionReport>
```

### 3.6 Disclaimer carried by the data

Register abstract, verbatim: "Podaci predstavljaju interpretaciju prostornih planova i
moguća su odstupanja od stanja u važećim prostornim planovima te se ne smiju koristiti u
svrhu izdavanja akata za provedbu zahvata u prostoru i drugih javnih isprava. U sve
službene svrhe potrebno je koristiti izvornike važećih prostornih planova." Any output
built on this layer must carry the same warning and the `plan_naziv`/`ozn_ispu`
provenance.

## 4. Vector: Other Ministry WFS Services

| Service | Endpoint | Feature types | Notes |
|---------|----------|---------------|-------|
| Registar brownfield područja | `https://brownfield.mpgi.hr/ows_public/wfs` | `brownfield:brownfield_area` | WFS 2.0, GeoJSON, Fees/AccessConstraints NONE; register says "bez ograničenja, uz obvezno navođenje izvora" |
| Registar geohazarda | `https://gis{1-4}.mgipu.hr/srv1/RGN_MGIPU_Public/wfs` | 8 feature types (per the ISPU research agent) | Capabilities returned no feature-type names on gis4 today; not verified |
| Plan približnih vrijednosti, cjenovni blokovi, akti za zahvate | Only as layers inside the geoportal (section 6) | | No public OGC endpoint found |

## 5. Vector: Regional and Municipal Services

Where a county or city runs its own GIS, vector land use with real attributes exists.
These are outside the ISPU contract and each has its own terms.

### 5.1 Primorsko-goranska županija (ArcGIS Server)

```text
https://gisportal.pgz.hr/server/rest/services/STANJE/NAMJENA_POVRSINA_NOVO/FeatureServer/0
```

Polygon layer "Namjena površina", EPSG:3765, `maxRecordCount` 2000, formats JSON,
geoJSON, PBF. Fields: `OBJECTID`, `POLAZNA_NAMJENA`, `PRIMARNA_NAMJENA`,
`SEKUNDARNA_NAMJENA`, `DETALJNA_NAMJENA`, `OZNAKA_NAMJENE`, `IZGRADJENOST`, `OPIS`,
`NASELJE`, `NAZIV`, `OPCINA_GRAD`, `IZVOR_PODATAKA`, `POVRSINA`, `MIKROREGIJA`,
`OSJETLJIVOST`. Query:

```http
GET .../FeatureServer/0/query?where=1%3D1&outFields=*&resultRecordCount=1&returnGeometry=false&f=json
GET .../FeatureServer/0/query?geometry=<x>,<y>&geometryType=esriGeometryPoint&inSR=3765
    &spatialRel=esriSpatialRelIntersects&outFields=*&f=geojson
```

Other PGŽ services: raster plan WMS `https://gisportal.pgz.hr/server/services/MGIPU/WMS_PPZ/MapServer/WMSServer`
and `MGIPU/WMS_PPUOG_01..03`, REST root `https://gisportal.pgz.hr/server/rest/services?f=json`.

### 5.2 Grad Zagreb (ArcGIS Online and GeoServer)

```text
https://services8.arcgis.com/Usi0jGQwMmBUpFjr/arcgis/rest/services/Geoportal_planirana_namjena/FeatureServer/0
```

Layer `planirana_namjena_grad_zagreb`, polygon, EPSG:3765, `maxRecordCount` 2000, JSON,
geoJSON, PBF. Fields: `Namjena`, `Skupna_namjena`, `Analitika`, `Naziv_plana`,
`Izradivac_plana`, `Izvorno_kartografsko_mjerilo`, `Godina_zadnje_izmjene`. The same data
is on data.gov.hr as SHP, GeoJSON, KML and CSV (dataset `geoportal-planirana-namjena-2023`,
Otvorena dozvola). GUP WMS:
`https://geoportal.zagreb.hr/Public/GUPZagreb_Public/MapServer/WMSServer?service=WMS&request=GetCapabilities`
(86 layers, e.g. `90` Namjena, `62` Urbana pravila; not queryable). INSPIRE-harmonised
2013 land use (DGU): `https://transformiraj.nipp.hr/ows/services/org.4.372e8210-b425-4869-8684-96620ece941b_wms`
and the matching `_wfs` (layer `LU.ZoningElement`).

### 5.3 Municipalities on the pipgis platform (Promet i prostor)

About forty JLS publish their plans as queryable vector WMS:

```text
https://<jls>.pipgis.hr/xyz-services/<pp|pp-ppu|pp-ppug|pp-gup>/wms?service=WMS&request=GetCapabilities
```

Verified: `lumbarda.pipgis.hr/xyz-services/pp/wms` (layers such as
`ppuo_2017_lumbarda_1_polygon` "1. Korištenje i namjena prostora",
`ppuo_2017_lumbarda_4_polygon` "4. Građevinska područja"; CRS EPSG:3765, 3857, 4326;
GetFeatureInfo `application/json`). No WFS on the same base. GetFeatureInfo returns one
attribute:

```json
{"type": "FeatureCollection",
 "features": [{"type": "Feature", "id": "ppuo_2017_lumbarda_1_polygon.83", "properties": {"id": 83, "opis": "Mješovita namjena"}, "geometry": {"...": "..."}}]}
```

Šibenik: `https://sibenik.pipgis.hr/xyz-services/pp-gup/wms` and `.../pp-ppug/wms`. The
full list of pipgis hosts is in the NIPP catalogue (section 8.1, search "pipgis").

### 5.4 Istarska županija (Kaliopa iObčina)

```text
https://www.iopcina.hr/wms_vektor/istra?service=WMS&request=GetCapabilities   (54 vector layers)
https://www.iopcina.hr/wms_raster/istra?service=WMS&request=GetCapabilities   (688 raster layers)
```

### 5.5 Others (from the NIPP catalogue, not probed)

Brodsko-posavska `https://wms.bpzzpu.hr/mapguide/mapagent/mapagent.fcgi?service=wms&REQUEST=GetCapabilities`
(demo-only access constraint), Sisačko-moslavačka `http://zpusmz.geoportal.hr/wms`,
Zagrebačka županija ArcGIS Experience viewer (WMS URL not published), GDi Visios viewers
for Split, Dubrovnik and Dubrovačko-neretvanska (no OGC endpoint found), Zadar county GIS
Cloud viewer (no OGC endpoint).

## 6. ISPU Geoportal Internal JSON API (Observed)

Base: `https://ispu.mgipu.hr/api/v1/`. Undocumented, no OpenAPI, no versioning promise.
Observed by watching the geoportal's own calls; documented here so that nobody has to
rediscover it, not as an integration target. Rule 3 of `CLAUDE.md` applies: the
plan-information step is gated by a reCAPTCHA dialog ("Za nastavak odaberi 'Nisam
Robot'") and must not be automated. The endpoints that answered plain GET requests are
listed with their observed responses; all others require the app's `layerHash` tokens.

| Method and path | Parameters | Response |
|-----------------|------------|----------|
| `GET auth/authz` | none | `{"id": null, "ime": null, "prezime": null, "organizacijaOib": null, "organizacijaNaziv": null, "authz": ["{\"OV_ALAT\": [...], \"OV_IZBORNIK\": [...]}"]}`: anonymous authorisation matrix (tool ids, menu ids) |
| `GET gis/nav-traka-usluga` | none | `[{"label": "Geoportal ISPU", "link": "https://ispu.mgipu.hr/"}, {"label": "ePlanovi", "link": "https://planovi.mgipu.hr/"}, {"label": "eKatalog prostornih planova", "link": "https://katalog.mgipu.hr/"}, ...]` (15 entries) |
| `GET gis/catalog-izbornik` | none | JSON array, 7 top-level panels, 247 nodes (150 KB). Node shape below. |
| `GET gis/get-capabilities-servis` | `servisId`, `layers`, `layerHash` | Proxied capabilities for one configured service; 403 without a valid hash |
| `GET gis/wms` | Standard WMS KVP plus `serviceId`, `layerHash` | Proxied GetMap; 403 `{"succeeded": false, "message": "Neovlašten pristup resursima aplikacije.", ...}` without the hash |
| `GET gis/search-text` | `input` (free text) | Grouped search results, shape below |
| `GET gis/search-kat-opcina` | `input` (name fragment) | `[{"maticniBroj": "334979", "labela": "ZADAR, SAVAR"}]`; prefix search over all k.o., ordered by office name |
| `GET gis/info-lokacija-kat-cestica` | `labela` (parcel number), `maticniBroj` (k.o.) | HTTP 200, a JSON string containing the parcel outline as WKT in EPSG:3765: `"POLYGON ((380593.89 4880915.63, ...))"`. HTTP 204, empty body, when the parcel does not exist |

Catalogue node (layer "Građevinsko područje izvan naselja"):

```json
{
  "id": "134",
  "label": {"hr": "Građevinsko područje izvan naselja", "en": "Detached part of the building area outside a settlement"},
  "type": "sloj",
  "info": {"hash": "vZB9TKwk5Zc", "hashIdentify": "jUwiucjvJY", "hasLegende": true, "hasMetapodaci": false, "hasSastavnice": false},
  "extensionData": {"type": "wms", "isExternal": false, "layerHash": "flmc7VetMc", "serviceId": "10", "url": "wms",
                    "params": {"layers": "224", "format": "image/png"}, "opacity": 0.5, "scales": [10000, 50000]},
  "items": null
}
```

Node `type` values: `glavni_panel`, `stablo` (folder), `sloj` (layer), `podloga` (base
map), `alat_pp_vazeci` and `alat_pp_u_izradi` (plan registry tools), `alat_dokument_isp`,
`info_wfs`. The cadastre layers are DGU services proxied with `serviceId` 4 (DKP) and the
building areas are `serviceId` 10, layers 224 and 225.

Text search response (input `SAVAR 103/2`), one group per result kind:

```json
[
  {"label": {"hr": "Katastarske čestice", "en": "Cadastral plots"}, "total": 1,
   "items": [{"id": "1020011", "label": "KČ 103/2, KO SAVAR Zadar",
              "info": {"hr": "<strong>Kat. čestica:</strong>&nbsp;103/2<br><strong>Kat. općina:</strong>&nbsp;SAVAR<br><strong>Kat. ured:</strong>&nbsp;ZADAR", "en": "..."},
              "source": "katastarska_cestica", "hash": "DSPmzVfWQA"}]},
  {"label": {"hr": "Katastarske općine", "en": "Cadastral districts"}, "total": 0, "items": []},
  {"label": {"hr": "Naselja"}, "total": 0, "items": []},
  {"label": {"hr": "Gradovi i općine"}, "total": 0, "items": []},
  {"label": {"hr": "Adrese"}, "total": 0, "items": []},
  {"label": {"hr": "Dozvole"}, "total": 0, "items": []},
  {"label": {"hr": "Energetski certifikati"}, "total": 0, "items": []},
  {"label": {"hr": "Prostorni planovi"}, "total": 0, "items": []},
  {"label": {"hr": "Dokumentacija o prostoru"}, "total": 0, "items": []}
]
```

Input `PPUO Sali` returns the plan group with `source: "pp_vazeci_stari"` and
`"Oznaka plana: HR-ISPU-PPGO-03794-R07"` in the HTML `info`. The item `id` for a parcel
(`1020011`) is the geoportal's own id, not the OSS parcel id.

The "Lokacijska informacija" tool (select by point, polygon, `Kat. česticom` with k.o.
autocomplete and up to 12 parcels, or KML/GML/GeoJSON upload) produces tabs "Važeći
planovi", "Planovi u izradi", "Uvid u prostorni plan", "Pojmovnik", permits, selected and
neighbouring parcels, spatial units and regimes. Its backend call was not captured
because the captcha dialog precedes it.

## 7. eKatalog Public JSON API

Base: `https://katalog.mgipu.hr/service/api/public/`. Undocumented; the Angular app's
service class names the paths. Responses are `application/json`.

| Method and path | Response |
|-----------------|----------|
| `GET sifarnik/vrstaPlana` | `{"items": [{"key": "96", "value": "DPPR"}, {"key": "92", "value": "PPPPO"}, {"key": "1", "value": "PPŽ"}, {"key": "2", "value": "PPGZ"}, {"key": "4", "value": "PPUG"}, {"key": "5", "value": "PPUO"}, {"key": "9", "value": "GUP"}, {"key": "12", "value": "UPU"}, {"key": "18", "value": "DPU"}, {"key": "13", "value": "PUP"}, {"key": "95", "value": "ISP"}, {"key": "1121", "value": "OST"}, {"key": "97", "value": "PPIGP"}]}` |
| `GET sifarnik/namjenaPlana` | `{"items": [{"key": "1", "value": "Naselje/dio naselja"}, {"key": "2", "value": "Gospodarska/poduzetnička/radna/poslovna zona"}, {"key": "3", "value": "Ugostiteljsko-turistička zona"}, {"key": "4", "value": "Sport i rekreacija"}, {"key": "5", "value": "Povijesna jezgra"}, {"key": "6", "value": "Mješovita zona"}, {"key": "7", "value": "Groblje/proširenje groblja"}, {"key": "11", "value": "Luka"}, {"key": "12", "value": "Golf"}, {"key": "9", "value": "Pojedinačni zahvat"}, {"key": "10", "value": "Ostalo"}]}` |
| `GET geo/config` | `{"items": [...]}`: the catalogue map's layers (DGU orthophoto WMTS with an `authKey`, TK25, and internal WMS `public/geo/internal?id=1..5` for županija, JLS, naselje, katastarska općina, katastarska čestica) |
| `GET geo/external?url=` | Proxy for an external capabilities URL; 400 `"Nedostaje parametar url"` without it |
| `GET metadata/search`, `GET izvjestaj/search` | Plan metadata search. Search attributes named in the app: `nazivPlana`, `oznaka`, `zupanija`, `gradOpcina`, `vrstaPlana`, `namjena`, `organizacija`, `datumObjavePlana`, `datumZadnjeRevizije`, `datumStavljanjaIzvanSnage`, `obuhvatZop`, `povrsinaNaKopnu`, `planovi`, `prilozi`; default sort `datumObjavePlana desc`. Every GET and POST variant tried returned 500 `"Problem s metadata zahtjevom"` or 404; the request contract is not verified. |

`namjenaPlana` is the plan's declared purpose (what a UPU or DPU is for), not the
land-use code of a polygon.

## 8. Catalogues and Registers

### 8.1 NIPP GeoNetwork CSW

```text
https://geoportal.nipp.hr/geonetwork/srv/eng/csw
```

Full-text search (CSW 2.0.2 KVP, CQL):

```http
GET ?service=CSW&version=2.0.2&request=GetRecords&typeNames=csw:Record&resultType=results
    &elementSetName=full&maxRecords=100&constraintLanguage=CQL_TEXT&constraint_language_version=1.1.0
    &constraint=AnyText like '%Građevinska područja%'
```

Response: `csw:GetRecordsResponse` with `numberOfRecordsMatched` and `csw:Record` elements
carrying `dc:identifier`, `dc:title`, `dc:type` (`dataset`, `service`, `series`),
`dc:subject`, `dct:abstract`, `dc:URI` (service URLs). Today: 446 matches for "Građevinska
područja", 93 for "ISPU", 980 for "Planirano korištenje zemljišta" (most are Zagreb and
municipal records). Record by id:

```http
GET ?service=CSW&request=GetRecordById&version=2.0.2&outputSchema=http://www.isotc211.org/2005/gmd
    &elementSetName=full&id=9310e114-b20d-4282-a1dc-6bc1c1ef20be
```

Response: ISO 19139 `gmd:MD_Metadata` (29 KB for the Zadar county plan record). The
`/geonetwork/srv/eng/q` search endpoint returns 500. The newer Elasticsearch endpoint
`POST /geonetwork/srv/api/search/records/_search` accepts Query DSL (per the regional
research agent, not exercised here).

### 8.2 NIPP register API

```text
https://registri.nipp.hr/api/izvori/?format=json&limit=2000     (all 1686 sources)
https://registri.nipp.hr/api/izvori/<id>/                        (one source)
https://registri.nipp.hr/api/izvori/xml/?identifier=<oznaka>     (ISO XML)
```

Source 246 (building-areas WFS), abbreviated:

```json
{"id": 246, "jedinstvena_oznaka": "0248", "naziv_izvora": "Građevinska područja - WFS",
 "sazetak_izvora": "Podaci o građevinskim područjima izvan naselja nastali obradom prostornih planova ...",
 "vrsta_izvora": {"id": 3, "vrsta_izvora": "usluga"},
 "format_podataka": [{"id": 93, "name": "WFS"}],
 "nipp_teme": [{"id": 18, "skupina": "III", "broj": 4, "naziv": "Korištenje i namjena zemljišta", "naziv_engleski": "Land use"}],
 "geografski_obuhvat": {"id": 225, "...": "..."}}
```

The HTML pages `registri.nipp.hr/izvori/view.php?id=` are gone (they return "Ne postoji
traženi izvor"); use the API. MPGI is subject 236 (`/subjekti/236`).

### 8.3 data.gov.hr CKAN

```text
https://data.gov.hr/ckan/api/3/action/package_search?q=prostorni+plan
```

Standard CKAN. 21 datasets `prostorni-planovi-<županija>-wms` (publisher marked
inactive; resources are metadata XML pointing at the `gisN.mgipu.hr` WMS), Zagreb's
`geoportal-planirana-namjena-2023` (SHP, GeoJSON, KML, CSV), DGU's
`planirana-namjena-zemljita-2013-grada-zagreba-inspire`. No nationwide download beyond
the WFS in section 3.

## 9. Cadastre-Side Geometry Endpoints for Matching

Plans do not reference parcel identifiers, so matching is spatial and needs parcel
outlines. Three sources exist; the first is the one this repository already uses.

### 9.1 OSS ATOM download of the digital cadastral map

```text
https://oss.uredjenazemlja.hr/oss/public/atom/atom_feed.xml
https://oss.uredjenazemlja.hr/oss/public/atom/ko-<MBKO>.zip
```

Feed: Atom 1.0, 3495 entries (one per cadastral municipality), regenerated nightly
(feed `updated` 2026-09-13T23:00, SAVAR entry 2026-09-14T00:41). No authentication.
Entry:

```xml
<entry>
  <title>Cadastral municipality SAVAR</title>
  <link href="https://oss.uredjenazemlja.hr/oss/public/atom/ko-334979.zip" rel="alternate"
        type="application/x-gmz;charset=utf-8;version=3.2.1" hreflang="hr" title=""/>
  <id>https://oss.uredjenazemlja.hr/oss/public/atom/ko-334979.zip</id>
  <updated>2026-09-14T00:41:42Z</updated>
  <polygon>208311.05 4608969.52 744179.92 4608969.52 744179.92 5161549.72 208311.05 5161549.72 208311.05 4608969.52</polygon>
  <category term="http://www.opengis.net/def/crs/EPSG/0/3765" label="HTRS96/TM"/>
</entry>
```

The `<polygon>` is the national extent on every entry, not the k.o. extent. Zip contents:
`katastarske_cestice.gml`, `katastarske_opcine.gml`, `nacini_uporabe_zemljista.gml`,
`nacini_uporabe_zgrada.gml`, GML 2 feature collections (namespace `oss`), EPSG:3765.
Parcel attributes: `CESTICA_ID` (equals the parcel id `key1` of the OSS public JSON API),
`BROJ_CESTICE` (building parcels with a leading asterisk, `*35/1`), `POVRSINA_GRAFICKA`,
`MATICNI_BROJ_KO`, `GEOM` (Polygon, occasionally MultiPolygon). `GMLParser` in this
repository reads this file; `to_wkt()` produces the WKT used in section 3.5.

### 9.2 INSPIRE Cadastral Parcels WFS (DGU, open)

```text
https://api.uredjenazemlja.hr/services/inspire/cp/wfs?SERVICE=WFS&REQUEST=GetCapabilities&VERSION=2.0.0
https://api.uredjenazemlja.hr/services/inspire/cp_wms/wms?service=WMS&request=GetCapabilities&version=1.3.0
```

WFS 2.0.0, feature types `cp:CadastralParcel` and `cp:CadastralZoning` (INSPIRE CP 4.0
schema: `inspireId`, `label`, `nationalCadastralReference`, `areaValue`, `geometry`,
`referencePoint`, `validFrom`, `validTo`, `zoning`), EPSG:3765, GeoJSON, GML 3.2, KML,
SHAPE-ZIP, CSV; `CountDefault` 1000; documented limits 1000 parcels and a 2000 m diagonal
per request. Not verified: every GetFeature request timed out today, so attribute values
and the `nationalCadastralReference` format were not seen. The path
`https://geoportal.dgu.hr/services/inspire/cp/wfs` returns 404.

### 9.3 OSS GeoServer (token-protected)

`https://oss.uredjenazemlja.hr/OssWebServices/wfs` answers GetCapabilities anonymously
(55 feature types, e.g. `oss:DKP_CESTICE`, `oss:K_IZM_CESTICE`, `jis:CESTICE`) but every
data request returns 401 `"Nedostaje parametar token u zahtjevu."`. The URL
`https://oss.uredjenazemlja.hr/wfs` listed in `croatian-cadastral-api-specification.md`
serves the OSS web app's HTML, not a WFS. Not a target for this project.

### 9.4 DGU base maps used by the ministry portals

Orthophoto and topographic WMTS at `https://geoportal.dgu.hr/services/sla/<name>/wmts`
need an `authKey` query parameter issued to registered users. The key visible in the
ministry portals' configuration is theirs; do not reuse it.

## 10. New-Generation Plan Model (Pravilnik NN 152/2023)

### 10.1 Legal basis

Pravilnik o prostornim planovima, NN 152/2023, in force since 1 January 2024
(<https://narodne-novine.nn.hr/clanci/sluzbeni/2023_12_152_2228.html>). Uredba o ISPU,
NN 115/2015 (HTRS96/TM mandatory; vector delivery as topologically clean GML or SHP plus
raster and PDF). Zakon o prostornom uređenju, NN 155/2025, in force since 1 January 2026
(čl. 31 to 36 ISPU; čl. 37 lokacijska informacija generated electronically from ISPU
where a new-generation plan exists, otherwise issued by the municipality within fifteen
days for up to five parcels).

### 10.2 Structure

The Pravilnik defines the model in its annexes: Prilog I (Pregled prostornih tema, the
layer and theme code list), Prilog II (Sadržaj namjena prostora), Prilog III (Relacijske
tablice), Prilog IV (Kartografski prikazi). The annexes are published in Narodne novine
only as 165 JPG page images; the ministry describes the model as a "digital rulebook"
embedded in ePlanovi Editor. No GML application schema, GeoPackage template or
attribute dictionary is published. The Pravilnik names no file format and no attribute
names; the CRS comes from the Uredba.

Layer groups (26 layers):

| Group | Layers | Content |
|-------|--------|---------|
| 0 Obuhvat | `OB-1-1` | Plan extent |
| 1 Osnovno korištenje prostora | `KN-1-1` primarna namjena (one to three primary designations), `KN-1-2` sekundarna namjena, `KN-2-x` građevinska područja, `KN-3-1` pravila provedbe, `KN-3-2` obveza izrade GUP/UPU, `KN-3-3` urbana sanacija i preobrazba | Land use, building areas, implementation |
| 2 Infrastrukturni sustavi | `IS-1-1` to `IS-4-4` | Transport, communications, energy, water |
| 3 Posebne mjere | `ZP-1-1` to `ZP-3-2` | Values, restrictions, special uses |

Theme code grammar: `<layer>-<L><TTT>` where `<L>` is the plan level (1 DPPR, 2 PPŽ or
PPGZ, 3 PPUO or PPUG, 4 GUP, 5 UPU, 6 PPPPO) and `<TTT>` the theme. Each row of Prilog I
also carries the map label (oznaka teme), name, applicable plan types, inclusion scales
and the RGB fill. Examples read from the annex images:

| Code (level x) | Label | Theme |
|----------------|-------|-------|
| `KN-1-1-x001` to `x006` | S1 to S6 | Stambena namjena |
| `KN-1-1-x051` to `x054` | M1 to M4 | Mješovita namjena |
| `KN-1-1-x100`, `x1nn` | D, D1, D2, D3 | Javna i društvena (upravna, socijalna, zdravstvena) |
| `KN-1-1-x401` | T1 | Ugostiteljsko-turistička namjena u građevinskom području naselja |
| `KN-1-1-x402` | T2 | Ugostiteljsko-turistička u izdvojenom građevinskom području izvan naselja, s gradnjom smještajnih građevina |
| `KN-1-1-x403` | T3 | Same, bez gradnje smještajnih građevina |
| `KN-1-1-x600` to `x608` | R, R1 to R8 | Sportsko-rekreacijska (golf, sports buildings, playgrounds, amusement park, winter sports, beaches) |
| `KN-1-1-x70n` | Z | Zelene površine |
| `KN-1-1-x290` | | Groblje |
| `KN-1-1-x9nn` | | Površine infrastrukturnih sustava (prometna, pješačka, biciklistička, parkirališna, luke) |
| `KN-2-1-x201` to `x204` | GPI | Izdvojeno građevinsko područje izvan naselja, with izgrađeno / neizgrađeno / neuređeno sub-codes |
| `KN-2-1-x301` | NA | Građevinsko područje naselja |
| `KN-2-1-x401` | | Izdvojeni dio građevinskog područja naselja |

Note that the T2/T3 semantics changed against the old plans: in old plans T1/T2/T3 mean
hotel / tourist settlement / camp (section 3.3), in the new model T1/T2/T3 distinguish
inside-settlement, detached-with-accommodation and detached-without-accommodation.

### 10.3 Access today and how to detect change

No new-generation plan is downloadable or served through OGC services. The ePlanovi
front end contains export mappings for GeoPackage, GeoJSON, CSV, XLSX and PDF, and the
Editor guide says any drawn layer can be downloaded in a chosen format, but both are
login-only (NIAS, business certificate). The state plan (DPPR) is still in preparation.
The EU-funded transformation of about 1500 old plans runs until September 2026.

To detect publication without polling the login-only apps: query the NIPP CSW for new
MPGI records (section 8.1), re-read `gis/catalog-izbornik` for new `sloj` nodes under
"Registar prostornih planova" (section 6), and probe the `gisN.mgipu.hr/srv1/` proxy for
a new workspace name once one is announced. The CSW record type `service` with a
`dc:URI` containing `/wfs` is the signal to look for.

## 11. Matching Recipe

1. Resolve the parcel: k.o. code plus parcel number through the existing OSS JSON API
   (parcel id, area, possessors) and the ATOM GML (geometry). Normalise the number as
   `GMLParser` expects (`*35/1` for building parcels).
2. Building area: two `INTERSECTS` queries on the WFS (section 3.5). Compute the overlap
   fraction locally (shapely) because parcels straddle boundaries drawn at 1:5000; apply a
   small negative buffer (0.5 m) to the parcel before testing to drop sliver hits. Result:
   inside settlement area, inside a detached zone with code and name, or outside.
3. Detail: pick the county workspace from the parcel's county (via k.o. to JLS to county,
   or the WFS `zup_rb` of the nearest polygon), select the covering sheets by bounding box
   (section 2.5), and give the caller a GetMap URL of the `KN_1_1` sheet clipped to the
   parcel bbox for human reading.
4. Land registry: LR unit to sheet A parcels to cadastral parcels, then steps 1 to 3.
   Match on the cadastral side only (geometry exists only there); record the k.o. and
   plan revision (`ozn_ispu`) used.
5. Regional override: where the parcel's county or city has a vector service with full
   land-use attributes (section 5), query it as well and report both sources.
6. Output must carry the disclaimer of section 3.6 and the dataset date.

Verified outcome for the mock-server sample parcels of SAVAR (103/2, 45, 396/1, 279/6):
all outside the building areas of PPUO Sali; the nearest settlement polygon is Savar's
`GPN` (izvor 4.5, 212 230 m2) to the east; the T2 zones "SAVAR - UVALA ILO" and "SAVAR -
UVALA OVČA" and the T3 camps of Zaglav and Veli Rat are the tourist zones of the
municipality.

## 12. Verification Log and Open Items

Verified today with live requests: sections 2 (Z01 to Z21 capabilities where reachable,
GetMap 1.1.1 and 1.3.0, GetLegendGraphic), 3 (all operations and examples), 4 (brownfield
capabilities), 5.1, 5.2, 5.3 (Lumbarda), 6 (all listed endpoints), 7 (`sifarnik/*`,
`geo/config`, `geo/external`), 8.1, 8.2, 8.3 (record counts from the regional agent),
9.1 (feed and SAVAR zip), 9.3 (401 behaviour), 10 (annex images OCR by the ISPU agent).

Not verified or open:

- Workspaces Z04, Z14, Z20 (502 on all mirrors today) and the RGN geohazard feature types.
- GetFeatureInfo on raster sheets (502 during the test; band values per the ISPU agent).
- The eKatalog `metadata/search` request contract.
- The INSPIRE CP WFS GetFeature response and the `nationalCadastralReference` format.
- The backend call and response of the geoportal's captcha-gated plan report.
- The complete `ozn_namjen` code list and a full transcription of Prilog I and II.
- Whether the building-areas WFS is served by gis1 to gis3 as well.
- Terms of use of the regional and vendor services in section 5 (each has its own).
