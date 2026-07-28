"""Re-filter Week 1 sheets with the strict PSA gate (pre-Product-2 cleanup).

Reads existing clean + quarantine CSVs, re-scores every row, and rewrites:
  - datasets/processed/week1_psa_merged.csv
  - datasets/processed/week1_psa_quarantined.csv
  - datasets/processed/week1_merge_stats.json
Then refreshes the Week 2 baseline via prepare_week2_baseline.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.metadata.psa_core import extract_psa_core  # noqa: E402
from services.metadata.psa_gate import (  # noqa: E402
    MAX_TOKENS,
    MIN_CLASSIFIER_SCORE,
    strict_psa_rejection_reason,
)


CLEAN = ROOT / "datasets" / "processed" / "week1_psa_merged.csv"
QUAR = ROOT / "datasets" / "processed" / "week1_psa_quarantined.csv"
STATS = ROOT / "datasets" / "processed" / "week1_merge_stats.json"

FIELDS = [
    "PSA_ID",
    "Domain",
    "English",
    "Kiswahili",
    "Target Languages",
    "Source",
    "Date",
    "Metadata",
]


def load_rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def primary_text(row: dict) -> str:
    en = (row.get("English") or "").strip()
    sw = (row.get("Kiswahili") or "").strip()
    return en if len(en.split()) >= len(sw.split()) else sw


def _title_hint(text: str) -> str:
    t = " ".join((text or "").split())
    if ". " in t[:160]:
        return t.split(". ", 1)[0]
    return t[:100]


def renumber(rows: list[dict], prefix: str) -> list[dict]:
    year = datetime.now(timezone.utc).year
    out = []
    for i, row in enumerate(rows, start=1):
        r = dict(row)
        try:
            meta = json.loads(r.get("Metadata") or "{}")
        except json.JSONDecodeError:
            meta = {}
        meta["original_psa_id"] = r.get("PSA_ID")
        r["PSA_ID"] = f"{prefix}_{year}_{i:06d}"
        r["Metadata"] = json.dumps(meta, ensure_ascii=False)
        out.append(r)
    return out


def main() -> None:
    combined = load_rows(CLEAN) + load_rows(QUAR)
    if not combined:
        raise SystemExit("No Week 1 CSVs found to refilter.")

    # Dedupe by content hash / text
    seen = set()
    unique = []
    for row in combined:
        text = primary_text(row).lower()
        key = " ".join(text.split())
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(row)

    clean: list[dict] = []
    quarantined: list[dict] = []
    reasons: Counter[str] = Counter()
    by_contrib_q: Counter[str] = Counter()
    by_domain: Counter[str] = Counter()
    by_lang: Counter[str] = Counter()
    by_contrib_c: Counter[str] = Counter()

    for row in unique:
        try:
            meta = json.loads(row.get("Metadata") or "{}")
        except json.JSONDecodeError:
            meta = {}
        text = primary_text(row)
        if len(text.split()) > MAX_TOKENS:
            text = extract_psa_core(_title_hint(text), text, max_tokens=MAX_TOKENS)
            row = dict(row)
            row["English"] = text
        lang = meta.get("lang_detected") or "unknown"
        reason = strict_psa_rejection_reason(
            text,
            source=row.get("Source") or "",
            lang=lang,
            contributor=meta.get("contributor") or "",
            origin_file=meta.get("origin_file") or "",
        )
        contrib = meta.get("contributor") or "unknown"
        if reason:
            meta["quarantine_reason"] = reason
            q = {k: row.get(k, "") for k in FIELDS}
            q["Metadata"] = json.dumps(meta, ensure_ascii=False)
            q["Quarantine_Reason"] = reason
            quarantined.append(q)
            reasons[reason] += 1
            by_contrib_q[contrib] += 1
        else:
            meta.pop("quarantine_reason", None)
            meta["strict_psa_pass"] = True
            c = {k: row.get(k, "") for k in FIELDS}
            c["Metadata"] = json.dumps(meta, ensure_ascii=False)
            clean.append(c)
            by_domain[c.get("Domain") or "Governance"] += 1
            by_lang[lang] += 1
            by_contrib_c[contrib] += 1

    clean = renumber(clean, "psa")
    quarantined = renumber(quarantined, "qpsa")

    with CLEAN.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(clean)

    q_fields = FIELDS + ["Quarantine_Reason"]
    with QUAR.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=q_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(quarantined)

    sentences = 0
    with_sw = 0
    for r in clean:
        try:
            meta = json.loads(r["Metadata"])
        except json.JSONDecodeError:
            meta = {}
        sentences += int(meta.get("sentence_count") or 1)
        if (r.get("Kiswahili") or "").strip():
            with_sw += 1

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strict_refilter": True,
        "rows_input_unique": len(unique),
        "rows_final_clean": len(clean),
        "rows_quarantined": len(quarantined),
        "quarantine_reasons": dict(reasons),
        "quarantine_by_contributor": dict(by_contrib_q),
        "by_domain": dict(by_domain),
        "by_lang_detected": dict(by_lang),
        "by_contributor": dict(by_contrib_c),
        "approx_english_sentences": sentences,
        "rows_with_kiswahili_text": with_sw,
        "gate": {
            "min_tokens": 12,
            "max_tokens": MAX_TOKENS,
            "min_classifier_score": MIN_CLASSIFIER_SCORE,
        },
    }
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    print(f"\nClean: {CLEAN} ({len(clean)})")
    print(f"Quarantine: {QUAR} ({len(quarantined)})")


if __name__ == "__main__":
    main()
