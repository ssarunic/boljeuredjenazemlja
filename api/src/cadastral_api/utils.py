"""Shared helpers for parsing and normalizing cadastral/land-registry data."""

import re
from datetime import date
from decimal import Decimal, InvalidOperation

_FRACTION_RE = re.compile(r"(\d+)\s*/\s*(\d+)")

# Land-registry file/diary number, e.g. "Z-12564/2026" -> code "Z", order 12564,
# year 2026. The code is a short alphabetic prefix (Z, Zs, ...); allows Croatian
# letters defensively even though codes are ASCII in practice.
_FILE_NUMBER_RE = re.compile(r"^\s*([A-Za-zČĆŠĐŽčćšđž]+)-(\d+)/(\d+)\s*$")


def parse_file_number(file_number: str | None) -> tuple[str, int, int] | None:
    """Split a land-registry file (plomba/spis) number into its components.

    The ``/lr/file-status`` endpoint does not accept the rendered number; it
    wants the parts separately (``lrFileCode``, ``lrFileOrderNumber``,
    ``lrFileYear``). This parses the rendered form into them:

        "Z-12564/2026"   -> ("Z", 12564, 2026)
        "Z-18444/2026"   -> ("Z", 18444, 2026)

    Returns ``(code, order_number, year)`` or ``None`` when the string is not a
    recognisable file number.
    """
    if not file_number:
        return None
    match = _FILE_NUMBER_RE.match(file_number)
    if not match:
        return None
    return match.group(1), int(match.group(2)), int(match.group(3))


# Building parcels (katastarska čestica zgrade) are stored by the API with a
# leading asterisk: "*35/1". Users write them in several ways; every form below
# normalises to the API spelling. "35/1.ZGR" / "35/1 ZGR" / "35/1zgr" (suffix) and
# "zgr. 35/1" / "ZGR 35/1" (prefix).
_ZGR_SUFFIX_RE = re.compile(r"^(?P<num>.+?)\s*\.?\s*zgr\.?\s*$", re.IGNORECASE)
_ZGR_PREFIX_RE = re.compile(r"^zgr\.?\s*(?P<num>\S+)\s*$", re.IGNORECASE)
_STAR_RE = re.compile(r"^\*\s*(?P<num>\S+)\s*$")

BUILDING_PARCEL_PREFIX = "*"


def normalize_parcel_number(text: str | None) -> str:
    """Map every user spelling of a parcel number to the API spelling.

    Building parcels: ``"35/1.ZGR"``, ``"35/1 ZGR"``, ``"35/1 zgr"``,
    ``"zgr. 35/1"`` and ``"* 35/1"`` all become ``"*35/1"``. Other numbers are
    returned stripped of surrounding whitespace and otherwise untouched.
    """
    if text is None:
        return ""
    value = text.strip()
    if not value:
        return value
    match = _STAR_RE.match(value) or _ZGR_PREFIX_RE.match(value) or _ZGR_SUFFIX_RE.match(value)
    if match:
        return BUILDING_PARCEL_PREFIX + match.group("num").strip()
    return value


def is_building_parcel_number(parcel_number: str | None) -> bool:
    """True for the API spelling of a building parcel (leading asterisk)."""
    return bool(parcel_number) and parcel_number.lstrip().startswith(BUILDING_PARCEL_PREFIX)


def display_parcel_number(parcel_number: str | None) -> str:
    """Croatian display form of a parcel number: ``"*35/1"`` renders as ``"zgr. 35/1"``.

    Land parcels are returned unchanged. The API spelling stays in
    ``parcel_number``; this is what the CLI prints next to it
    (see specs/terminology.md, "Building parcel").
    """
    if not parcel_number:
        return parcel_number or ""
    if is_building_parcel_number(parcel_number):
        return f"zgr. {parcel_number.lstrip().lstrip(BUILDING_PARCEL_PREFIX).strip()}"
    return parcel_number


