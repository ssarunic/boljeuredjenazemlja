<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/get-lr-unit.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega i ne smije se spajati na službeni katastar ni zemljišne knjige Republike Hrvatske. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.1.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Uvid u zemljišnoknjižni uložak: vlasnici, čestice, tereti

Zemljišnoknjižni uložak sadrži pravno stanje nekretnine. Ova naredba prikazuje
njegova tri lista: čestice koje obuhvaća (posjedovnica, list A), vlasnike i
njihove udjele (vlastovnica, list B) te terete poput hipoteka i služnosti
(teretovnica, list C). Prikazuje i plombe.

## Kada vam ovo treba

- Trebate znati tko je pravni vlasnik čestice i u kojim udjelima.
- Provjeravate hipoteke, služnosti, zabilježbe ili druge terete prije prodaje
  ili kredita.
- Želite znati je li na ulošku u tijeku neki prijedlog za upis, na primjer
  rješenje o nasljeđivanju koje još nije provedeno.

## Prije nego počnete

Uložak možete odrediti na dva načina. Ako krećete od čestice, zadajte broj
čestice i katastarsku općinu, a alat sam pronalazi uložak. Ako već imate broj
uloška i glavnu knjigu kojoj pripada, zadajte to dvoje.

Glavna knjiga određena je brojem koji alat naziva identifikatorom glavne knjige
(main book ID). Dobivate ga iz rezultata naredbe
[skupno-čestice](batch-fetch.md) ili iz ranijeg dohvata. Kretanje od čestice
lakši je put.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   uz uložak --od-čestice 103/2 -ko SAVAR --sve
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output uz uložak --od-čestice 103/2 -ko SAVAR --sve -->
   ```text
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
   ```
   <!-- END GENERATED: output -->

4. Prva tablica, **ZEMLJIŠNOKNJIŽNI ULOŽAK**, određuje uložak: njegov broj,
   glavnu knjigu, ured koji ga vodi i **Zadnji broj dnevnika**, najnoviji
   poslovni broj upisan u dnevnik. **POSJEDOVNICA (LIST A)** je list A.
   **VLASTOVNICA (LIST B)** je list B, s udjelom svakog vlasnika kao razlomkom.
   **TERETOVNICA (LIST C)** je list C. Kada je list C prazan, alat ispisuje
   **Nema tereta**.

5. Ako uložak ima plombe, u prvoj tablici pojavljuje se dodatni redak **Plombe
   (u tijeku)** s poslovnim brojevima, a slijedi upozorenje. Plomba znači da je
   prijedlog za upis zaprimljen i da se uložak možda uskoro mijenja. Ne
   smatrajte listove konačnima dok se on ne riješi.

## Što možete odabrati

`--sve` prikazuje sva tri lista. Da vidite samo jedan, upotrijebite `--vlasnici`
za list B, `--čestice` za list A ili `--tereti` za list C. Bez ijednog od njih
alat ispisuje samo prvu tablicu.

Da vidite o čemu je svaka plomba, dodajte `--plombe`. Alat tada za svaku plombu
pita zemljišnu knjigu, što je jedan dodatni upit po plombi, i ispisuje tablicu s
vrstom prijedloga za upis, njegovim statusom i datumom zaprimanja:

```bash
uz uložak --broj-uloška 449 --glavna-knjiga 21277 --sve --plombe
```

<!-- BEGIN GENERATED: output uz uložak --broj-uloška 449 --glavna-knjiga 21277 --sve --plombe -->
```text
             ZEMLJIŠNOKNJIŽNI ULOŽAK
 Broj uloška           449
 Glavna knjiga         TESTMUNICIPALITY
 Institucija           Test Land Registry Office
 Status                Aktivan
 Tip uloška            VLASNIČKI
 Zadnji broj dnevnika  Z-15677/2026
 Plombe (u tijeku)     Z-12564/2026, Z-18444/2026
⚠️  Ovaj uložak ima plombe (zaprimljeni neriješeni prijedlozi) - moguća je promjena u tijeku.

                         DETALJ PLOMBI (ZAPRIMLJENI PRIJEDLOZI)
 Broj plombe   Prijedlog                  Status                  Zaprimljeno  Ishod
 Z-12564/2026  Rješenje o nasljeđivanju   IZRADA NACRTA RJEŠENJA   2026-04-20  U tijeku
 Z-18444/2026  Uknjižba prava vlasništva  IZRADA NACRTA RJEŠENJA   2026-06-09  U tijeku

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
```
<!-- END GENERATED: output -->

