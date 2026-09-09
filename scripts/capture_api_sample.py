#!/usr/bin/env python3
"""Re-fetch the raw API sample that specs/api-coverage-specification.md is based on.

Writes one raw JSON file per request into RAW_DIR, untouched, so that
``scripts/redact_capture.py`` can regenerate the redacted fixtures and the
mock-server data sets from it. The raw files contain personal data: keep them
out of the repository (write them to a temporary directory).

The script never runs against a server it was not told about: the base URL
must be given explicitly with ``--base-url`` (``CADASTRAL_API_BASE_URL`` in the
environment or in ``.env`` is ignored on purpose). Point it at the mock
server to regenerate the sample from the mock, or at another server only with
the authorisation its terms of service require; see docs/legal.md.

Usage:
    python scripts/capture_api_sample.py --base-url http://localhost:8000 /tmp/capture

Sample (section 2 of the specification): 59 parcels of k.o. Savar (334979),
including six building parcels, every land-registry unit they reference, one
historical-overview call, the condominium unit 13998 of main book 30783, the
search probes for the building-parcel spelling, one possession-sheet search,
one main-book search, one books-of-DC search and the offices list.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "api" / "src"))

from cadastral_api.models.entities import LandRegistryUnitDetailed, ParcelInfo  # noqa: E402
from cadastral_api.utils import normalize_parcel_number, parse_file_number  # noqa: E402

from cadastral_api import CadastralAPIClient  # noqa: E402

MUNICIPALITY = "334979"
PARCELS = """35/1.ZGR 1072/12 37/2.ZGR 56/.ZGR 70 353 373/18 411/1 427/1 427/2 427/5 469/4 474
490 593 594/6 611/6 611/33 659 660/4 916/1 942/3 951/3 973 980/3 1000/1 1021/2 1029/1 1089/2
1153/1 1133 35/5.ZGR 1092 1131/1 199/2 1139/1 375 954 1067 1072/6 1073/1 1086/1 1129 1141
1139/4 221/7 469/1 118/4 192/3 267/6 279/6 1090 1098/1 1110/1 1111/1 1122/1 1131/6 1198
35/4.ZGR 35/2.ZGR""".split()
SEARCH_PROBES = [
    "1072/1", "35", "35/1", "*35/1", "35/1 ZGR", "35/1.ZGR", "35/1ZGR", "ZGR", "56", "37/2",
]
CONDOMINIUM = ("13998", "30783")


def safe(text: str) -> str:
    return text.replace("/", "_").replace("*", "star").replace(" ", "-")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("raw_dir", type=Path, help="directory to write the raw responses into")
    parser.add_argument(
        "--base-url", required=True, help="server to sample (required; the environment is ignored)"
    )
    parser.add_argument("--rate-limit", type=float, default=0.75, help="seconds between requests")
    args = parser.parse_args(argv)

    out: Path = args.raw_dir
    out.mkdir(parents=True, exist_ok=True)

    def save(name: str, data: object) -> None:
        (out / f"{name}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    with CadastralAPIClient(base_url=args.base_url, rate_limit=args.rate_limit, timeout=30.0) as c:
        save("offices", c._make_request("/search-cad-parcels/offices"))
        save("municipalities_SAVAR", c._make_request(
            "/search-cad-parcels/municipalities", {"search": "SAVAR"}
        ))
        save("main_books_SAVAR", c._make_request(
            "/search-lr-parcels/main-books",
            {"search": "SAVAR", "officeId": "", "institutionName": ""},
        ))
        save("books_of_dc_ZADAR", c._make_request(
            "/search-lr-parcels/books-of-dc",
            {"search": "ZADAR", "officeId": "", "institutionName": ""},
        ))
        save("possession_sheets_363", c._make_request(
            "/search-cad-parcels/possession-sheet-numbers",
            {"search": "363", "municipalityRegNum": MUNICIPALITY},
        ))
        for probe in SEARCH_PROBES:
            save(f"search_{safe(probe)}", c._make_request(
                "/search-cad-parcels/parcel-numbers",
                {"search": probe, "municipalityRegNum": MUNICIPALITY},
            ))

        units_seen: set[tuple[str, int]] = set()
        for number in PARCELS:
            api_number = normalize_parcel_number(number)
            search = c._make_request(
                "/search-cad-parcels/parcel-numbers",
                {"search": api_number, "municipalityRegNum": MUNICIPALITY},
            )
            save(f"search_{safe(api_number)}", search)
            exact = [r for r in (search or []) if r.get("value1") == api_number]
            if not exact:
                print(f"{number}: no exact match", flush=True)
                continue
            info = c._make_request("/cad/parcel-info", {"parcelId": str(exact[0]["key1"])})
            save(f"parcelinfo_{safe(api_number)}", info)
            ref = ParcelInfo.model_validate(info).resolved_lr_unit()
            if ref is None:
                print(f"{number}: no land-registry reference", flush=True)
                continue
            key = (ref.lr_unit_number, ref.main_book_id)
            if key in units_seen:
                continue
            units_seen.add(key)
            unit = c._make_request("/lr/lr-unit", {
                "lrUnitNumber": ref.lr_unit_number,
                "mainBookId": str(ref.main_book_id),
                "historicalOverview": "false",
            })
            save(f"lrunit_{ref.main_book_id}_{ref.lr_unit_number}", unit)
            payload = unit[0] if isinstance(unit, list) else unit
            detailed = LandRegistryUnitDetailed.model_validate(payload)
            for plumb in detailed.active_plumbs:
                parts = parse_file_number(plumb.file_number)
                if plumb.cad_plumb or parts is None:
                    continue
                code, order, year = parts
                status = c._make_post_request("/lr/file-status", {
                    "lrFileCode": code, "lrFileOrderNumber": order, "lrFileYear": year,
                    "institutionId": detailed.institution_id,
                })
                save(f"filestatus_{safe(plumb.file_number)}", status)
            print(f"{number}: unit {ref.lr_unit_number}/{ref.main_book_id}", flush=True)

        if units_seen:
            unit_number, book = sorted(units_seen)[0]
            save(f"lrunit_hist_{book}_{unit_number}", c._make_request("/lr/lr-unit", {
                "lrUnitNumber": unit_number, "mainBookId": str(book), "historicalOverview": "true",
            }))
        unit_number, book = CONDOMINIUM
        save(f"lrunit_{book}_{unit_number}", c._make_request("/lr/lr-unit", {
            "lrUnitNumber": unit_number, "mainBookId": book, "historicalOverview": "false",
        }))
    print(f"raw sample written to {out} - redact it with scripts/redact_capture.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
