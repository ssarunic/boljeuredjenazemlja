<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/batch-lr-unit.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega i ne smije se spajati na službeni katastar ni zemljišne knjige Republike Hrvatske. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.1.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Uvid u više zemljišnoknjižnih uložaka odjednom

Zadajte alatu popis zemljišnoknjižnih uložaka, ili rezultat naredbe
[batch-fetch](batch-fetch.md), i on ispisuje listove svakog uloška jedan za
drugim.

## Kada vam ovo treba

- Provjerili ste popis čestica naredbom batch-fetch i sada želite vlasnike i
  terete svake od njih.
- Vodite popis uložaka za predmet i želite ih sve ponovno pročitati nakon
  promjene.

## Prije nego počnete

Svaki je uložak određen svojim brojem i identifikatorom glavne knjige (main book
ID). Najlakše ćete oboje dobiti iz JSON datoteke koju zapisuje
[batch-fetch](batch-fetch.md). Možete pripremiti i CSV datoteku s dva stupca,
`lr_unit_number` i `main_book_id`, poput primjera
[lr_units.csv](../examples/lr_units.csv):

```text
lr_unit_number,main_book_id
657,21277
769,21277
449,21277
```

## Korak po korak

1. Otvorite Terminal u mapi u kojoj je vaša datoteka.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   cadastral batch-lr-unit --input lr_units.csv --show-owners
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output cadastral batch-lr-unit --input lr_units.csv --show-owners -->
   ```text
   📄 Učitavam ZK uloške iz: lr_units.csv
   📊 Pronađena 3 ZK uloška za obradu

                   ZEMLJIŠNOKNJIŽNI ULOŽAK
    Broj uloška           657
    Glavna knjiga         SAVAR
    Institucija           Test Land Registry Office SAVAR
    Status                Aktivan
    Tip uloška            VLASNIČKI
    Zadnji broj dnevnika  Z-12345/2024

           POSJEDOVNICA (LIST A)
    Broj čestice  Adresa  Površina (m²)
    103/2         POLJE            1200
    UKUPNO                         1200

                      VLASTOVNICA (LIST B)
    Udio  Vlasnik                Adresa                  OIB
    1/2   IVIĆ MARKO, SIN PETRA  TESTNA ULICA 15, SPLIT  -
    1/2   IVIĆ ANA, KĆI PETRA    SAVAR                   -

    TERETOVNICA (LIST C)
    Opis         Detalji
    Nema tereta

   ---

                ZEMLJIŠNOKNJIŽNI ULOŽAK
    Broj uloška           769
    Glavna knjiga         TESTMUNICIPALITY
    Institucija           Test Land Registry Office
    Status                Aktivan
    Tip uloška            VLASNIČKI
    Zadnji broj dnevnika  Z-27986/2025

              POSJEDOVNICA (LIST A)
    Broj čestice  Adresa         Površina (m²)
    118/4         TEST FIELD               409
    192/3         TEST AREA                322
    279/6         TEST LOCATION           1890
    UKUPNO                                2621

                       VLASTOVNICA (LIST B)
    Udio  Vlasnik       Adresa                      OIB
    4/8   Test Owner A  -                           -
    1/8   Test Owner B  -                           -
    1/8   Test Owner C  -                           -
    1/8   Test Owner D  Test Street 123, Test City  12345678901
    1/8   Test Owner E  Test Avenue 456, Test City  98765432109

                                     TERETOVNICA (LIST C)
    Opis                            Detalji
    1. Na suvlasnički dio: 1 (4/8)  • 1.1: Zaprimljeno 05.05.2016.g. pod brojem Z-9139/2016

                                    ZABILJEŽBA, TRAŽBINA SOCIJALNE POMOĆI

   ---

                ZEMLJIŠNOKNJIŽNI ULOŽAK
    Broj uloška           449
    Glavna knjiga         TESTMUNICIPALITY
    Institucija           Test Land Registry Office
    Status                Aktivan
    Tip uloška            VLASNIČKI
    Zadnji broj dnevnika  Z-15677/2026
    Plombe (u tijeku)     Z-12564/2026, Z-18444/2026
   ⚠️  Ovaj uložak ima plombe (zaprimljeni neriješeni prijedlozi) - moguća je promjena u tijeku.

           POSJEDOVNICA (LIST A)
    Broj čestice  Adresa  Površina (m²)
    1122/1        OVČJA            3291
    UKUPNO                         3291

                        VLASTOVNICA (LIST B)
    Udio  Vlasnik         Adresa                      OIB
    1/4   Test Owner One  Test Street 1, Test City    00000000001
    1/12  Test Nephew A   Test Street 17, Test City   00000000130
    1/12  Test Nephew B   Test Street 110, Test City  00000000131
    1/12  Test Nephew C   Test Street 110, Test City  00000000132

    TERETOVNICA (LIST C)
    Opis         Detalji
    Nema tereta

   ✓ ✓ Uspješno obrađeno svih 3 ZK uložaka
   ```
   <!-- END GENERATED: output -->