Da uložak odredite izravno umjesto polaskom od čestice, upotrijebite zajedno
`--broj-uloška` i `--glavna-knjiga`, kao u gornjem primjeru. Da rezultat
spremite u datoteku, dodajte `--oblik json` i `--datoteka` s nazivom datoteke.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `--broj-uloška`, `-u` `TEXT` | Broj zemljišnoknjižnog uloška (npr. '769') | Ne koristi se |
| `--glavna-knjiga`, `-b` `INTEGER` | ID glavne knjige (npr. 21277) | Ne koristi se |
| `--od-čestice`, `-p` `TEXT` | Dohvati ZK uložak prema broju čestice | Ne koristi se |
| `--općina`, `-ko` `TEXT` | Naziv ili šifra općine (obavezno uz --from-parcel) | Ne koristi se |
| `--vlasnici`, `-o` | Prikaži podatke o vlasništvu (list B) | Nije uključeno |
| `--čestice`, `-P` | Prikaži sve čestice u ulošku (list A) | Nije uključeno |
| `--tereti`, `-e` | Prikaži terete (list C) | Nije uključeno |
| `--plombe`, `-D` | Razriješi detalje plombi - jedan dodatni zahtjev po plombi | Nije uključeno |
| `--sve`, `-a` | Prikaži sve listove | Nije uključeno |
| `--oblik`, `-f` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--datoteka` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako zadate česticu, a zaboravite općinu, alat staje i traži je:

<!-- BEGIN GENERATED: output uz uložak --od-čestice 103/2 -->
```text
✗ Greška: --municipality je obavezan uz --from-parcel
```
<!-- END GENERATED: output -->

Dodajte `-ko` i naziv ili šifru općine.

Ako broj uloška ne postoji u toj glavnoj knjizi, alat javlja grešku koja
završava s `404 Not Found`. Provjerite oba broja na svom dokumentu. Ostale
poruke objašnjene su na [stranici o greškama](../errors.md).

## Povezane stranice

- [čestica](get-parcel.md) prikazuje katastarsku stranu iste čestice,
  uključujući posjednike.
- [skupno-ulošci](batch-lr-unit.md) čita više uložaka odjednom.
- [Pojmovnik](../glossary.md) objašnjava listove A, B i C te plombu.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `uz uložak --help`:

```text
Uporaba: uz uložak [OPCIJE]

  Dohvat detaljnih podataka o zemljišnoknjižnom ulošku.

  Dohvaća potpune podatke o zemljišnoknjižnom ulošku, uključujući vlasništvo
  (list B), čestice (list A) i terete (list C).

  Primjeri:
    # Prema broju uloška i ID-u glavne knjige
    uz uložak --broj-uloška 769 --glavna-knjiga 21277

    # Prema čestici (automatsko pronalaženje)
    uz uložak --od-čestice 279/6 -ko SAVAR

    # Samo podaci o vlasništvu
    uz uložak -u 769 -b 21277 --vlasnici

    # Svi listovi
    uz uložak -p 279/6 -ko SAVAR --sve

    # Izvoz u JSON
    uz uložak -u 769 -b 21277 --oblik json -o lr-unit.json

  ⚠️  SAMO ZA DEMONSTRACIJU I EDUKACIJU - isključivo podaci probnog poslužitelja

Opcije:
  -u, --broj-uloška TEXT          Broj zemljišnoknjižnog uloška (npr. '769')
  -b, --glavna-knjiga INTEGER     ID glavne knjige (npr. 21277)
  -p, --od-čestice TEXT           Dohvati ZK uložak prema broju čestice
  -ko, --općina TEXT              Naziv ili šifra općine (obavezno uz --from-
                                  parcel)
  -o, --vlasnici                  Prikaži podatke o vlasništvu (list B)
  -P, --čestice                   Prikaži sve čestice u ulošku (list A)
  -e, --tereti                    Prikaži terete (list C)
  -D, --plombe                    Razriješi detalje plombi - jedan dodatni
                                  zahtjev po plombi
  -a, --sve                       Prikaži sve listove
  -f, --oblik [tablica|json|csv]  Format izlaza
  --datoteka PUTANJA              Spremi izlaz u datoteku
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
