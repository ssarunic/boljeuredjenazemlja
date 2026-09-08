<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/download-gis.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega i ne smije se spajati na službeni katastar ni zemljišne knjige Republike Hrvatske. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.1.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Preuzimanje podataka o granicama cijele općine

Dohvaća datoteku s granicama svih čestica jedne katastarske općine i raspakirava
je u mapu po vašem izboru, za uporabu u kartografskom programu.

## Kada vam ovo treba

- Geodet ili arhitekt traži granice čestica nekog područja, a ne samo jedne
  čestice.
- Želite otvoriti cijelu općinu u kartografskom programu kao što je QGIS.

## Prije nego počnete

Trebate općinu, po nazivu ili šifri, i naziv mape u koju datoteke trebaju otići.
Mapa se stvara ako ne postoji. Datoteke su u obliku GML, tekstualnom zapisu
geografskih podataka koji kartografski programi čitaju.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   cadastral download-gis SAVAR --output ./gis_data
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output cadastral download-gis SAVAR --output ./gis_data -->
   ```text
   Preuzimam GIS podatke za općinu 334979...
   ✓ Preuzeto: ko-334979.zip (0.7 KB)
   ✓ Raspakirano u: gis_data

   Datoteke:
     • katastarske_cestice.gml (0.0 MB)

   Ukupno čestica: 3

   Za dohvaćanje geometrije čestice: cadastral get-geometry <čestica> -m 334979
   ```
   <!-- END GENERATED: output -->

4. Alat javlja koju je datoteku dohvatio, u koju ju je mapu raspakirao i koliko
   čestica sadrže podaci. Mapa sada sadrži datoteku `katastarske_cestice.gml` sa
   svim granicama čestica.

## Što možete odabrati

`--output` je obavezan i imenuje mapu. Dodajte `--no-extract` da zadržite samo
preuzetu ZIP datoteku bez raspakiravanja. Dodajte `--clear-cache` za novo
preuzimanje čak i ako alat već ima podatke iz ranijeg pokretanja.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `MUNICIPALITY` | Vrijednost koju upisujete odmah iza naziva naredbe, bez naziva ispred nje | Obavezno |
| `--output`, `-o` `PUTANJA` | Izlazni direktorij | Obavezno |
| `--extract` / `--no-extract` | Raspakiraj ZIP datoteku | Koristi se `--extract` |
| `--clear-cache` | Najprije očisti predmemorirane podatke | Nije uključeno |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako zaboravite `--output`, alat staje i kaže vam da opcija nedostaje:

<!-- BEGIN GENERATED: output cadastral download-gis SAVAR -->
```text
Uporaba: python -m cadastral_cli download-gis [OPTIONS] MUNICIPALITY
Za pomoć pokrenite 'python -m cadastral_cli download-gis --help'.

Greška: Nedostaje opcija '--output' / '-o'.
```
<!-- END GENERATED: output -->

Dodajte je s nazivom mape.

Ako preuzimanje ne uspije, probni poslužitelj možda nije pokrenut. Obratite se
osobi koja je instalirala alat. Ostale poruke objašnjene su na [stranici o
greškama](../errors.md).

## Povezane stranice

- [get-geometry](get-geometry.md) daje granicu jedne čestice.
- [cache-clear](cache-clear.md) briše preuzete podatke s vašeg računala.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `cadastral download-gis --help`:

```text
Uporaba: cadastral download-gis [OPTIONS] MUNICIPALITY

  Preuzimanje potpunih GIS podataka za općinu.

  Primjeri:
    cadastral download-gis 334979 --output ./gis_data
    cadastral download-gis SAVAR --output ./savar_gis --extract
    cadastral download-gis 334979 -o ./data --clear-cache

Opcije:
  -o, --output PUTANJA      Izlazni direktorij  [obavezno]
  --extract / --no-extract  Raspakiraj ZIP datoteku
  --clear-cache             Najprije očisti predmemorirane podatke
  --help                    Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
