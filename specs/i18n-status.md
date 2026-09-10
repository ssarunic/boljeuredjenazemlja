# i18n Status

**Last Updated**: 2026-09-08

## Overall Status: Complete (verified by `cli/tests/test_i18n_coverage.py`)

- Infrastructure: complete
- Automated coverage gate: complete (`cd cli && pytest tests/test_i18n_coverage.py`)
- Code localization: complete for the CLI (option help, command help, output,
  error messages, and click's own messages such as "Usage:" / "Missing option")
- Croatian translations: 377/377 extracted strings translated (click 8.3.0)
- `--lang` flag: switches help texts and runtime output at any position
  (`cadastral --lang en search ...`); `CADASTRAL_LANG` and the system locale
  are still honoured
- MCP server: not localized by design (tool descriptions and responses are
  consumed by an AI agent, not shown to a person)

The sections below this one predate the coverage gate and describe the state
on 2025-11-14; the gate output is authoritative.

## Gaps Closed (2026-09-08)

1. 16 untranslated Croatian entries translated.
2. All click option `help=` texts wrapped in `_()`; all 16 commands pass their
   description via `help=command_help(_(...))` instead of relying on the
   docstring. `command_help()` re-inserts click's `\b` no-wrap marker in front
   of indented example blocks so the marker stays out of the .po files.
3. Stray literals (`Use '... --help'`, `Reading parcels from`, `Details:`,
   `Field` / `Value` / `Metric` column headers) wrapped in `_()`.
4. `--lang` was a no-op: command modules bound `_` at import time. `i18n` now
   exposes delegating `_` / `ngettext` / `pgettext` functions and `main.py`
   pre-scans `sys.argv` for `--lang` before importing the command modules.
   The duplicate `--lang` option on `get-lr-unit` was removed.
5. API error types are rendered through translated labels
   (`formatters.describe_error`, `error_type_label`, `error_type_value_label`)
   instead of the raw `ErrorType` value.
6. click's own messages are extracted into the catalog
   (`scripts/generate_pot.sh` scans the installed click package) and
   translated to Croatian.
7. The catalog had been extracted from a stray user-site click 8.1.8 while the
   venv (and therefore the CLI and the gate) run click 8.3.0, so 4 messages
   were missing and 16 were stale (`No such option: --x` leaked in English).
   `generate_pot.sh` now defaults to the repository `.venv` interpreter; the
   click version it scanned is printed. Override with `PYTHON=...` only when
   that interpreter is the one the CLI runs with.
8. click builds the `[required]` help marker as `_(extra["required"])`, a
   variable xgettext cannot see, so it stayed English. `i18n.N_()` was added
   and `main.py` marks `N_("required")`; the help now shows `[obavezno]`.
   Use the same trick for any other library string reached via a variable;
   the gate cannot detect this class of gap on its own.

## ✅ Completed

### Infrastructure (100%)

**Core i18n Module** (`api/src/cadastral_api/i18n.py`):
- Automatic language detection (system locale → Croatian default)
- `_()` for basic translation
- `ngettext()` for plural forms
- `pgettext()` for context-specific translation
- Language switching at runtime
- Environment variable support (`CADASTRAL_LANG`)

**Translation Scripts**:
- `scripts/generate_pot.sh` - Extract strings from source
- `scripts/update_translations.sh` - Update translations
- `scripts/compile_translations.sh` - Compile .po to .mo
- `scripts/init_language.sh` - Initialize new language

**Build System**:
- Package data configuration for .mo files
- Automatic compilation on build

### Code Localization (100%)

**All CLI commands localized**:
- `cli/src/cadastral_cli/main.py` - Main entry point
- `cli/src/cadastral_cli/formatters.py` - Output formatters
- `cli/src/cadastral_cli/commands/search.py`
- `cli/src/cadastral_cli/commands/parcel.py`
- `cli/src/cadastral_cli/commands/discovery.py`
- `cli/src/cadastral_cli/commands/gis.py`
- `cli/src/cadastral_cli/commands/cache.py`

All user-facing strings wrapped in `_()`, `ngettext()`, or `pgettext()`.

### Translation Files (100%) ✅

**Created**:
- `po/hr.po` - Croatian (186/186 translated, 100% ✅)
- `po/en.po` - English (15 explicit, rest use source)
- `api/src/cadastral_api/locale/hr/LC_MESSAGES/cadastral.mo` (14KB)
- `api/src/cadastral_api/locale/en/LC_MESSAGES/cadastral.mo` (1.2KB)

**Coverage**:
- ✅ Common UI messages (errors, success, status)
- ✅ Table headers (Parcel Number → Broj čestice, etc.)
- ✅ Section headers (PARCEL INFORMATION → INFORMACIJE O ČESTICI)
- ✅ Status messages (Searching... → Pretražujem...)
- ✅ Error messages (Parcel not found → Čestica nije pronađena)
- ✅ Cache management messages (all 9 strings completed)
- ✅ Municipality search messages (all 10 strings completed)
- ✅ GIS operation messages (all 14 strings completed)
- ✅ Plural forms (3 forms for Croatian)
- ✅ All CLI output text (100% translated)

---

## ✅ Recently Completed (2025-11-14)

### Croatian Translations (100% complete) ✅

**Status**: 186/186 translated (all strings completed!)

**Completed translations include**:
- Cache management: "Location: {cache_dir}" → "Lokacija: {cache_dir}"
- Municipality search: "Municipality '{municipality}' not found" → "Općina '{municipality}' nije pronađena"
- Parcel operations: "Fetching parcel {parcel_number}..." → "Dohvaćam česticu {parcel_number}..."
- GIS operations: "Geometry not found" → "Geometrija nije pronađena"
- File exports: "WKT saved to: {output}" → "WKT spremljen u: {output}"
- Error messages: "API error: {error_type}" → "API greška: {error_type}"

**Compilation**:
```bash
./scripts/compile_translations.sh
# ✓ Compiled 186 messages to cadastral.mo
```

---

## ⏳ Pending

### Testing (Not Started)

Need to verify:
- [ ] Croatian output works (default)
- [ ] English output works (`--lang en`)
- [ ] Environment variable works (`CADASTRAL_LANG=en`)
- [ ] System locale detection
- [ ] All output formats (table, JSON, CSV)
- [ ] Plural forms in Croatian

**Test commands**:
```bash
# Croatian (default)
cadastral search 103/2 -m SAVAR
cadastral get-parcel 103/2 -m SAVAR --show-owners

# English
cadastral search 103/2 -m SAVAR --lang en
CADASTRAL_LANG=en cadastral get-parcel 103/2 -m SAVAR

# Plural forms
cadastral get-parcel <1_owner> -m SAVAR   # 1 vlasnik
cadastral get-parcel <2_owners> -m SAVAR  # 2 vlasnika
cadastral get-parcel <5_owners> -m SAVAR  # 5 vlasnika
```

---

## 📋 Next Steps

### 1. ~~Complete Croatian Translations~~ ✅ DONE
~~Add 33 missing translations in `po/hr.po`~~

### 2. Test End-to-End (~2-3 hours) ⏳ NEXT
Verify all functionality works in both languages

### 3. Fix Issues (~1-2 hours) ⏳
Address any bugs found during testing

---

## 📚 Translation Examples

### Croatian Cadastral Terminology

| English | Croatian |
|---------|----------|
| Cadastral parcel | Katastarska čestica |
| Cadastral municipality | Katastarska općina |
| Possession sheet | Posjedovni list |
| Land registry | Zemljišna knjiga |
| Land registry unit | Zemljišnoknjižni uložak |
| Land use | Namjena zemljišta |
| Cadastral office | Područni ured za katastar |
| Parcel number | Broj čestice |
| Municipality | Općina |
| Area | Površina |
| Owners | Vlasnici |

### Plural Forms

Croatian has 3 plural forms:

```text
n%10==1 && n%100!=11 ? 0     # 1, 21, 31, 41, ...
n%10>=2 && n%10<=4 && ... ? 1 # 2-4, 22-24, 32-34, ...
: 2                           # 0, 5-20, 25-30, ...
```

Examples:
- 1 vlasnik (singular)
- 2 vlasnika (paucal)
- 5 vlasnika (plural)

---

## 💡 Design Decisions

1. **Croatian as Default** - System defaults to Croatian, not English
2. **gettext Standard** - Using Python's standard gettext (industry standard)
3. **Commands in English** - CLI commands/options stay in English (best practice)
4. **JSON Keys in English** - API data keys remain in English (standard)
5. **Display Text Localized** - All user-facing text in Croatian
6. **Proper Plural Forms** - Croatian 3-form pluralization implemented

---

## 🔧 Known Issues

1. ✅ ~~Translation infrastructure~~ - FIXED
2. ✅ ~~Translation files~~ - FIXED
3. ✅ ~~Code localization~~ - FIXED
4. ✅ ~~Compiled .mo files~~ - FIXED
5. 🔄 **39 Croatian strings untranslated** - In progress (79% done)
6. ⏳ **No testing performed** - Not started

---

## 📖 Documentation

- [i18n-guide.md](i18n-guide.md) - Developer guide for adding translations
- [localization_example.py](localization_example.py) - Code example
- [i18n-status.md](i18n-status.md) - This file

---

## 🚀 Effort Estimate

- ~~Infrastructure~~ ✅ DONE
- ~~Code localization~~ ✅ DONE
- ~~Complete 33 translations~~ ✅ DONE (2025-11-14)
- Testing: **2-3 hours** ⏳
- Bug fixes: **0-1 hours** ⏳

Total remaining: 2-4 hours

---

**Status**: Production-ready for translations! All 186 strings translated to Croatian. Only testing remains.
