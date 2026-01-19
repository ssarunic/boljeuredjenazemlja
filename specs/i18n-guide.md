# Internationalization (i18n) Guide

This document provides guidance for localizing CLI commands in the Croatian Cadastral API project.

## Quick Reference

### Import Statement
```python
from ...i18n import _, ngettext, pgettext
```

### Basic Translation
```python
# Wrap user-facing strings in _()
print(_("Hello, world!"))
message = _("Parcel not found")
```

### String Formatting
```python
# Use named placeholders
_("Parcel {num} in municipality {muni}").format(num=n, muni=m)

# NOT concatenation
_("Found ") + str(count) + _(" results")  # ❌ Wrong
```

### Plural Forms
```python
from ...i18n import ngettext

count = len(results)
msg = ngettext(
    "Found {count} municipality",
    "Found {count} municipalities",
    count
).format(count=count)
```

### Context-Specific Translation
```python
from ...i18n import pgettext

# When same English word has different meanings
button_label = pgettext("button", "Open")  # Open a file
status = pgettext("status", "Open")        # Status is open
```

## What to Localize

### ✅ YES - Localize These

1. **Help text and descriptions**
   ```python
   @click.option("--municipality", "-m", help=_("Municipality name or code"))
   ```

2. **User messages**
   ```python
   print_error(_("Parcel not found"))
   print_success(_("Download complete"))
   ```

3. **Status messages**
   ```python
   with console.status(_("Searching...")):
       pass
   ```

4. **Table headers (for display)**
   ```python
   data = {
       _("Parcel Number"): parcel.parcel_number,
       _("Municipality"): parcel.municipality_name,
   }
   ```

5. **Suggestions and hints**
   ```python
   console.print(_("💡 Tip: Use --partial for fuzzy search"), style="dim")
   ```

### ❌ NO - Don't Localize These

1. **Command names**
   ```python
   @click.command("search")  # Keep in English
   ```

2. **Parameter names**
   ```python
   @click.option("--municipality")  # Keep in English
   ```

3. **JSON/CSV keys (API standard)**
   ```python
   export_data = {
       "parcel_number": parcel.parcel_number,  # Keep in English
       "municipality_code": muni_code,
   }
   ```

4. **Technical format names**
   ```python
   @click.option("--format", type=click.Choice(["wkt", "geojson"]))  # Keep as-is
   ```

## Localization Pattern for Commands

### Template
```python
"""Command description."""

import click
from rich.console import Console

from ... import CadastralAPIClient
from ...exceptions import CadastralAPIError
from ...i18n import _, ngettext
from ..formatters import print_error, print_success

console = Console()

# Define help text as module constants (can't use _() in decorators directly)
_COMMAND_HELP = _("Command description")
_OPTION_HELP = _("Option description")

@click.command()
@click.argument("argument_name")
@click.option("--option-name", "-o", help=_OPTION_HELP)
@click.pass_context
def command_name(ctx: click.Context, argument_name: str, option_name: str) -> None:
    try:
        with CadastralAPIClient() as client:
            # Status messages
            with console.status(_("Processing...")):
                result = client.some_method()

            if not result:
                # Error messages
                print_error(_("Not found"))
                console.print(_("\nSuggestions:"), style="yellow")
                raise SystemExit(1)

            # Table headers (display)
            data = {
                _("Field Name"): result.field,
                _("Other Field"): result.other,
            }

            # Success messages
            print_success(_("Operation complete"))

    except CadastralAPIError as e:
        print_error(_("API error: {error}").format(error=e))
        raise SystemExit(1)
```

## Croatian Translation Examples

### Common Translations

