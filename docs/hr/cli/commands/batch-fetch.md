<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/batch-fetch.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega i ne smije se spajati na službeni katastar ni zemljišne knjige Republike Hrvatske. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.1.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Pretraga više čestica odjednom

Zadajte alatu više brojeva čestica, ili datoteku s popisom, i dobit ćete jednu
tablicu s površinom, internim brojem čestice i zemljišnoknjižnim uloškom svake
od njih. Ta je tablica polazište za čitanje više zemljišnoknjižnih uložaka
odjednom.

## Kada vam ovo treba

- Nasljeđivanje ili prodaja obuhvaća više čestica i želite ih provjeriti sve
  zajedno.
- Od klijenta ste dobili tablicu čestica i želite zemljišnoknjižni uložak svake
  od njih.
- Želite utvrditi koje čestice s popisa ne postoje ili imaju pogrešan broj.

## Prije nego počnete

Za nekoliko čestica u istoj općini upisujete ih u istom retku, odvojene
zarezima. Za dulje popise pripremite datoteku. Najjednostavnija je CSV datoteka,
koju možete spremiti iz bilo kojeg programa za tablice. Ima dva stupca,
`parcel_number` i `municipality`, i izgleda ovako:

```text
parcel_number,municipality
103/2,SAVAR
45,
396/1,
```

Prazno polje općine znači „isto kao u retku iznad”. Prihvaća se i JSON datoteka
istog sadržaja. Primjeri datoteka: [parcels.csv](../examples/parcels.csv),
[parcels.json](../examples/parcels.json).

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter. Navodnici oko popisa su važni.

   ```bash
   cadastral batch-fetch "103/2,45,396/1" -m SAVAR
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output cadastral batch-fetch "103/2,45,396/1" -m SAVAR -->
   ```text
   📊 Pronađene 3 čestice za obradu


   SAŽETAK GRUPNE OBRADE
   =====================
     Ukupno čestica    3
     Uspješno          3
     Neuspješno        0
     Stopa uspjeha     100.0%


   REZULTATI
   =========
     #    Status    Čestica    Općina            Površina (m²)    ID čestice    ZK uložak
     1      ✓       103/2      SAVAR (334979)            1,200    6564817       657
     2      ✓       45         SAVAR (334979)              981    6564715       138
     3      ✓       396/1      SAVAR (334979)            2,077    6565198       645

   ✓ ✓ Uspješno obrađeno svih 3 čestica
   ```
   <!-- END GENERATED: output -->

4. **SAŽETAK GRUPNE OBRADE** broji koliko je čestica pronađeno. **REZULTATI**
   ima jedan redak po čestici. **Status** pokazuje kvačicu za pronađenu i križić
   za nepronađenu česticu. **ZK uložak** je broj zemljišnoknjižnog uloška
   čestice, koji vam treba za sljedeći korak.

## Što možete odabrati

Da biste popis pročitali iz datoteke, umjesto upisivanja čestica upotrijebite
`--input` s nazivom datoteke. Otvorite Terminal u mapi u kojoj je datoteka:

```bash
cadastral batch-fetch --input parcels.csv
```

Kada jedna čestica nije pronađena, alat nastavlja s ostalima i na kraju ispisuje
neuspjele. Ako radije želite stati kod prvog problema, dodajte
`--stop-on-error`.

Za nastavak prema zemljišnoj knjizi spremite rezultat kao JSON datoteku pomoću
`--format json` i `--output`. Stranica [batch-lr-unit](batch-lr-unit.md) tu
datoteku može izravno pročitati:

```bash
cadastral batch-fetch "103/2,45,396/1" -m SAVAR --format json --output parcels-found.json
cadastral batch-lr-unit --from-batch-output parcels-found.json
```

Dodajte `--detail full` za ispis cijelog katastarskog zapisa svake čestice, kao
na stranici [get-parcel](get-parcel.md), i `--show-owners` da uključite
posjednike.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `[PARCELS]` | Neobavezno. Vrijednost koju upisujete odmah iza naziva naredbe | Ne koristi se |
| `--input`, `-i` `PUTANJA` | Ulazna datoteka (CSV ili JSON) s popisom čestica | Ne koristi se |
| `--municipality`, `-m` `TEXT` | Naziv ili šifra općine (obavezno kod popisa u naredbenom retku) | Ne koristi se |
| `--output`, `-o` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--format`, `-f` | Format izlaza (`table`, `json`, `csv`) | Koristi se `table` |
| `--detail` | Razina detalja: basic (samo sažetak) ili full (potpuni podaci za svaku česticu) (`basic`, `full`) | Koristi se `basic` |
| `--show-owners` | Uključi detaljne podatke o vlasništvu u izlaz | Nije uključeno |
| `--continue-on-error` / `--stop-on-error` | Nastavi obradu nakon grešaka (zadano: nastavi) | Koristi se `--continue-on-error` |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Čestica koja ne postoji ne prekida obradu. Dobiva križić u stupcu **Status** i
objašnjenje u tablici **GREŠKE** na kraju:

<!-- BEGIN GENERATED: output cadastral batch-fetch "103/2,999" -m SAVAR -->
```text
📊 Pronađene 2 čestice za obradu


SAŽETAK GRUPNE OBRADE
=====================
  Ukupno čestica    2
  Uspješno          1
  Neuspješno        1
  Stopa uspjeha     50.0%


REZULTATI
=========
  #    Status    Čestica    Općina                     Površina (m²)    ID čestice    ZK uložak
  1      ✓       103/2      SAVAR (334979)                     1,200    6564817       657
  2      ✗       999        SAVAR             Čestica nije pronađena    -             -

GREŠKE
======
  #    Čestica        Vrsta greške              Poruka greške
  2    999 (SAVAR)    Čestica nije pronađena    Čestica nije pronađena (parcel_number=999,
                                                municipality_reg_num=334979)

⚠️  Obrađeno 1/2 čestica (50.0% stopa uspjeha)
   1 čestica nije uspjela - pogledajte ispis za detalje
```
<!-- END GENERATED: output -->

Ispravite broj i ponovno pokrenite naredbu samo za tu česticu.

Ako alat ne može pronaći datoteku koju ste naveli, provjerite je li Terminal u
mapi u kojoj je datoteka, ili upišite njezinu punu putanju. Ostale poruke
objašnjene su na [stranici o greškama](../errors.md).

## Povezane stranice

- [batch-lr-unit](batch-lr-unit.md) čita zemljišnoknjižne uloške koje ste ovdje
  pronašli.
- [search](search.md) provjerava jednu česticu.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `cadastral batch-fetch --help`:

```text
Uporaba: cadastral batch-fetch [OPTIONS] [PARCELS]

  Dohvat podataka za više čestica odjednom (skupna obrada).

  Podržana su dva načina unosa:

  1. Popis odvojen zarezima u naredbenom retku (za male skupine):
     cadastral batch-fetch "103/2,45,396/1" --municipality SAVAR

  2. Ulazna datoteka (za velike skupine):
     cadastral batch-fetch --input parcels.csv
     cadastral batch-fetch --input parcels.json

  CSV format (brojevi čestica s općinom):
    parcel_number,municipality
    103/2,334979
    45,
    396/1,

  Napomena: prazna polja općine preuzimaju vrijednost iz prethodnog retka.

  CSV format (izravni ID-ovi čestica):
    parcel_id
    12345678
    87654321

  JSON format:
    [
      {"parcel_number": "103/2", "municipality": "334979"},
      {"parcel_number": "45", "municipality": "SAVAR"}
    ]

  Ili:
    [
      {"parcel_id": "12345678"},
      {"parcel_id": "87654321"}
    ]

  Primjeri:
    # Brza skupna obrada iz popisa u naredbenom retku
    cadastral batch-fetch "103/2,45,396/1" -m SAVAR

    # Skupna obrada iz CSV datoteke
    cadastral batch-fetch --input parcels.csv --format csv -o results.csv

    # Skupna obrada s potpunim podacima za svaku česticu (kao get-parcel)
    cadastral batch-fetch "103/2,45,396/1" -m SAVAR --detail full

    # Skupna obrada s podacima o vlasništvu u JSON formatu
    cadastral batch-fetch --input parcels.json --show-owners --format json -o results.json

Opcije:
  -i, --input PUTANJA             Ulazna datoteka (CSV ili JSON) s popisom
                                  čestica
  -m, --municipality TEXT         Naziv ili šifra općine (obavezno kod popisa u
                                  naredbenom retku)
  -o, --output PUTANJA            Spremi izlaz u datoteku
  -f, --format [table|json|csv]   Format izlaza
  --detail [basic|full]           Razina detalja: basic (samo sažetak) ili full
                                  (potpuni podaci za svaku česticu)
  --show-owners                   Uključi detaljne podatke o vlasništvu u izlaz
  --continue-on-error / --stop-on-error
                                  Nastavi obradu nakon grešaka (zadano: nastavi)
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