4. Ulošci se ispisuju jedan za drugim, odvojeni crticama. Svaki je prikazan kao
   na stranici [get-lr-unit](get-lr-unit.md): **ZEMLJIŠNOKNJIŽNI ULOŽAK**, zatim
   **POSJEDOVNICA (LIST A)**, **VLASTOVNICA (LIST B)** i **TERETOVNICA (LIST
   C)**. Uložak s plombama ima isti redak **Plombe (u tijeku)** i upozorenje.

## Što možete odabrati

Za nastavak iz rezultata naredbe batch-fetch upotrijebite `--from-batch-output`
s JSON datotekom koju je ona zapisala:

```bash
cadastral batch-lr-unit --from-batch-output parcels-found.json --show-owners
```

Kod dugog popisa ispis na zaslonu teško je čitati. Umjesto toga spremite ga u
datoteku pomoću `--format json` i `--output`:

```bash
cadastral batch-lr-unit --input lr_units.csv --show-owners --format json --output units.json
```

Kada se jedan uložak ne može pročitati, alat nastavlja s ostalima. Dodajte
`--stop-on-error` da umjesto toga stane kod prvog problema.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `--input`, `-i` `PUTANJA` | Ulazna datoteka (CSV ili JSON) s popisom ZK uložaka | Ne koristi se |
| `--from-batch-output`, `-b` `PUTANJA` | Učitaj reference ZK uložaka iz JSON izlaza naredbe batch-fetch | Ne koristi se |
| `--output`, `-o` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--format`, `-f` | Format izlaza (`table`, `json`, `csv`) | Koristi se `table` |
| `--show-owners` | Uključi detaljne podatke o vlasništvu u izlaz | Nije uključeno |
| `--continue-on-error` / `--stop-on-error` | Nastavi obradu nakon grešaka (zadano: nastavi) | Koristi se `--continue-on-error` |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako alat ne može pronaći datoteku koju ste naveli, staje prije nego išta
pročita. Provjerite je li Terminal u mapi u kojoj je datoteka, ili upišite
njezinu punu putanju.

Ako jedan uložak s popisa ne postoji, taj se uložak označava kao neuspio, a
ostali se svejedno ispisuju. Provjerite njegov broj i identifikator glavne
knjige u svojoj datoteci. Ostale poruke objašnjene su na [stranici o
greškama](../errors.md).

## Povezane stranice

- [batch-fetch](batch-fetch.md) iz popisa čestica izrađuje popis uložaka.
- [get-lr-unit](get-lr-unit.md) čita jedan uložak i objašnjava listove.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `cadastral batch-lr-unit --help`:

```text
Uporaba: cadastral batch-lr-unit [OPTIONS]

  Dohvat podataka za više zemljišnoknjižnih uložaka odjednom (skupna obrada).

  Podržana su dva načina unosa:

  1. Datoteka sa ZK ulošcima (CSV ili JSON):
     cadastral batch-lr-unit --input lr_units.csv

  2. Izlaz naredbe batch-fetch (učitava jedinstvene reference ZK uložaka):
     cadastral batch-fetch "103/2,45" -m SAVAR --format json -o parcels.json
     cadastral batch-lr-unit --from-batch-output parcels.json

  CSV format:
    lr_unit_number,main_book_id
    769,21277
    123,45678

  JSON format:
    [
      {"lr_unit_number": "769", "main_book_id": 21277},
      {"lr_unit_number": "123", "main_book_id": 45678}
    ]

  Primjeri:
    # Iz datoteke sa ZK ulošcima
    cadastral batch-lr-unit --input lr_units.csv

    # Iz izlaza naredbe batch-fetch (lanac naredbi)
    cadastral batch-fetch "103/2,45,396/1" -m SAVAR --format json -o parcels.json
    cadastral batch-lr-unit --from-batch-output parcels.json

    # S podacima o vlasništvu u JSON formatu
    cadastral batch-lr-unit -i lr_units.json --show-owners --format json -o results.json

  ⚠️  SAMO ZA DEMONSTRACIJU I EDUKACIJU - isključivo podaci probnog poslužitelja

Opcije:
  -i, --input PUTANJA             Ulazna datoteka (CSV ili JSON) s popisom ZK
                                  uložaka
  -b, --from-batch-output PUTANJA
                                  Učitaj reference ZK uložaka iz JSON izlaza
                                  naredbe batch-fetch
  -o, --output PUTANJA            Spremi izlaz u datoteku
  -f, --format [table|json|csv]   Format izlaza
  --show-owners                   Uključi detaljne podatke o vlasništvu u izlaz
  --continue-on-error / --stop-on-error
                                  Nastavi obradu nakon grešaka (zadano: nastavi)
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
