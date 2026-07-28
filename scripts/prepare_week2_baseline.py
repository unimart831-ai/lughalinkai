"""Freeze Week 1 clean corpus and build Week 2 seed candidates."""

from __future__ import annotations

import csv
import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "datasets" / "processed" / "week2_ready_psas.csv"
SRC_FALLBACK = ROOT / "datasets" / "processed" / "week1_psa_merged.csv"
BASELINE = ROOT / "datasets" / "processed" / "week1_baseline_psa.csv"
CANDIDATES = ROOT / "datasets" / "interim" / "week2_seed_candidates.csv"
STATS = ROOT / "datasets" / "interim" / "week2_baseline_stats.json"
LANG_CFG = ROOT / "configs" / "languages.yaml"


def load_seed_defaults() -> dict:
    if not LANG_CFG.exists():
        return {"min_source_tokens": 12, "max_source_tokens": 200}
    cfg = yaml.safe_load(LANG_CFG.read_text(encoding="utf-8"))
    return cfg.get("seed_defaults") or {"min_source_tokens": 12, "max_source_tokens": 200}


def first_sentences(text: str, max_chars: int = 600) -> str:
    """Prefer the full short PSA body; only trim very long ones."""
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return ""
    # Keep whole text when it is already PSA-length.
    if len(text.split()) <= 200:
        return text[:max_chars].strip()
    parts = re.split(r"(?<=[.!?])\s+", text)
    out = []
    for p in parts:
        if len(p.split()) < 5:
            continue
        out.append(p)
        joined = " ".join(out)
        if len(joined) >= 120 or len(out) >= 2:
            break
    joined = " ".join(out) if out else text
    return joined[:max_chars].strip()


def main() -> None:
    src = SRC if SRC.exists() else SRC_FALLBACK
    if not src.exists():
        raise SystemExit(f"Missing clean PSA sheet: {SRC} or {SRC_FALLBACK}")

    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "datasets" / "parallel").mkdir(parents=True, exist_ok=True)
    (ROOT / "datasets" / "gold").mkdir(parents=True, exist_ok=True)

    shutil.copy2(src, BASELINE)

    defaults = load_seed_defaults()
    min_tok = int(defaults.get("min_source_tokens", 12))
    max_tok = int(defaults.get("max_source_tokens", 200))

    rows = list(csv.DictReader(src.open(encoding="utf-8", newline="")))
    candidates = []
    domain_counts: Counter[str] = Counter()
    cand_domains: Counter[str] = Counter()

    for row in rows:
        domain = row.get("Domain") or "Governance"
        domain_counts[domain] += 1
        english = (row.get("English") or "").strip()
        tokens = len(english.split())
        if tokens < min_tok or tokens > max_tok:
            continue
        seed_text = first_sentences(english)
        if len(seed_text.split()) < min_tok:
            continue
        candidates.append(
            {
                "psa_id": row.get("PSA_ID") or "",
                "Domain": domain,
                "seed_text": seed_text,
                "token_count": len(seed_text.split()),
                "Source": row.get("Source") or "",
                "Date": row.get("Date") or "",
                "full_token_count": tokens,
            }
        )
        cand_domains[domain] += 1

    fieldnames = [
        "psa_id",
        "Domain",
        "seed_text",
        "token_count",
        "Source",
        "Date",
        "full_token_count",
    ]
    with CANDIDATES.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(candidates)

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "baseline": str(BASELINE.relative_to(ROOT)),
        "baseline_rows": len(rows),
        "by_domain": dict(domain_counts),
        "seed_candidates": str(CANDIDATES.relative_to(ROOT)),
        "seed_candidate_rows": len(candidates),
        "seed_candidates_by_domain": dict(cand_domains),
        "min_source_tokens": min_tok,
        "max_source_tokens": max_tok,
    }
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    print(f"\nFroze baseline -> {BASELINE}")
    print(f"Seed candidates -> {CANDIDATES} ({len(candidates)} rows)")


if __name__ == "__main__":
    main()
