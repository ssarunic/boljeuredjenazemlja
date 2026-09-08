# Terminology

The vocabulary the CLI and its documentation must use for Croatian cadastre
and land registry concepts. It exists because a wrong word in this domain is
not a style problem: a notary who reads "vlasnici" above a cadastre possession
sheet, or "prijava" where the law says "prijedlog", stops trusting the tool.

The rules apply to `po/hr.po` (what the CLI prints), `po/docs-hr.po` and
`docs/hr/cli/` (the Croatian documentation), and to the English source where
an English term carries a legal meaning. `cli/tests/test_terminology.py`
enforces the "Do not write" table below on every push; the i18n and
documentation guides point here.

## 1. Sources of authority

1. Zakon o zemljišnim knjigama (Land Registry Act) and Zakon o vlasništvu i
   drugim stvarnim pravima (Ownership Act) for land registry terms.
2. Zakon o državnoj izmjeri i katastru nekretnina (Survey and Cadastre Act)
   for cadastre terms.
3. The wording printed on an official zemljišnoknjižni izvadak and on a
   posjedovni list. When the statute and the printed extract differ, use the
   printed extract, because that is what the reader compares against.

## 2. Concepts

| Concept (English, as in the code) | Croatian to use | Notes |
|---|---|---|
| Parcel | katastarska čestica, k.č. | "čestica" alone is fine after first use. |
| Cadastral municipality | katastarska općina, k.o. | Its identifier is the **matični broj** (MBKO). The CLI prints it under the label **Šifra**; prose says "matični broj (na zaslonu: Šifra)". |
| Municipality registration number | matični broj katastarske općine | Not "registarski broj". |
| Possession sheet | posjedovni list | A cadastre record. Never proof of ownership. |
| Possessor | posjednik | Everyone listed in the cadastre. The cadastre never has "vlasnici"; only the land registry does. |
| Owner | vlasnik | Only for persons in sheet B of the land registry. |
| Co-ownership share | suvlasnički udio | Written as a fraction. |
| Land registry unit | zemljišnoknjižni uložak, ZK uložak | Kept by the zemljišnoknjižni odjel of the općinski sud. |
| Main book | glavna knjiga | The tool's "main book ID" is "identifikator glavne knjige (main book ID)". |
| Sheet A | posjedovnica (list A) | Lists the parcels of the unit. |
| Sheet B | vlastovnica (list B) | Owners and shares. |
| Sheet C | teretovnica (list C) | Založna prava (hipoteke), služnosti, stvarni tereti, zabilježbe. |
| Encumbrance | teret | Plural "tereti". "Hipoteka" is acceptable alongside "založno pravo". |
| Pending entry | plomba | A mark that a prijedlog za upis has been received and not yet decided. |
| Request (for registration) | prijedlog za upis, prijedlog | The party files a prijedlog; the court decides by rješenje. |
| Diary, file number | dnevnik, poslovni broj Z (Z-broj) | |
| Condominium ownership | etažno vlasništvo, vlasništvo posebnog dijela nekretnine | A flat or business premises as a special part, tied to a co-ownership share. |
| Land use (cadastre culture) | način uporabe zemljišta, kultura | "Namjena" is a spatial planning term and is wrong here. |
| Building permitted (`hasBuildingRight`) | dopušteno građenje | Means "building is allowed". Never "pravo građenja", which is a distinct real right under the Ownership Act. |
| Cadastral office | područni ured za katastar | |
| OIB | osobni identifikacijski broj fizičke ili pravne osobe | |
| Parcel boundary | granica čestice | Coordinates in HTRS96/TM (EPSG:3765). |
| Extract | izvadak (zemljišnoknjižni izvadak, izvadak iz posjedovnog lista) | |
| To consult the register | uvid u zemljišnu knjigu, uvid u uložak | Use "uvid", not "čitanje", in titles. |

## 3. Register (documentation only)

- Formal address, second person plural: Upišite, Pokrenite, Vidjet ćete.
- The test server and its data are **probni poslužitelj** and **probni podaci**.
- The "If something goes wrong" heading is **Ako nešto ne uspije**.
- Copying a command is **kopirajte**, not "prepišite".
- A folder is **mapa**; the terminal application is **Terminal**; the
  tool's stored GIS data is **predmemorija**, because the CLI prints that word.

## 4. Do not write

`cli/tests/test_terminology.py` reads this table. The first column is a
regular expression (Python syntax, `(?i)` for case-insensitive). "hr" rows
are checked against the Croatian strings of `po/hr.po`, all of
`po/docs-hr.po`, `docs/hr/cli/` and the Croatian text in
`scripts/build_docs.py`; "en" rows against the English strings of `po/hr.po`
and `docs/en/cli/`.

| Do not write | Write instead | Scope |
|---|---|---|
| `(?i)\bprijav\w*` | prijedlog (za upis), prijedlozi | hr |
| `VLASNIČKI LIST` | VLASTOVNICA | hr |
| `TERETNI LIST` | TERETOVNICA | hr |
| `POPIS ČESTICA \(LIST A\)` | POSJEDOVNICA (LIST A) | hr |
| `(?i)namjen[aeiou] zemljišta` | način uporabe zemljišta | hr |
| `(?i)pravo građenja` | dopušteno građenje | hr |
| `(?i)vježbovn\w*` | probni | hr |
| `(?i)pođe po zlu` | ne uspije | hr |
| `(?i)\bprepišite\b` | kopirajte | hr |
| `(?i)\bčitanje (zemljišnoknjižnog|uloška)` | uvid u | hr |
| `(?i)building right` | building permitted | en |
| `(?i)\bcadastre (owners?|ownership)\b` | possessor, possession sheet | en |

Add a row whenever a reviewer finds a wrong term, together with the fix.