def parse_fraction(text: str | None) -> tuple[int, int] | None:
    """Extract an ownership fraction (numerator, denominator) from free text.

    Land-registry shares carry the fraction inside a description string rather
    than in structured fields, e.g.:

        "1. Suvlasnički dio: 4/8"                          -> (4, 8)
        "1. Na suvlasnički dio: 1 (4/8)"                   -> (4, 8)
        "16. Suvlasnički dio: 61/4651 ETAŽNO VLASNIŠTVO"   -> (61, 4651)
        "22.3. Suvlasnički dio etaže: 1/2"                 -> (1, 2)
        "1/4"                                              -> (1, 4)

    The fraction is taken from the portion after the last colon (the share
    value), to avoid matching the leading order number. Returns None when no
    fraction is present or the denominator is zero.
    """
    if not text:
        return None
    candidate = text.rsplit(":", 1)[-1]
    match = _FRACTION_RE.search(candidate)
    if not match:
        return None
    numerator, denominator = int(match.group(1)), int(match.group(2))
    if denominator == 0:
        return None
    return numerator, denominator


def normalize_name(name: str) -> str:
    """Normalize a party name for display/matching consistency.

    Conservative: collapse internal whitespace and apply consistent
    title-casing so all-caps registry names (``"KOLAR RAJKA"``) and mixed-case
    names (``"Šarunić Augustin"``) render uniformly. The raw value is always
    preserved separately; this never edits the original.
    """
    if not name:
        return name
    return " ".join(name.split()).title()


_HTML_TAG = re.compile(r"<[^>]+>")

# Croatian phrases naming the right an encumbrance entry registers, most
# specific first. Values are RightType member values (kept as strings so this
# module stays free of model imports). "ploduživanj" covers a spelling the
# registry actually uses; "uporab"/"stanovanj" are the other personal servitudes.
_RIGHT_TYPE_PATTERNS: tuple[tuple[str, str], ...] = (
    ("mortgage", r"založn[oa]g?\s+prav|hipotek"),
    ("usufruct", r"plodo?uživanj|pravo\s+uživanja"),
    ("easement", r"služnost|pravo\s+uporabe|pravo\s+stanovanja"),
    ("preemption", r"prvokup"),
    ("prohibition", r"zabran[aeu]\s+(otuđenja|opterećenja|raspolaganja)"),
    ("lien", r"tražbin"),
    ("annotation", r"zabilježb"),
)


def strip_html(text: str | None) -> str:
    """Drop HTML tags, unescape ``&amp;``-style entities and collapse whitespace."""
    if not text:
        return ""
    import html

    return " ".join(html.unescape(_HTML_TAG.sub(" ", text)).split())


def parse_right_type(text: str | None) -> str | None:
    """Classify the right an encumbrance entry registers from its Croatian text.

    Returns a ``RightType`` value (``"usufruct"``, ``"mortgage"``, ...),
    ``"other"`` when the text names no known right, or ``None`` for empty text.
    HTML in ``text`` is stripped first, so the raw ``description`` can be passed.
    """
    plain = strip_html(text).lower()
    if not plain:
        return None
    for value, pattern in _RIGHT_TYPE_PATTERNS:
        if re.search(pattern, plain):
            return value
    return "other"


