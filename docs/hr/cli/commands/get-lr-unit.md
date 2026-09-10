<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/get-lr-unit.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega. Prije spajanja na bilo koji drugi poslužitelj, uključujući službeni katastar i zemljišne knjige Republike Hrvatske, provjerite imate li pravo koristiti taj poslužitelj i njegove podatke; to činite na vlastitu odgovornost. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
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
(main book ID). Dobivate ga iz rezultata popisa čestica naredbe
[čestica](get-parcel.md) ili iz ranijeg dohvata. Kretanje od čestice lakši je
put.

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
   ```
   <!-- END GENERATED: output -->

4. Prva tablica, **ZEMLJIŠNOKNJIŽNI ULOŽAK**, određuje uložak: njegov broj,
   glavnu knjigu, ured koji ga vodi i **Zadnji broj dnevnika**, najnoviji
   poslovni broj upisan u dnevnik. **POSJEDOVNICA (LIST A)** je list A.
   **VLASTOVNICA (LIST B)** je list B, s udjelom svakog vlasnika kao razlomkom.
   **TERETOVNICA (LIST C)** je list C. Kada je list C prazan, alat ispisuje
   **Nema tereta**. Kada je upis uknjižen u nečiju korist (tekst mu završava s
   "u korist:"), osobe slijede pod **U korist**, s adresom i OIB-om kada ih
   zemljišna knjiga ima.

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
 Glavna knjiga         SAVAR
 Institucija           Zemljišnoknjižni odjel Zadar
 Status                Aktivan
 Tip uloška            VLASNIČKI
 Zadnji broj dnevnika  Z-18444/2026
 Plombe (u tijeku)     Z-12564/2026
⚠️  Ovaj uložak ima plombe (zaprimljeni neriješeni prijedlozi) - moguća je promjena u tijeku.

                        DETALJ PLOMBI (ZAPRIMLJENI PRIJEDLOZI)
 Broj plombe   Prijedlog                 Status                  Zaprimljeno  Ishod
 Z-12564/2026  Rješenje o nasljeđivanju  IZRADA NACRTA RJEŠENJA   2026-04-20  U tijeku

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
```
<!-- END GENERATED: output -->

Da biste uložak zadali izravno umjesto od čestice, upotrijebite zajedno
`--unit-number` i `--main-book`, kao u gornjem primjeru. Ako znate naziv glavne
knjige (u pravilu naziv katastarske općine), ali ne i njezin broj, zadajte naziv
opcijom `--main-book-name` i alat će broj pronaći za vas:

```bash
uz uložak --broj-uloška 769 --naziv-glavne-knjige SAVAR --vlasnici
```

Posljednji stupac vlastovnice, **Upis**, kaže kako je svaki vlasnik dospio u
uložak: redni broj upisa, datum zaprimanja prijedloga i njegov broj dnevnika
(Z-broj). Uz `--all` alat ispod udjela ispisuje i zabilježbe upisane samo na tom
udjelu, na primjer ugovor o doživotnom uzdržavanju ili spor.

Da biste rezultat spremili kao datoteku, dodajte `--format json` i `--output` s
nazivom datoteke.

Za uvid u više uložaka odjednom stavite ih u datoteku i navedite je uz `--ulaz`.
Najlakša je JSON datoteka koju naredba [čestica](get-parcel.md) zapisuje za
popis čestica uz `--detalji registry`: alat uzima uložak svake pronađene čestice
i svaki uložak čita jednom. Možete pripremiti i CSV datoteku s dva stupca,
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

Otvorite Terminal u mapi u kojoj je datoteka i upišite:

```bash
uz uložak --ulaz parcels-found.json --vlasnici
```

