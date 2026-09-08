<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/search-municipality.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega i ne smije se spajati na službeni katastar ni zemljišne knjige Republike Hrvatske. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.1.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Matični broj katastarske općine

Svaka katastarska općina (k.o.) ima matični broj, koji alat ispisuje kao šifru.
Ova je naredba pronalazi iz naziva ili ispisuje općine koje pripadaju nekom
katastarskom uredu.

## Kada vam ovo treba

- Dvije općine imaju isti ili sličan naziv i želite biti sigurni koju gledate.
- Naredba je odbila naziv općine i umjesto njega trebate šifru.
- Želite znati kojem područnom uredu za katastar i odjelu općina pripada.

## Prije nego počnete

Trebate naziv općine ili njegov dio.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   cadastral search-municipality SAVAR
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output cadastral search-municipality SAVAR -->
   ```text
   Pronađeno 1 općina (search='SAVAR'):

   +---------+---------+--------+---------+
   |   Šifra | Naziv   |   Ured |   Odjel |
   +=========+=========+========+=========+
   |  334979 | SAVAR   |    114 |     116 |
   +---------+---------+--------+---------+
   ```
   <!-- END GENERATED: output -->

4. **Šifra** je matični broj koji svakoj drugoj naredbi možete zadati iza `-m`.
   **Ured** i **Odjel** su brojevi katastarskog ureda i njegova odjela.

## Što možete odabrati

Da ispišete sve općine jednog ureda, zadajte broj ureda uz `--office`. Možete ga
kombinirati s nazivom da suzite popis:

```bash
cadastral search-municipality --office 114
```

Ako samo želite znati koliko se općina podudara, dodajte `--count-only`. Da
popis spremite u datoteku, dodajte `--format csv` i `--output` s nazivom
datoteke.

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `[SEARCH_TERM]` | Neobavezno. Vrijednost koju upisujete odmah iza naziva naredbe | Ne koristi se |
| `--office`, `-o` `TEXT` | Filtriraj prema ID-u katastarskog ureda (npr. 114) | Ne koristi se |
| `--department`, `-d` `TEXT` | Filtriraj prema ID-u odjela (npr. 116) | Ne koristi se |
| `--format`, `-f` | Format izlaza (`table`, `json`, `csv`) | Koristi se `table` |
| `--output`, `-out` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
| `--count-only` | Prikaži samo broj | Nije uključeno |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ako se ništa ne podudara, vidjet ćete ovo:

<!-- BEGIN GENERATED: output cadastral search-municipality NOWHERE -->
```text
✗ Greška: Nema pronađenih općina za 'NOWHERE'
```
<!-- END GENERATED: output -->

Pokušajte s kraćim dijelom naziva, ili ispišite cijeli ured uz `--office` i
potražite naziv na popisu. Ostale poruke objašnjene su na [stranici o
greškama](../errors.md).

## Povezane stranice

- [list-municipalities](list-municipalities.md) radi isti posao s drukčijim
  filtrima.
- [list-offices](list-offices.md) prikazuje brojeve ureda za `--office`.
- [search](search.md) je mjesto gdje pronađenu šifru koristite.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `cadastral search-municipality --help`:

```text
Uporaba: cadastral search-municipality [OPTIONS] [SEARCH_TERM]

  Pretraživanje i filtriranje općina.

  Primjeri:
    cadastral search-municipality SAVAR
    cadastral search-municipality --office 114
    cadastral search-municipality --office 114 --department 116
    cadastral search-municipality SAVAR --office 114

Opcije:
  -o, --office TEXT              Filtriraj prema ID-u katastarskog ureda (npr.
                                 114)
  -d, --department TEXT          Filtriraj prema ID-u odjela (npr. 116)
  -f, --format [table|json|csv]  Format izlaza
  -out, --output PUTANJA         Spremi izlaz u datoteku
  --count-only                   Prikaži samo broj
  --help                         Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
