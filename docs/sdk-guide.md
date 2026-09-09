# Python SDK Guide

The `cadastral_api` package is the foundation the CLI and the MCP server are built
on. It gives you a rate-limited HTTP client, Pydantic V2 models for every response,
and GIS helpers for parcel geometry. Everything here runs against the included
mock server; see [legal.md](legal.md).

## Installation

```bash
pip install -e ./api
```

Requires Python 3.12 or newer.

## Configuration

The client reads a `.env` file and these environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `CADASTRAL_API_BASE_URL` | `http://localhost:8000` | Upstream address, the mock server by default |
| `CADASTRAL_API_TIMEOUT` | `10.0` | Request timeout in seconds |
| `CADASTRAL_API_RATE_LIMIT` | `0.375` | Minimum seconds between upstream requests |
| `CADASTRAL_CACHE_DIR` | `~/.cadastral_api_cache` | Where downloaded GML files are kept |

All of them can be overridden per client:

```python
from cadastral_api import CadastralAPIClient

client = CadastralAPIClient(
    base_url="http://localhost:8000",
    timeout=10.0,
    rate_limit=0.375,
    cache_dir="./gis_cache",
)
```

Use the client as a context manager so the HTTP connection is closed.

## The three-step lookup

The upstream API needs a municipality code before it can find a parcel, and a
parcel id before it can return details. The SDK exposes each step and also
shortcuts across them.

```python
from cadastral_api import CadastralAPIClient

with CadastralAPIClient() as client:
    # 1. Municipality name to registration number
    municipalities = client.find_municipality("SAVAR")
    code = municipalities[0].municipality_reg_num          # "334979"

    # 2. Parcel number to parcel id
    results = client.find_parcel("103/2", code)
    parcel_id = results[0].parcel_id

    # 3. Full details
    parcel = client.get_parcel_info(parcel_id)
    print(parcel.parcel_number, parcel.area_numeric, "m²")
    print(parcel.total_possessors, "possessors")
    for land_type, area in parcel.land_use_summary.items():
        print(f"  {land_type}: {area} m²")

    # Steps 2 and 3 in one call
    parcel = client.get_parcel_by_number("103/2", code)
```

`find_municipality` also accepts `office_id` and `department_id` to list the
municipalities of one cadastral office. `find_parcel` matches partially: "114"
returns 114, 1140/1, and so on.

## Land registry units

A land registry unit (zemljišnoknjižni uložak) holds the legal record: sheet A
lists parcels, sheet B owners, sheet C encumbrances. Pending entries (plombe) mark
changes in progress.

```python
with CadastralAPIClient() as client:
    # From a parcel
    unit = client.get_lr_unit_from_parcel("103/2", "SAVAR")

    # Or directly, when you know the unit number and main book id
    unit = client.get_lr_unit_detailed("769", 21277)

    print(unit.summary())
    # {'unit_number': ..., 'main_book': ..., 'total_parcels': ..., 'total_area_m2': ...,
    #  'num_owners': ..., 'has_sheet_c_entries': ..., 'is_condominium': ...,
    #  'has_pending_plombe': ..., 'pending_plombe': [...]}

    for owner in unit.get_all_owners():
        print(owner.name, owner.address)

    for parcel in unit.get_all_parcels():
        print(parcel.parcel_number, parcel.area_numeric)

    if unit.has_pending_plombe():
        details = client.get_plombe_details(unit)   # one extra request per plomba
```

`unit.cadastre_harmonized` reports whether the cadastre and the land registry agree
on the source parcel, when the unit was reached from a parcel. `unit.is_condominium()`
detects condominium units (etažno vlasništvo) from `lr_unit_type_name`, which is more
reliable than the upstream `condominiums` flag; individual apartments appear as
shares in `unit.ownership_sheet_b.lr_unit_shares`. `unit.lr_unit_type` is the same
information as an enum (`LRUnitType.OWNERSHIP`, `CONDOMINIUM_DEFINED_SHARES`, `OTHER`).

