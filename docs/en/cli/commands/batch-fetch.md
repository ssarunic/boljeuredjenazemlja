<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/batch-fetch.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it and must not be connected to the official Croatian cadastre or land registry. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.1.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# Look up a list of parcels at once

Give the tool several parcel numbers, or a file with a list, and get one table
with the area, the internal parcel number and the land registry unit of each.
The table is the starting point for reading many land registry units in one go.

## When you would use this

- An inheritance or a sale covers several parcels and you want to check all of them together.
- You have a spreadsheet of parcels from a client and want the land registry unit of each.
- You want to find out which parcels of a list do not exist or are misnumbered.

## Before you start

For a handful of parcels in one municipality, you type them on the line,
separated by commas. For longer lists, prepare a file. The simplest file is a
CSV, which you can save from any spreadsheet program. It has two columns,
`parcel_number` and `municipality`, and looks like this:

```text
parcel_number,municipality
103/2,SAVAR
45,
396/1,
```

An empty municipality cell means "same as the row above". A JSON file with the
same content is accepted too. Example files:
[parcels.csv](../examples/parcels.csv), [parcels.json](../examples/parcels.json).

## Step by step

1. Open Terminal.
2. Type the following line and press Enter. The quotes around the list matter.

   ```bash
   cadastral batch-fetch "103/2,45,396/1" -m SAVAR
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral batch-fetch "103/2,45,396/1" -m SAVAR -->
   ```text
   📊 Found 3 parcels to process


   BATCH PROCESSING SUMMARY
   ========================
     Total Parcels    3
     Successful       3
     Failed           0
     Success Rate     100.0%


   RESULTS
   =======
     #    Status    Parcel    Municipality      Area (m²)    Parcel ID    LR Unit
     1      ✓       103/2     SAVAR (334979)        1,200    6564817      657
     2      ✓       45        SAVAR (334979)          981    6564715      138
     3      ✓       396/1     SAVAR (334979)        2,077    6565198      645

   ✓ ✓ Successfully processed all 3 parcel(s)
   ```
   <!-- END GENERATED: output -->

4. **BATCH PROCESSING SUMMARY** counts how many parcels were found.
   **RESULTS** has one row per parcel. **Status** shows a tick for found and a
   cross for not found. **LR Unit** is the land registry unit number of the
   parcel, which you need for the next step.

## Choices you can make

To read the list from a file, use `--input` with the file name instead of
typing the parcels. Open Terminal in the folder where the file is:

```bash
cadastral batch-fetch --input parcels.csv
```

When one parcel is not found, the tool continues with the rest and lists the
failures at the end. If you would rather stop at the first problem, add
`--stop-on-error`.

To go on to the land registry, keep the result as a JSON file with
`--format json` and `--output`. The [batch-lr-unit](batch-lr-unit.md) page can
read that file directly:

```bash
cadastral batch-fetch "103/2,45,396/1" -m SAVAR --format json --output parcels-found.json
cadastral batch-lr-unit --from-batch-output parcels-found.json
```

Add `--detail full` to print the whole cadastral record of every parcel, as
the [get-parcel](get-parcel.md) page does, and `--show-owners` to include the
possessors.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `PARCELS` | Optional. A value you type right after the command name | Not used |
| `--input`, `-i` `PATH` | Input file (CSV or JSON) with parcel specifications | Not used |
| `--municipality`, `-m` `TEXT` | Municipality name or code (required for CLI list mode) | Not used |
| `--output`, `-o` `PATH` | Save output to file | Not used |
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--detail` | Detail level: basic (summary only) or full (complete parcel info for each) (`basic`, `full`) | `basic` is used |
| `--show-owners` | Include detailed ownership information in output | Not switched on |
| `--continue-on-error` / `--stop-on-error` | Continue processing after errors (default: continue) | `--continue-on-error` is used |
<!-- END GENERATED: options -->

## If something goes wrong

A parcel that does not exist does not stop the run. It gets a cross in the
**Status** column and an explanation in an **ERRORS** table at the end:

<!-- BEGIN GENERATED: output cadastral batch-fetch "103/2,999" -m SAVAR -->
```text
📊 Found 2 parcels to process


BATCH PROCESSING SUMMARY
========================
  Total Parcels    2
  Successful       1
  Failed           1
  Success Rate     50.0%


RESULTS
=======
  #    Status    Parcel    Municipality             Area (m²)    Parcel ID    LR Unit
  1      ✓       103/2     SAVAR (334979)               1,200    6564817      657
  2      ✗       999       SAVAR             Parcel not found    -            -

ERRORS
======
  #    Parcel         Error Type          Error Message
  2    999 (SAVAR)    Parcel not found    Parcel not found (parcel_number=999,
                                          municipality_reg_num=334979)

⚠️  Processed 1/2 parcels (50.0% success rate)
   1 parcel failed - see output for details
```
<!-- END GENERATED: output -->

Correct the number and run the command again for that parcel alone.

If the tool cannot find the file you named, check that Terminal is in the
folder where the file is, or type the full path to it. Other messages are
explained on the [errors page](../errors.md).

## Related pages

- [batch-lr-unit](batch-lr-unit.md) reads the land registry units found here.
- [search](search.md) checks one parcel.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral batch-fetch --help` prints:

```text
Usage: cadastral batch-fetch [OPTIONS] PARCELS

  Fetch information for multiple parcels in batch mode.

  Supports two input methods:

  1. CLI comma-separated list (for quick batches):
     cadastral batch-fetch "103/2,45,396/1" --municipality SAVAR

  2. File input (for large batches):
     cadastral batch-fetch --input parcels.csv
     cadastral batch-fetch --input parcels.json

  CSV Format (parcel numbers with municipality):
    parcel_number,municipality
    103/2,334979
    45,
    396/1,

  Note: Empty municipality cells inherit from the previous row.

  CSV Format (direct parcel IDs):
    parcel_id
    12345678
    87654321

  JSON Format:
    [
      {"parcel_number": "103/2", "municipality": "334979"},
      {"parcel_number": "45", "municipality": "SAVAR"}
    ]

  Or:
    [
      {"parcel_id": "12345678"},
      {"parcel_id": "87654321"}
    ]

  Examples:
    # Quick batch with CLI list
    cadastral batch-fetch "103/2,45,396/1" -m SAVAR

    # Batch from CSV file
    cadastral batch-fetch --input parcels.csv --format csv -o results.csv

    # Batch with full details for each parcel (like get-parcel)
    cadastral batch-fetch "103/2,45,396/1" -m SAVAR --detail full

    # Batch with ownership details in JSON format
    cadastral batch-fetch --input parcels.json --show-owners --format json -o results.json

Options:
  -i, --input PATH                Input file (CSV or JSON) with parcel
                                  specifications
  -m, --municipality TEXT         Municipality name or code (required for CLI
                                  list mode)
  -o, --output PATH               Save output to file
  -f, --format [table|json|csv]   Output format
  --detail [basic|full]           Detail level: basic (summary only) or full
                                  (complete parcel info for each)
  --show-owners                   Include detailed ownership information in
                                  output
  --continue-on-error / --stop-on-error
                                  Continue processing after errors (default:
                                  continue)
  --help                          Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
