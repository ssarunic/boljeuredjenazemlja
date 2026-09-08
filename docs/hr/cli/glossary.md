<!-- BEGIN GENERATED: banner -->
[English](../../en/cli/glossary.md) | **Hrvatski**

> **Samo probni podaci.** Ovaj je alat demonstracija. Radi s probnim poslužiteljem koji dolazi uz njega i ne smije se spajati na službeni katastar ni zemljišne knjige Republike Hrvatske. Ništa na ovoj stranici nisu stvarni podaci o nekretninama.
>
> Izrađeno iz `cadastral 0.1.0` skriptom `scripts/build_docs.py`. Tekst između generiranih oznaka ponovno se ispisuje pri svakoj izradi.
> Ova je stranica izrađena iz engleskog izvornika i datoteke `po/docs-hr.po`. Ne uređujte je ručno.
<!-- END GENERATED: banner -->

# Pojmovnik

Riječi katastra i zemljišne knjige te gdje ih alat prikazuje. Pojmovi su
navedeni onako kako stoje na službenim ispravama.

| Pojam | Što znači | Gdje ga vidite u alatu |
|---|---|---|
| Katastarska čestica (k.č.) | Čestica: jedan numerirani dio zemljišta u katastru. | Broj čestice koji upisujete iza `search`, `get-parcel` i `get-geometry`. |
| Katastarska općina (k.o.) | Katastarska općina kojoj čestica pripada. Svaka ima naziv i matični broj, koji alat ispisuje kao šifru. | Vrijednost iza `-m` u većini naredbi. [search-municipality](commands/search-municipality.md) pronalazi matični broj. |
| Posjedovni list | Posjedovni list katastra: tko posjeduje česticu prema katastru. Nije dokaz vlasništva. | [get-parcel](commands/get-parcel.md) uz `--show-owners`. |
| Posjednik | Posjednik upisan u katastru. | Reci posjedovnog lista na [get-parcel](commands/get-parcel.md). |
| Zemljišnoknjižni uložak (ZK uložak) | Sadrži pravno stanje nekretnine; vodi ga zemljišnoknjižni odjel općinskog suda. | [get-lr-unit](commands/get-lr-unit.md). Njegov broj pojavljuje se i na [get-parcel](commands/get-parcel.md) te u rezultatima grupne obrade. |
| Glavna knjiga | Svezak zemljišne knjige koji sadrži uloške jedne katastarske općine. | `--main-book` na [get-lr-unit](commands/get-lr-unit.md). |
| Posjedovnica (list A) | List A: čestice koje čine uložak. | Prva tablica iza zaglavlja uloška na [get-lr-unit](commands/get-lr-unit.md). |
| Vlastovnica (list B) | List B: vlasnici i njihovi udjeli. | `--show-owners` na [get-lr-unit](commands/get-lr-unit.md). |
| Teretovnica (list C) | List C: založna prava (hipoteke), služnosti, stvarni tereti i zabilježbe. | `--show-encumbrances` na [get-lr-unit](commands/get-lr-unit.md). |
| Suvlasnički udio | Udio u suvlasništvu, zapisan kao razlomak, na primjer 1/2. | Stupac udjela lista B. |
| Plomba | Naznaka da je prijedlog za upis zaprimljen, a još nije riješen. Uložak se može promijeniti. | Redak s plombama na [get-lr-unit](commands/get-lr-unit.md); `--plombe-detail` pokazuje o čemu je svaki prijedlog. |
| Dnevnik, broj Z | Dnevnik zemljišne knjige i poslovni broj (Z-broj) prijedloga za upis. | Zadnji broj dnevnika na [get-lr-unit](commands/get-lr-unit.md) i poslovni brojevi plombi. |
| Etažno vlasništvo | Vlasništvo posebnog dijela nekretnine (stana ili poslovnog prostora), povezano sa suvlasničkim dijelom cijele nekretnine. | Redak tipa uloška u zaglavlju uloška na [get-lr-unit](commands/get-lr-unit.md). |
| Kultura, način uporabe zemljišta | Način uporabe zemljišta upisan u katastru, na primjer oranica, pašnjak ili voćnjak. | Tablica načina uporabe na [get-parcel](commands/get-parcel.md). |
| OIB | Osobni identifikacijski broj fizičke ili pravne osobe. | Stupac OIB lista B, kada ga zemljišna knjiga ima. |
| Područni ured za katastar | Područni ured za katastar. | [list-offices](commands/list-offices.md). |
| Granica čestice | Granica čestice zapisana koordinatama. | [get-geometry](commands/get-geometry.md) i [download-gis](commands/download-gis.md). |
| HTRS96/TM (EPSG:3765) | Službeni koordinatni sustav Hrvatske, koristi se za sve granice. | Svaka koordinata koju alat ispiše. |
