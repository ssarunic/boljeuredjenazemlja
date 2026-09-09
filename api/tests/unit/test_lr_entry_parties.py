"""C-sheet entries keep the objects the server nests under them.

The encumbrance text ends with "u korist:" and the beneficiaries follow as
``lrOwners`` objects (verified against the live response for unit 657 / main
book 21277). ``LREntry.owners`` types that list; ``extra="allow"`` keeps any
other nested field, and ``get_parties()`` returns both.
"""

from datetime import date

import pytest

from cadastral_api.models.entities import EncumbranceGroup, EncumbranceSheetC, LREntry, RightType
from cadastral_api.utils import parse_lr_entry, parse_right_type, split_name_share, strip_html

USUFRUCT_ENTRY = {
    "description": (
        "Pr. 20. srpnja 1979. Z 2444/79<br>Na temelju rješenja o nasljeđivanju "
        "uknjižuje se pravo ploduživanja u korist:"
    ),
    "lrEntryId": 93357927,
    "orderNumber": "2.1",
    "lrOwners": [
        {"lrOwnerId": 71, "name": "TEST OSOBA UD. BOŽE", "address": "SAVAR"},
    ],
    # Undeclared fields: kept verbatim; name-bearing objects count as parties.
    "deletionNote": {"name": "BRISANJE", "diary": "Z 1/2000"},
    "flags": ["x"],
}


def test_entry_keeps_undeclared_fields_verbatim() -> None:
    entry = LREntry.model_validate(USUFRUCT_ENTRY)
    assert set(entry.source_fields) == {"deletionNote", "flags"}
    assert entry.owners[0].lr_owner_id == 71
    # And they survive serialization (what the MCP "full" detail returns).
    dumped = entry.model_dump(mode="json")
    assert dumped["owners"][0]["name"] == "TEST OSOBA UD. BOŽE"
    assert dumped["deletionNote"] == {"name": "BRISANJE", "diary": "Z 1/2000"}


def test_entry_parties_are_owners_then_other_name_bearing_objects() -> None:
    entry = LREntry.model_validate(USUFRUCT_ENTRY)
    names = [p.name for p in entry.get_parties()]
    assert names == ["TEST OSOBA UD. BOŽE", "BRISANJE"]
    party = entry.get_parties()[0]
    assert party.lr_owner_id == 71
    assert party.address == "SAVAR"
    assert party.register == "land_registry"


def test_entry_without_extras_has_no_parties() -> None:
    entry = LREntry(description="ZABILJEŽBA", orderNumber="1.1")
    assert entry.get_parties() == []
    assert entry.source_fields == {}


def test_group_collects_parties_from_entries_and_itself() -> None:
    group = EncumbranceGroup.model_validate(
        {
            "description": "1. Na cijelo",
            "shareOrderNumber": None,
            "lrEntries": [USUFRUCT_ENTRY],
            "beneficiary": {"name": "BANKA D.D.", "address": "ZAGREB"},
            "holders": [{"name": "GRUPNI OVLAŠTENIK"}],
        }
    )
    names = [p.name for p in group.get_parties()]
    assert names == ["BANKA D.D.", "GRUPNI OVLAŠTENIK", "TEST OSOBA UD. BOŽE", "BRISANJE"]


def test_sheet_keeps_undeclared_fields() -> None:
    sheet = EncumbranceSheetC.model_validate({"lrEntryGroups": [], "note": "n"})
    assert sheet.model_extra == {"note": "n"}
    assert not sheet.has_encumbrances()


def test_group_derives_beneficiary_and_right_type_from_entries() -> None:
    group = EncumbranceGroup.model_validate(
        {"description": "2. ", "lrEntries": [USUFRUCT_ENTRY]}
    )
    assert group.beneficiary is not None
    assert group.beneficiary.name == "TEST OSOBA UD. BOŽE"
    assert group.right_type is RightType.USUFRUCT
    # Serialized output no longer needs the HTML description to be read.
    dumped = group.model_dump(mode="json")
    assert dumped["right_type"] == "usufruct"
    assert dumped["beneficiary"]["name"] == "TEST OSOBA UD. BOŽE"
    # beneficiary is listed once by get_parties()
    assert [p.name for p in group.get_parties()] == ["TEST OSOBA UD. BOŽE", "BRISANJE"]


