<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/get-lr-unit.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it and must not be connected to the official Croatian cadastre or land registry. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.1.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Read the land registry unit: owners, parcels, encumbrances

The land registry unit (zemljišnoknjižni uložak) is the legal record of a
property. This command shows its three sheets: the parcels it covers
(posjedovnica, list A), the owners and their shares (vlastovnica, list B), and
the encumbrances such as mortgages and easements (teretovnica, list C). It also
shows pending entries (plombe).

## When you would use this

- You need to know who legally owns a parcel and in what shares.
- You are checking for mortgages, easements, notes or other charges before a sale or a loan.
- You want to know whether a request for registration (prijedlog za upis) is pending on the unit, for example an inheritance decision that has not been entered yet.

## Before you start

There are two ways to name the unit. If you start from a parcel, give the
parcel number and the cadastral municipality, and the tool finds the unit for
you. If you already have the unit number and the main book (glavna knjiga) it
belongs to, give those two instead.

The main book is identified by a number the tool calls the main book ID. You
get it from the [batch-fetch](batch-fetch.md) results or from a previous
lookup. Starting from the parcel is the easier route.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral get-lr-unit --from-parcel 103/2 -m SAVAR --all
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral get-lr-unit --from-parcel 103/2 -m SAVAR --all -->
   ```text
                    LAND REGISTRY UNIT
    Unit Number        657
    Main Book          SAVAR
    Institution        Test Land Registry Office SAVAR
    Status             Aktivan
    Unit Type          VLASNIČKI
    Last Diary Number  Z-12345/2024

          PARCEL LIST (SHEET A)
    Parcel Number  Address  Area (m²)
    103/2          POLJE         1200
    TOTAL                        1200

                    OWNERSHIP SHEET (LIST B)
    Share  Owner                  Address                 OIB
    1/2    IVIĆ MARKO, SIN PETRA  TESTNA ULICA 15, SPLIT  -
    1/2    IVIĆ ANA, KĆI PETRA    SAVAR                   -

     ENCUMBRANCES SHEET (LIST C)
    Description            Details
    No encumbrances found
   ```
   <!-- END GENERATED: output -->

4. The first table, **LAND REGISTRY UNIT**, identifies the unit: its number,
   the main book, the office that keeps it, and **Last Diary Number**, the most
   recent file number entered in the diary (dnevnik). **PARCEL LIST (SHEET A)**
   is the posjedovnica, list A. **OWNERSHIP SHEET (LIST B)** is the
   vlastovnica, list B, with the share of each owner as a fraction.
   **ENCUMBRANCES SHEET (LIST C)** is the teretovnica, list C. When list C is
   empty, the tool prints **No encumbrances found**.

5. If the unit has pending entries, an extra line **Pending entries (plombe)**
   appears in the first table with the file numbers, and a warning follows. A
   plomba means a request for registration (prijedlog za upis) has been
   received and the unit may be about to change. Do not treat the sheets as final until it is resolved.

## Choices you can make

`--all` shows the three sheets. To see only one, use `--show-owners` for list
B, `--show-parcels` for list A, or `--show-encumbrances` for list C. Without any
of them the tool prints the first table only.

To see what each pending entry is about, add `--plombe-detail`. The tool then
asks the registry about every plomba, which takes one extra lookup each, and
prints a table with the type of the request for registration, its status and
the date it was received:

```bash
cadastral get-lr-unit --unit-number 449 --main-book 21277 --all --plombe-detail
```

<!-- BEGIN GENERATED: output cadastral get-lr-unit --unit-number 449 --main-book 21277 --all --plombe-detail -->
```text
                  LAND REGISTRY UNIT
 Unit Number               449
 Main Book                 TESTMUNICIPALITY
 Institution               Test Land Registry Office
 Status                    Aktivan
 Unit Type                 VLASNIČKI
 Last Diary Number         Z-15677/2026
 Pending entries (plombe)  Z-12564/2026, Z-18444/2026
⚠️  This unit has pending entries (plombe) - a change may be in progress.

                             PENDING ENTRIES DETAIL (PLOMBE)
 File Number   Request                    Status                    Received  Outcome
 Z-12564/2026  Rješenje o nasljeđivanju   IZRADA NACRTA RJEŠENJA  2026-04-20  In progress
 Z-18444/2026  Uknjižba prava vlasništva  IZRADA NACRTA RJEŠENJA  2026-06-09  In progress

       PARCEL LIST (SHEET A)
 Parcel Number  Address  Area (m²)
 1122/1         OVČJA         3291
 TOTAL                        3291

                    OWNERSHIP SHEET (LIST B)
 Share  Owner           Address                     OIB
 1/4    Test Owner One  Test Street 1, Test City    00000000001
 1/12   Test Nephew A   Test Street 17, Test City   00000000130
 1/12   Test Nephew B   Test Street 110, Test City  00000000131
 1/12   Test Nephew C   Test Street 110, Test City  00000000132

  ENCUMBRANCES SHEET (LIST C)
 Description            Details
 No encumbrances found
```
<!-- END GENERATED: output -->

