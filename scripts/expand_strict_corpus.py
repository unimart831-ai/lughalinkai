"""Scrape notice sources → export → framework-strict merge → refresh Week 2 freeze.

Target: grow datasets/processed/week2_ready_psas.csv toward 5,000 strict PSAs.

Usage:
  python scripts/expand_strict_corpus.py
  python scripts/expand_strict_corpus.py --skip-scrape   # only export+merge existing DB
  python scripts/expand_strict_corpus.py iebc moh_kenya sha_kenya
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

READY = ROOT / "datasets" / "processed" / "week2_ready_psas.csv"
STRICT = ROOT / "datasets" / "processed" / "week2_strict_psas.csv"
EXPORT = ROOT / "datasets" / "processed" / "psa_export_expand.csv"
STATS = ROOT / "datasets" / "interim" / "expand_strict_stats.json"
TARGET = 5000


def run(cmd: list[str]) -> int:
    print(">>", " ".join(cmd), flush=True)
    env = {**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONUNBUFFERED": "1"}
    # Windows gov HTTPS often fails cert verify in Python — allow override.
    env.setdefault("SCRAPER_SSL_VERIFY", "false")
    return subprocess.run(cmd, cwd=str(ROOT), env=env).returncode


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("sources", nargs="*", help="Optional source_id subset")
    p.add_argument("--skip-scrape", action="store_true")
    p.add_argument("--skip-init", action="store_true")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    sources = list(args.sources)

    if not args.skip_init:
        run([sys.executable, "-m", "services.cli", "init-db"])

    if not args.skip_scrape:
        # Delegate to notice scraper (all priority sources, or a subset).
        cmd = [sys.executable, "scripts/scrape_notice_sources.py", *sources]
        code = run(cmd)
        print(f"=== scrape_notice_sources exit={code} ===", flush=True)

    run(
        [
            sys.executable,
            "-m",
            "services.cli",
            "export",
            "--output",
            str(EXPORT),
        ]
    )

    # Merge export into clean using framework-aware ingest
    run([sys.executable, "scripts/ingest_export_to_clean.py", str(EXPORT)])

    # Re-audit merged clean with framework (+ gate) and promote
    run([sys.executable, "scripts/audit_psa_framework.py", "--also-gate",
         "--input", str(ROOT / "datasets" / "processed" / "week1_psa_merged.csv")])

    if STRICT.exists():
        shutil.copy2(STRICT, READY)
        shutil.copy2(STRICT, ROOT / "datasets" / "processed" / "week1_psa_merged.csv")

    run([sys.executable, "scripts/prepare_week2_baseline.py"])
    run([sys.executable, "scripts/prepare_mt_training_data.py", "--allow-empty"])

    rows = list(csv.DictReader(READY.open(encoding="utf-8", newline="")))
    by_domain = Counter(r.get("Domain") or "Unknown" for r in rows)
    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strict_psas": len(rows),
        "target": TARGET,
        "gap_to_target": max(0, TARGET - len(rows)),
        "by_domain": dict(by_domain),
        "sources_attempted": sources or "NOTICE_SOURCES_default",
        "export": str(EXPORT.relative_to(ROOT)),
    }
    STATS.parent.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    if len(rows) < TARGET:
        print(f"\nStill short by {TARGET - len(rows)}. Re-run with more sources / higher max_items.")
    else:
        print(f"\nReached target: {len(rows)} >= {TARGET}")


if __name__ == "__main__":
    main()
