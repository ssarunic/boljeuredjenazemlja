<!-- BEGIN GENERATED: banner -->
**English** | [Hrvatski](../../../hr/cli/commands/list-offices.md)

> **Practice data only.** This tool is a demonstration. It works with the practice server that comes with it and must not be connected to the official Croatian cadastre or land registry. Nothing shown on this page is real property data.
>
> Generated from `cadastral 0.1.0` by `scripts/build_docs.py`. Text between the generated markers is rewritten on every build.
<!-- END GENERATED: banner -->

# List the cadastral offices

Shows every regional cadastral office (područni ured za katastar) with its
number. You need the number to list the municipalities of an office.

## When you would use this

- You want to know which office is responsible for an area.
- Another command asks for an office number and you do not know it.

## Before you start

Nothing. This command takes no input.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral list-offices
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output cadastral list-offices -->
   ```text
   15 Cadastral Offices in Croatia:

   +------+------------------------------------------+
   |   ID | Name                                     |
   +======+==========================================+
   |   35 | PODRUČNI URED ZA KATASTAR KRAPINA        |
   +------+------------------------------------------+
   |   57 | PODRUČNI URED ZA KATASTAR ZAGREB         |
   +------+------------------------------------------+
   |   72 | PODRUČNI URED ZA KATASTAR RIJEKA         |
   +------+------------------------------------------+
   |   89 | PODRUČNI URED ZA KATASTAR SPLIT          |
   +------+------------------------------------------+
   |  104 | PODRUČNI URED ZA KATASTAR DUBROVNIK      |
   +------+------------------------------------------+
   |  114 | PODRUČNI URED ZA KATASTAR ZADAR          |
   +------+------------------------------------------+
   |  130 | PODRUČNI URED ZA KATASTAR ŠIBENIK        |
   +------+------------------------------------------+
   |  145 | PODRUČNI URED ZA KATASTAR PULA           |
   +------+------------------------------------------+
   |  156 | PODRUČNI URED ZA KATASTAR OSIJEK         |
   +------+------------------------------------------+
   |  171 | PODRUČNI URED ZA KATASTAR VARAŽDIN       |
   +------+------------------------------------------+
   |  183 | PODRUČNI URED ZA KATASTAR SLAVONSKI BROD |
   +------+------------------------------------------+
   |  198 | PODRUČNI URED ZA KATASTAR SISAK          |
   +------+------------------------------------------+
   |  209 | PODRUČNI URED ZA KATASTAR KARLOVAC       |
   +------+------------------------------------------+
   |  224 | PODRUČNI URED ZA KATASTAR GOSPIĆ         |
   +------+------------------------------------------+
   |  235 | PODRUČNI URED ZA KATASTAR BJELOVAR       |
   +------+------------------------------------------+
   ```
   <!-- END GENERATED: output -->

4. **ID** is the office number. Use it with `--office` on the
   [list-municipalities](list-municipalities.md) page.

## Choices you can make

To keep the list as a file, add `--format csv` and `--output` with a file name:

```bash
cadastral list-offices --format csv --output offices.csv
```

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|---|---|---|
| `--format`, `-f` | Output format (`table`, `json`, `csv`) | `table` is used |
| `--output`, `-o` `PATH` | Save output to file | Not used |
<!-- END GENERATED: options -->

## If something goes wrong

This command only fails when the tool cannot reach the practice server. The
message is explained on the [errors page](../errors.md); ask the person who
installed the tool to start the server.

## Related pages

- [list-municipalities](list-municipalities.md) uses the office number.
- [info](info.md) shows which server the tool is talking to.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
This is what `cadastral list-offices --help` prints:

```text
Usage: cadastral list-offices [OPTIONS]

  List all cadastral offices in Croatia.

  Example:
    cadastral list-offices
    cadastral list-offices --format json

Options:
  -f, --format [table|json|csv]  Output format
  -o, --output PATH              Save output to file
  --help                         Show this message and exit.
```
<!-- END GENERATED: synopsis -->

</details>