To name the unit directly instead of starting from a parcel, use
`--unit-number` and `--main-book` together, as in the example above. To keep
the result as a file, add `--format json` and `--output` with a file name.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `--unit-number`, `-u` `TEXT` | Land registry unit number (e.g., '769') | Not used |
| `--main-book`, `-b` `INTEGER` | Main book ID (e.g., 21277) | Not used |
| `--from-parcel`, `-p` `TEXT` | Get LR unit from parcel number | Not used |
| `--municipality`, `-m` `TEXT` | Municipality name or code (required with --from-parcel) | Not used |
| `--show-owners`, `-o` | Display ownership details (Sheet B) | Not switched on |
| `--show-parcels`, `-P` | Display all parcels in unit (Sheet A) | Not switched on |
| `--show-encumbrances`, `-e` | Display encumbrances (Sheet C) | Not switched on |
| `--plombe-detail`, `-D` | Resolve detail of pending entries (plombe) - one extra request per plomba | Not switched on |
| `--all`, `-a` | Show all sheets | Not switched on |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--output` `PATH` | Save output to file | Not used |
<!-- END GENERATED: options -->

## If something goes wrong

If you give a parcel but forget the municipality, the tool stops and asks for it:

<!-- BEGIN GENERATED: output cadastral get-lr-unit --from-parcel 103/2 -->
```text
✗ Error: --municipality is required when using --from-parcel
```
<!-- END GENERATED: output -->

Add `-m` and the municipality name or number.

If the unit number does not exist in that main book, the tool reports an error
that ends with `404 Not Found`. Check both numbers against your document. Other
messages are explained on the [errors page](../errors.md).

## Related pages

- [get-parcel](get-parcel.md) shows the cadastral side of the same parcel, including the possessors.
- [batch-lr-unit](batch-lr-unit.md) reads many units in one go.
- [Glossary](../glossary.md) explains list A, B and C and the plomba.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral get-lr-unit --help` prints:

```text
Usage: cadastral get-lr-unit [OPTIONS]

  Get detailed land registry unit information.

  Retrieve complete information about a land registry unit (zemljišnoknjižni
  uložak), including ownership (Sheet B), parcels (Sheet A), and encumbrances
  (Sheet C).

  Examples:
    # Get by unit number and main book ID
    cadastral get-lr-unit --unit-number 769 --main-book 21277

    # Get from parcel (automatic lookup)
    cadastral get-lr-unit --from-parcel 279/6 -m SAVAR

    # Show only ownership information
    cadastral get-lr-unit -u 769 -b 21277 --show-owners

    # Show all sheets
    cadastral get-lr-unit -p 279/6 -m SAVAR --all

    # Export to JSON
    cadastral get-lr-unit -u 769 -b 21277 --format json -o lr-unit.json

  ⚠️  DEMO/EDUCATIONAL USE ONLY - Mock server data only

Options:
  -u, --unit-number TEXT         Land registry unit number (e.g., '769')
  -b, --main-book INTEGER        Main book ID (e.g., 21277)
  -p, --from-parcel TEXT         Get LR unit from parcel number
  -m, --municipality TEXT        Municipality name or code (required with
                                 --from-parcel)
  -o, --show-owners              Display ownership details (Sheet B)
  -P, --show-parcels             Display all parcels in unit (Sheet A)
  -e, --show-encumbrances        Display encumbrances (Sheet C)
  -D, --plombe-detail            Resolve detail of pending entries (plombe) -
                                 one extra request per plomba
  -a, --all                      Show all sheets
  -f, --format [table|json|csv]  Output format
  --output PATH                  Save output to file
  --help                         Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
