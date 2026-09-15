"""One person identity for both registers: folded names, relatives, tax numbers."""

from __future__ import annotations

from cadastral_api.analysis import count_distinct_persons, person_key, plain_reorder, same_person


def test_key_folds_case_diacritics_punctuation_and_the_share_suffix() -> None:
    key = person_key("ŠARUNIĆ AUGUSTIN POK. BOŽE ZA 2/6")
    assert key.strict == "sarunic augustin pok boze"
    assert key.fuzzy == "sarunic augustin"
    assert key.tax_number is None
    assert person_key("  Sarunic   Sasa ").strict == person_key("ŠARUNIĆ SAŠA").strict


def test_relative_markers_are_dropped_from_the_fuzzy_key_only() -> None:
    assert person_key("TEST OSOBA UD. BOŽE").fuzzy == "test osoba"
    assert person_key("KOLAR RAJKA ROĐ. MARIĆ").fuzzy == "kolar rajka"
    assert person_key("KOLAR RAJKA ROĐ. MARIĆ").strict == "kolar rajka rod maric"
    # A marker with nothing after it, or a name that is only a marker, still keys.
    assert person_key("IVIĆ IVAN POK.").fuzzy == "ivic ivan"
    assert person_key("POK").fuzzy == "pok"


def test_same_person_exact_fuzzy_and_different() -> None:
    assert same_person(person_key("ŠARUNIĆ SAŠA"), person_key("Sarunic Sasa")) == (True, False)
    assert same_person(
        person_key("ŠARUNIĆ AUGUSTIN POK. BOŽE"), person_key("ŠARUNIĆ AUGUSTIN")
    ) == (True, True)
    assert same_person(
        person_key("ŠARUNIĆ AUGUSTIN POK. BOŽE"), person_key("ŠARUNIĆ AUGUSTIN POK. IVE")
    ) == (True, True)
    assert same_person(person_key("ŠARUNIĆ SAŠA"), person_key("ŠARUNIĆ AUGUSTIN")) == (
        False,
        False,
    )
    assert same_person(person_key(""), person_key("")) == (False, False)


def test_tax_numbers_decide_when_both_records_have_one() -> None:
    assert same_person(person_key("A B", "1"), person_key("A B", "2")) == (False, False)
    assert same_person(person_key("A B", "1"), person_key("C D", "1")) == (True, False)
    # One tax number alone does not decide; the name does.
    assert same_person(person_key("A B", "1"), person_key("a b")) == (True, False)


def test_count_distinct_persons() -> None:
    records = [
        ("ŠARUNIĆ SAŠA", None),
        ("Sarunic Sasa", None),
        ("KOLAR RAJKA", "11111111111"),
        ("KOLAR RAJKA", "22222222222"),
        ("KOLAR RAJKA", None),
        ("", None),
        (None, None),
    ]
    # One Šarunić; two Kolars told apart by tax number, the third record joins them.
    assert count_distinct_persons(records) == 3
    assert count_distinct_persons([]) == 0
    # The loose key is not used for counting: a relative's name keeps records apart.
    assert count_distinct_persons([("A B POK. C", None), ("A B", None)]) == 2


def test_infer_party_type() -> None:
    from cadastral_api.analysis import infer_party_type

    assert infer_party_type("REPUBLIKA HRVATSKA").party_type == "state"
    assert infer_party_type("REPUBLIKE HRVATSKE, Ministarstvo financija").party_type == "state"
    assert infer_party_type("GRAD ZAGREB").party_type == "municipality"
    assert infer_party_type("OPĆINA SALI").party_type == "municipality"
    assert infer_party_type("ZADARSKA ŽUPANIJA").party_type == "municipality"
    assert infer_party_type("HRVATSKE ŠUME d.o.o.").party_type == "company"
    assert infer_party_type("ZAGREBAČKA BANKA D.D.").party_type == "company"
    assert infer_party_type("OBRT ZA USLUGE MARIĆ").party_type == "company"
    assert infer_party_type("ŠARUNIĆ SAŠA").party_type == "individual"
    assert infer_party_type("ŠARUNIĆ AUGUSTIN POK. BOŽE ZA 2/6").party_type == "individual"
    assert infer_party_type("").party_type == "unknown"
    inferred = infer_party_type("HRVATSKE ŠUME d.o.o.")
    assert inferred.inferred is True and "doo" in inferred.basis


def test_group_by_person_and_group_keys() -> None:
    from cadastral_api.analysis.persons import group_by_person, group_size, person_group_key

    groups = group_by_person([("A B", None), ("a b", "2"), ("A B", "1"), ("C D", None), ("", "9")])
    assert groups == {"a b": {"1", "2"}, "c d": set()}
    assert [group_size(t) for t in groups.values()] == [2, 1]
    # A record with a tax number keeps it; one without joins the group's first tax number.
    assert person_group_key("a b", "2", groups) == "a b#2"
    assert person_group_key("a b", None, groups) == "a b#1"
    assert person_group_key("c d", None, groups) == "c d"
    assert person_group_key("x y", None, groups) == "x y"


def test_a_relative_after_a_comma_and_a_reversed_name_match_loosely() -> None:
    # The cadastre writes the father's name after a comma, the register after "pok.".
    register = person_key("ŠARUNIĆ AUGUSTIN POK. BOŽE")
    cadastre = person_key("ŠARUNIĆ AUGUSTIN, BOŽO")
    assert cadastre.fuzzy == "sarunic augustin"
    assert person_key("ŠARUNIĆ ANTE, P. BOŽE").fuzzy == "sarunic ante"
    assert person_key("IVIĆ MARKO, SIN PETRA").fuzzy == "ivic marko"
    assert same_person(register, cadastre) == (True, True)
    # The cadastre sometimes writes the given name first: a match, fuzzy until
    # the register comparison corroborates it (a namesake looks the same).
    reversed_a, reversed_b = person_key("AUGUSTIN ŠARUNIĆ"), person_key("ŠARUNIĆ AUGUSTIN")
    assert same_person(reversed_a, reversed_b) == (True, True)
    assert plain_reorder(reversed_a, reversed_b) is True
    # Out of order and with a relative on one side is two deviations at once:
    # not matched (a namesake is as likely), and not a plain reorder.
    assert same_person(reversed_a, register) == (False, False)
    assert plain_reorder(reversed_a, register) is False
    assert same_person(person_key("Fjordana Šarunić"), register) == (False, False)
    # A single word is never matched out of order (it is the strict match or nothing).
    assert same_person(person_key("ŠARUNIĆ"), person_key("ŠARUNIĆ")) == (True, False)
    # The strict key keeps the comma part: distinct counts do not merge on a guess.
    assert cadastre.strict == "sarunic augustin bozo"
