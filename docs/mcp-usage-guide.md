# Claude Desktop MCP Usage Guide

This guide helps Claude (the AI assistant) use the Cadastral MCP server correctly when integrated with Claude Desktop.

## ✅ Working Tools

### 1. `find_parcel` - Find a parcel
**Status:** ✅ Working

Finds a parcel and returns basic information including parcel_id.

**Example:**

```text
Find parcel 103/2 in SAVAR
```

**What you'll get:**
- `parcel_id`: Unique identifier (e.g., "6564817")
- `parcel_number`: The parcel number (e.g., "103/2")
- `municipality`: Municipality name (e.g., "SAVAR")
- `municipality_code`: Municipality registration number (e.g., "334979")
- `map_url`: Interactive map centred on the parcel, when the municipality's
  GIS data is available (the first search in a municipality downloads it; later
  searches use the cache). Omitted if the data cannot be fetched or the parcel
  is not in it.
- `requested_parcel_number` and `exact_match`: what was asked for, and whether
  the parcel returned is it.

**Prefix matches:** the search matches on the prefix, so a number that does not
exist can still return a longer one ("973" in a municipality that has only
973/1). When that happens `exact_match` is `false` and `match_note` and
`other_matches` say what was found instead. Treat it as "no such parcel, here is
what exists", not as a hit. Building parcels are the one case where the number
legitimately changes shape: "35/1.ZGR", "zgr. 35/1" and "*35/1" all resolve to
"*35/1" with `exact_match` `true`.

---

### 2. `batch_fetch_parcels` - Fetch multiple parcels
**Status:** ✅ Working

Fetches detailed information for multiple parcels in one operation.

**Important:** Use `parcel_id` directly (from find_parcel results), NOT just parcel_number.

**Example - CORRECT:**
```json
{
  "parcels": [
    {"parcel_id": "6564817"},
    {"parcel_id": "1234567"}
  ],
  "source": "cadastre"
}
```

**Example - ALSO CORRECT (but slower):**
```json
{
  "parcels": [
    {"parcel_number": "103/2", "municipality": "SAVAR"},
    {"parcel_number": "45", "municipality": "334979"}
  ],
  "source": "cadastre"
}
```

**Register selection (`source`):** cadastre POSSESSORS (posjedovni list) are
often NOT the registered land-registry OWNERS (vlasnici / vlastovnica / B-list).
Choose explicitly:

- `"cadastre"` (default) - include possession-sheet possessors.
- `"land_registry"` - omit possessors; return the LR unit reference + a hint to
  fetch true owners via `get_lr_unit_from_parcel` / `batch_lr_units`. Use this
  for "vlasnik" / "prema zemljišnim knjigama".
- `"none"` - parcel metadata only.

Every person record is tagged with a `register` field (`"cadastre"` |
`"land_registry"`) so the two can never be confused.

**Map link:** Each successful result carries `map_url` (interactive map centred
on the parcel) when the municipality's GIS data is available; see `find_parcel`.

**LR unit references:** Each successful result includes:
- `lr_unit.lr_unit_number` - Land registry unit number
- `lr_unit.main_book_id` - Main book ID

These can be used with `batch_lr_units` to get detailed ownership and encumbrance information.

**Recommended workflow:**
1. First use `search_parcel` to get the `parcel_id`
2. Then use `batch_fetch_parcels` with the `parcel_id`
3. (Optional) Use `batch_lr_units` with the LR refs for detailed ownership

---

### 3. `resolve_municipality` - Get municipality code
**Status:** ✅ Working

Resolves a municipality name to its registration code.

**Example:**

```text
What is the municipality code for SAVAR?
```

**Response:**
```json
{
  "code": "334979",
  "name": "SAVAR",
  "full_name": "334979 SAVAR, ZADAR, PUK ZADAR"
}
```

---

### 4. `list_cadastral_offices` - List all offices
**Status:** ✅ Working

Lists all cadastral offices in Croatia, optionally filtered by name.

**Example:**

```text
List all cadastral offices
```

