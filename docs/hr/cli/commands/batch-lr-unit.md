<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/batch-lr-unit.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.1.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Uvid u više zemljišnoknjižnih uložaka odjednom

Zadajte alatu popis zemljišnoknjižnih uložaka, ili rezultat naredbe
[skupno-čestice](batch-fetch.md), i on ispisuje listove svakog uloška jedan za
drugim.

## Kada vam ovo treba

- Provjerili ste popis čestica naredbom skupno-čestice i sada želite vlasnike i
  terete svake od njih.
- Vodite popis uložaka za predmet i želite ih sve ponovno pročitati nakon
  promjene.

## Prije nego počnete

Svaki je uložak određen svojim brojem i identifikatorom glavne knjige (main book
ID). Najlakše ćete oboje dobiti iz JSON datoteke koju zapisuje
[skupno-čestice](batch-fetch.md). Možete pripremiti i CSV datoteku s dva stupca,
`broj_zk_uloska` i `id_glavne_knjige`, poput primjera
[lr_units.csv](../examples/lr_units.csv):

<!-- BEGIN GENERATED: file lr_units.csv -->
```text
broj_zk_uloska,id_glavne_knjige
657,21277
769,21277
449,21277
```
<!-- END GENERATED: file -->

## Korak po korak

1. Otvorite Terminal u mapi u kojoj je vaša datoteka.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz skupno-ulošci --ulaz lr_units.csv --vlasnici
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz skupno-ulošci --ulaz lr_units.csv --vlasnici -->
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
   Popis čestica prema zemljišnoj knjizi; stupac Adresa je kultura ili toponim iz stare zemljišne
   knjige, a ne lokacija.

                                      VLASTOVNICA (LIST B)
    Udio  Vlasnik                Adresa                  OIB  Upis
    1/2   IVIĆ MARKO, SIN PETRA  TESTNA ULICA 15, SPLIT  -    1.1 · 2018-06-10 · Z-5678/2018
    1/2   IVIĆ ANA, KĆI PETRA    SAVAR                   -    2.1 · 2018-06-10 · Z-5678/2018

                                           TERETOVNICA (LIST C)
    Opis  Detalji
    1.    • 1.1: Stig. 23. svibnja 1949.
          Z 487/49
          Na temelju presude 29. siječnja 1940. agr. 1996/31 Sreskog suda u Preku, uknjižuje se pravo
          ploduživanja do udaje, u korist:
            U korist:
              IVIĆ MARIJA, KĆI PETRA, SAVAR
    2.    • 2.1: Pr. 20. srpnja 1979.
          Z 2444/79
          Na temelju rješenja o nasljeđivanju od 27. studenog 1967. pod brojem O 533/67, Općinskog
          suda u Zadru, uknjižuje se pravo ploduživanja u korist:
            U korist:
              IVIĆ JELA UD. PETRA ZA 2/6

   ---

                 ZEMLJIŠNOKNJIŽNI ULOŽAK
    Broj uloška           769
    Glavna knjiga         SAVAR
    Institucija           Zemljišnoknjižni odjel Zadar
    Status                Aktivan
    Tip uloška            VLASNIČKI
    Zadnji broj dnevnika  Z-27986/2025

            POSJEDOVNICA (LIST A)
    Broj čestice  Adresa    Površina (m²)
    118/4         POLJE               409
    192/3         BANIŠINA            322
    198/3         BANIŠINA            255
    202/1         BANIŠINA            312
    221/6         BANIŠINA            501
    267/6         BANIŠINA            680
    279/6         VOLUNJAK           1890
    UKUPNO                           4369
   Popis čestica prema katastru.

                              VLASTOVNICA (LIST B)
    Udio  Vlasnik      Adresa     OIB          Upis
    4/8   Vlasnik 117  -          -            1.1 · 2012-04-05 · Z-3983/2012
    1/8   Vlasnik 119  -          -            3.1 · 2012-04-05 · Z-3983/2012
    1/8   Vlasnik 326  -          -            4.1 · 2012-04-05 · Z-3983/2012
    1/8   Vlasnik 116  Adresa 31  00000000036  5.2 · 2020-02-14 · Z-3937/2020
    1/24  Vlasnik 135  Adresa 10  00000000850  6.1 · 2018-03-21 · Z-6789/2018
    1/24  Vlasnik 327  Adresa 10  00000000868  7.1 · 2018-03-21 · Z-6789/2018
    1/24  Vlasnik 328  Adresa 32  00000000876  8.1 · 2018-03-21 · Z-6789/2018

                                           TERETOVNICA (LIST C)
    Opis                            Detalji
    1. Na suvlasnički dio: 1 (4/8)  • 1.1: Zaprimljeno 05.05.2016.g. pod brojem Z-9139/2016

                                    ZABILJEŽBA, TRAŽBINA SOCIJALNE POMOĆI, RJEŠENJE CENTRA ZA
                                    SOCIJALNU SKRB ZADAR KLASA: UP/I-551-04/16-02/29, URBROJ:
                                    2198-12-22-16-2 25.04.2016, počevši od 15. travnja 2016. godine pa
                                    nadalje, utvrđeno rješenjem Centra za socijalnu skrb Zadar KLASA:
                                    UP/I-551-04/16-02/29, URBROJ: 2198-12-22-16-2 od 25. travnja 2016.
                                    godine i prijedloga RH po zz od 04. svibnja 2016. godine, na
                                    nekretninamam, uknjiženog prava vlasništva na ime N.N. rođ. N.N.,
                                    OIB: 00000000884, N.N., za korist REPUBLIKE HRVATSKE, Centar za
                                    socijalnu skrb Zadar.

   ---

                 ZEMLJIŠNOKNJIŽNI ULOŽAK
    Broj uloška           449
    Glavna knjiga         SAVAR
    Institucija           Zemljišnoknjižni odjel Zadar
    Status                Aktivan
    Tip uloška            VLASNIČKI
    Zadnji broj dnevnika  Z-18444/2026
    Plombe (u tijeku)     Z-12564/2026
   ⚠️  Ovaj uložak ima plombe (zaprimljeni neriješeni prijedlozi) - moguća je promjena u tijeku.

           POSJEDOVNICA (LIST A)
    Broj čestice  Adresa  Površina (m²)
    1122/1        OVČJA            3291
    UKUPNO                         3291
   Popis čestica prema zemljišnoj knjizi; stupac Adresa je kultura ili toponim iz stare zemljišne
   knjige, a ne lokacija.

                                VLASTOVNICA (LIST B)
    Udio  Vlasnik      Adresa     OIB          Upis
    1/4   Vlasnik 114  Adresa 75  00000000010  127.2 · 2026-05-14 · Z-15677/2026
    1/4   Vlasnik 115  Adresa 41  00000000028  128.1 · 2025-09-29 · Z-31325/2025
    1/4   Vlasnik 116  Adresa 31  00000000036  129.1 · 2025-09-29 · Z-31325/2025
    1/4   Vlasnik 116  Adresa 76  00000000036  133.1 · 2026-06-09 · Z-18444/2026

    TERETOVNICA (LIST C)
    Opis         Detalji
    Nema tereta

   ✓ ✓ Uspješno obrađeno svih 3 ZK uložaka
   ```
   <!-- END GENERATED: output -->

4. Ulošci se ispisuju jedan za drugim, odvojeni crticama. Svaki je prikazan kao
   na stranici [uložak](get-lr-unit.md): **ZEMLJIŠNOKNJIŽNI ULOŽAK**, zatim
   **POSJEDOVNICA (LIST A)**, **VLASTOVNICA (LIST B)** i **TERETOVNICA (LIST
   C)**. Uložak s plombama ima isti redak **Plombe (u tijeku)** i upozorenje.

## Što možete odabrati

Za nastavak iz rezultata naredbe skupno-čestice upotrijebite
`--iz-skupnog-ispisa` s JSON datotekom koju je ona zapisala:

```bash
uz skupno-ulošci --iz-skupnog-ispisa parcels-found.json --vlasnici
```

Kod dugog popisa ispis na zaslonu teško je čitati. Umjesto toga spremite ga u
datoteku pomoću `--oblik json` i `--datoteka`:

```bash
uz skupno-ulošci --ulaz lr_units.csv --vlasnici --oblik json --datoteka units.json
```

Kada se jedan uložak ne može pročitati, alat nastavlja s ostalima. Dodajte
`--stani-kod-greške` da umjesto toga stane kod prvog problema.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `--ulaz`, `-ul` `PUTANJA` | Ulazna datoteka (CSV ili JSON) s popisom ZK uložaka | Ne koristi se |
| `--iz-skupnog-ispisa`, `-gk` `PUTANJA` | Učitaj reference ZK uložaka iz JSON izlaza naredbe batch-fetch | Ne koristi se |
| `--datoteka`, `-dt` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--vlasnici` | Uključi detaljne podatke o vlasništvu u izlaz | Nije uključeno |
| `--nastavi-kod-greške` / `--stani-kod-greške` | Nastavi obradu nakon grešaka (zadano: nastavi) | Koristi se `--nastavi-kod-greške` |
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

