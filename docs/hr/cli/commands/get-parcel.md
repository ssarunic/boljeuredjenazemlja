<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/get-parcel.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega i ne smije se spajati na službeni katastar ni zemljišne knjige Republike Hrvatske. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.1.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Sve što katastar ima o čestici

Potpuni katastarski zapis jedne čestice: položaj, površina, način uporabe
zemljišta, posjedovni list s osobama koje katastar vodi i broj zemljišnoknjižnog
uloška u kojem su pravni vlasnici.

## Kada vam ovo treba

- Pripremate ugovor i trebate površinu, način uporabe zemljišta i katastarsko
  stanje čestice na jednom mjestu.
- Želite usporediti koga katastar vodi kao posjednika s onim koga zemljišna
  knjiga vodi kao vlasnika.
- Trebate broj zemljišnoknjižnog uloška čestice da biste pročitali njegove
  vlasnike i terete.

## Prije nego počnete

Trebate broj čestice i katastarsku općinu, po nazivu ili šifri, kao za
[search](search.md).

Dok čitate, imajte na umu jednu razliku. Katastar vodi posjednike; zemljišna
knjiga vodi vlasnike. Često su to iste osobe, ali ne uvijek, a samo je zemljišna
knjiga dokaz vlasništva. Ova stranica prikazuje katastar. Stranica
[get-lr-unit](get-lr-unit.md) prikazuje zemljišnu knjigu.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   cadastral get-parcel 103/2 -m SAVAR --show-owners
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output cadastral get-parcel 103/2 -m SAVAR --show-owners -->
   ```text
   INFORMACIJE O ČESTICI
   =====================
     Broj čestice             103/2
     ID čestice               6564817
     Općina                   SAVAR (334979)
     Adresa                   POLJE
     Površina                 1,200 m²
     Dozvoljeno građenje      Ne
     Katastar/ZK usklađeni    Da


   NAČIN UPORABE
   =============
     Vrsta        Površina (m²)    Postotak    Zgrade
     MASLINJAK            1,200      100.0%    Ne


   POSJEDOVNI LIST (katastar) (2 posjednika)
   =========================================
   Napomena: posjednici u katastru mogu se razlikovati od upisanih vlasnika. Za vlasnike iz zemljišnih
   knjiga koristite: cadastral get-lr-unit
     Naziv                    Vlasništvo    Adresa
     IVIĆ MARKO, SIN PETRA           N/D    TESTNA ULICA 15, SPLIT
     IVIĆ ANA, KĆI PETRA             N/D    SAVAR


   ZEMLJIŠNA KNJIGA
   ================
     Broj uloška      657
     Glavna knjiga    N/D
     Institucija      N/D
     Status           Neaktivno
     Provjereno       Ne


   DODATNE INFORMACIJE
   ===================
     URL karte        https://oss.uredjenazemlja.hr/map?center=380616.77,4880907.83&zoom=19&layers=DO
                      F5_2023_2024,DKP_CESTICE,DKP_KATASTARSKE_OPCINE,zupanija,ulica,kucni_broj
     List pregleda    4
   ```
   <!-- END GENERATED: output -->

4. Zaslon ima pet dijelova. **INFORMACIJE O ČESTICI** određuje česticu; redak
   **Katastar/ZK usklađeni** kaže slažu li se katastar i zemljišna knjiga o
   njoj. **NAČIN UPORABE** dijeli površinu po katastarskoj kulturi. **POSJEDOVNI
   LIST (katastar)** ispisuje posjednike koje katastar vodi, s udjelom gdje ga
   katastar ima. **ZEMLJIŠNA KNJIGA** daje broj zemljišnoknjižnog uloška (**Broj
   uloška**) koji zatim možete potražiti. **DODATNE INFORMACIJE** sadrži
   poveznicu koja otvara česticu na javnoj karti.

5. Gdje vrijednost nije upisana, alat ispisuje **N/D**. U posjedovnom listu to
   je često: katastar nerijetko vodi tko posjeduje, a ne vodi udio.

## Što možete odabrati

Bez `--show-owners` posjedovni list se izostavlja i zaslon je kraći. Dodajte ga
kad god želite vidjeti osobe.

`--detail` sužava zaslon na jedan dio: `basic` samo za identifikaciju, `owners`
za posjedovni list, `landuse` za podjelu po namjeni, `geometry` za koordinate
granice, `full` za sve.

```bash
cadastral get-parcel 103/2 -m SAVAR --detail landuse
```

Da zapis spremite u datoteku, dodajte `--format json` i `--output` s nazivom
datoteke. Taj oblik koristite kad podatke želite priložiti spisu ili
proslijediti kolegi.

```bash
cadastral get-parcel 103/2 -m SAVAR --show-owners --format json --output parcel-103-2.json
```

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `PARCEL_NUMBER` | Vrijednost koju upisujete odmah iza naziva naredbe, bez naziva ispred nje | Obavezno |
| `--municipality`, `-m` `TEXT` | Naziv ili šifra općine | Obavezno |
| `--detail` | Razina detalja (`basic`, `full`, `owners`, `landuse`, `geometry`) | Koristi se `full` |
| `--show-owners` | Uključi vlasničke podatke | Nije uključeno |
| `--show-geometry` | Uključi koordinate granica | Nije uključeno |
| `--format`, `-f` | Format izlaza (`table`, `json`, `yaml`, `csv`) | Koristi se `table` |
| `--output`, `-o` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako općina nije prepoznata, alat to kaže i staje:

<!-- BEGIN GENERATED: output cadastral get-parcel 103/2 -m NOWHERE -->
```text
✗ Greška: Općina 'NOWHERE' nije pronađena
```
<!-- END GENERATED: output -->

Provjerite pravopis ili umjesto naziva upotrijebite šifru. Možete je pronaći
naredbom [search-municipality](search-municipality.md).

Ako čestica nije pronađena, provjerite broj na svom dokumentu, uključujući dio
iza kose crte. Ostale poruke objašnjene su na [stranici o
greškama](../errors.md).

## Povezane stranice

- [get-lr-unit](get-lr-unit.md) čita zemljišnoknjižni uložak čiji se broj
  pojavljuje pod naslovom zemljišne knjige.
- [search](search.md) je kraći oblik ove naredbe.
- [get-geometry](get-geometry.md) daje granicu čestice za kartu.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `cadastral get-parcel --help`:

```text
Uporaba: cadastral get-parcel [OPTIONS] PARCEL_NUMBER

  Dohvat potpunih podataka o čestici s podacima o vlasništvu.

  Primjeri:
    cadastral get-parcel 103/2 -m SAVAR
    cadastral get-parcel 103/2 -m 334979 --show-owners
    cadastral get-parcel 103/2 -m 334979 --detail owners
    cadastral get-parcel 103/2 -m 334979 --format json -o parcel.json

Opcije:
  -m, --municipality TEXT         Naziv ili šifra općine  [obavezno]
  --detail [basic|full|owners|landuse|geometry]
                                  Razina detalja
  --show-owners                   Uključi vlasničke podatke
  --show-geometry                 Uključi koordinate granica
  -f, --format [table|json|yaml|csv]
                                  Format izlaza
  -o, --output PUTANJA            Spremi izlaz u datoteku
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
