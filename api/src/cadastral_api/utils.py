"""Shared helpers for parsing and normalizing cadastral/land-registry data."""

import re

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
