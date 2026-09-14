# Web Map Exploration

Exploratory notes for a possible web front end to this project: a page that
shows a parcel on a map, lets the user draw an area, and lists the parcels in
that area with their possessors, land-registry units and building-area
(građevinsko područje) designation. Nothing here is implemented. The document
records which map sources and libraries can be used openly, which cannot, and
the stack that fits the data this repository already handles.

Status: exploration, not implemented. Findings dated 2026-09-14; licences and
free tiers change, so re-check the sources before building.

Related: [spatial-planning-api-specification.md](spatial-planning-api-specification.md)
(building-areas WFS, plan-sheet WMS, cadastre geometry endpoints),
[gateway-service.md](gateway-service.md) (the hosted REST service such a page
would call), [croatian-cadastral-api-specification.md](croatian-cadastral-api-specification.md).

## Scope Notice

This project is a demonstration. Its defaults use the included mock server.
Every government or third-party service named below is listed so that the
option is documented, not as an instruction to use it. Whoever builds the page
verifies their right to use each service and its data (terms of use, data
protection) and does so at their own risk; see `docs/legal.md`. Possessor and
owner names are personal data and stay out of the repository and out of any
cache that outlives a request longer than it must.

## 1. What the Page Has to Do

1. Show a base map of Croatia with an optional aerial or satellite background.
2. Draw cadastral parcel boundaries and building-area polygons on top of it.
3. Let the user pick one parcel (by number and k.o., or by clicking) and centre on it.
4. Let the user draw a polygon or rectangle and get every parcel inside it.
5. For those parcels, show what the SDK already returns: possessors, LR unit
   reference, owners and encumbrances on request, and the zoning verdict of
   `get_parcel_zoning`.

Everything in step 5 exists in `api/`. The new work is the map (steps 1 to 4)
and a thin HTTP layer between the browser and the SDK, which is what
[gateway-service.md](gateway-service.md) already proposes.

## 2. Map Layers and Their Sources

The map is three layers with three different licensing situations.

### 2.1 Base map (streets, place names)

| Source | Data and licence | Cost and limits | Fit |
|---|---|---|---|
| OpenFreeMap (`openfreemap.org`) | OpenStreetMap vector tiles, ODbL; attribution "© OpenStreetMap contributors" | Free public instance, no key, no registration, no request limit; self-hostable | Recommended default. Matches a project meant to be forked. |
| Protomaps (PMTiles) | OpenStreetMap, ODbL; same attribution | Free download of a single PMTiles file (a Croatia extract is a few hundred MB), served from any static host or object store, no tile server | Recommended for self-hosting or offline demos. |
| OpenStreetMap raster tiles (`tile.openstreetmap.org`) | ODbL | Free but governed by the OSMF tile usage policy: attribution, real `User-Agent` and `Referer`, 7-day client caching, no bulk download, no heavy use; access can be cut without notice | Development only. Not for a public site. |
| MapTiler, Stadia, Thunderforest | OpenStreetMap-derived, proprietary hosting | Freemium, API key, monthly quota | Not needed; skip. |
| Google Maps Platform | Proprietary | See section 4 | Not recommended here. |

### 2.2 Aerial and satellite imagery

OpenStreetMap-based sources have no imagery at all. For parcels only the first
row below is useful: a Croatian parcel is a few pixels wide at 10 m per pixel.

| Source | What it is | Licence | Fit |
|---|---|---|---|
| DGU digitalni ortofoto (DOF) WMS, `geoportal.dgu.hr` | Aerial orthophoto, about 0.5 m per pixel nationwide, better in the 2021 and 2022 cycles; the same imagery the official OSS map shows behind parcels | DGU stated in a freedom-of-information answer that the DOF WMS for anonymous users is under the Croatian Open Licence (`data.gov.hr/otvorena-dozvola`), with an attribution line naming DGU, the data type and the dates. An older 2019 statement to OSM Croatia allowed non-commercial reuse and forbade redistribution of the underlying data. Read the current terms on the geoportal before use. | The one imagery source on which cadastral boundaries fit the picture. Recommended as a switchable layer. |
| DGU HOK and TK25 WMS | Croatian base map 1:5000 and topographic map 1:25000 | Same as above | Optional. |
| Copernicus Sentinel-2 | Open satellite imagery, 10 m per pixel | Open; the ready-made EOX "Sentinel-2 cloudless" WMTS tiles are non-commercial with attribution | Scenic background only. |
| NASA GIBS and similar | 250 m and coarser | Public domain | Not useful. |
| Esri World Imagery, Mapbox Satellite, Bing | High resolution, proprietary | Free tiers with keys, own attribution rules; Bing and Google imagery may not be used in third-party map libraries | Not needed. |

