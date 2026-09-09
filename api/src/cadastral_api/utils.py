"""Shared helpers for parsing and normalizing cadastral/land-registry data."""

import re
from datetime import date

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
# Action verbs, most decisive first: a deletion of an annotation is a deletion.
_ACTION_PATTERNS: tuple[tuple[str, str], ...] = (
    ("brisanje", r"\bbri[sš]e\s+se\b|\bbrisanje\b|\bbri[sš]u\s+se\b"),
    ("predbilježba", r"\bpredbilje[žz]"),
    ("zabilježba", r"\bzabilje[žz]"),
    ("upis", r"\buknji[žz]|\bupisuje\s+se\b|\bupis\b"),
)
_BASIS_RE = re.compile(
    r"\b(?:na\s+temelju|temeljem)\s+(.+?)"
    r"(?:,?\s+(?:uknji[žz]uje|upisuje|zabilje[žz]uje|predbilje[žz]uje|bri[sš]e|dopu[sš]ta|"
    r"odre[dđ]uje|provodi)\b|\s*$)",
    re.IGNORECASE | re.DOTALL,
)


def parse_lr_entry(text: str | None) -> dict[str, object]:
    """Pull the structured parts out of a land-registry entry's Croatian text.

    Returns a dict with ``action_type`` (an ``ActionType`` value or ``None``),
    ``diary_number`` (normalised to ``"Z-487/49"``), ``entry_date`` (the first
    date in the text, i.e. the receipt date after "Stig."/"Pr."/"Zaprimljeno")
    and ``basis_document`` (the phrase after "Na temelju" up to the action verb,
    e.g. ``"rješenja o nasljeđivanju od 27. studenog 1967. pod brojem O 533/67,
    Općinskog suda u Zadru"``). Missing parts are ``None``. HTML is stripped.
    """
    plain = strip_html(text)
    result: dict[str, object] = {
        "action_type": None,
        "diary_number": None,
        "entry_date": None,
        "basis_document": None,
    }
    if not plain:
        return result
    lower = plain.lower()

    for value, pattern in _ACTION_PATTERNS:
        if re.search(pattern, lower):
            result["action_type"] = value
            break

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
