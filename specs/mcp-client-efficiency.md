# MCP Client Efficiency Specification

Status: Partially implemented
Scope: `mcp/` (server + tools), with supporting changes in `api/` and `cli/`
Related: [mcp-server.md](mcp-server.md), [croatian-cadastral-api-specification.md](croatian-cadastral-api-specification.md), [pydantic-entities-implementation.md](pydantic-entities-implementation.md)

## Implementation status (as-built)

- **F2 (register source)** - shipped. Implemented as an explicit `source`
  argument ("cadastre" | "land_registry" | "none", default "cadastre" on the
  parcel-level tool). The deprecated `include_owners` boolean was **removed
  outright** rather than kept as a shim (no back-compat requirement). Every
  owner/possessor record carries a `register` tag.
- **F3 (lr_unit fallback)** - shipped. Resolution falls back to parcel links;
  `lr_unit_derived_from_links` is exposed on the unit model.
- **F4 (response shaping)** - shipped with **three** detail levels
  ("summary" | "ownership" | "full", default "ownership") plus `owners_limit`.
  The pre-existing `include_full_details` boolean was removed.
- **F5 (structured data)** - shipped. Fractions parsed from the share
  description into `{num, den, decimal}`; `name_normalized` added.
- **F1 (discovery)** - the remaining item (bilingual tool descriptions +
  routing Skill).

The section bodies below are the original design; where they differ from the
as-built notes above, the as-built notes win.

## 1. Background and Problem Statement

A real client session retrieving ownership for a portfolio of parcels took roughly
six tool calls and two out-of-band post-processing detours. A code-grounded review
of the friction (not the original optimisation advice, which proposed building
capabilities that already exist) isolated four causes that are worth fixing and two
that are not.

Confirmed causes worth fixing:

1. **Discovery miss.** The client did not reach for the cadastral tools unprompted.
   The registered tools already carry rich English docstrings
   (e.g. `batch_fetch_parcels` in [server.py](../mcp/src/cadastral_mcp/server.py)),
   so the fix is not "write descriptions" but (a) bilingual Croatian/English trigger
   vocabulary and (b) a proactive discovery surface.
2. **Semantic mismatch: cadastre vs. land registry.** `batch_fetch_parcels(..., include_owners=True)`
   returns possessors from the *posjedovni list* (cadastre), not owners from the
   *vlastovnica* / B-list (land registry). The boolean conflates two different
   registers, which caused the wrong data to be fetched first.
