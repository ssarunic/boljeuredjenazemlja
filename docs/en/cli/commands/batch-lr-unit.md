<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/batch-lr-unit.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it. Before connecting it to any other server, including the official Croatian cadastre and land registry, verify that you have the rights to use that server and its data; you do so at your own risk. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.1.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Read many land registry units at once

Give the tool a list of land registry units, or the result of a
[batch-fetch](batch-fetch.md) run, and it prints the sheets of every unit one
after another.

## When you would use this

- You have checked a list of parcels with batch-fetch and now want the owners and encumbrances of each.
- You keep a list of units for a case and want to re-read all of them after a change.

## Before you start

Each unit is identified by its number and the main book ID. The easiest way to
get both is the JSON file that [batch-fetch](batch-fetch.md) writes. You can
also prepare a CSV file with two columns, `lr_unit_number` and `main_book_id`,
like the example [lr_units.csv](../examples/lr_units.csv):

<!-- BEGIN GENERATED: file lr_units.csv -->
```text
lr_unit_number,main_book_id
657,21277
769,21277
449,21277
```
<!-- END GENERATED: file -->

## Step by step

1. Open Terminal in the folder where your file is.
2. Type the following line and press Enter:

   ```bash
   cadastral batch-lr-unit --input lr_units.csv --show-owners
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral batch-lr-unit --input lr_units.csv --show-owners -->
   ```text
   📄 Reading LR units from: lr_units.csv
   📊 Found 3 LR units to process

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
   Parcel list as recorded in the land register; the address column is the culture or toponym of the
   old land register, not a location.

                                    OWNERSHIP SHEET (LIST B)
    Share  Owner                  Address                 OIB  Entry
    1/2    IVIĆ MARKO, SIN PETRA  TESTNA ULICA 15, SPLIT  -    1.1 · 2018-06-10 · Z-5678/2018
    1/2    IVIĆ ANA, KĆI PETRA    SAVAR                   -    2.1 · 2018-06-10 · Z-5678/2018

                                       ENCUMBRANCES SHEET (LIST C)
    Description  Details
    1.           • 1.1: Stig. 23. svibnja 1949.
                 Z 487/49
                 Na temelju presude 29. siječnja 1940. agr. 1996/31 Sreskog suda u Preku, uknjižuje se
                 pravo ploduživanja do udaje, u korist:
                   In favour of:
                     IVIĆ MARIJA, KĆI PETRA, SAVAR
    2.           • 2.1: Pr. 20. srpnja 1979.
                 Z 2444/79
                 Na temelju rješenja o nasljeđivanju od 27. studenog 1967. pod brojem O 533/67,
                 Općinskog suda u Zadru, uknjižuje se pravo ploduživanja u korist:
                   In favour of:
                     IVIĆ JELA UD. PETRA ZA 2/6

   ---

                  LAND REGISTRY UNIT
    Unit Number        769
    Main Book          SAVAR
    Institution        Zemljišnoknjižni odjel Zadar
    Status             Aktivan
    Unit Type          VLASNIČKI
    Last Diary Number  Z-27986/2025

          PARCEL LIST (SHEET A)
    Parcel Number  Address   Area (m²)
    118/4          POLJE           409
    192/3          BANIŠINA        322
    198/3          BANIŠINA        255
    202/1          BANIŠINA        312
    221/6          BANIŠINA        501
    267/6          BANIŠINA        680
    279/6          VOLUNJAK       1890
    TOTAL                         4369
   Parcel list as recorded in the cadastre.

                             OWNERSHIP SHEET (LIST B)
    Share  Owner        Address    OIB          Entry
    4/8    Vlasnik 117  -          -            1.1 · 2012-04-05 · Z-3983/2012
    1/8    Vlasnik 119  -          -            3.1 · 2012-04-05 · Z-3983/2012
    1/8    Vlasnik 326  -          -            4.1 · 2012-04-05 · Z-3983/2012
    1/8    Vlasnik 116  Adresa 31  00000000036  5.2 · 2020-02-14 · Z-3937/2020
    1/24   Vlasnik 135  Adresa 10  00000000850  6.1 · 2018-03-21 · Z-6789/2018
    1/24   Vlasnik 327  Adresa 10  00000000868  7.1 · 2018-03-21 · Z-6789/2018
    1/24   Vlasnik 328  Adresa 32  00000000876  8.1 · 2018-03-21 · Z-6789/2018

                                       ENCUMBRANCES SHEET (LIST C)
    Description                     Details
    1. Na suvlasnički dio: 1 (4/8)  • 1.1: Zaprimljeno 05.05.2016.g. pod brojem Z-9139/2016

                                    ZABILJEŽBA, TRAŽBINA SOCIJALNE POMOĆI, RJEŠENJE CENTRA ZA
                                    SOCIJALNU SKRB ZADAR KLASA: UP/I-551-04/16-02/29, URBROJ:
                                    2198-12-22-16-2 25.04.2016, počevši od 15. travnja 2016. godine pa
                                    nadalje, utvrđeno rješenjem Centra za socijalnu skrb Zadar KLASA:
                                    UP/I-551-04/16-02/29, URBROJ: 2198-12-22-16-2 od 25. travnja 2016.
                                    godine i prijedloga RH po zz od 04. svibnja 2016. godine, na
                                    nekretninamam, uknjiženog prava vlasništva na ime N.N. rođ. N.N.,
                                    OIB: 00000000884, N.N., za korist REPUBLIKE HRVATSKE, Centar za
                                    socijalnu skrb Zadar.

   ---

                      LAND REGISTRY UNIT
    Unit Number               449
    Main Book                 SAVAR
    Institution               Zemljišnoknjižni odjel Zadar
    Status                    Aktivan
    Unit Type                 VLASNIČKI
    Last Diary Number         Z-18444/2026
    Pending entries (plombe)  Z-12564/2026
   ⚠️  This unit has pending entries (plombe) - a change may be in progress.

          PARCEL LIST (SHEET A)
    Parcel Number  Address  Area (m²)
    1122/1         OVČJA         3291
    TOTAL                        3291
   Parcel list as recorded in the land register; the address column is the culture or toponym of the
   old land register, not a location.

                              OWNERSHIP SHEET (LIST B)
    Share  Owner        Address    OIB          Entry
    1/4    Vlasnik 114  Adresa 75  00000000010  127.2 · 2026-05-14 · Z-15677/2026
    1/4    Vlasnik 115  Adresa 41  00000000028  128.1 · 2025-09-29 · Z-31325/2025
    1/4    Vlasnik 116  Adresa 31  00000000036  129.1 · 2025-09-29 · Z-31325/2025
    1/4    Vlasnik 116  Adresa 76  00000000036  133.1 · 2026-06-09 · Z-18444/2026

     ENCUMBRANCES SHEET (LIST C)
    Description            Details
    No encumbrances found

   ✓ ✓ Successfully processed all 3 LR unit(s)
   ```
   <!-- END GENERATED: output -->

4. The units are printed one after another, separated by a line of dashes.
   Each is laid out as on the [get-lr-unit](get-lr-unit.md) page:
   **LAND REGISTRY UNIT**, then **PARCEL LIST (SHEET A)**,
   **OWNERSHIP SHEET (LIST B)** and **ENCUMBRANCES SHEET (LIST C)**. A unit
   with pending entries carries the same **Pending entries (plombe)** line and
   warning.

## Choices you can make

To continue from a batch-fetch result, use `--from-batch-output` with the JSON
file it wrote:

```bash
cadastral batch-lr-unit --from-batch-output parcels-found.json --show-owners
```

For a long list, screen output is hard to read. Keep it as a file instead with
`--format json` and `--output`:

```bash
cadastral batch-lr-unit --input lr_units.csv --show-owners --format json --output units.json
```

When one unit cannot be read, the tool continues with the rest. Add
`--stop-on-error` to stop at the first problem instead.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `--input`, `-i` `PATH` | Input file (CSV or JSON) with LR unit specifications | Not used |
| `--from-batch-output`, `-b` `PATH` | Read LR unit refs from batch-fetch JSON output | Not used |
| `--output`, `-o` `PATH` | Save output to file | Not used |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--show-owners` | Include detailed ownership information in output | Not switched on |
| `--continue-on-error` / `--stop-on-error` | Continue processing after errors (default: continue) | `--continue-on-error` is used |
<!-- END GENERATED: options -->

