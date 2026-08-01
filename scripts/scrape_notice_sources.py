"""Scrape government/UN notice-style sources only (skip media/news dumps)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Priority notice / advisory sources across all 5 course domains.
NOTICE_SOURCES = [
    # Governance
    "iebc",
    "kra_kenya",
    "kra_press",
    "kra_news",
    "eacc_kenya",
    "huduma",
    "psc_kenya",
    "ca_kenya",
    "odpp_kenya",
    "treasury_kenya",
    "presidency_kenya",
    "cbk_kenya",
    "cma_kenya",
    "ict_kenya",
    "labour_kenya",
    "trade_kenya",
    "energy_kenya",
    "ira_kenya",
    # Health
    "moh_kenya",
    "kphd_kenya",
    "sha_kenya",
    "who_kenya",
    "who_africa",
    "unicef_kenya",
    "kenya_red_cross",
    # Education
    "moe_kenya",
    "moe_circulars",
    "moe_announcements",
    "knec",
    "helb",
    "kuccps",
    # Security / safety
    "ndma",
    "ndma_advisories",
    "met_kenya",
    "met_products",
    "meteo_advisories",
    "nps",
    "interior_kenya",
    "ntsa_kenya",
    "nema_kenya",
    "kws_kenya",
    "kplc_kenya",
    "gender_kenya",
    # Agriculture
    "kilimo",
    "kilimo_news2",
    "fao_kenya",
    "kephis",
    "kalro",
    "water_kenya",
    "kebs_kenya",
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