def test_group_keeps_supplied_beneficiary_and_right_type() -> None:
    group = EncumbranceGroup.model_validate(
        {
            "description": "1.",
            "lrEntries": [USUFRUCT_ENTRY],
            "beneficiary": {"name": "BANKA D.D."},
            "right_type": "mortgage",
        }
    )
    assert group.beneficiary.name == "BANKA D.D."
    assert group.right_type is RightType.MORTGAGE


def test_group_without_entries_derives_nothing() -> None:
    group = EncumbranceGroup(description="1.")
    assert group.beneficiary is None
    assert group.right_type is None


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("uknjižuje se pravo ploduživanja do udaje, u korist:", "usufruct"),
        ("uknjižuje se pravo plodouživanja u korist:", "usufruct"),
        ("UKNJIŽBA, ZALOŽNO PRAVO za iznos od 100.000,00 EUR", "mortgage"),
        ("uknjižuje se založnog prava (hipoteke)", "mortgage"),
        ("Zaprimljeno 05.05.2016. <br><br>ZABILJEŽBA, TRAŽBINA SOCIJALNE POMOĆI", "lien"),
        ("uknjižuje se pravo služnosti puta u korist svakodobnog vlasnika", "easement"),
        ("uknjižuje se pravo stanovanja u korist:", "easement"),
        ("zabilježba zabrane otuđenja i opterećenja", "prohibition"),
        ("uknjižuje se pravo prvokupa u korist:", "preemption"),
        ("ZABILJEŽBA OVRHE", "annotation"),
        ("uknjižuje se pravo građenja", "other"),
        ("", None),
        (None, None),
    ],
)
def test_parse_right_type(text: str | None, expected: str | None) -> None:
    assert parse_right_type(text) == expected


def test_strip_html() -> None:
    raw = "Stig.&nbsp;1949.<br><br>Z 487/49  <b>u korist:</b>"
    assert strip_html(raw) == "Stig. 1949. Z 487/49 u korist:"


def test_entry_fields_are_parsed_from_description() -> None:
    entry = LREntry.model_validate(USUFRUCT_ENTRY)
    assert entry.action_type == "upis"
    assert entry.diary_number == "Z-2444/79"
    assert entry.entry_date == date(1979, 7, 20)
    assert entry.basis_document == "rješenja o nasljeđivanju"


def test_entry_keeps_supplied_structured_fields() -> None:
    entry = LREntry.model_validate(
        {**USUFRUCT_ENTRY, "action_type": "brisanje", "diary_number": "Z-1/2000"}
    )
    assert entry.action_type == "brisanje"
    assert entry.diary_number == "Z-1/2000"
    assert entry.entry_date == date(1979, 7, 20)


