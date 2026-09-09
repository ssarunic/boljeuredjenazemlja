#!/usr/bin/env python3
"""Turn a raw API capture into redacted test fixtures and mock-server data.

Implements section 9 of specs/api-coverage-specification.md. The raw capture
(produced by ``scripts/capture_api_sample.py``) contains personal data and is
never committed; this script derives from it

- the SDK test fixtures under ``api/src/cadastral_api/tests/fixtures/``, one
  file per endpoint shape, named ``<endpoint>_<case>.json``;
- the mock-server data sets under ``mock-server/data/``.

Redaction rules (every key, type, null and empty list is kept exactly as
received; ids, parcel numbers, areas, cultures and toponyms are unchanged):

- every person record under ``possessors`` and ``lrOwners`` (sub-shares and
  sheet C beneficiaries included) gets a deterministic placeholder: the same
  real name always maps to the same number, so co-ownership across shares
  stays recognisable ("Posjednik 12" in the cadastre, "Vlasnik 12" in the land
  register, "Adresa 12", a synthetic 11-digit OIB with a valid check digit);
- entry descriptions and condominium (apartment) texts are scrubbed word by
  word: dates, diary and file numbers, amounts and legal vocabulary stay, every
  other capitalised word (personal names of owners, notaries, deceased
  persons, companies) becomes ``N.N.``; 11-digit numbers become synthetic OIBs.

The scrub is deliberately conservative: a capitalised word survives only if it
is in the legal/institution allowlist below, also occurs in lower case
somewhere in the capture (ordinary Croatian prose), is a code with digits or a
trailing hyphen ("Z-", "O-", "UPP-OS-"), or is at most two letters. Run with
``--report`` to review what was kept and what was replaced before writing.

Usage:
    python scripts/redact_capture.py RAW_DIR --report
    python scripts/redact_capture.py RAW_DIR --fixtures api/src/cadastral_api/tests/fixtures \\
        --mock mock-server/data
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURES = REPO / "api" / "src" / "cadastral_api" / "tests" / "fixtures"
DEFAULT_MOCK = REPO / "mock-server" / "data"

PLACEHOLDER = "N.N."
PERSON_KEYS = ("possessors", "lrOwners")
TEXT_KEYS = ("description",)
TEXT_LIST_KEYS = ("condominiums",)

# Words that may stay capitalised in entry texts: registry actions and rights,
# courts and offices, places, document words. Compared case-insensitively.
# Anything capitalised that is not here, not an ordinary word (seen in lower
# case elsewhere in the capture) and not a code is replaced.
ALLOWLIST = {
    # actions, rights, sheet vocabulary
    "zaprimljeno", "zapremljeno", "primljeno", "predano", "uknjižba", "predbilježba",
    "zabilježba", "brisanje", "prvenstveni", "red", "upisa", "upisom", "pravo", "pravu",
    "prava", "vlasništva", "vlasništvo", "vlasnici", "suvlasnički", "etažno", "etažnog",
    "založno", "založnog", "hipoteke", "služnost", "plodouživanja", "tražbina", "socijalne",
    "pomoći", "doživotno", "doživotnom", "dosmrtnom", "uzdržavanje", "uzdržavanju",
    "zk", "uloška", "ulošku", "preneseni", "prenijete", "posjedovnici", "a-posjedovnici",
    "međuvlasnički", "međusuvlasnički", "stan", "garažni", "boks", "označuje", "pr",
    # documents, procedure
    "poslovni", "broj", "brojem", "pod", "posl", "osl", "podp", "rbr", "potvrda", "odbijeni",
    "prijedlog", "smrtni", "list", "sudski", "sudskom", "povjerenik", "povjereniku",
    "ostavinskom", "postupku", "naknadno", "pronađenoj", "imovini", "doneseno", "dodatak",
    "aneks", "sporazum", "sporazumom", "sporazumu", "zaključen", "potvrđen", "ovjerena",
    "ovjerene", "ovjerenogkod", "sastavljenog", "osobna", "nekretninama", "nekretnini",
    "dopuni", "primitku", "namirenju", "zasnivanju", "zasnivanjem", "potrošačkom",
    "osnivanju", "zaprimljena", "obavijest", "ovršivost", "stambenom", "kupoprodajnog",
    "kupoprodajne", "kupoprodajni", "cijene", "cijelog", "podmirenju", "konačnom", "darovni",
    "tužbe", "tužba", "pokretanje", "prigovor", "žalba", "odluku", "elektroničkog",
    "podneska", "ovoga", "uvjerenje", "skica", "lica", "mjesta", "kulturno", "dobro",
    "uporabna", "javne", "bilježnice", "javnom", "javnoom", "bilježniku", "bilježnika",
    "vršitelju", "dužnosti", "neposrednu", "ovrhu", "zakona", "zzk-a", "eur-a", "oib",
    # institutions and places
    "općinskog", "općinskgo", "općinskim", "općinski", "općine", "sud", "suda", "sudu",
    "građanskog", "stalna", "služba", "republike", "republika", "hrvatske", "hrvatska",
    "ministarstvo", "uprave", "upravnog", "odjela", "odjel", "okoliša", "županije",
    "zadarske", "matičnog", "ureda", "ured", "skupštine", "referade", "gradonačelnika",
    "centra", "centar", "fonda", "europska", "europske", "veleposlanstvom", "veleposlanstvo",
    "zadru", "zadra", "zadar", "splitu", "splita", "split", "zagrebu", "zagreba", "zagreb",
    "novom", "novoj", "gradiški", "vinkovcima", "vukovaru", "rijeci", "šibeniku", "šibenika",
    "opatiji", "opatije", "madridu", "kaštel", "starom", "metkovića", "narone", "savar",
    "mali", "malog", "iž", "iža", "čiova", "okrug", "gornji", "sv", "vukovarska", "tolstojeva",
    "stepinčeva", "alojzija", "stepinca", "put",
    # currencies and misc codes
    "eur", "kn", "hrd", "rh", "nn", "pd", "up", "ur", "os", "upp", "ovr",
}

ROMAN_RE = re.compile(r"^[IVXLC]+$")
CODE_RE = re.compile(r"^[A-Z]{1,4}(-[A-Z]{1,4})+-?$")  # "UPP-OS-VK", "OS-O-"
WORD_RE = re.compile(r"[A-Za-zČĆŠĐŽčćšđž][A-Za-zČĆŠĐŽčćšđž'\-]*")
TAG_SPLIT_RE = re.compile(r"(<[^>]+>)")
OIB_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")
NAME_SHARE_RE = re.compile(r"^(?P<name>.*?)\s+(?P<share>za\s+\d+\s*/\s*\d+.*)$", re.IGNORECASE)


def synthetic_oib(index: int) -> str:
    """An 11-digit number with a valid ISO 7064 MOD 11,10 check digit (never a real OIB)."""
    body = f"{90_000_000_000 + index:010d}"[-10:]
    remainder = 10
    for digit in body:
        remainder = (remainder + int(digit)) % 10 or 10
        remainder = (remainder * 2) % 11
    check = (11 - remainder) % 10
    return body + str(check)


class Redactor:
    """Deterministic redaction state shared by one run over a whole capture."""

    def __init__(self, common_words: set[str]) -> None:
        self.common_words = common_words
        self.names: dict[str, int] = {}
        self.addresses: dict[str, int] = {}
        self.oibs: dict[str, int] = {}
        self.replaced_words: Counter[str] = Counter()
        self.kept_common: Counter[str] = Counter()
        self.kept_allowlisted: Counter[str] = Counter()

    # -- persons -------------------------------------------------------------

    @staticmethod
    def _key(value: str) -> str:
        return " ".join(value.split()).casefold()

    def _index(self, table: dict[str, int], value: str) -> int:
        key = self._key(value)
        if key not in table:
            table[key] = len(table) + 1
        return table[key]

    def person(self, record: dict[str, Any], role: str) -> dict[str, Any]:
        out = dict(record)
        name = record.get("name")
        if isinstance(name, str) and name.strip():
            share = NAME_SHARE_RE.match(name.strip())
            bare = share.group("name") if share else name
            placeholder = f"{role} {self._index(self.names, bare)}"
            out["name"] = f"{placeholder} {share.group('share')}" if share else placeholder
        address = record.get("address")
        if isinstance(address, str) and address.strip():
            out["address"] = f"Adresa {self._index(self.addresses, address)}"
        tax = record.get("taxNumber")
        if isinstance(tax, str) and tax.strip():
            out["taxNumber"] = synthetic_oib(self._index(self.oibs, tax))
        return out

    # -- free text -----------------------------------------------------------

    def _keep_word(self, word: str) -> bool:
        if word[0].islower():
            return True
        if len(word) <= 2 or ROMAN_RE.match(word):
            return True
        if any(ch.isdigit() for ch in word) or word.endswith("-") or CODE_RE.match(word):
            return True
        folded = word.casefold()
        if folded in ALLOWLIST:
            self.kept_allowlisted[word] += 1
            return True
        if folded in self.common_words:
            self.kept_common[word] += 1
            return True
        return False

    def _scrub_segment(self, text: str) -> str:
        out: list[str] = []
        last = 0
        pending = False  # a placeholder was just emitted; merge adjacent names
        for match in WORD_RE.finditer(text):
            word = match.group()
            between = text[last : match.start()]
            if self._keep_word(word):
                out.append(between)
                out.append(word)
                pending = False
            else:
                self.replaced_words[word] += 1
                if pending and between.strip() in ("", ",", "-", "."):
                    pass  # "Ime Prezime" -> one N.N.
                else:
                    out.append(between)
                    out.append(PLACEHOLDER)
                pending = True
            last = match.end()
        out.append(text[last:])
        scrubbed = "".join(out)
        return OIB_RE.sub(lambda m: synthetic_oib(self._index(self.oibs, m.group())), scrubbed)

    def text(self, value: str) -> str:
        """Scrub a description: HTML tags are kept, text between them is scrubbed."""
        parts = TAG_SPLIT_RE.split(value)
        return "".join(
            part if part.startswith("<") else self._scrub_segment(part) for part in parts
        )

    # -- tree walk -----------------------------------------------------------

    def walk(self, node: Any, role: str = "Vlasnik") -> Any:
        if isinstance(node, dict):
            out: dict[str, Any] = {}
            for key, value in node.items():
                if key in PERSON_KEYS and isinstance(value, list):
                    person_role = "Posjednik" if key == "possessors" else "Vlasnik"
                    out[key] = [
                        self.walk(self.person(item, person_role), person_role)
                        if isinstance(item, dict)
                        else item
                        for item in value
                    ]
                elif key in TEXT_KEYS and isinstance(value, str):
                    out[key] = self.text(value)
                elif key in TEXT_LIST_KEYS and isinstance(value, list):
                    out[key] = [self.text(v) if isinstance(v, str) else self.walk(v) for v in value]
                else:
                    out[key] = self.walk(value, role)
            return out
        if isinstance(node, list):
            return [self.walk(item, role) for item in node]
        return node


# ---------------------------------------------------------------------------
# Capture inventory
# ---------------------------------------------------------------------------


def classify(name: str) -> tuple[str, str] | None:
    """(kind, label) of a raw file, or None for files that are not captures.

    Accepts the names ``capture_api_sample.py`` writes and the older
    ``probe_*`` names of the first capture.
    """
    stem = name[:-5] if name.endswith(".json") else None
    if stem is None:
        return None
    fixed = {
        "offices": ("offices", ""),
        "probe_offices": ("offices", ""),
        "probe_possession-sheet-numbers": ("possession_sheets", "363"),
    }
    if stem in fixed:
        return fixed[stem]
    prefixes = [
        ("municipalities_", "municipalities"),
        ("possession_sheets_", "possession_sheets"),
        ("main_books_", "main_books"),
        ("probe_main-books_", "main_books"),
        ("books_of_dc_", "books_of_dc"),
        ("probe_books-of-dc_", "books_of_dc"),
        ("lrunit_hist_", "lrunit_hist"),
        ("probe_lrunit_condo_", "lrunit"),
        ("lrunit_", "lrunit"),
        ("parcelinfo_", "parcelinfo"),
        ("filestatus_", "filestatus"),
        ("search_", "search"),
        ("probe_", "search"),
    ]
    for prefix, kind in prefixes:
        if stem.startswith(prefix):
            return kind, stem[len(prefix) :]
    return None


def load_capture(raw_dir: Path) -> dict[str, dict[str, Any]]:
    capture: dict[str, dict[str, Any]] = {}
    for path in sorted(raw_dir.glob("*.json")):
        kind_label = classify(path.name)
        if kind_label is None:
            continue
        kind, label = kind_label
        capture.setdefault(kind, {})[label] = json.loads(path.read_text(encoding="utf-8"))
    return capture


def collect_texts(node: Any, out: list[str]) -> None:
    if isinstance(node, dict):
        for key, value in node.items():
            if key in TEXT_KEYS and isinstance(value, str):
                out.append(value)
            elif key in TEXT_LIST_KEYS and isinstance(value, list):
                out.extend(v for v in value if isinstance(v, str))
            else:
                collect_texts(value, out)
    elif isinstance(node, list):
        for item in node:
            collect_texts(item, out)


def common_words(capture: dict[str, dict[str, Any]]) -> set[str]:
    """Words that occur in lower case somewhere: ordinary prose, safe to keep."""
    texts: list[str] = []
    collect_texts(capture, texts)
    words: set[str] = set()
    for text in texts:
        for word in WORD_RE.findall(TAG_SPLIT_RE.sub(" ", text)):
            if word[0].islower():
                words.add(word.casefold())
    return words


# ---------------------------------------------------------------------------
# Output selection
# ---------------------------------------------------------------------------


def unit_payload(data: Any) -> dict[str, Any]:
    return data[0] if isinstance(data, list) else data


def parcel_number_key(number: str) -> tuple[int, int, str]:
    bare = number.lstrip("*")
    main, _, sub = bare.partition("/")
    try:
        return int(main), int(sub or 0), number
    except ValueError:
        return sys.maxsize, 0, number


def has_share_entry(unit: dict[str, Any]) -> bool:
    for share in unit["ownershipSheetB"].get("lrUnitShares") or []:
        for item in share.get("subSharesAndEntries") or []:
            if "lrEntryId" in item:
                return True
    return False


def has_missing_owners(unit: dict[str, Any]) -> bool:
    """A share without the ``lrOwners`` key (the server omits it, or sends null)."""
    shares = unit["ownershipSheetB"].get("lrUnitShares") or []
    return any("lrOwners" not in share or share["lrOwners"] is None for share in shares)


def is_ownership_unit(unit: dict[str, Any]) -> bool:
    return unit["lrUnitTypeId"] == 1


def has_entries(unit: dict[str, Any], sheet: str) -> bool:
    return bool(unit[sheet].get("lrEntries"))


def has_groups(unit: dict[str, Any]) -> bool:
    return bool(unit["encumbranceSheetC"].get("lrEntryGroups"))


def size_of(data: Any) -> int:
    return len(json.dumps(data, ensure_ascii=False))


def pick(units: dict[str, Any], predicate: Any) -> tuple[str, Any] | None:
    """The smallest unit satisfying ``predicate`` (deterministic)."""
    candidates = [
        (size_of(u), label, u) for label, u in units.items() if predicate(unit_payload(u))
    ]
    if not candidates:
        return None
    _, label, unit = min(candidates, key=lambda c: (c[0], c[1]))
    return label, unit


def select_fixtures(capture: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Fixture file name -> raw payload, one per endpoint shape of the spec."""
    out: dict[str, Any] = {}
    if capture.get("offices"):
        out["offices.json"] = next(iter(capture["offices"].values()))
    for label, data in capture.get("municipalities", {}).items():
        out[f"municipalities_{label.lower()}.json"] = data
    searches = capture.get("search", {})
    for label, name in (("1072_1", "prefix"), ("star35_1", "building"), ("35_1", "bare_building")):
        if label in searches:
            out[f"parcel_search_{name}.json"] = searches[label]
    if capture.get("possession_sheets"):
        out["possession_sheet_search.json"] = next(iter(capture["possession_sheets"].values()))
    for label, data in capture.get("main_books", {}).items():
        out[f"main_books_{label.lower()}.json"] = data
    for label, data in capture.get("books_of_dc", {}).items():
        out[f"books_of_dc_{label.lower()}.json"] = data

    parcels = capture.get("parcelinfo", {})
    by_size = sorted(parcels.items(), key=lambda kv: (size_of(kv[1]), kv[0]))
    direct = next((p for _, p in by_size if "lrUnit" in p), None)
    linked = parcels.get("1122_1") or next(
        (p for _, p in by_size if p.get("lrUnitsFromParcelLinks")), None
    )
    building = next((p for _, p in by_size if str(p.get("parcelNumber", "")).startswith("*")), None)
    for name, parcel in (("direct", direct), ("linked", linked), ("building", building)):
        if parcel is not None:
            out[f"parcel_info_{name}.json"] = parcel

    units = capture.get("lrunit", {})
    cases = [
        ("lrparcels", lambda u: "lrParcels" in u["possessionSheetA1"] and is_ownership_unit(u)),
        ("cadparcels", lambda u: "cadParcels" in u["possessionSheetA1"]),
        ("share_entries", lambda u: has_share_entry(u) and is_ownership_unit(u)),
        ("missing_owners", lambda u: has_missing_owners(u) and is_ownership_unit(u)),
        ("sheet_b_entries", lambda u: has_entries(u, "ownershipSheetB") and is_ownership_unit(u)),
        (
            "sheet_a2_entries",
            lambda u: has_entries(u, "possessionSheetA2") and is_ownership_unit(u),
        ),
        ("encumbrances", lambda u: has_groups(u) and is_ownership_unit(u)),
        ("condominium", lambda u: u["lrUnitTypeId"] == 3),
    ]
    if "21277_449" in units:  # the unit the existing tests are written against
        out["lr_unit_lrparcels.json"] = units["21277_449"]
        cases = cases[1:]
    for name, predicate in cases:
        picked = pick(units, predicate)
        if picked is not None:
            out[f"lr_unit_{name}.json"] = picked[1]
    for label, data in capture.get("lrunit_hist", {}).items():
        out["lr_unit_historical_overview.json"] = data
        break
    for label, data in capture.get("filestatus", {}).items():
        state = "pending" if "executionDate" not in data else "resolved"
        out[f"file_status_{state}.json"] = data
    return out


