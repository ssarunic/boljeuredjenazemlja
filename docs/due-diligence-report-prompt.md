# Due-diligence report prompt

A prompt for producing a due-diligence screening report of a set of parcels
from the JSON that the `build_assembly` MCP tool returns. The MCP server
ships it as the prompt `due_diligence_report(parcels, municipality,
language, format)`; this page is the same text for pasting into a client
that has the cadastral MCP server attached but no prompt picker (Claude Code,
for instance). Replace the parcel references, the municipality, the language
and the format in the first and last paragraphs.

The report is rendered by the model from the tool's JSON. The prompt fixes
what must not vary: the section order, the Croatian register terms with the
English gloss, the rule that every fact keeps its register and retrieval
time, and the notices that the verdict is a screening and the flags are
inferred. The format is the reader's choice: Markdown for an email, one
self-contained HTML file for a page that prints to PDF.

> Demo project: the default configuration reads the included mock server.
> Before pointing the tools at any other server, verify your rights to use
> it; use at your own risk. Nothing produced from the mock is real property data.

## The prompt (example: two parcels in k.o. SAVAR, Croatian, Markdown)

```text
Prepare a due-diligence screening report of 2 parcel(s) in cadastral municipality SAVAR for a reader who did not run the tool and will forward it to a lawyer. Write the prose in Croatian; keep Croatian register terms with the English gloss on first use (zemljišnoknjižni uložak / land-registry unit, vlastovnica / sheet B (owners), posjedovni list / possession sheet (cadastre), teretovnica / sheet C (encumbrances), plomba / pending request, zabilježba / note, založno pravo / mortgage, služnost / servitude, pravo prvokupa / pre-emption right, ostavina / estate, suvlasnički udio / co-ownership share).

Step 1. Call build_assembly with parcels=[{"parcel_number": "103/2", "municipality": "SAVAR"}, {"parcel_number": "1122/1", "municipality": "SAVAR"}], include_plombe_detail=true, include_zoning=true, persons_limit=null. If the response is too large, call again with include_blockers=false and read the blockers with export="blockers_csv" in a second call.

Step 2. Render the JSON as a report in this order, and in nothing else:

1. Header: the municipality, the parcel count and total area (totals), when and from where the registers were read (each parcel's provenance: register, source_url, retrieved_at), and the references that failed (failed, with error_type), so the reader knows what is missing.
2. Verdict roll-up: parcels by verdict (totals.parcels_by_verdict), persons likely deceased and abroad (totals.persons_likely_deceased, totals.persons_address_abroad), public bodies present (totals.public_body_parcels), and the three sentences those numbers mean for an acquisition.
3. Parcels, easiest first (the order of parcels): number, area, land use, the unit (lr_unit_number / main_book_id), distinct owners and possessors, relationship between the registers, zoning status when read, area_mismatch, sale_verdict with blocker_counts, score. Under each parcel list its rows of blockers: kind, severity, what it applies to (scope, share_order_number, condominium_unit), the description, amount and beneficiary, the entry (order_number, entry_date, diary_number) or file_number and request_kind for a plomba, and likely_lapsed where set. Quote an other_annotation entry's description for the reader.
4. Persons by controlled area (persons): name as the register writes it, party_type_inferred, owner_of and possessor_of, owned / possessed / controlled area, likely_deceased and address_abroad, fuzzy_matches. Then surname_groups with person_count, parcel_count, controlled_area_m2, likely_deceased_count and address_abroad_count.
5. Closing: the screening rule verbatim (any parcel's blockers carry it as rule in sale_blockers; quote: a screening of the register's text, not a legal opinion), the inference notice (party types, likely_deceased, address_abroad and likely_estate are inferred; each carries its basis), the zoning dataset disclaimer when zoning was read, and the notes.

Rules: copy every number, name, share, date and reference from the JSON, never recompute or round them; do not add a fact the JSON does not hold, and say "not read" where a field is null; keep every person exactly as the registers spell them; state the register (cadastre or land registry) behind every fact; do not give legal advice or a recommendation to buy; where the tool could not answer (unknown kind of plomba, unrecognised note), say so and name what would settle it (the plomba detail, the entry text, a lokacijska informacija for buildability).

Format. Markdown: tables for the parcels, the persons and the blockers; one heading per section; readable as plain text in an email.
```

## Using it in Claude Code

With the cadastral MCP server attached (see the [MCP usage
guide](mcp-usage-guide.md)), paste the text above as the message, or ask for
it by name: "run the due_diligence_report prompt for 103/2 and 1122/1 in
SAVAR". For an HTML page ask for `format: html`; Claude Code writes the file
and can open it. For a spreadsheet ask for the `blockers_csv`, `parcels_csv`
and `persons_csv` exports of the same call and have them written to disk, or
ask Claude Code to assemble them into one workbook with `openpyxl`.