3. **`lr_unit = None` has no internal fallback.** `get_lr_unit_from_parcel`
   raises `LR_UNIT_NOT_FOUND` as soon as `parcel_info.lr_unit` is null
   ([api_client.py:669](../api/src/cadastral_api/client/api_client.py#L669)),
   even though the parcel model carries `parcel_links` and
   `lr_units_from_parcel_links` ([entities.py:372-375](../api/src/cadastral_api/models/entities.py#L372)).
   The client had to resolve this by hand.
4. **Oversized, unshaped responses.** Detailed LR-unit results return every sheet,
   geometry, and raw internal IDs, forcing responses too large for context and
   subsequent local parsing — including regexing ownership fractions out of free-text
   description strings because numerator/denominator came back unstructured.

Explicitly **not** problems (and therefore out of scope, see Section 7):

- The "missing consolidated parcel to ownership tool" — `get_lr_unit_from_parcel`
  (MCP and API) and `get-lr-unit --from-parcel` (CLI) already collapse the chain.
- "Replace MCP with REST/CLI" — this was argued on an unverified network-egress
  assumption and does not apply to a local execution environment.

## 2. Goals

- Reduce a portfolio ownership lookup from ~6 calls to 1-2 calls with no out-of-band
  post-processing.
- Make register choice (land registry vs. cadastre) explicit and unambiguous.
- Return ownership data already structured (fractions, normalised names) so the
  client never parses free text.
- Keep responses small enough to stay in context by default, with explicit opt-in
  to full detail.
- Make the tools discoverable in Croatian and English without the client being told
  where they are.

## 3. Non-Goals

- No new aggregation tool that duplicates `get_lr_unit_from_parcel`.
- No change to the underlying three-step API workflow or the mock server contract.
- No removal or deprecation of the low-level primitives (`find_parcel`,
  `batch_fetch_parcels`, `get_lr_unit`, `batch_lr_units`); they remain available.
- No production-system configuration. Mock server only.

## 4. Functional Requirements

Requirements are ordered by value. F1-F3 deliver most of the benefit; F4-F5 are
incremental; F6 is optional.

### F1 - Bilingual discovery (P0)

**F1.1 Description enrichment.** Every registered MCP tool description MUST include
Croatian and English trigger vocabulary for the concepts it serves. Minimum terms to
cover across the tool set:

- katastar / cadastre, katastarska čestica / parcel (k.č.), katastarska općina (k.o.)
- zemljišne knjige / land registry, gruntovnica, zemljišnoknjižni uložak / LR unit
- vlasnici / owners, suvlasnički udjeli / co-ownership shares, vlastovnica / B-list
- posjedovni list / possession sheet, posjednici / possessors
- teret, teretovnica / encumbrances, C-list

The tool that returns land-registry ownership MUST state in its description that it
returns *vlastovnica / B-list* owners, and the cadastre path MUST state it returns
*posjedovni list* possessors, so the distinction is visible at selection time.

**F1.2 Discovery Skill.** Add a thin Skill (SKILL.md) whose description advertises the
capability ("for any Croatian cadastre or land-registry question, use the cadastral
MCP tools") and whose body encodes the routing playbook:

- ZK / "prema zemljišnim knjigama" -> `source = land_registry`
- kataster / posjed -> `source = cadastre`
- `in_land_registry = false` means the parcel is cadastre-only
- units above the configured owner threshold should be summarised, not dumped

The Skill is the "make the client look in the first place" lever; F1.1 is the
"make the search rank" lever. Both are required.

### F2 - Explicit register selection (P0)

**F2.1** Introduce a `source` argument on every ownership-returning tool:

```
source: "land_registry" | "cadastre" = "land_registry"
```

- `land_registry` returns vlastovnica / B-list owners.
- `cadastre` returns posjedovni-list possessors.

**F2.2** The existing `include_owners: bool` on `batch_fetch_parcels` MUST be
deprecated, not removed. When `include_owners=True` and `source` is unset, behaviour
is unchanged (cadastre possessors) but the response MUST carry a
`deprecation_notice` field naming `source` as the replacement. Remove the boolean only
in a future major version.

**F2.3** Every result that contains owner/possessor records MUST tag them with the
register they came from: `"register": "land_registry" | "cadastre"`.

### F3 - Internal `lr_unit` resolution with link fallback (P0)

**F3.1** `get_lr_unit_from_parcel` and the batch LR-unit path MUST, when
`parcel_info.lr_unit` is `None`, attempt to derive the LR unit from
`parcel_links` / `lr_units_from_parcel_links` before raising `LR_UNIT_NOT_FOUND`.

**F3.2** Each result MUST report how the unit was obtained:

```
in_land_registry: bool             # false when the parcel has no LR unit at all (cadastre-only)
lr_unit_derived_from_links: bool   # true when resolved via the parcel_links fallback
```

**F3.3** `LR_UNIT_NOT_FOUND` is raised only when both the direct `lr_unit` and the
link fallback yield nothing. In that case `in_land_registry` is `false` and the error
detail MUST state `reason: "parcel_not_in_land_registry"` so the client can fall back
to the cadastre register without a second probe.

### F4 - Response shaping (P1)

**F4.1** Add a `detail` argument to LR-unit and parcel-ownership tools:

```
detail: "ownership" | "full" = "ownership"
```

- `ownership` (default): B-list owners plus the existing `summary`. Excludes
  geometry, sheet A2, raw internal IDs, and the C-sheet.
- `full`: current behaviour (all sheets).

**F4.2** Add owner-count guards to any tool that can return a large ownership set:

```
owners_limit: int | None = None
```

When set, return at most `owners_limit` owner records and always include
`total_owners` (the full count) so the client can decide to summarise rather than
enumerate. When truncation occurs the response MUST set `"owners_truncated": true`.
Truncation MUST never be silent.

### F5 - Structured ownership data (P1)

**F5.1** Each ownership/possession share MUST expose its fraction as structured
fields in addition to any source string:

```
share: { "num": int, "den": int, "decimal": float }
```

Where the source provides only a description string
(e.g. `"Suvlasnički dio: 3/48"`), the server parses it once and populates `share`.
If parsing fails, `share` is `null` and the original string is retained.

**F5.2** Each owner MUST carry both the raw name and a normalised form:

```
name: str              # verbatim, including source quirks (e.g. "ŠAR7UNIĆ")
name_normalized: str   # cleaned for matching/dedup
```

Raw values are never mutated; `name_normalized` is additive.

### F6 - Optional batch convenience (P2)

The single-parcel chain is already covered by `get_lr_unit_from_parcel`. For the
multi-parcel case the designed two-hop (`batch_fetch_parcels` ->
`batch_lr_units`) remains correct and is documented in the tool descriptions. A
single `batch_parcel_ownership(municipality, parcel_numbers, source, detail, owners_limit)`
tool that performs both hops internally MAY be added as ergonomic sugar, returning
one shaped record per parcel (including `in_land_registry` and
`lr_unit_derived_from_links` from F3). This is optional and lower priority than F1-F5.

## 5. Response Contract (target shape, `detail = "ownership"`)

Per-parcel record returned by the ownership path:

```json
{
  "parcel_number": "279/6",
  "municipality": "SAVAR",
  "register": "land_registry",
  "in_land_registry": true,
  "lr_unit_derived_from_links": false,
  "lr_unit_number": "769",
  "main_book_id": 21277,
  "owners": [
    {
      "name": "ŠAR7UNIĆ IVAN",
      "name_normalized": "Šarunić Ivan",
      "oib": "...",
      "address": "...",
      "share": { "num": 3, "den": 48, "decimal": 0.0625 }
    }
  ],
  "total_owners": 1,
  "owners_truncated": false,
  "summary": { "...": "..." }
}
```

A cadastre-only parcel:

```json
{
  "parcel_number": "454/3",
  "register": "land_registry",
  "in_land_registry": false,
  "owners": [],
  "error": { "type": "LR_UNIT_NOT_FOUND", "reason": "parcel_not_in_land_registry" }
}
```

## 6. Backward Compatibility

- All new arguments are optional with defaults preserving current behaviour, except
  that the default `detail = "ownership"` changes the *shape* of LR-unit responses.
  This is a behavioural change and MUST be called out in the changelog; clients
  needing every sheet pass `detail = "full"`.
- `include_owners` continues to work (F2.2) with a deprecation notice.
- Low-level primitives are unchanged.
- New response fields (`register`, `in_land_registry`, `lr_unit_derived_from_links`,
  `share`, `name_normalized`, `total_owners`, `owners_truncated`) are additive.

## 7. Out of Scope

- A consolidated parcel-to-ownership tool that duplicates the existing
  `get_lr_unit_from_parcel` — rejected; the capability exists.
- Replacing MCP transport with a REST or CLI frontend on network-egress grounds —
  rejected as unverified and environment-specific.
- Caching live registry state (plombe, recent uknjižbe) — out of scope; this data
  must be fetched live.
- Updating the stale "batch operations" entry in
  [docs/cli-reference.md](../docs/cli-reference.md) — tracked separately as a docs fix,
  not part of this MCP spec.

## 8. Acceptance Criteria

1. A portfolio ownership request resolves in 1-2 tool calls with no client-side
   fraction parsing, name cleaning, or `lr_unit` fallback logic.
2. Selecting the land-registry register never returns posjedovni-list possessors, and
   vice versa; the `register` tag on every owner record confirms provenance.
3. A parcel whose `lr_unit` is null but resolvable via links returns owners with
   `lr_unit_derived_from_links = true`; a genuinely cadastre-only parcel returns
   `in_land_registry = false` with no second client probe required.
4. `detail = "ownership"` responses for a large unit fit in context; `owners_limit`
   truncation always sets `owners_truncated = true` and reports `total_owners`.
5. Every fraction is delivered as `{num, den, decimal}` or explicitly `null`; no
   client regex over description strings is needed.
6. With the discovery Skill installed and descriptions enriched, the client selects a
   cadastral tool for a Croatian-language ownership query without being pointed at it.

## 9. Test Plan

- Unit tests for the link-fallback path: parcel with `lr_unit`, parcel with only
  `lr_units_from_parcel_links`, parcel with neither.
- Unit tests for fraction parsing across observed string formats, including failure
  to `null`.
- Snapshot tests for `detail = "ownership"` vs. `full` payload size and field set.
- A `source` matrix test asserting `register` provenance for both registers.
- A condominium case (etažno vlasništvo) exercising F3-F5 against a split unit, since
  shares there carry `condominium_number` / nested co-owners.

## 10. Open Questions

- Default value for `owners_limit` when unset on a very large unit: unlimited, or a
  high soft cap that still sets `owners_truncated`?
- Should the discovery Skill live in `mcp/` or at repository root so it is shared
  across frontends?
- Does the mock server expose `lr_units_from_parcel_links` for a parcel without a
  direct `lr_unit`? If not, a fixture is needed to test F3.