### Finding the main book

The unit endpoint wants a main book id. When you only know the name (normally the
cadastral municipality), let the client resolve it, or search yourself:

```python
with CadastralAPIClient() as client:
    unit = client.get_lr_unit_detailed("769", main_book_name="SAVAR")

    for book in client.find_main_book("SAVAR"):
        print(book.main_book_id, book.main_book_name, book.court_name)   # 21277 SAVAR ZADAR
    for book in client.find_book_of_dc("ZADAR"):        # knjige položenih ugovora (KPU)
        print(book.book_id, book.book_name, book.office_name)
    for sheet in client.find_possession_sheet("363", "334979"):   # cadastre possession sheets
        print(sheet.possession_sheet_id, sheet.sheet_number)
```

A name that matches several books raises `LR_UNIT_NOT_FOUND` with reason
`main_book_ambiguous` and the candidates in `details`.

### Entry provenance

Every owner on sheet B carries the registration entry that put them there:

```python
for share in unit.ownership_sheet_b.lr_unit_shares:
    for owner in share.owners:
        entry = owner.entry                       # None on older shares
        if entry:
            print(entry.order_number, entry.entry_date, entry.diary_number,
                  entry.action_type, entry.priority_diary_number,
                  entry.transferred_from_unit, entry.description_text)
    for note in share.share_entries:              # zabilježbe on this share alone
        print(note.order_number, note.description_text)
    for sub in share.sub_shares:                  # co-owners of a divided share
        print(sub.description, [o.name for o in sub.owners])
```

`share.sub_shares_and_entries` holds both kinds as typed objects (`LRShare` or
`LREntry`), routed by the presence of `lrUnitShareId`. `OwnershipSheetB.owner_rows()`
and `share_entry_rows()` flatten them into the dicts the CLI and the MCP server
emit. On sheet C, `entry.amount` is the secured amount as sent ("134.000,00 EUR")
and `entry.amount_value` / `entry.amount_currency` the parsed number and currency.

### Sheet A1 variants

The parcel list of a unit arrives under one of two keys, never both:
`lrParcels` (lean land-register records, where `address` is the culture or
toponym of the old land register, not a location) or `cadParcels` (full cadastre
records). `unit.sheet_a1_source_key` says which; both populate
`unit.possessory_sheet_a1.cad_parcels`, with `parcel_parts` typed as `ParcelPart`
in both shapes.

### Building parcels

The API spells building parcels with a leading asterisk (`*35/1`). Pass any of
`"35/1.ZGR"`, `"35/1 ZGR"`, `"zgr. 35/1"` or `"*35/1"` to `find_parcel`,
`get_parcel_by_number` or `get_lr_unit_from_parcel`; `normalize_parcel_number`
maps them to the API spelling. `parcel.is_building_parcel` is true for them,
`parcel.parcel_number_display` renders `zgr. 35/1`, and they have no land
registry unit of their own (`get_lr_unit_from_parcel` reports
`parcel_not_in_land_registry`). Asking for the land parcel `"35/1"` when only
`*35/1` exists raises `PARCEL_NOT_FOUND` with reason `only_building_parcel_exists`,
so the two are never confused.

### Unknown server fields

Every model keeps keys it does not declare in `source_fields`. The client
reports them according to `unknown_fields` (`"warn"` logs each new key path once,
`"ignore"`, `"error"` raises `INVALID_RESPONSE` with reason `unknown_fields`;
also `CADASTRAL_API_UNKNOWN_FIELDS`). The coverage gate
`api/src/cadastral_api/tests/test_api_coverage.py` keeps `source_fields` empty
on every committed fixture.

## Parcel geometry

Geometry comes from INSPIRE GML files published per municipality. The client
downloads the file once, caches it under `CADASTRAL_CACHE_DIR`, and parses the
parcel out of it. Next to each ZIP the cache keeps a `source.txt` marker with
the base URL it was downloaded from; a client configured for a different server
downloads the municipality again instead of reusing that copy. The method returns
`None` when the parcel is not in the file.