- [skupno-čestice](batch-fetch.md) iz popisa čestica izrađuje popis uložaka.
- [uložak](get-lr-unit.md) čita jedan uložak i objašnjava listove.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz skupno-ulošci --help`:

```text
Uporaba: uz skupno-ulošci [OPCIJE]

  Dohvat podataka za više zemljišnoknjižnih uložaka odjednom (skupna obrada).

  Podržana su dva načina unosa:

  1. Datoteka sa ZK ulošcima (CSV ili JSON):
     uz skupno-ulošci --ulaz lr_units.csv

  2. Izlaz naredbe batch-fetch (učitava jedinstvene reference ZK uložaka):
     uz skupno-čestice "103/2,45" -ko SAVAR --oblik json -dt parcels.json
     uz skupno-ulošci --iz-skupnog-ispisa parcels.json

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
    uz skupno-ulošci --ulaz lr_units.csv

    # Iz izlaza naredbe batch-fetch (lanac naredbi)
    uz skupno-čestice "103/2,45,396/1" -ko SAVAR --oblik json -dt parcels.json
    uz skupno-ulošci --iz-skupnog-ispisa parcels.json

    # S podacima o vlasništvu u JSON formatu
    uz skupno-ulošci -ul lr_units.json --vlasnici --oblik json -dt results.json

  ⚠️  Demonstracijski projekt: prije uporabe bilo kojeg poslužitelja osim
  priloženog probnog provjerite svoja prava na njegovu uporabu; koristite na
  vlastitu odgovornost

Opcije:
  -ul, --ulaz PUTANJA             Ulazna datoteka (CSV ili JSON) s popisom ZK
                                  uložaka
  -gk, --iz-skupnog-ispisa PUTANJA
                                  Učitaj reference ZK uložaka iz JSON izlaza
                                  naredbe batch-fetch
  -dt, --datoteka PUTANJA         Spremi izlaz u datoteku
  -ob, --oblik [tablica|json|csv]
                                  Format izlaza
  --vlasnici                      Uključi detaljne podatke o vlasništvu u izlaz
  --nastavi-kod-greške / --stani-kod-greške
                                  Nastavi obradu nakon grešaka (zadano: nastavi)
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