| English | Croatian |
|---------|----------|
| Parcel Number | Broj čestice |
| Municipality | Općina |
| Area | Površina |
| Address | Adresa |
| Land Use | Namjena zemljišta |
| Building Permitted | Dozvoljeno građenje |
| Owners | Vlasnici |
| Yes | Da |
| No | Ne |
| N/A | N/D |
| Error | Greška |
| Success | Uspjeh |
| Searching... | Pretražujem... |
| Loading... | Učitavam... |
| Not found | Nije pronađeno |
| Parcel not found | Čestica nije pronađena |
| Municipality not found | Općina nije pronađena |
| Download complete | Preuzimanje završeno |
| File saved | Datoteka spremljena |
| Suggestions | Prijedlozi |
| Total | Ukupno |
| Count | Broj |

### Plural Forms (Croatian has 3 forms)

```python
# English: 2 forms (singular, plural)
ngettext("Found {count} result", "Found {count} results", count)

# Croatian: 3 forms
msgid "Found {count} result"
msgid_plural "Found {count} results"
msgstr[0] "Pronađen {count} rezultat"    # 1, 21, 31, ...
msgstr[1] "Pronađena {count} rezultata"  # 2-4, 22-24, ...
msgstr[2] "Pronađeno {count} rezultata"  # 0, 5-20, 25-30, ...
```

## Workflow

### 1. Add Translatable Strings to Code
```python
from ...i18n import _
print(_("New message"))
```

### 2. Extract Strings to Template
```bash
./scripts/generate_pot.sh
```

### 3. Update Translation Files
```bash
./scripts/update_translations.sh
```

### 4. Edit Translations
Edit `po/hr.po` and `po/en.po` files:
```po
msgid "Parcel Number"
msgstr "Broj čestice"
```

### 5. Compile Translations
```bash
./scripts/compile_translations.sh
```

### 6. Test
```bash
# Croatian (default)
cadastral search 103/2 -m SAVAR

# English
cadastral search 103/2 -m SAVAR --lang en
CADASTRAL_LANG=en cadastral search 103/2 -m SAVAR
```

## Testing Checklist

- [ ] All user-facing strings wrapped in `_()`
- [ ] Named placeholders used in format strings
- [ ] Table headers localized for display output
- [ ] JSON/CSV keys kept in English
- [ ] Command/parameter names kept in English
- [ ] Help text localized
- [ ] Error messages localized
- [ ] Success messages localized
- [ ] Status messages localized
- [ ] Plural forms handled correctly
- [ ] Both languages tested

## Common Mistakes to Avoid

### ❌ Don't Concatenate Translations
```python
# Wrong
message = _("Found ") + str(count) + _(" results")

# Right
message = _("Found {count} results").format(count=count)
```

### ❌ Don't Use _() in Decorators
```python
# Wrong - won't work
@click.option("--opt", help=_("Help text"))

# Right - use constant
_OPT_HELP = _("Help text")
@click.option("--opt", help=_OPT_HELP)
```

### ❌ Don't Localize Technical Terms
```python
# Wrong
format_type = _("wkt")  # Don't translate format names

# Right
format_type = "wkt"  # Keep technical terms in English
```

### ❌ Don't Localize JSON Keys
```python
# Wrong
data = {
    _("parcel_number"): value  # Don't translate keys
}

# Right - keys in English, display in Croatian
if output_format == "json":
    data = {
        "parcel_number": value  # API standard
    }
else:
    data = {
        _("Parcel Number"): value  # Display
    }
```

## Resources

- [GNU gettext Manual](https://www.gnu.org/software/gettext/manual/)
- [Python gettext Documentation](https://docs.python.org/3/library/gettext.html)
- [Click i18n Support](https://click.palletsprojects.com/en/8.1.x/utils/#click.get_text_stream)
- [Poedit](https://poedit.net/) - GUI editor for .po files

## Next Steps

1. Localize remaining command files following the pattern above
2. Extract all strings with `./scripts/generate_pot.sh`
3. Translate strings in `po/hr.po`
4. Compile with `./scripts/compile_translations.sh`
5. Test both languages thoroughly
6. Update CLI.md with language selection documentation