_CROATIAN_MONTHS = {
    "siječnja": 1, "veljače": 2, "ožujka": 3, "travnja": 4, "svibnja": 5, "lipnja": 6,
    "srpnja": 7, "kolovoza": 8, "rujna": 9, "listopada": 10, "studenog": 11,
    "studenoga": 11, "prosinca": 12,
}
_DATE_WORDS_RE = re.compile(
    r"\b(\d{1,2})\.\s*(" + "|".join(_CROATIAN_MONTHS) + r")\s+(\d{4})\b", re.IGNORECASE
)
_DATE_NUMERIC_RE = re.compile(r"\b(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})\b")
_DIARY_RE = re.compile(r"\b(Z)\s*[-–]?\s*(\d+)\s*/\s*(\d{2,4})\b", re.IGNORECASE)
# "Prvenstveni red upisa: Z-8920/2012" - the entry whose priority (rank) this
# entry inherits; rendered in bold in the server's HTML.
_PRIORITY_RE = re.compile(
    r"prvenstveni\s+red\s+upisa\s*:?\s*(Z)\s*[-–]?\s*(\d+)\s*/\s*(\d{2,4})", re.IGNORECASE
)
# Owners carried over when the unit was formed from another unit.
_TRANSFERRED_RE = re.compile(r"iz\s+zk\s+ulo[šs]ka\s+preneseni", re.IGNORECASE)
# Leading style span: <span class='lr-entry-black' > (often never closed).
_STYLE_CLASS_RE = re.compile(r"^\s*<span\s+class\s*=\s*['\"]([^'\"]+)['\"]", re.IGNORECASE)
# Croatian number format with an optional currency: "134.000,00 EUR", "43.000,00 KN".
_AMOUNT_RE = re.compile(r"^\s*(-?[\d.]+(?:,\d+)?)\s*([A-Za-z]{2,4})?\s*$")
# The statutory kinds of entry (Land Registry Act): uknjižba (unconditional
# registration), predbilježba (conditional registration), zabilježba (note);
# "upis" is the generic fallback when only "upisuje se" is said. A deletion
# ("briše se") is an effect on an earlier entry, not a kind of its own: it is
# reported through ``deletes_prior_entry`` and named as the action only when
# the text names no kind at all.
_ACTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("predbilježba", r"\bpredbilje[žz]"),
    ("zabilježba", r"\bzabilje[žz]"),
    ("uknjižba", r"\buknji[žz]"),
    ("upis", r"\bupisuje\s+se\b|\bupis\b"),
)
_DELETION_RE = re.compile(r"\bbri[sš]e\s+se\b|\bbrisanje\b|\bbri[sš]u\s+se\b")
_BASIS_RE = re.compile(
    r"\b(?:na\s+temelju|temeljem)\s+(.+?)"
    r"(?:,?\s+(?:uknji[žz]uje|upisuje|zabilje[žz]uje|predbilje[žz]uje|bri[sš]e|dopu[sš]ta|"
    r"odre[dđ]uje|provodi)\b|\s*$)",
    re.IGNORECASE | re.DOTALL,
)


def parse_lr_entry(text: str | None) -> dict[str, object]:
    """Pull the structured parts out of a land-registry entry's Croatian text.

    Returns a dict with ``action_type`` (an ``ActionType`` value or ``None``:
    ``uknjižba``, ``predbilježba``, ``zabilježba``, the generic ``upis``, or
    ``brisanje`` when a deletion names no kind), ``deletes_prior_entry`` (True
    when the text says "briše se" / "brisanje"),
    ``diary_number`` (normalised to ``"Z-487/49"``), ``entry_date`` (the first
    date in the text, i.e. the receipt date after "Stig."/"Pr."/"Zaprimljeno")
    and ``basis_document`` (the phrase after "Na temelju" up to the action verb,
    e.g. ``"rješenja o nasljeđivanju od 27. studenog 1967. pod brojem O 533/67,
    Općinskog suda u Zadru"``), ``priority_diary_number`` (the "Prvenstveni red
    upisa" reference, when the entry inherits the rank of an earlier one) and
    ``transferred_from_unit`` (True when the text says the owners were carried
    over from another unit, "IZ ZK ULOŠKA PRENESENI VLASNICI"). Missing parts
    are ``None``. HTML is stripped.
    """
    plain = strip_html(text)
    result: dict[str, object] = {
        "action_type": None,
        "diary_number": None,
        "entry_date": None,
        "basis_document": None,
        "priority_diary_number": None,
        "transferred_from_unit": False,
        "deletes_prior_entry": False,
    }
    if not plain:
        return result
    lower = plain.lower()

    priority = _PRIORITY_RE.search(plain)
    if priority:
        result["priority_diary_number"] = (
            f"{priority.group(1).upper()}-{int(priority.group(2))}/{priority.group(3)}"
        )
    result["transferred_from_unit"] = _TRANSFERRED_RE.search(plain) is not None

    for value, pattern in _ACTION_PATTERNS:
        if re.search(pattern, lower):
            result["action_type"] = value
            break
    if _DELETION_RE.search(lower):
        result["deletes_prior_entry"] = True
        if result["action_type"] is None:
            result["action_type"] = "brisanje"

    diary = _DIARY_RE.search(plain)
    if diary:
        result["diary_number"] = f"{diary.group(1).upper()}-{int(diary.group(2))}/{diary.group(3)}"

    result["entry_date"] = first_date(plain)

    basis = _BASIS_RE.search(plain)
    if basis:
        result["basis_document"] = basis.group(1).strip(" ,;")

    return result


