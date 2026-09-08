<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/get-geometry.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega i ne smije se spajati na službeni katastar ni zemljišne knjige Republike Hrvatske. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.1.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Granica čestice za kartu

Ispisuje lomne točke čestice u službenom hrvatskom koordinatnom sustavu, tako da
je geodet ili kartografski program može nacrtati. Može izračunati i površinu iz
tih točaka.

## Kada vam ovo treba

- Želite geodetu ili arhitektu predati točan obris čestice.
- Želite usporediti površinu izračunatu iz granice s površinom upisanom u
  katastru.
- Želite smjestiti česticu na kartu u programu koji razumije geografske podatke.

## Prije nego počnete

Trebate broj čestice i katastarsku općinu. Podaci o granicama cijele općine
preuzimaju se jednom i čuvaju na vašem računalu; prvi dohvat u nekoj općini
stoga traje dulje od sljedećih.

Koordinate su u sustavu HTRS96/TM (EPSG:3765), službenoj projekciji za Hrvatsku.
To nisu stupnjevi kakve vidite u automobilskoj navigaciji. Kartografski program
znat će što s njima.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   cadastral get-geometry 103/2 -m SAVAR --show-stats
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output cadastral get-geometry 103/2 -m SAVAR --show-stats -->
   ```text
   STATISTIKA GEOMETRIJE
   =====================
     Čestica               103/2
     Koordinatni sustav    EPSG:3765
     Vrhovi                5
     Površina (GIS)        1200.00 m²

     Granični okvir
       Min X               380,596.77 m
       Min Y               4,880,892.83 m
       Max X               380,636.77 m
       Max Y               4,880,922.83 m
       Širina              40.00 m
       Visina              30.00 m

   POLYGON((380596.77 4880892.83, 380636.77 4880892.83, 380636.77 4880922.83, 380596.77 4880922.83,
   380596.77 4880892.83))
   ```
   <!-- END GENERATED: output -->

4. **STATISTIKA GEOMETRIJE** sažima oblik: broj lomnih točaka (**Vrhovi**),
   površinu izračunatu iz njih (**Površina (GIS)**) i najmanji pravokutnik koji
   obuhvaća česticu (**Granični okvir**). Zadnji blok je sama granica, zapisana
   kao poligon u standardnom tekstualnom obliku. Svaki par brojeva jedna je
   lomna točka.

## Što možete odabrati

`--format` bira oblik granice. `wkt` je standardni tekstualni oblik prikazan
gore. `geojson` je oblik koji čita većina web karata. `csv` daje jednu lomnu
točku po retku za tablicu. `json` daje iste podatke za druge programe.

Da biste granicu nekome predali, zapišite je u datoteku pomoću `--output`.
GeoJSON datoteku možete povući na mnoge mrežne preglednike karata:

```bash
cadastral get-geometry 103/2 -m SAVAR --format geojson --output parcel-103-2.geojson
```

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `PARCEL_NUMBER` | Vrijednost koju upisujete odmah iza naziva naredbe, bez naziva ispred nje | Obavezno |
| `--municipality`, `-m` `TEXT` | Naziv ili šifra općine | Obavezno |
| `--format`, `-f` | Format izvoza (`wkt`, `geojson`, `csv`, `json`) | Koristi se `wkt` |
| `--output`, `-o` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--show-stats` | Uključi statistiku geometrije | Nije uključeno |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako čestice nema u podacima o granicama općine, vidjet ćete ovo:

<!-- BEGIN GENERATED: output cadastral get-geometry 999 -m SAVAR -->
```text
✗ Greška: Geometrija nije pronađena za česticu '999'

Napomena: GIS podaci moraju biti prvo preuzeti (to se događa automatski)
```
<!-- END GENERATED: output -->

Podaci o granicama i katastar nisu uvijek usklađeni; prvo provjerite česticu
naredbom [search](search.md).

Ako se podaci o granicama općine ne mogu preuzeti, pitajte osobu koja je
instalirala alat je li probni poslužitelj pokrenut. Ostale poruke objašnjene su
na [stranici o greškama](../errors.md).

## Povezane stranice

- [download-gis](download-gis.md) preuzima podatke o granicama cijele općine.
- [cache-list](cache-list.md) pokazuje koje su općine već na vašem računalu.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `cadastral get-geometry --help`:

```text
Uporaba: cadastral get-geometry [OPTIONS] PARCEL_NUMBER

  Dohvat koordinata granica čestice za GIS integraciju.

  Primjeri:
    cadastral get-geometry 103/2 -m SAVAR
    cadastral get-geometry 103/2 -m 334979 --format wkt
    cadastral get-geometry 103/2 -m 334979 --format geojson -o parcel.geojson
    cadastral get-geometry 103/2 -m 334979 --format csv -o coords.csv

Opcije:
  -m, --municipality TEXT         Naziv ili šifra općine  [obavezno]
  -f, --format [wkt|geojson|csv|json]
                                  Format izvoza
  -o, --output PUTANJA            Spremi izlaz u datoteku
  --show-stats                    Uključi statistiku geometrije
  --help                          Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