ENTRY_1949 = (
    "Stig. 23. svibnja 1949.<br>Z 487/49<br>Na temelju presude 29. siječnja 1940. "
    "agr. 1996/31 Sreskog suda u Preku, uknjižuje se pravo ploduživanja do udaje, u korist:"
)
ENTRY_1979 = (
    "Pr. 20. srpnja 1979.<br>Z 2444/79<br>Na temelju rješenja o nasljeđivanju od "
    "27. studenog 1967. pod brojem O 533/67, Općinskog suda u Zadru, uknjižuje se "
    "pravo ploduživanja u korist:"
)
ENTRY_2016 = (
    "Zaprimljeno 05.05.2016.g. pod brojem Z-9139/2016<br><br>ZABILJEŽBA, TRAŽBINA SOCIJALNE POMOĆI"
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            ENTRY_1949,
            {
                "action_type": "upis",
                "diary_number": "Z-487/49",
                "entry_date": date(1949, 5, 23),
                "basis_document": "presude 29. siječnja 1940. agr. 1996/31 Sreskog suda u Preku",
            },
        ),
        (
            ENTRY_1979,
            {
                "action_type": "upis",
                "diary_number": "Z-2444/79",
                "entry_date": date(1979, 7, 20),
                "basis_document": (
                    "rješenja o nasljeđivanju od 27. studenog 1967. pod brojem O 533/67, "
                    "Općinskog suda u Zadru"
                ),
            },
        ),
        (
            ENTRY_2016,
            {
                "action_type": "zabilježba",
                "diary_number": "Z-9139/2016",
                "entry_date": date(2016, 5, 5),
                "basis_document": None,
            },
        ),
        (
            "UKNJIŽBA, PRAVO VLASNIŠTVA",
            {
                "action_type": "upis",
                "diary_number": None,
                "entry_date": None,
                "basis_document": None,
            },
        ),
        (
            "Briše se zabilježba ovrhe upisana pod Z-12/2020",
            {
                "action_type": "brisanje",
                "diary_number": "Z-12/2020",
                "entry_date": None,
                "basis_document": None,
            },
        ),
        (
            "Temeljem ugovora o kreditu od 1.2.2020. predbilježuje se založno pravo",
            {
                "action_type": "predbilježba",
                "diary_number": None,
                "entry_date": date(2020, 2, 1),
                "basis_document": "ugovora o kreditu od 1.2.2020.",
            },
        ),
        (
            "",
            {
                "action_type": None,
                "diary_number": None,
                "entry_date": None,
                "basis_document": None,
            },
        ),
    ],
)
def test_parse_lr_entry(text: str, expected: dict) -> None:
    assert parse_lr_entry(text) == expected


@pytest.mark.parametrize(
    ("name", "bare", "fraction"),
    [
        ("ŠARUNIĆ AUGUSTIN POK. BOŽE ZA 2/6", "ŠARUNIĆ AUGUSTIN POK. BOŽE", (2, 6)),
        ("IVIĆ ANA za 1/2 dijela", "IVIĆ ANA", (1, 2)),
        ("IVIĆ ANA ZA 1/2 idealnog dijela.", "IVIĆ ANA", (1, 2)),
        ("ŠARUNIĆ EVICA POK. BOŽE", "ŠARUNIĆ EVICA POK. BOŽE", None),
        ("ZADRUGA ZA 1/0", "ZADRUGA ZA 1/0", None),
        ("", "", None),
    ],
)
def test_split_name_share(name: str, bare: str, fraction: tuple[int, int] | None) -> None:
    assert split_name_share(name) == (bare, fraction)


def test_party_share_from_name_suffix() -> None:
    entry = LREntry.model_validate(
        {
            "description": "u korist:",
            "orderNumber": "2.1",
            "lrOwners": [{"lrOwnerId": 1, "name": "ŠARUNIĆ AUGUSTIN POK. BOŽE ZA 2/6"}],
        }
    )
    party = entry.owners[0]
    assert party.name == "ŠARUNIĆ AUGUSTIN POK. BOŽE ZA 2/6"  # raw preserved
    assert party.name_normalized == "Šarunić Augustin Pok. Bože"
    assert party.share == {"num": 2, "den": 6, "decimal": 2 / 6}
    dumped = party.model_dump(mode="json")
    assert dumped["share"]["den"] == 6
    plain = LREntry.model_validate(USUFRUCT_ENTRY).owners[0]
    assert plain.share is None


def test_basis_date_is_parsed_from_basis_document() -> None:
    e1 = LREntry(description=ENTRY_1949, orderNumber="1.1")
    assert e1.entry_date == date(1949, 5, 23)
    assert e1.basis_date == date(1940, 1, 29)
    e2 = LREntry(description=ENTRY_1979, orderNumber="2.1")
    assert e2.basis_date == date(1967, 11, 27)
    e3 = LREntry(description=ENTRY_2016, orderNumber="1.1")
    assert e3.basis_document is None and e3.basis_date is None
