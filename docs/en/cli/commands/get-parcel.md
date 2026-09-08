<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/get-parcel.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it and must not be connected to the official Croatian cadastre or land registry. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.1.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# See everything the cadastre holds about a parcel

The full cadastral record of one parcel: location, area, land use, the
possession sheet (posjedovni list) with the people the cadastre records, and
the number of the land registry unit where the legal owners are.

## When you would use this

- You are preparing a contract and need the area, the land use and the cadastral state of the parcel in one place.
- You want to compare who the cadastre records as possessor with who the land registry records as owner.
- You need the number of the land registry unit (zemljišnoknjižni uložak) of a parcel so you can read its owners and encumbrances.

## Before you start

You need the parcel number and the cadastral municipality, by name or number,
as for [search](search.md).

Keep one distinction in mind while you read. The cadastre records possessors
(posjednici); the land registry records owners (vlasnici). They are often the
same people, but not always, and only the land registry is proof of ownership.
This page shows the cadastre. The [get-lr-unit](get-lr-unit.md) page shows the
land registry.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral get-parcel 103/2 -m SAVAR --show-owners
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral get-parcel 103/2 -m SAVAR --show-owners -->
   ```text
   PARCEL INFORMATION
   ==================
     Parcel Number             103/2
     Parcel ID                 6564817
     Municipality              SAVAR (334979)
     Address                   POLJE
     Area                      1,200 m²
     Building Permitted        No
     Cadastre/LR harmonized    Yes


   LAND USE
   ========
     Type         Area (m²)    Percentage    Buildings
     MASLINJAK        1,200        100.0%    No


   POSSESSION SHEET (cadastre / posjedovni list) (2 possessors)
   ============================================================
   Note: cadastre possessors may differ from registered owners. For land-registry owners (vlasnici),
   use: cadastral get-lr-unit
     Name                     Ownership    Address
     IVIĆ MARKO, SIN PETRA          N/A    TESTNA ULICA 15, SPLIT
     IVIĆ ANA, KĆI PETRA            N/A    SAVAR


   LAND REGISTRY
   =============
     Unit Number    657
     Main Book      N/A
     Institution    N/A
     Status         Inactive
     Verified       No


   ADDITIONAL INFO
   ===============
     Map URL         https://oss.uredjenazemlja.hr/map?center=380616.77,4880907.83&zoom=19&layers=DOF
                     5_2023_2024,DKP_CESTICE,DKP_KATASTARSKE_OPCINE,zupanija,ulica,kucni_broj
     Detail Sheet    4
   ```
   <!-- END GENERATED: output -->

4. The screen has five parts. **PARCEL INFORMATION** identifies the parcel;
   the line **Cadastre/LR harmonized** says whether the cadastre and the land
   registry agree about it. **LAND USE** splits the area by cadastral culture.
   **POSSESSION SHEET (cadastre / posjedovni list)** lists the possessors the
   cadastre records, with their share where the cadastre has one.
   **LAND REGISTRY** gives the number of the land registry unit
   (**Unit Number**) that you can look up next. **ADDITIONAL INFO** contains a
   link that opens the parcel on the public map.

5. Where a value is not recorded, the tool prints **N/A**. In the possession
   sheet this is common: the cadastre often records who possesses without
   recording a share.

## Choices you can make

Without `--show-owners` the possession sheet is left out and the screen is
shorter. Add it whenever you want to see the people.

`--detail` narrows the screen to one part: `basic` for the identification only,
`owners` for the possession sheet, `landuse` for the land use split, `geometry`
for the boundary coordinates, `full` for everything.

```bash
cadastral get-parcel 103/2 -m SAVAR --detail landuse
```

To keep the record as a file, add `--format json` and `--output` with a file
name. This is the form to use when you want to attach the data to a case file
or pass it to a colleague.

```bash
cadastral get-parcel 103/2 -m SAVAR --show-owners --format json --output parcel-103-2.json
```

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `PARCEL_NUMBER` | A value you type right after the command name, without a name in front of it | Required |
| `--municipality`, `-m` `TEXT` | Municipality name or code | Required |
| `--detail` | Detail level (`basic`, `full`, `owners`, `landuse`, `geometry`) | `full` is used |
| `--show-owners` | Include ownership details | Not switched on |
| `--show-geometry` | Include boundary coordinates | Not switched on |
| `--format`, `-f` | Output format (`table`, `json`, `yaml`, `csv`) | `table` is used |
| `--output`, `-o` `PATH` | Save output to file | Not used |
<!-- END GENERATED: options -->

## If something goes wrong

If the municipality is not recognised, the tool says so and stops:

<!-- BEGIN GENERATED: output cadastral get-parcel 103/2 -m NOWHERE -->
```text
✗ Error: Municipality 'NOWHERE' not found
```
<!-- END GENERATED: output -->

Check the spelling, or use the registration number instead of the name. You can
find it with [search-municipality](search-municipality.md).

If the parcel is not found, check the number on your document, including any
part after the slash. Other messages are explained on the
[errors page](../errors.md).

## Related pages

- [get-lr-unit](get-lr-unit.md) reads the land registry unit whose number appears under the land registry heading.
- [search](search.md) is the short form of this command.
- [get-geometry](get-geometry.md) gives the boundary of the parcel for a map.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral get-parcel --help` prints:

```text
Usage: cadastral get-parcel [OPTIONS] PARCEL_NUMBER

  Get complete parcel information with ownership details.

  Examples:
    cadastral get-parcel 103/2 -m SAVAR
    cadastral get-parcel 103/2 -m 334979 --show-owners
    cadastral get-parcel 103/2 -m 334979 --detail owners
    cadastral get-parcel 103/2 -m 334979 --format json -o parcel.json

Options:
  -m, --municipality TEXT         Municipality name or code  [required]
  --detail [basic|full|owners|landuse|geometry]
                                  Detail level
  --show-owners                   Include ownership details
  --show-geometry                 Include boundary coordinates
  -f, --format [table|json|yaml|csv]
                                  Output format
  -o, --output PATH               Save output to file
  --help                          Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
