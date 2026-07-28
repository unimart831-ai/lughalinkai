"""Scrape government/UN notice-style sources only (skip media/news dumps)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

NOTICE_SOURCES = [
    "iebc",
    "kra_kenya",
    "kra_press",
    "kra_news",
    "eacc_kenya",
    "huduma",
    "psc_kenya",
    "ca_kenya",
    "nema_kenya",
    "kebs_kenya",
    "odpp_kenya",
    "treasury_kenya",
    "presidency_kenya",
    "moh_kenya",
    "moe_kenya",
    "moe_circulars",
    "knec",
    "helb",
    "kuccps",
    "ndma",
    "met_kenya",
    "met_products",
    "kilimo",
    "fao_kenya",
    "who_kenya",
    "who_africa",
    "unicef_kenya",
    "kenya_red_cross",
]


def main() -> None:
    only = sys.argv[1:] or NOTICE_SOURCES
    for sid in only:
        print(f"\n=== SCRAPE {sid} ===", flush=True)
        proc = subprocess.run(
            [sys.executable, "-m", "services.cli", "scrape", "--source", sid],
            cwd=str(ROOT),
        )
        print(f"=== DONE {sid} exit={proc.returncode} ===", flush=True)


if __name__ == "__main__":
    main()