Georeferencing matters more than resolution here. Google's and other
commercial imagery in Croatia is not aligned to HTRS96 as tightly as the DGU
orthophoto; cadastral lines drawn over it sit a few metres off fences and
buildings, which users read as an error in the cadastre. On the DOF they line
up.

### 2.3 Cadastral parcels and building areas (the overlay)

Both come from sources this repository already reads, in EPSG:3765:

- Parcel polygons: the OSS ATOM feed (GML per k.o., `CESTICA_ID` equals the
  public API's parcel `key1`), parsed by `GMLParser`; or the INSPIRE cadastral
  parcels WFS at `api.uredjenazemlja.hr/services/inspire/cp/wfs`, which timed
  out on every 2026-09-14 attempt and caps results at 1000 features or 2 km;
  or the INSPIRE cadastral parcels WMS, display only. See
  [spatial-planning-api-specification.md](spatial-planning-api-specification.md) section 9.
- Building areas: the nationwide building-areas WFS (`Gradj_podrucje_naselje`,
  `Gradj_podrucje_izvan_naselja`), already wrapped by `PlanningWFSClient`,
  Fees and AccessConstraints NONE, with the dataset's own "not for official use"
  disclaimer. See section 3 of the same document.
- Plan sheets: the county raster WMS, one layer per sheet, for a "show me the
  plan" toggle. Section 2 of the same document.

Whether parcel polygons may be republished from the site's own server is the
open question in section 6. The pattern that avoids it is to fetch geometry per
request for the area the user drew and proxy it, rather than pre-building a
nationwide parcel tile set.

## 3. Map Libraries

All three candidates are BSD-licensed and free.

| Library | Strengths | Weaknesses | Drawing tool |
|---|---|---|---|
| OpenLayers | Native WMS, WFS, GML and arbitrary projections through proj4, so EPSG:3765 sources render without reprojection; mixes raster and vector sources; renders OpenFreeMap vector tiles through `ol-mapbox-style` | Larger API, plainer default look | `ol/interaction/Draw`, `ol-ext` |
| MapLibre GL JS | Best-looking vector rendering, the natural client for OpenFreeMap and PMTiles | Web Mercator only; every overlay must arrive in WGS84 or EPSG:3857; WMS only as a raster source requested in EPSG:3857 | Terra Draw, `mapbox-gl-draw` |
| Leaflet | Smallest and simplest; raster tiles and GeoJSON | No vector tiles without plugins, no native WMS feature queries, projection support via `Proj4Leaflet` only | Leaflet-Geoman, Leaflet.draw |

## 4. Google Maps Platform, Assessed

Google Maps was considered because of its familiarity and imagery.

- Cost: the Maps JavaScript API needs an API key with a billing account.
  Since March 2025 the Dynamic Maps SKU includes 10,000 free map loads per
  month (one per page view), satellite view included; about 7 USD per 1,000
  loads beyond that. The free Embed API (iframe) allows only markers, places
  and routes, so it cannot show parcels.
- Overlays: allowed. GeoJSON through the Data layer or `Polygon` objects, WMS
  through `ImageMapType` with a per-tile EPSG:3857 bounding box, drawing
  through the Drawing Library. Everything must be converted to WGS84 first.
- Terms that bite: no caching, pre-fetching or storing of tiles or imagery; no
  tracing or deriving data from it; Google content may not be shown in a
  non-Google map library, and a non-Google base map may not be shown under
  Google content, which rules out the DGU orthophoto layer; the key is
  restricted per domain, so each deployer of an open-source page brings their
  own; logo and attribution stay visible.
- Imagery alignment: see section 2.2. Parcel boundaries visibly misfit.

Conclusion: it adds a billing dependency and a licence that excludes the one
imagery layer that fits the cadastre, and gives nothing the open stack lacks.
Not recommended for this page.

## 5. Recommended Stack

- Front end: OpenLayers. Base layer OpenFreeMap vector tiles via
  `ol-mapbox-style`; optional DGU DOF WMS layer requested in EPSG:3765;
  optional county plan-sheet WMS layer; parcel and building-area polygons as
  vector layers in EPSG:3765, no reprojection anywhere on the client. A draw
  interaction for polygon and rectangle.
- Back end: the gateway of [gateway-service.md](gateway-service.md), FastAPI,
  reusing the SDK. Two additions to its REST surface:
  - `GET /parcels/{municipality}/{parcel_number}/geometry`, GeoJSON in
    EPSG:3765 or EPSG:4326 on request (`get_parcel_geometry` already does the
    work).
  - `POST /areas/parcels` with a polygon body, returning the parcels that
    intersect it, then the per-parcel lookups the caller asks for
    (`detail=registry|owners|zoning`) with the same list semantics as
    `get-parcel` (per-item status, partial failure).
- Area query: intersect the drawn polygon locally against the cached GML of
  every k.o. whose extent it touches. `geometry_ops.polygons_intersect` is
  correct but linear; a whole k.o. needs a spatial index, so add shapely with
  an `STRtree` over the parsed parcels, built once per k.o. and kept in
  memory. The INSPIRE WFS with `INTERSECTS` is the fallback, subject to its
  caps and timeouts.
- Per-parcel data: the existing client with its rate limiter; results cached
  per parcel with the gateway's cache TTLs, owners cached shortest.
- Runner-up: MapLibre GL JS with OpenFreeMap and Terra Draw, if appearance
  outweighs projection fidelity. The DGU WMS is then requested in EPSG:3857,
  which it advertises, and all polygons are converted to WGS84 on the server
  (HTRS96 to WGS84 is a null datum shift, about 1 m, pyproj needs no grids).

## 6. Open Items

1. Current DGU terms for the DOF, HOK and TK WMS: confirm on
   `geoportal.dgu.hr` that the Open Licence answer applies to embedding on a
   third-party site, and record the exact attribution wording.
2. Redistribution of parcel geometry: whether polygons from the ATOM feed may
   be served from the project's own server, or only fetched and proxied per
   request. Until answered, do not pre-build parcel tiles.
3. INSPIRE cadastral parcels WFS availability: every GetFeature timed out on
   2026-09-14; retest before relying on it as the fallback.
4. Personal data: an area query that lists possessors of hundreds of parcels
   is a bulk personal-data extraction. Decide the caps (area, parcel count,
   rate) and whether owner detail needs a per-parcel click rather than a list.
5. Building-areas dataset is a September 2024 interpretation of the plans,
   "not for official use"; the disclaimer must be visible on the map, not only
   in the API response.
6. Mock server: add `/planning/wfs`-style imitations for the parcel geometry
   endpoints so the page works end to end against `localhost:8000`.

## 7. Sources Consulted (2026-09-14)

- OpenFreeMap: <https://openfreemap.org/>
- OSMF tile usage policy: <https://operations.osmfoundation.org/policies/tiles/>
- OpenMapTiles and Protomaps: <https://openmaptiles.org/>, <https://protomaps.com/>
- DGU answer on DOF WMS usage (imamopravoznati.org):
  <https://imamopravoznati.org/request/koristenje_dof_podataka_dgu>
- OSM Croatia on DGU network-service rights, 2019:
  <https://osm-hr.org/2019/06/04/pravo-koristenja-mreznih-usluga-prostornih-podataka-drzavne-geodetske-uprave/>
- DGU, how to obtain spatial data: <https://dgu.gov.hr/kako-doci-do-prostornih-podataka/6764>
- Google Maps Platform pricing changes, March 2025:
  <https://developers.google.com/maps/billing-and-pricing/march-2025>