<!-- BEGIN GENERATED: output uz uložak --ulaz parcels-found.json --vlasnici -->
```text
📄 Učitavam ZK uloške iz: parcels-found.json
📊 Pronađena 3 ZK uloška za obradu

                ZEMLJIŠNOKNJIŽNI ULOŽAK
 Broj uloška           657
 Glavna knjiga         SAVAR
 Institucija           Test Land Registry Office SAVAR
 Status                Aktivan
 Tip uloška            VLASNIČKI
 Zadnji broj dnevnika  Z-12345/2024

                                   VLASTOVNICA (LIST B)
 Udio  Vlasnik                Adresa                  OIB  Upis
 1/2   IVIĆ MARKO, SIN PETRA  TESTNA ULICA 15, SPLIT  -    1.1 · 2018-06-10 · Z-5678/2018
 1/2   IVIĆ ANA, KĆI PETRA    SAVAR                   -    2.1 · 2018-06-10 · Z-5678/2018

---

              ZEMLJIŠNOKNJIŽNI ULOŽAK
 Broj uloška           769
 Glavna knjiga         SAVAR
 Institucija           Zemljišnoknjižni odjel Zadar
 Status                Aktivan
 Tip uloška            VLASNIČKI
 Zadnji broj dnevnika  Z-27986/2025

                           VLASTOVNICA (LIST B)
 Udio  Vlasnik      Adresa     OIB          Upis
 4/8   Vlasnik 117  -          -            1.1 · 2012-04-05 · Z-3983/2012
 1/8   Vlasnik 119  -          -            3.1 · 2012-04-05 · Z-3983/2012
 1/8   Vlasnik 326  -          -            4.1 · 2012-04-05 · Z-3983/2012
 1/8   Vlasnik 116  Adresa 31  00000000036  5.2 · 2020-02-14 · Z-3937/2020
 1/24  Vlasnik 135  Adresa 10  00000000850  6.1 · 2018-03-21 · Z-6789/2018
 1/24  Vlasnik 327  Adresa 10  00000000868  7.1 · 2018-03-21 · Z-6789/2018
 1/24  Vlasnik 328  Adresa 32  00000000876  8.1 · 2018-03-21 · Z-6789/2018

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

                             VLASTOVNICA (LIST B)
 Udio  Vlasnik      Adresa     OIB          Upis
 1/4   Vlasnik 114  Adresa 75  00000000010  127.2 · 2026-05-14 · Z-15677/2026
 1/4   Vlasnik 115  Adresa 41  00000000028  128.1 · 2025-09-29 · Z-31325/2025
 1/4   Vlasnik 116  Adresa 31  00000000036  129.1 · 2025-09-29 · Z-31325/2025
 1/4   Vlasnik 116  Adresa 76  00000000036  133.1 · 2026-06-09 · Z-18444/2026

✓ Uspješno obrađena sva 3 ZK uloška
```
<!-- END GENERATED: output -->