## If something goes wrong

If the tool cannot find the file you named, it stops before reading anything.
Check that Terminal is in the folder where the file is, or type the full path
to it.

If one unit in the list does not exist, that unit is reported as failed and
the others are still printed. Check its number and main book ID in your file.
Other messages are explained on the [errors page](../errors.md).

## Related pages

- [batch-fetch](batch-fetch.md) produces the list of units from a list of parcels.
- [get-lr-unit](get-lr-unit.md) reads one unit and explains the sheets.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral batch-lr-unit --help` prints:

```text
Usage: cadastral batch-lr-unit [OPTIONS]

  Fetch information for multiple land registry units in batch mode.

  Supports two input methods:

  1. Direct LR unit file (CSV or JSON):
     cadastral batch-lr-unit --input lr_units.csv

  2. From batch-fetch output (reads unique LR unit refs):
     cadastral batch-fetch "103/2,45" -m SAVAR --format json -o parcels.json
     cadastral batch-lr-unit --from-batch-output parcels.json

  CSV Format:
    lr_unit_number,main_book_id
    769,21277
    123,45678

  JSON Format:
    [
      {"lr_unit_number": "769", "main_book_id": 21277},
      {"lr_unit_number": "123", "main_book_id": 45678}
    ]

  Examples:
    # From direct LR unit input
    cadastral batch-lr-unit --input lr_units.csv

    # From batch-fetch output (pipeline)
    cadastral batch-fetch "103/2,45,396/1" -m SAVAR --format json -o parcels.json
    cadastral batch-lr-unit --from-batch-output parcels.json

    # With ownership details in JSON format
    cadastral batch-lr-unit -i lr_units.json --show-owners --format json -o results.json

  ⚠️  Demo project: before using any server other than the included mock, verify
  your rights to use it; use at your own risk

Options:
  -i, --input PATH                Input file (CSV or JSON) with LR unit
                                  specifications
  -b, --from-batch-output PATH    Read LR unit refs from batch-fetch JSON output
  -o, --output PATH               Save output to file
  -f, --format [table|json|csv]   Output format
  --show-owners                   Include detailed ownership information in
                                  output
  --continue-on-error / --stop-on-error
                                  Continue processing after errors (default:
                                  continue)
  --help                          Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
