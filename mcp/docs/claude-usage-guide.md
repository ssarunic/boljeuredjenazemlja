# Claude Desktop MCP Usage Guide

This guide helps Claude (the AI assistant) use the Cadastral MCP server correctly when integrated with Claude Desktop.

## ✅ Working Tools

### 1. `search_parcel` - Search for a parcel
**Status:** ✅ Working

Searches for a parcel and returns basic information including parcel_id.

**Example:**
```
Search for parcel 103/2 in SAVAR
```

**What you'll get:**
- `parcel_id`: Unique identifier (e.g., "6564817")
- `parcel_number`: The parcel number (e.g., "103/2")
- `municipality`: Municipality name (e.g., "SAVAR")
- `municipality_code`: Municipality registration number (e.g., "334979")

---

### 2. `batch_fetch_parcels` - Fetch multiple parcels
**Status:** ✅ Working (after fix)

Fetches detailed information for multiple parcels in one operation.

**Important:** Use `parcel_id` directly (from search_parcel results), NOT just parcel_number.

**Example - CORRECT:**
```json
{
  "parcels": [
    {"parcel_id": "6564817"},
    {"parcel_id": "1234567"}
  ],
  "include_owners": true
}
```

**Example - ALSO CORRECT (but slower):**
```json
{
  "parcels": [
    {"parcel_number": "103/2", "municipality": "SAVAR"},
    {"parcel_number": "45", "municipality": "334979"}
  ],
  "include_owners": true
}
```

**Recommended workflow:**
1. First use `search_parcel` to get the `parcel_id`
2. Then use `batch_fetch_parcels` with the `parcel_id`

---

### 3. `resolve_municipality` - Get municipality code
**Status:** ✅ Working

Resolves a municipality name to its registration code.

**Example:**
```
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
```
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
```
Get the geometry for parcel 103/2 in SAVAR as GeoJSON
```

**Supported formats:**
- `"geojson"` - GeoJSON format (default)
- `"wkt"` - Well-Known Text format
- `"dict"` - Plain dictionary with coordinates

**Note:** First time use downloads GML data for the municipality (~1-10 MB).

---

### 6. `get_lr_unit_from_parcel` - Get Land Registry Unit from parcel
**Status:** ✅ Working (fixed 2025-11-18)

Gets complete land registry unit (LR unit) information starting from a parcel number.

**Example:**
```
Get the land registry unit for parcel 103/2 in SAVAR
```

**What you'll get:**
- **Sheet A (Posjedovni list)**: All parcels in the LR unit (not just the one searched)
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
  "include_full_details": true
}
```

**Note:** Usually it's easier to use `get_lr_unit_from_parcel` instead, which handles the lookup for you.

---

## ✅ Recently Fixed (2025-11-18)

### `get_lr_unit_from_parcel` - Land Registry Unit
**Status:** ✅ **FIXED!** (Now working)

**What was fixed:**
The `shareOrderNumber` field in the `EncumbranceGroup` Pydantic model is now optional (`str | None`) instead of required. This handles cases where the Croatian government API returns encumbrance data without this field.

**Example usage:**
```
Get the land registry unit for parcel 103/2 in SAVAR
```

**What you'll get:**
- Complete land registry unit information (LR unit - "zemljišnoknjižni uložak")
- **Sheet A (Posjedovni list)**: All parcels in the unit
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

```
# Good
search_parcel("103/2", "334979")

# Also works but slower
search_parcel("103/2", "SAVAR")
```

### Tip 2: Two-step workflow for detailed info
1. First search to get parcel_id
2. Then batch fetch for full details

```python
# Step 1: Search
result = search_parcel("103/2", "SAVAR")
parcel_id = result["parcel_id"]

# Step 2: Get details
details = batch_fetch_parcels([{"parcel_id": parcel_id}], include_owners=True)
```

### Tip 3: Batch operations are efficient
If you need info on multiple parcels, use one batch_fetch call instead of multiple individual calls.

```python
# Good - one call
batch_fetch_parcels([
    {"parcel_id": "6564817"},
    {"parcel_id": "7891234"},
    {"parcel_id": "5678901"}
], include_owners=True)

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

### "Could not retrieve land registry unit"
- This is the known Pydantic validation issue
- Use `batch_fetch_parcels` with `include_owners=true` instead
- This gives you possession sheet data (similar to ownership)

### Rate limiting
- The API has rate limits (0.75s between requests by default)
- Use batch operations when possible
- If you get rate limit errors, the SDK automatically handles retries

---

## 🎯 Common Query Patterns

### Pattern 1: Find parcel and show ownership
```
1. Search for parcel 103/2 in SAVAR
2. Get detailed information with owners for that parcel
```

### Pattern 2: Compare multiple parcels
```
1. Search for parcels 103/2, 45, and 396/1 in SAVAR
2. Fetch full details for all of them
3. Compare their areas and ownership
```

### Pattern 3: Explore municipality
```
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

- ✅ search_parcel
- ✅ batch_fetch_parcels (use parcel_id)
- ✅ resolve_municipality
- ✅ list_cadastral_offices
- ✅ get_parcel_geometry
- ✅ **get_lr_unit_from_parcel** (FIXED 2025-11-18)
- ✅ **get_lr_unit** (FIXED 2025-11-18)

**What was fixed:**
The Pydantic validation error for LR units has been resolved. The `shareOrderNumber` field is now optional, allowing the API to return encumbrance data even when this field is missing.
