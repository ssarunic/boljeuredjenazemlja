<!-- BEGIN GENERATED: banner -->
[English](../../../en/cli/commands/list-offices.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega i ne smije se spajati na službeni katastar ni zemljišne knjige Republike Hrvatske. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.1.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Popis katastarskih ureda

Prikazuje sve područne urede za katastar s njihovim brojevima. Broj vam treba da
biste ispisali općine nekog ureda.

## Kada vam ovo treba

- Želite znati koji je ured nadležan za neko područje.
- Druga naredba traži broj ureda, a vi ga ne znate.

## Prije nego počnete

Ništa. Ova naredba ne traži unos.

## Korak po korak

1. Otvorite Terminal.
2. Upišite sljedeći redak i pritisnite Enter:

   ```bash
   cadastral list-offices
   ```

3. Vidjet ćete otprilike ovo:

   <!-- BEGIN GENERATED: output cadastral list-offices -->
   ```text
   15 katastarskih ureda u Hrvatskoj:

   +------+------------------------------------------+
   |   ID | Naziv                                    |
   +======+==========================================+
   |   35 | PODRUČNI URED ZA KATASTAR KRAPINA        |
   +------+------------------------------------------+
   |   57 | PODRUČNI URED ZA KATASTAR ZAGREB         |
   +------+------------------------------------------+
   |   72 | PODRUČNI URED ZA KATASTAR RIJEKA         |
   +------+------------------------------------------+
   |   89 | PODRUČNI URED ZA KATASTAR SPLIT          |
   +------+------------------------------------------+
   |  104 | PODRUČNI URED ZA KATASTAR DUBROVNIK      |
   +------+------------------------------------------+
   |  114 | PODRUČNI URED ZA KATASTAR ZADAR          |
   +------+------------------------------------------+
   |  130 | PODRUČNI URED ZA KATASTAR ŠIBENIK        |
   +------+------------------------------------------+
   |  145 | PODRUČNI URED ZA KATASTAR PULA           |
   +------+------------------------------------------+
   |  156 | PODRUČNI URED ZA KATASTAR OSIJEK         |
   +------+------------------------------------------+
   |  171 | PODRUČNI URED ZA KATASTAR VARAŽDIN       |
   +------+------------------------------------------+
   |  183 | PODRUČNI URED ZA KATASTAR SLAVONSKI BROD |
   +------+------------------------------------------+
   |  198 | PODRUČNI URED ZA KATASTAR SISAK          |
   +------+------------------------------------------+
   |  209 | PODRUČNI URED ZA KATASTAR KARLOVAC       |
   +------+------------------------------------------+
   |  224 | PODRUČNI URED ZA KATASTAR GOSPIĆ         |
   +------+------------------------------------------+
   |  235 | PODRUČNI URED ZA KATASTAR BJELOVAR       |
   +------+------------------------------------------+
   ```
   <!-- END GENERATED: output -->

4. **ID** je broj ureda. Koristite ga uz `--office` na stranici
   [list-municipalities](list-municipalities.md).

## Što možete odabrati

Da popis spremite u datoteku, dodajte `--format csv` i `--output` s nazivom
datoteke:

```bash
cadastral list-offices --format csv --output offices.csv
```

<!-- BEGIN GENERATED: options -->
| Upišite | Što radi | Ako izostavite |
|---|---|---|
| `--format`, `-f` | Format izlaza (`table`, `json`, `csv`) | Koristi se `table` |
| `--output`, `-o` `PUTANJA` | Spremi izlaz u datoteku | Ne koristi se |
<!-- END GENERATED: options -->

## Ako nešto ne uspije

Ova naredba ne uspijeva samo kad alat ne može doseći probni poslužitelj. Poruka
je objašnjena na [stranici o greškama](../errors.md); zamolite osobu koja je
instalirala alat da pokrene poslužitelj.

## Povezane stranice

- [list-municipalities](list-municipalities.md) koristi broj ureda.
- [info](info.md) pokazuje s kojim poslužiteljem alat razgovara.

<details>
<summary>Tehnički detalji</summary>

<!-- BEGIN GENERATED: synopsis -->
Ovo ispisuje `cadastral list-offices --help`:

```text
Uporaba: cadastral list-offices [OPTIONS]

  Popis svih katastarskih ureda u Hrvatskoj.

  Primjer:
    cadastral list-offices
    cadastral list-offices --format json

Opcije:
  -f, --format [table|json|csv]  Format izlaza
  -o, --output PUTANJA           Spremi izlaz u datoteku
  --help                         Prikaži ovu poruku i izađi.
```
<!-- END GENERATED: synopsis -->

</details>
