<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/cache-clear.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega i ne smije se spajati na službeni katastar ni zemljišne knjige Republike Hrvatske. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.1.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Brisanje pohranjenih podataka o granicama

Briše podatke o granicama jedne općine, ili svih općina, s vašeg računala. Alat
će podatke ponovno preuzeti kada sljedeći put zatražite granicu.

## Kada vam ovo treba

- Granice općine su se promijenile i želite da alat dohvati aktualne podatke.
- Želite osloboditi prostor na disku.

## Prije nego počnete

Odlučite želite li ukloniti jednu općinu ili sve. Ništa drugo nije pogođeno:
pohranjeni podaci samo su kopija onoga što poslužitelj može ponovno poslati.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter. Zamijenite SAVAR općinom koju
   želite ukloniti.

   ```bash
   cadastral cache clear -m SAVAR --force
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output cadastral cache clear -m SAVAR --force -->
   ```text
   ✓ Očišćena općina 334979 (oslobođeno 0.7 KB)
   ```
   <!-- END GENERATED: output -->

4. Alat potvrđuje što je uklonio i koliko je prostora oslobodio.

## Što možete odabrati

`--force` preskače pitanje koje alat inače postavlja prije brisanja. Bez njega
alat traži potvrdu; upišite `y` i pritisnite Enter za nastavak, ili samo
pritisnite Enter da podatke zadržite.

Da biste uklonili sve, umjesto naziva općine upotrijebite `--all`:

```bash
cadastral cache clear --all
```

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `--municipality`, `-m` `TEXT` | Očisti specifičnu općinu | Ne koristi se |
| `--all`, `-a` | Očisti svu predmemoriju | Nije uključeno |
| `--force`, `-f` | Preskoči potvrdu | Nije uključeno |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako navedete općinu koja nije pohranjena, alat vam to kaže i ne uklanja ništa:

<!-- BEGIN GENERATED: output cadastral cache clear -m LUKA --force -->
```text
Općina 334731 nije u predmemoriji
```
<!-- END GENERATED: output -->

Ako ne navedete ni općinu ni `--all`, vidjet ćete ovo:

<!-- BEGIN GENERATED: output cadastral cache clear -->
```text
✗ Greška: Potrebno je --municipality ili --all

Pokušajte: cadastral cache clear --help
```
<!-- END GENERATED: output -->

## Povezane stranice

- [cache-list](cache-list.md) pokazuje što je pohranjeno prije nego što išta
  uklonite.
- [download-gis](download-gis.md) ponovno preuzima općinu.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `cadastral cache clear --help`:

```text
Uporaba: cadastral cache clear [OPTIONS]

  Brisanje predmemoriranih GIS podataka.

  Primjeri:
    cadastral cache clear --municipality 334979
    cadastral cache clear --all
    cadastral cache clear -m SAVAR --force

Opcije:
  -m, --municipality TEXT  Očisti specifičnu općinu
  -a, --all                Očisti svu predmemoriju
  -f, --force              Preskoči potvrdu
  --help                   Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