def first_date(text: str) -> date | None:
    """First date in ``text``, written in words ("23. svibnja 1949.") or digits."""
    candidates: list[tuple[int, date]] = []
    for m in _DATE_WORDS_RE.finditer(text):
        try:
            month = _CROATIAN_MONTHS[m.group(2).lower()]
            candidates.append((m.start(), date(int(m.group(3)), month, int(m.group(1)))))
        except ValueError:
            continue
    for m in _DATE_NUMERIC_RE.finditer(text):
        try:
            candidates.append((m.start(), date(int(m.group(3)), int(m.group(2)), int(m.group(1)))))
        except ValueError:
            continue
    return min(candidates)[1] if candidates else None


_NAME_SHARE_RE = re.compile(
    r"\s+za\s+(\d+)\s*/\s*(\d+)(?:\s+(?:idealn\w*\s+)?dijel\w*)?\s*[.,]?\s*$", re.IGNORECASE
)


def split_name_share(name: str | None) -> tuple[str, tuple[int, int] | None]:
    """Split a trailing share off a party name.

    Sheet C beneficiaries sometimes carry the share of the right in the name
    itself: ``"ŠARUNIĆ AUGUSTIN POK. BOŽE ZA 2/6"``. Returns the bare name and
    the fraction, ``("ŠARUNIĆ AUGUSTIN POK. BOŽE", (2, 6))``; a name without
    such a suffix comes back unchanged with ``None``.
    """
    if not name:
        return name or "", None
    match = _NAME_SHARE_RE.search(name)
    if not match or int(match.group(2)) == 0:
        return name, None
    return name[: match.start()].rstrip(), (int(match.group(1)), int(match.group(2)))


def parse_style_class(description: str | None) -> str | None:
    """The CSS class of the span an entry description opens with, if any.

    Sheet A2 and sheet C entries start with ``<span class='lr-entry-black' >``
    (the tag is usually never closed). The class is recorded so that a future
    ``lr-entry-red`` or similar (expected for deleted entries in a historical
    overview) is not lost when the HTML is stripped.
    """
    if not description:
        return None
    match = _STYLE_CLASS_RE.match(description)
    return match.group(1) if match else None


def parse_amount(text: str | None) -> tuple[Decimal, str | None] | None:
    """Parse a Croatian-formatted monetary amount with an optional currency.

        "134.000,00 EUR"      -> (Decimal("134000.00"), "EUR")
        "43.000,00 KN"        -> (Decimal("43000.00"), "KN")
        "10.092.021,00 HRD"   -> (Decimal("10092021.00"), "HRD")
        "1500"                -> (Decimal("1500"), None)

    Dots are thousands separators and the comma is the decimal mark. Returns
    ``None`` when the text is not an amount.
    """
    if not text:
        return None
    match = _AMOUNT_RE.match(text)
    if not match:
        return None
    number = match.group(1).replace(".", "").replace(",", ".")
    try:
        value = Decimal(number)
    except InvalidOperation:
        return None
    currency = match.group(2).upper() if match.group(2) else None
    return value, currency
