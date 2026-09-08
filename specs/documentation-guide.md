# CLI Documentation Guide

This document is the operating manual for whoever writes or updates the CLI
user documentation, whether a person or an LLM. It defines who the documents
are for, how they are structured, which parts are generated and which are
written by hand, how the Croatian edition is produced, and what has to happen
every time a command is added, changed, or removed.

The documentation it governs lives under `docs/en/cli/` (source) and
`docs/hr/cli/` (generated). The old single-file reference
`docs/cli-reference.md` is superseded by it.

## 1. Who reads the documentation

There are exactly two readers. Every page is addressed to one of them, never
both.

### 1.1 The professional user

A lawyer, public notary, court clerk, surveyor, or real-estate agent. They know
the land registry far better than the software: they can explain what a
teretovnica is, but they have never opened a terminal. They want to answer a
concrete question ("who owns parcel 279/6 in k.o. Savar and is there a mortgage
on it") and get back to their work.

Assumptions about this reader, which every page may rely on:

- The tool is already installed on their computer and works. They did not
  install it.
- The practice server is running, or they know who to ask to start it.
- They can open the Terminal application and type a line of text.
- They will copy commands from the page. They will not compose them from a
  syntax description.

Assumptions the pages must not make:

- That they know what a "flag", "argument", "stdout", "JSON", "CSV", "path",
  or "environment variable" is. Each is either avoided or explained in place,
  in one sentence, the first time it appears on a page.
- That they read English. The Croatian edition is the primary one for this
  reader.

### 1.2 The installer

An IT colleague, a system administrator, or a technically comfortable friend.
They are asked by the professional user to "set this up for me". They are
comfortable with Python, virtual environments, and running a local server.

The installer reads one page: `install.md`. That page is written for them, in
ordinary technical language, and ends with a hand-over checklist: what to leave
running, setting `CADASTRAL_LANG` to the user's language so they never need
`--lang`, what to show the user, and the one command the user can type to
confirm everything works (`cadastral info`).

The professional user's `start-here.md` opens with a short paragraph that
says, in effect: "Ask a technical colleague to follow the installation page.
When they are done, open Terminal and type `cadastral info`. If you see a table
and no red text, you are ready." Nothing more about installation appears on any
user-facing page.

This split is deliberate. Trying to make installation friendly for a
non-technical reader produces a long, fragile page that still fails at the
first Python version mismatch. Sending them to a helper produces a short page
that works.

## 2. Writing rules

The standard is the "for Dummies" register: friendly, concrete, one idea at a
time, and never condescending about the reader's own profession.

### 2.1 Language

- Second person, imperative: "Type the following line", not "The user should
  enter".
- One instruction per sentence. One task per numbered step.
- Lead every page and every section with what the reader gets, not with what
  the software does. "Find out who owns a parcel" rather than "Retrieve
  possession sheet data".
- Use the reader's own vocabulary first, then the tool's: "the land registry
  unit (zemljišnoknjižni uložak, what the tool calls an LR unit)". The
  glossary page maps every legal term to the command or option that produces
  it.
- Never use a technical term without a plain-language gloss on the same page.
  A short "Words used on this page" box at the top is acceptable when three or
  more such terms are unavoidable.
- No abbreviations in prose except the ones the reader already uses daily
  (k.o., k.č., ZK). Expand every other one on first use.
- English words with a legal meaning follow `specs/terminology.md` too: the
  cadastre has possessors, never owners; the building flag is "building
  permitted", never "building right"; a plomba marks a "request for
  registration".
- Numbers, identifiers and command lines go in code blocks or tables, not in
  running text.
- Show what appears on screen after every command that produces output. A
  reader who cannot compare their screen to the page does not know whether it
  worked.
- Say what to do when it goes wrong, on the same page, in a "If something
  goes wrong" section. Quote the actual message the tool prints.
- The demonstration disclaimer required by `CLAUDE.md` appears once, at the
  top of every page, in the generated banner. Do not repeat it in the body.

### 2.2 Croatian

The Croatian edition documents the Croatian CLI, not the English page. A
Croatian reader runs the tool with Croatian output (the default language), so
every label, column heading, prompt and error message they see comes from
`po/hr.po`. The Croatian page must quote those strings, never a translation of
the English page's wording. The two editions are therefore equivalent in
meaning and structure, but not word for word.

- The reference for every piece of screen text is the localized CLI itself.
  Before translating a paragraph that names something on screen, run the
  command with `--lang hr` against the mock server, or look the string up in
  `po/hr.po`, and quote what the tool prints. Example: the English page says
  the reader will find the **Owners** table; the Croatian page names the table
  as the Croatian CLI prints it, which may be **Vlasnici** or **Posjednici**
  depending on the command. Check, do not assume.
- Screen text quoted in prose is written in bold. That convention is what lets
  the gate verify that every quoted label exists in the catalog of that
  edition's language (section 6, check 8).
- Where the English paragraph explains an English word the Croatian reader
  does not need explained (or the reverse), the Croatian paragraph says what
  the Croatian reader needs instead. It may be shorter, longer, or ordered
  differently. It must still be exactly one paragraph, because the paragraph
  is the unit of alignment between the editions.
- Formal address, second person plural: "Upišite", "Pokrenite", "Vidjet ćete".
- Legal and cadastral terms follow `specs/terminology.md`: posjedovnica,
  vlastovnica, teretovnica for the sheets; prijedlog za upis, never
  "prijava"; posjednik for anyone in the cadastre, vlasnik only for sheet B;
  način uporabe, never "namjena"; dopušteno građenje, never "pravo
  građenja". Its "Do not write" table is enforced by
  `cli/tests/test_terminology.py`. When a reviewer rejects a term, add a row
  there first, then fix the text, so the mistake cannot come back.
- Where the CLI already prints a term (through `po/hr.po`), use the CLI's
  term even if a synonym reads better. If the CLI's term is wrong, fix
  `po/hr.po` and the terminology table, never only the docs.
- Stock phrases have fixed translations (terminology.md section 3): probni
  poslužitelj and probni podaci, "Ako nešto ne uspije" for the trouble
  heading, kopirajte for copying a command, "uvid u" for consulting the
  register in titles.
- File names, JSON keys and format names (`json`, `csv`, `wkt`) stay in
  English. Command and option names have Croatian spellings (previous
  bullet); the generated option tables and `--help` captures show them
  because the Croatian CLI prints them.
- Examples do not carry `--lang`. The installer sets `CADASTRAL_LANG` for the
  user's preferred language (section 1.2), and the build captures output for
  each edition with the matching language explicitly.
- Command lines on Croatian pages use the Croatian program name and
  spellings: `uz čestica 103/2 -ko SAVAR --posjednici`. The writer never
  translates them by hand. The build rewrites every command line in a shell
  block or an output marker through the CLI's own alias table
  (`cadastral_cli.localized`, see `specs/terminology.md` section 4), and the
  output is captured by running the Croatian line. Only prose mentions of a
  command or option in a code span are translated in `po/docs-hr.po`, using
  the same spellings.

### 2.3 Things that are forbidden

- Describing an option, default, or behaviour from memory. Run
  `cadastral <command> --help` and, where output is shown, run the command
  against the mock server. The gate (section 6) rejects examples that do not
  parse, but it cannot detect a plausible lie about what an option does.
- Editing anything inside a generated region or anything under `docs/hr/`.
  Both are overwritten by the next build.
- Reflowing or rewording English paragraphs that did not need to change. Each
  paragraph is a translation unit; touching it invalidates its Croatian
  translation and creates work for no benefit.
- Emojis, ASCII art, and decorative formatting. Bold is reserved for text the
  reader must find on screen (section 2.2); list items and lead-ins are plain.

## 3. Layout

```text
docs/
  en/cli/
    start-here.md            Quick tutorial for the professional user. Authored.
    reference.md             Complete reference index. Generated.
    install.md               For the installer. Authored, with a generated
                             output block for the verification step.
    glossary.md              Legal term -> command/option. Authored.
    errors.md                What each message means. Generated table plus
                             authored advice.
    commands/
      search.md              One page per command, 14 pages. Authored with
      get-parcel.md          generated regions.
      get-lr-unit.md
      ...
      cache-clear.md         Subcommands use the group name as prefix.
    examples/                Input files the pages link to and that examples
                             run against: parcels.csv, parcels.json,
                             lr_units.csv, parcels-found.json. Copied into
                             the Croatian tree by the build.
  hr/cli/                    Same tree. Generated, never edited.
mock-server/data/geometry/
  334979.zip                 Synthetic boundary fixture so that geometry
                             commands run offline during the build.
po/
  docs.pot                   Extracted from docs/en/cli/**/*.md.
  docs-hr.po                 Croatian translations of the prose.
scripts/
  build_docs.py              The build (section 5).
cli/tests/
  test_docs_coverage.py      The gate (section 6).
specs/
  documentation-guide.md     This document.
```

File names follow `specs/naming-conventions.md`: kebab-case, one page per
command, named exactly as the command is typed (with the group prefix for
subcommands, so `cache clear` becomes `cache-clear.md`).

## 4. The command page template

Every file under `commands/` has this shape. Headings are fixed so the gate
can check them and so the Croatian edition mirrors them one to one. Generated
regions are delimited by HTML comments and are replaced wholesale on every
build; the text between them is never edited by hand.

```markdown
<!-- BEGIN GENERATED: banner -->
(language switcher, demo disclaimer, "last generated from version x.y.z")
<!-- END GENERATED: banner -->

# Find out who owns a parcel

One or two sentences: what question this command answers, in the reader's
words.

## When you would use this

- Two to four bullets, each a concrete situation from legal practice.

## Before you start

What the reader needs in hand (for example a parcel number and the name of
the cadastral municipality) and where they usually find it.

## Step by step

1. Open Terminal.
2. Type the following line and press Enter:

   ```bash
   cadastral get-parcel 103/2 -m SAVAR --show-owners
   ```

3. You will see something like this:

   <!-- BEGIN GENERATED: output get-parcel 103/2 -m SAVAR --show-owners -->
   ```text
   (captured from the mock server at build time)
   ```
   <!-- END GENERATED: output -->

4. How to read what is on the screen, line by line if needed.

## Choices you can make

Plain-language explanation of the options that matter to this reader, with
one example each. Not every option needs a paragraph; the full list follows.

<!-- BEGIN GENERATED: options -->
| Type this | What it does | If you leave it out |
|-----------|--------------|---------------------|
(one row per option, text taken from the tool's own help catalog)
<!-- END GENERATED: options -->

## If something goes wrong

Each subsection quotes a message the tool prints and says what to do.

## Related pages

- Links to the two or three commands the reader is likely to need next.

<details>
<summary>Technical details</summary>

<!-- BEGIN GENERATED: synopsis -->
(full usage line, argument list, exit codes)
<!-- END GENERATED: synopsis -->

</details>
```

The tutorial `start-here.md` is organised by task, not by command: "Check who
owns a parcel", "Check for mortgages and other charges", "Look up many parcels
at once", "Save the result for a file or a colleague", "See the parcel on a
map". Each task is three to six steps and ends with a pointer to the command
page for the details.

## 5. Two layers: generated and authored

The rule that keeps the documentation honest: **anything the code knows, the
code writes.** A human writes only what the code cannot know.

| Content | Source | Written by |
|---------|--------|------------|
| Command list, one-line descriptions, reference index | `click` command tree | Generated |
| Option names, short flags, types, choices, defaults, required-ness | `click` parameters | Generated |
| Option help text, command descriptions, in both languages | gettext catalog `po/hr.po` via `set_language()` | Generated |
| Error message labels (`errors.md` table) | `ErrorType` and `error_type_label()` | Generated |
| Screen output under "You will see" | Command run against the mock server at build time | Generated |
| Contents of an example input file (`file` region) | `docs/en/cli/examples/`, column names and keys localized by the CLI for the Croatian tree | Generated |
| Demo disclaimer, language switcher, version stamp | Build script | Generated |
| Purpose, situations, prerequisites, step narrative, tips, troubleshooting advice, related pages | The writer | Authored (English) |
| Croatian edition of authored text | `po/docs-hr.po`, written against the Croatian CLI as the reference | Authored (localization, not literal translation) |

Because the option help text is pulled from the same catalog the terminal
uses, the documentation can never describe an option differently from what
the reader sees when they type `--help`, in either language. This is the main
reason the generator reads the catalog rather than having the docs translated
separately.

### 5.1 The build

`python scripts/build_docs.py` performs, in order:

1. Import the CLI under `--lang en`, walk `cli.commands`, and rewrite every
   generated region in `docs/en/cli/`. Options tables, synopses, the
   reference index, the errors table, and the banners.
2. Start the mock server on a free port, run every command listed in an
   `output` region, and paste the captured text into that region. Output is
   captured with `--lang en` for the English tree and `--lang hr` for the
   Croatian tree. Every command starts from a fresh home directory seeded
   with the geometry fixture and the example files, at a terminal width of
   100 columns, so the text does not depend on the machine or on the order
   of the pages. The server address is rewritten to `http://localhost:8000`,
   the home directory to `~`, and transient progress lines are dropped.
3. Extract every authored paragraph from `docs/en/cli/` into `po/docs.pot`
   and merge into `po/docs-hr.po`. The extractor is a small block-level
   splitter in `build_docs.py` built on `polib` (pure Python): headings, list
   items, paragraphs, blockquotes, table rows and `<summary>` lines are the
   units; code fences, HTML and generated regions are opaque. A changed
   paragraph is matched to its closest old translation and marked fuzzy.
   (`mdpo` was the first choice but it needs the `md4c` C library.)
4. Render `docs/hr/cli/` by applying `po/docs-hr.po` to the English tree, then
   rerun step 1 and step 2 under `--lang hr` on the result.
5. Print the count of untranslated and fuzzy entries in `po/docs-hr.po`.

Step 2 can be skipped with `--no-output` when the mock server cannot run; the
gate will then report the output regions as stale.

### 5.2 Translation workflow

Prose translation reuses the mechanism that already governs the CLI strings
(see `specs/i18n-guide.md`), with the paragraph as the unit instead of the
string.

1. After changing English pages, run the build. Changed paragraphs appear in
   `po/docs-hr.po` as fuzzy, new paragraphs as untranslated.
2. Localize exactly those entries. Do not touch entries that are not fuzzy.
   For each entry that quotes screen text, run the command with `--lang hr`
   (or search `po/hr.po`) and quote the Croatian string the tool prints. See
   section 2.2.
3. Run the build again. `docs/hr/cli/` is regenerated.
4. Run the gate.

`po/hr.po` is the authority for anything the tool prints; `po/docs-hr.po` is
the memory for everything else. Before translating a term, search both, in
that order, and reuse what is there.

The build and the gate always set `CADASTRAL_API_BASE_URL` to the mock server
they start, so a `.env` file pointing elsewhere is never used. GIS downloads
go through the same base URL (`<base>/atom/ko-<code>.zip`), which the mock
server serves from `mock-server/data/geometry/`.

## 6. The gate

`cd cli && pytest tests/test_docs_coverage.py` fails when any of the following
is true. It runs in CI on every push, next to the existing i18n coverage gate.

1. A command in `cli.commands` (recursively, including group subcommands) has
   no page under `docs/en/cli/commands/`, or a page exists for a command that
   no longer does.
2. A generated region differs from what the build would produce now. This
   catches a new option, a changed default, a changed help text, or a changed
   version, in either language.
3. A fenced `bash` block contains a `cadastral ...` line that the real click
   parser rejects: unknown command, unknown option, missing required option,
   invalid choice. Every example on every page is parsed, in both editions.
4. `po/docs-hr.po` has an untranslated or fuzzy entry.
5. `docs/hr/cli/` differs from what applying `po/docs-hr.po` would produce
   now.
6. A relative link on any page points to a file or heading that does not
   exist.
7. A command page is missing one of the fixed headings from section 4, or its
   Croatian counterpart has a different number of headings, paragraphs, or
   code blocks.
8. Bold text in prose (the convention for quoted screen text, section 2.2)
   does not occur in the CLI catalog of that edition's language: as a msgid
   for the English pages, as a msgstr in `po/hr.po` for the Croatian pages.
   This catches a Croatian page that translates a label literally instead of
   quoting what the Croatian CLI prints, and an English page that quotes a
   label the tool no longer prints.
9. A term from the "Do not write" table of `specs/terminology.md` appears in
   either edition or in `po/hr.po` (`cli/tests/test_terminology.py`).

Check 3 is the one that catches the most mistakes. It is also why examples
must be real command lines in `bash` blocks and never paraphrased in prose.
Examples are parsed with `docs/en/cli/examples/` as the working directory, so
a file an example names must exist there.

Check 8 accepts a bold label when it equals a catalog string (placeholders
such as `{parcel}` match anything, a trailing colon is ignored, case is
ignored) or when it occurs verbatim in an `output` region on the same page.
Headings are not checked, so a page title may use words the CLI never prints.

The gate starts the mock server and captures every documented command, which
takes about half a minute. It needs the mock server dependencies installed
(`pip install -r mock-server/requirements.txt`).

## 7. Procedure when the CLI changes

The person or LLM who changes a command owns the documentation change. It is
part of the same commit or pull request, not a follow-up.

### 7.1 A new command

1. Write the code, help text and option help through `_()` as
   `specs/i18n-guide.md` requires, and bring `po/hr.po` up to date.
2. Run `python scripts/build_docs.py`. It creates
   `docs/en/cli/commands/<name>.md` from the template with generated regions
   filled and authored sections containing `TODO` placeholders. The gate fails
   on `TODO`.
3. Write the authored sections following section 2 and section 4. Run the
   command against the mock server yourself before describing it.
4. Add the command to `start-here.md` only if it belongs to one of the reader's
   tasks. Add its legal terms to `glossary.md`.
5. Run the build, translate the fuzzy and untranslated entries in
   `po/docs-hr.po`, run the build again, run the gate.

### 7.2 A changed command

Any of: option added, removed, or renamed; default changed; output format
changed; behaviour changed.

1. Run the build. Generated regions update themselves.
2. Read the page as the professional user. If the change affects what they
   would type or what they would see, update the authored sections. If the
   change added a choice worth explaining, add a paragraph under "Choices you
   can make". Do not rewrite paragraphs that are still true.
3. Run the build, translate what became fuzzy, run the build again, run the
   gate.

### 7.3 A removed command

1. Delete `docs/en/cli/commands/<name>.md`.
2. Search all pages for links to it and for its name in prose; update them.
3. Run the build. The Croatian page disappears, the obsolete entries in
   `po/docs-hr.po` are marked `#~`.
4. Run the gate.

### 7.4 Definition of done

- `cd cli && pytest tests/test_i18n_coverage.py tests/test_terminology.py tests/test_docs_coverage.py`
  passes.
- Every new or changed example was actually run against the mock server.
- No `TODO` remains on any page.
- The page was read once top to bottom in the voice of the professional user,
  and once in Croatian.

## 8. Notes for LLM writers

The rules above apply unchanged. These points address failure modes that are
specific to a model writing documentation.

- Do not describe a flag you have not seen in `--help` output during the
  current session. If the help output and this guide disagree, the help
  output is right and this guide needs a fix.
- Do not generate the Croatian tree yourself. Translate entries in
  `po/docs-hr.po` and let the build render the pages. A hand-written
  `docs/hr/` file will be overwritten and the gate will fail in the meantime.
- Translate only fuzzy and untranslated entries. Rewriting correct
  translations changes wording across pages and wastes review time.
- Never translate a screen label from the English page. Look it up in
  `po/hr.po` or run the command with `--lang hr` and quote the result. A
  fluent literal translation that the tool never prints is the most likely
  mistake a model makes here, and it sends the reader looking for text that
  is not on their screen.
- Keep English paragraphs stable. When a fact changes, change the sentence
  that states it, not the paragraph around it.
- When unsure whether a reader needs an explanation, they do. When unsure
  whether a paragraph is needed at all, it is not.
- Run the gate before reporting completion and paste its result.

## 9. Status

Implementation status (September 2026):

- [x] `scripts/build_docs.py` (generated regions, output capture, extraction
      and rendering)
- [x] `cli/tests/test_docs_coverage.py`, nine checks
- [x] `cli/tests/test_terminology.py` and `specs/terminology.md` (rejected terms
      cannot come back)
- [x] `docs/en/cli/` pages for all 14 commands, authored
- [x] `install.md`, `start-here.md`, `glossary.md`, `errors.md`, `reference.md`
- [x] `po/docs-hr.po` fully translated, `docs/hr/cli/` rendered
- [x] CI workflow `.github/workflows/docs-gate.yml` running both gates
- [x] `docs/cli-reference.md` replaced by a pointer to the new pages
- [x] `polib` added to the CLI dev dependencies
- [x] Croatian command, option, argument and choice spellings
      (`cli/src/cadastral_cli/localized.py`, program name `uz`); the build
      rewrites documented command lines mechanically
- [x] Geometry fixture `mock-server/data/geometry/334979.zip`; GIS downloads
      follow the configured base URL instead of a hard-coded production URL

Known limitations worth a follow-up:

- `get-lr-unit` with a unit number that does not exist reports a raw
  connection error ending in `404 Not Found` rather than the
  "Land registry unit not found" label. The page documents what the tool
  prints; the CLI is the thing to fix.
- `cache list` and `cache info` count from the seeded fixture, so the sizes on
  those pages are tiny. They are still real output.

Update the list as items land.