Ulošci se ispisuju jedan za drugim, odvojeni crticama, svaki složen kao gore.
Odabir listova vrijedi za svaki uložak. Kad se jedan uložak ne može pročitati,
alat nastavlja s ostalima i na kraju navodi neuspjele pod **GREŠKE**; dodajte
`--stani-kod-greške` da bi stao kod prvog problema. Za dugačak popis spremite
rezultat kao datoteku pomoću `--oblik json` i `--datoteka`.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `--broj-uloška`, `-bu` `TEKST` | Broj zemljišnoknjižnog uloška (npr. '769') | Ne koristi se |
| `--glavna-knjiga`, `-gk` `CIJELI_BROJ` | ID glavne knjige (npr. 21277) | Ne koristi se |
| `--naziv-glavne-knjige`, `-ng` `TEKST` | Naziv glavne knjige (npr. SAVAR), umjesto identifikatora | Ne koristi se |
| `--od-čestice`, `-oc` `TEKST` | Dohvati ZK uložak prema broju čestice | Ne koristi se |
| `--općina`, `-ko` `TEKST` | Naziv ili šifra općine (obavezno uz --from-parcel) | Ne koristi se |
| `--vlasnici`, `-vl` | Prikaži podatke o vlasništvu (list B) | Nije uključeno |
| `--čestice`, `-ce` | Prikaži sve čestice u ulošku (list A) | Nije uključeno |
| `--tereti`, `-te` | Prikaži terete (list C) | Nije uključeno |
| `--plombe`, `-pl` | Razriješi detalje plombi - jedan dodatni zahtjev po plombi | Nije uključeno |
| `--sve`, `-sv` | Prikaži sve listove | Nije uključeno |
| `--ulaz`, `-ul` `PUTANJA` | Datoteka (CSV ili JSON) s ulošcima za čitanje, ili rezultat naredbe čestica za popis čestica | Ne koristi se |
| `--oblik`, `-ob` | Format izlaza (`tablica`, `json`, `csv`) | Koristi se `tablica` |
| `--datoteka` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--nastavi-kod-greške` / `--stani-kod-greške` | Nastavi obradu nakon grešaka (zadano: nastavi) | Koristi se `--nastavi-kod-greške` |
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
- [čestica](get-parcel.md) uz `--detalji registry` ispisuje uloške više čestica,
  spremne za `--ulaz`.
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

  Jedan uložak, zadan brojem i glavnom knjigom ili pronađen iz čestice; ili
  popis uložaka iz datoteke uz --ulaz: CSV ili JSON s lr_unit_number i
  main_book_id, ili JSON koji naredba čestica zapisuje za popis čestica.

  Primjeri:
    # Prema broju uloška i ID-u glavne knjige
    uz uložak --broj-uloška 769 --glavna-knjiga 21277

    # Prema broju uloška i nazivu glavne knjige (pronalazi se pretragom glavnih knjiga)
    uz uložak --broj-uloška 769 --naziv-glavne-knjige SAVAR

    # Prema čestici (automatsko pronalaženje)
    uz uložak --od-čestice 279/6 -ko SAVAR

    # Samo podaci o vlasništvu
    uz uložak -bu 769 -gk 21277 --vlasnici

    # Svi listovi
    uz uložak -oc 279/6 -ko SAVAR --sve

    # Izvoz u JSON
    uz uložak -bu 769 -gk 21277 --oblik json --datoteka lr-unit.json

    # Više uložaka iz datoteke, svi listovi svakoga
    uz uložak --ulaz lr_units.csv --sve

    # Ulošci popisa čestica (lanac naredbi)
    uz čestica "103/2,45,396/1" -ko SAVAR --detalji registry --oblik json -dt parcels.json
    uz uložak --ulaz parcels.json --vlasnici

  ⚠️  Demonstracijski projekt: prije uporabe bilo kojeg poslužitelja osim
  priloženog probnog provjerite svoja prava na njegovu uporabu; koristite na
  vlastitu odgovornost

Opcije:
  -bu, --broj-uloška TEKST        Broj zemljišnoknjižnog uloška (npr. '769')
  -gk, --glavna-knjiga CIJELI_BROJ
                                  ID glavne knjige (npr. 21277)
  -ng, --naziv-glavne-knjige TEKST
                                  Naziv glavne knjige (npr. SAVAR), umjesto
                                  identifikatora
  -oc, --od-čestice TEKST         Dohvati ZK uložak prema broju čestice
  -ko, --općina TEKST             Naziv ili šifra općine (obavezno uz --from-
                                  parcel)
  -vl, --vlasnici                 Prikaži podatke o vlasništvu (list B)
  -ce, --čestice                  Prikaži sve čestice u ulošku (list A)
  -te, --tereti                   Prikaži terete (list C)
  -pl, --plombe                   Razriješi detalje plombi - jedan dodatni
                                  zahtjev po plombi
  -sv, --sve                      Prikaži sve listove
  -ul, --ulaz PUTANJA             Datoteka (CSV ili JSON) s ulošcima za čitanje,
                                  ili rezultat naredbe čestica za popis čestica
  -ob, --oblik [tablica|json|csv]
                                  Format izlaza
  --datoteka PUTANJA              Spremi izlaz u datoteku
  --nastavi-kod-greške / --stani-kod-greške
                                  Nastavi obradu nakon grešaka (zadano: nastavi)
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