```python
with CadastralAPIClient() as client:
    geometry = client.get_parcel_geometry("103/2", "334979")
    if geometry:
        print(geometry.povrsina_graficka, "m² (graphical area)")
        print(geometry.center, geometry.bounds)
        print(geometry.to_wkt())
        feature = geometry.to_geojson()      # GeoJSON Feature, properties carry map_url
        print(geometry.map_url())            # interactive map centred on the parcel
        print(geometry.map_url(zoom=20))     # closer, for very small parcels

    # Download URL for the whole municipality, for QGIS and similar tools
    url = client.get_municipality_gis_download_url("334979")

    # Interactive map link for a parcel
    map_url = client.get_map_url(parcel_id)
```

Coordinates are in EPSG:3765 (HTRS96 / Croatia TM). The GML parser is available on
its own as `cadastral_api.GMLParser` when you already have a file.

## Error handling

Every failure raises `CadastralAPIError` carrying an `ErrorType`:

```python
from cadastral_api import CadastralAPIClient, CadastralAPIError, ErrorType

with CadastralAPIClient() as client:
    try:
        parcel = client.get_parcel_by_number("999/9", "334979")
    except CadastralAPIError as e:
        if e.error_type is ErrorType.PARCEL_NOT_FOUND:
            print("no such parcel")
        elif e.error_type in (ErrorType.CONNECTION, ErrorType.TIMEOUT):
            print("upstream unreachable, is the mock server running?")
        else:
            print(e.error_type, e.details)
```

Error types: `CONNECTION`, `TIMEOUT`, `RATE_LIMIT`, `INVALID_RESPONSE`,
`PARCEL_NOT_FOUND`, `MUNICIPALITY_NOT_FOUND`, `LR_UNIT_NOT_FOUND`, `SERVER_ERROR`.
Connection and rate-limit errors are retried with backoff before being raised.

## Things to know about the data

- Ownership fractions are optional. Many possessor records have no `ownership`
  field, so `ownership_decimal` is `None`.
- The upstream returns area as a string. Models convert it; use `area_numeric` for
  an integer.
- One parcel can have several possession sheets.
- The `condominiums` boolean on a land registry unit is unreliable; use
  `is_condominium()`.
- Models validate strictly. Unexpected upstream data raises
  `ErrorType.INVALID_RESPONSE`; unknown keys are kept in `source_fields` and
  reported per the client's `unknown_fields` setting.
- Entry kinds are `uknjižba`, `predbilježba`, `zabilježba` and the generic
  `upis`; a deletion sets `entry.deletes_prior_entry`. `share.share_status` is
  `active` for status 0 and `historical` otherwise.
- A parcel whose links name different units raises `LR_UNIT_NOT_FOUND` with
  reason `lr_unit_ambiguous`; `parcel.lr_unit_candidates()` lists them.
- Share totals are exact: `unit.ownership_sheet_b.total_ownership_fraction()`
  is a `Fraction`, `total_ownership_accounted()` its float.
- Parcels of a unit in the lean `lrParcels` shape carry only number, area,
  address and status in the unit; the other cadastre fields are `None`, not false.
- A share's `lrOwners` may be null or absent (co-owners then live in
  `sub_shares`); `LRShare.has_direct_owners` tells the two apart.

## Reference

- Models are specified in [specs/pydantic-entities-implementation.md](../specs/pydantic-entities-implementation.md).
- Upstream endpoints and payloads are in [specs/croatian-cadastral-api-specification.md](../specs/croatian-cadastral-api-specification.md).
- Worked examples: [api/examples/](../api/examples/), starting with
  [basic_usage.py](../api/examples/basic_usage.py) and
  [lr_unit_example.py](../api/examples/lr_unit_example.py).