**Example with filter:**
```json
{
  "filter_name": "ZADAR"
}
```

---

### 5. `get_parcel_geometry` - Get parcel boundaries
**Status:** ✅ Working (requires GML data download)

Gets parcel boundary coordinates in various formats.

**Example:**

```text
Get the geometry for parcel 103/2 in SAVAR as GeoJSON
```

**Supported formats:**
- `"geojson"` - GeoJSON Feature (default); `properties.map_url` links to the interactive map
- `"wkt"` - Well-Known Text format (polygon only, no link)
- `"dict"` - Plain dictionary with coordinates and `map_url`

**Map link:** `map_url` opens the interactive map centred on the parcel, in the
form `https://oss.uredjenazemlja.hr/map?center=<x>,<y>&zoom=19&layers=...`
(EPSG:3765 centre of the parcel's bounding box). Pass `zoom` to change the
level; 19 fits one ordinary parcel, 20 suits very small ones.

**Note:** First time use downloads GML data for the municipality (~1-10 MB).

---

### 6. `get_lr_unit_from_parcel` - Get Land Registry Unit from parcel
**Status:** ✅ Working (fixed 2025-11-18)

Gets complete land registry unit (LR unit) information starting from a parcel number.

**Example:**

```text
Get the land registry unit for parcel 103/2 in SAVAR
```

**What you'll get:**
- **Sheet A (Popis čestica)**: All parcels in the LR unit (not just the one searched)
- **Sheet B (Vlasnički list)**: Complete ownership information with co-owners and shares
- **Sheet C (Teretni list)**: All encumbrances (mortgages, easements, liens, restrictions)
- Comprehensive summary (total area, number of owners, encumbrances)

**Use this when:**
- You need complete ownership structure with exact shares
- You want to see ALL parcels that belong to the same owners
- You need information about mortgages, easements, or other encumbrances
- You need more detailed ownership data than possession sheets provide

---

### 7. `get_lr_unit` - Get Land Registry Unit directly
**Status:** ✅ Working (fixed 2025-11-18)

Gets land registry unit information directly if you already know the unit number and main book ID.

**Example:**
```json
{
  "unit_number": "657",
  "main_book_id": 21277,
  "detail": "ownership"
}
```

**Response shaping (`detail`):** `"summary"` | `"ownership"` (default) | `"full"`.
`"ownership"` returns B-list owners with structured shares (`share = {num, den,
decimal}`) plus a summary, and fits in context; `"full"` returns every sheet
(geometry, A2, C-sheet, raw IDs). Pass `owners_limit` to cap owner records in
either view (`total_owners` / `owners_truncated` report what was capped). A unit
with hundreds of co-owners does not fit in one response even capped, so a `"full"`
dump that would be too large is refused with the smaller views named; use
`"ownership"` there.

**Note:** Usually it's easier to use `get_lr_unit_from_parcel` instead, which
handles the lookup for you - and it resolves the unit even when the parcel has
no direct lr_unit (reporting `lr_unit_derived_from_links`).

---

### 8. `batch_lr_units` - Fetch multiple LR units (NEW)
**Status:** ✅ Working (added 2025-11-24)

Fetches multiple land registry units in a single operation. Use this after `batch_fetch_parcels` to get detailed ownership and encumbrance information.

**Example:**
```json
{
  "lr_units": [
    {"lr_unit_number": "657", "main_book_id": 21277},
    {"lr_unit_number": "123", "main_book_id": 21277}
  ],
  "detail": "ownership"
}
```

**What you'll get for each LR unit:**

- **Sheet A (Popis čestica)**: All parcels in the unit
- **Sheet B (Vlasnički list)**: Ownership with shares
- **Sheet C (Teretni list)**: Encumbrances (mortgages, liens)
- **Summary**: Total area, number of owners, encumbrance status

**Key features:**

- Automatic deduplication (if multiple parcels share an LR unit)
- Returns `unique` count showing how many were actually fetched
- Continue-on-error behavior

**Recommended workflow:**

1. Use `batch_fetch_parcels` to get parcel info with LR refs
2. Extract `lr_unit.lr_unit_number` and `lr_unit.main_book_id` from each result
3. Pass those to `batch_lr_units` for detailed ownership info

---

### 9. `find_main_book` - Find a land registry main book

**Query examples:**
- "Which main book holds the land registry units of SAVAR?"
- "What is the main book ID for k.o. Savar?"

Returns `main_books` with `main_book_id`, `main_book_name`, `institution_id`
(land registry office) and `court_name`. `get_lr_unit` also accepts
`main_book_name` directly and resolves it the same way.

### 10. `find_book_of_dc` - Find a book of deposited contracts (KPU)

**Query examples:**
- "Which books of deposited contracts does the Zadar land registry office keep?"

Returns `books_of_dc` with `book_id`, `book_name`, `office_id` and `office_name`.

### 11. `find_possession_sheet` - Find a cadastre possession sheet by number

**Query examples:**
- "Does possession sheet 363 exist in k.o. Savar?"

Returns `possession_sheets` with `possession_sheet_id` and `sheet_number`. The
cadastre has no lookup by sheet id; use `find_parcel` / `batch_fetch_parcels`
on one of the sheet's parcels to see its possessors.

### Entry provenance in `get_lr_unit` / `get_lr_unit_from_parcel`

At `detail="ownership"` every owner row carries `entry`: the registration entry
that put the owner on the share (`order_number`, `entry_date`, `diary_number`,
`priority_diary_number`, `action_type`, `basis_document`,
`transferred_from_unit`, `description_text`). The result also carries
`share_entries` (annotations registered on individual shares) and
`sheet_a1_source_key` (`lrParcels` or `cadParcels`). `detail="full"` dumps every
field, including `amount` / `amount_value` / `amount_currency` on list C entries
and `plumb_mark` on pending entries.

## ✅ Recently Fixed (2025-11-18)

### `get_lr_unit_from_parcel` - Land Registry Unit
**Status:** ✅ **FIXED!** (Now working)

**What was fixed:**
The `shareOrderNumber` field in the `EncumbranceGroup` Pydantic model is now optional (`str | None`) instead of required. This handles cases where the Croatian government API returns encumbrance data without this field.

**Example usage:**

```text
Get the land registry unit for parcel 103/2 in SAVAR
```

**What you'll get:**
- Complete land registry unit information (LR unit - "zemljišnoknjižni uložak")
- **Sheet A (Popis čestica)**: All parcels in the unit
- **Sheet B (Vlasnički list)**: Ownership information with shares
- **Sheet C (Teretni list)**: Encumbrances (mortgages, easements, liens)
- Comprehensive summary with total area, number of owners, etc.

**Note:** LR units provide more complete ownership information than possession sheets from `batch_fetch_parcels`. They show the full ownership structure including co-owners and their exact shares.

---

## ⚠️ Known Issues

Currently no known issues! All tools are working.

---

## 💡 Usage Tips

### Tip 1: Always use municipality codes when you have them

Municipality codes are more reliable than names. Once you've resolved a name to a code, use the code.

```python
# Good
find_parcel("103/2", "334979")

# Also works but slower
find_parcel("103/2", "SAVAR")
```

### Tip 2: Two-step workflow for detailed info
1. First find to get parcel_id
2. Then batch fetch for full details

```python
# Step 1: Find
result = find_parcel("103/2", "SAVAR")
parcel_id = result["parcel_id"]

# Step 2: Get details (cadastre possessors)
details = batch_fetch_parcels([{"parcel_id": parcel_id}], source="cadastre")
```

### Tip 3: Batch operations are efficient
If you need info on multiple parcels, use one batch_fetch call instead of multiple individual calls.

```python
# Good - one call
batch_fetch_parcels([
    {"parcel_id": "6564817"},
    {"parcel_id": "7891234"},
    {"parcel_id": "5678901"}
], source="cadastre")

# Avoid - multiple calls
# (This would be slower and hit rate limits)
```

### Tip 4: Check for ownership data
Not all parcels have ownership information in possession sheets. Always check if the data exists:

```python
if parcel_data.get("possession_sheets"):
    # Has ownership info
    for sheet in parcel_data["possession_sheets"]:
        for possessor in sheet["possessors"]:
            print(possessor["name"])
else:
    # No ownership data available
    print("No ownership information available")
```

---

## 📊 Data Structure Reference

### ParcelInfo (from batch_fetch_parcels)

```json
{
  "parcel_number": "103/2",
  "municipality_name": "SAVAR",
  "area": "1200",
  "parcel_parts": [
    {
      "land_use_code": "21",
      "land_use_description": "Oranica",
      "area": "1200"
    }
  ],
  "possession_sheets": [
    {
      "sheet_number": "1",
      "possessors": [
        {
          "name": "JOHN DOE",
          "ownership": "1/1",
          "address": "Some Address, 23000 ZADAR"
        }
      ]
    }
  ],
  "has_building_right": false
}
```

### Municipality Codes (Examples)

| Municipality | Code   |
|-------------|--------|
| SAVAR       | 334979 |
| LUKA        | 334731 |

---

## 🔧 Troubleshooting

### "Municipality not found"
- Check spelling (Croatian municipality names)
- Try using the registration code instead
- Use `list_cadastral_offices()` to see available offices

### "No parcels found"
- Verify the parcel number format (e.g., "103/2" not "103-2")
- Ensure the parcel exists in that municipality
- Try searching with municipality code instead of name

### "has no geometry in the GIS data"
- The parcel number is not in the municipality's GML file; check the number
- If the cached GIS data may be stale, clear it with
  `cadastral cache clear -m <municipality code>` and try again

### "Could not retrieve land registry unit"
- Verify the parcel/unit number and municipality
- `get_lr_unit_from_parcel` resolves the unit even when the parcel has no direct
  lr_unit (via parcel links); a genuine `parcel_not_in_land_registry` means the
  parcel is cadastre-only - use `source="cadastre"` on `batch_fetch_parcels` for
  its possessors (note: possessors are NOT the registered owners)

### Rate limiting
- The API has rate limits (0.75s between requests by default)
- Use batch operations when possible
- If you get rate limit errors, the SDK automatically handles retries

---

## 🎯 Common Query Patterns

### Pattern 1: Find parcel and show ownership

```text
1. Find parcel 103/2 in SAVAR
2. Get detailed information with owners for that parcel
```

### Pattern 2: Compare multiple parcels

```text
1. Find parcels 103/2, 45, and 396/1 in SAVAR
2. Fetch full details for all of them
3. Compare their areas and ownership
```

### Pattern 3: Explore municipality

```text
1. Resolve SAVAR to get municipality code
2. List some common parcel numbers
3. Get details for each
```

---

## ⚠️ Important Reminders

1. **This is for demonstration/educational purposes only**
2. **Production API access requires proper authorization**
3. **Land ownership data is sensitive personal information**
4. **Respect Croatian data protection laws (GDPR)**
5. **The mock server should be used for testing whenever possible**

---

## 📝 Summary

**All Tools Working:** ✅

- ✅ find_parcel
- ✅ batch_fetch_parcels (use parcel_id) - now returns LR unit refs
- ✅ resolve_municipality
- ✅ list_cadastral_offices
- ✅ get_parcel_geometry
- ✅ get_lr_unit_from_parcel (FIXED 2025-11-18)
- ✅ get_lr_unit (FIXED 2025-11-18)
- ✅ **batch_lr_units** (NEW 2025-11-24)

**What's new (2025-11-24):**

- `batch_fetch_parcels` now returns LR unit references (`lr_unit.lr_unit_number`, `lr_unit.main_book_id`) for each parcel
- New `batch_lr_units` tool for fetching multiple LR units with automatic deduplication
- Pipeline workflow: parcels → LR refs → detailed ownership info

**Previously fixed (2025-11-18):**
The Pydantic validation error for LR units has been resolved. The `shareOrderNumber` field is now optional, allowing the API to return encumbrance data even when this field is missing.
