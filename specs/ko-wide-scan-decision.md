# Decision memo: scanning a whole cadastral municipality

Status: draft (a decision is needed before any code)
Date: 2026-09-15, revised the same day: the possession-sheet question is
resolved without a scan (section 0); the person search remains.
Related: [croatian-cadastral-api-specification.md](croatian-cadastral-api-specification.md),
[api-coverage-specification.md](api-coverage-specification.md) (OQ4),
[mcp-server.md](mcp-server.md), [gateway-service.md](gateway-service.md) section 6

## 0. Update: the possession-sheet question no longer needs a scan

A capture on 2026-09-15 (`notes/oq4-possession-sheet-capture-2026-09-15.md`)
found the endpoints the web form uses: `GET /cad/possession-sheet` returns a
sheet with its possessors and `POST /cad/search-parcels` every parcel on a
sheet by number. Both are covered by the client (`get_possession_sheet_parcels`)
and the MCP tool `get_possession_sheet`. What follows applies to the person
search only.

## 1. The question

Two requirements of the console/MCP layer cannot be met with the endpoints
the public API offers:

- the parcels of a possession sheet (posjedovni list N in k.o. Y);
- every parcel a named person owns or possesses within a k.o.

The cadastre search endpoints match on parcel number only (coverage
specification 4.2); the possession-sheet search returns the sheet id and
number, and no endpoint returns a sheet by id (OQ4); the land registry has
no search by person. The only way to answer either question is to read the
cadastre record of every parcel of the municipality (`/cad/parcel-info`, one
request per parcel) and filter the results locally: a k.o.-wide scan.

## 2. What a scan costs

| Item | Value |
|---|---|
| Requests | one `/cad/parcel-info` per parcel; the parcel ids come from the cached GML (`ParcelIndex`, one download) |
| Rate | 0.375 s minimum between requests (the client's default); the terms of the source allow no more |
| A small k.o. (Savar, about 1,500 parcels) | about 10 minutes |
| A large k.o. (10,000 parcels) | over an hour |
| Repeat cost | the same every time, since nothing may be kept (section 3) |
| Data volume | every possessor of every parcel of the municipality: names, shares, addresses |

The scan is not a lookup: it is a bulk extraction of personal data, whatever
question it is run to answer.

## 3. Constraints

1. CLAUDE.md rule 3: the project does not bypass rate limits or the terms
   of service of any server. A scan respects the rate but not the spirit of
   a per-parcel public lookup; the terms of the government service must be
   read before deciding that it is permitted.
2. Requirement 9 of the console layer: personal data (owner names, birth
   years) is held only in a short-TTL cache, never in a persistent index,
   unless a legal basis for that index is documented. A person index built
   from a scan is such a persistent index. Without the legal basis the scan
   can only produce a transient answer and must be repeated in full for
   every question.
3. The person search of requirement 2 is the more sensitive of the two:
   "every parcel of a named person in a k.o." is profiling. The
   possession-sheet question is about a sheet number, not a person, and its
   result is what an official extract of the sheet would show.

## 4. Options

| Option | What it means | Cost | Risk |
|---|---|---|---|
| A. Do not build | Both requirements stay unmet; the tools say so and point to the office | none | the two stories stay open |
| B. Transient scan with a budget | One tool that scans a k.o. with a hard request budget (per call and per day), keeps nothing beyond the call, answers the possession-sheet question and, if allowed, the person question | 10 minutes to hours per question; code for budgets and progress | terms of service; every question repeats the extraction |
| C. Official route | Ask the DGU / the land-registry office for the bulk or professional access that exists for these questions (requirement 9, official-access mode) | a request and a wait | none technical; depends on the answer |
| D. Scan once, index, document the basis | A per-k.o. index refreshed on a schedule, with a documented legal basis and retention | the index infrastructure; the legal work | the highest: a standing personal-data index |

## 5. Recommendation

- Decide C first: the professional-access demo (requirement 9) will show
  whether the official route answers both questions; if it does, A is the
  right answer for the public API and no scan is written.
- The possession-sheet question is answered by the endpoints of section 0;
  option B is no longer needed for it. Should the professional access (C)
  not exist for the person search either, B would be the only technical
  route, with a per-call cap, a daily budget, a progress report, no
  persistence beyond the call and an explicit note that the result was
  assembled from single-parcel lookups; but see the next point.
- Do not build the person search on the public API without a documented
  legal basis (D). Say so in the tool description so an agent does not try
  to emulate it with a loop of lookups.

## 6. Decision

| Field | Value |
|---|---|
| Decision | pending |
| Decided by | |
| Date | |
| Terms of service checked | |
| Legal basis for a person index | |