def merge_records(existing: list[dict[str, Any]], new: list[dict[str, Any]], key: str) -> list:
    """Existing records not superseded (same ``key``) plus the new ones."""
    new_keys = {str(record.get(key)) for record in new}
    kept = [record for record in existing if str(record.get(key)) not in new_keys]
    return kept + new


def load_existing(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_mock(capture: dict[str, dict[str, Any]], redactor: Redactor, mock_dir: Path) -> list[str]:
    written: list[str] = []

    def out(rel: str, data: Any) -> None:
        write_json(mock_dir / rel, data)
        written.append(rel)

    if capture.get("offices"):
        # The offices list is complete and public: it replaces any hand-made list.
        out("offices.json", next(iter(capture["offices"].values())))
    municipalities = [m for data in capture.get("municipalities", {}).values() for m in data]
    if municipalities:
        path = mock_dir / "municipalities.json"
        out("municipalities.json", merge_records(load_existing(path), municipalities, "key1"))
    for kind, filename in (("main_books", "main-books.json"), ("books_of_dc", "books-of-dc.json")):
        records = [r for data in capture.get(kind, {}).values() for r in data]
        if records:
            out(filename, merge_records(load_existing(mock_dir / filename), records, "key1"))

    by_municipality: dict[str, list[dict[str, Any]]] = {}
    for parcel in capture.get("parcelinfo", {}).values():
        by_municipality.setdefault(str(parcel["cadMunicipalityRegNum"]), []).append(parcel)
    for reg_num, parcels in by_municipality.items():
        path = mock_dir / "parcels" / f"{reg_num}.json"
        redacted = [redactor.walk(p) for p in parcels]
        merged = merge_records(load_existing(path), redacted, "parcelNumber")
        merged.sort(key=lambda p: parcel_number_key(str(p["parcelNumber"])))
        out(f"parcels/{reg_num}.json", merged)

    for data in capture.get("lrunit", {}).values():
        unit = unit_payload(data)
        rel = f"lr-units/{unit['mainBookId']}-{unit['lrUnitNumber']}.json"
        out(rel, redactor.walk(unit))

    for data in capture.get("filestatus", {}).values():
        if not data:
            continue
        number = str(data["lrFileNumber"])  # "Z-12564/2026"
        code, _, rest = number.partition("-")
        order, _, year = rest.partition("/")
        institution = (data.get("institution") or {}).get("institutionId")
        out(f"lr-file-status/{institution}-{code}-{order}-{year}.json", redactor.walk(data))
    return written


def report(redactor: Redactor, fixtures: dict[str, Any]) -> None:
    print(f"fixtures: {len(fixtures)}")
    for name, data in fixtures.items():
        print(f"  {name:40s} {size_of(data):>9,d} bytes")
    print(f"\npersons: {len(redactor.names)} names, {len(redactor.addresses)} addresses, "
          f"{len(redactor.oibs)} OIBs")
    print(f"\nreplaced in texts ({len(redactor.replaced_words)} distinct words):")
    print("  " + ", ".join(w for w, _ in redactor.replaced_words.most_common()))
    print(f"\nkept because they also occur in lower case ({len(redactor.kept_common)} distinct):")
    print("  " + ", ".join(w for w, _ in redactor.kept_common.most_common()))
    print(f"\nkept by the allowlist ({len(redactor.kept_allowlisted)} distinct):")
    print("  " + ", ".join(w for w, _ in redactor.kept_allowlisted.most_common()))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("raw_dir", type=Path, help="directory with the raw capture (*.json)")
    parser.add_argument(
        "--fixtures", type=Path, help=f"write fixtures here (default {DEFAULT_FIXTURES})"
    )
    parser.add_argument("--mock", type=Path, help=f"write mock data here (default {DEFAULT_MOCK})")
    parser.add_argument("--report", action="store_true", help="print what would be kept/replaced")
    parser.add_argument(
        "--write", action="store_true", help="write the fixtures and mock data (default paths)"
    )
    args = parser.parse_args(argv)

    capture = load_capture(args.raw_dir)
    if not capture:
        print(f"no capture files recognised in {args.raw_dir}", file=sys.stderr)
        return 1
    redactor = Redactor(common_words(capture))
    fixtures = select_fixtures(capture)
    redacted_fixtures = {name: redactor.walk(data) for name, data in fixtures.items()}

    fixtures_dir = args.fixtures or (DEFAULT_FIXTURES if args.write else None)
    mock_dir = args.mock or (DEFAULT_MOCK if args.write else None)
    if fixtures_dir is not None:
        for name, data in redacted_fixtures.items():
            write_json(fixtures_dir / name, data)
        print(f"wrote {len(redacted_fixtures)} fixture(s) to {fixtures_dir}")
    if mock_dir is not None:
        written = write_mock(capture, redactor, mock_dir)
        print(f"wrote {len(written)} mock data file(s) to {mock_dir}")
    if args.report or (fixtures_dir is None and mock_dir is None):
        report(redactor, redacted_fixtures)
    return 0


if __name__ == "__main__":
    sys.exit(main())
