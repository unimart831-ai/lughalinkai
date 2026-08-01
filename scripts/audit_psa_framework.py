"""Rescore PSA corpus against DOCS/PSA FRAMEWORK.pdf decision tree.

Reads week2_ready (or cleaned) PSAs, labels each row as:
  psa | press_release | other_gov_comm | not_psa

Writes:
  datasets/interim/psa_framework_audit.csv
  datasets/interim/psa_framework_audit_stats.json
  datasets/processed/week2_strict_psas.csv          (framework PSA only)
  datasets/processed/week2_framework_quarantine.csv (non-PSA labels)

Usage:
  python scripts/audit_psa_framework.py
  python scripts/audit_psa_framework.py --min-confidence 0.55
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.metadata.classifier import classify_psa
from services.metadata.psa_framework import classify_psa_framework
from services.metadata.psa_gate import strict_psa_rejection_reason

SRC_READY = ROOT / "datasets" / "processed" / "week2_ready_psas.csv"
SRC_CLEANED = ROOT / "datasets" / "processed" / "week2_cleaned_psas.csv"
AUDIT_CSV = ROOT / "datasets" / "interim" / "psa_framework_audit.csv"
STATS = ROOT / "datasets" / "interim" / "psa_framework_audit_stats.json"
STRICT = ROOT / "datasets" / "processed" / "week2_strict_psas.csv"
QUAR = ROOT / "datasets" / "processed" / "week2_framework_quarantine.csv"

EXPORT_FIELDS = [
    "PSA_ID",
    "Domain",
    "English",
    "Kiswahili",
    "Target Languages",
    "Source",
    "Date",
    "Metadata",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Audit corpus vs PSA Framework")
    p.add_argument("--input", type=Path, default=None)
    p.add_argument("--min-confidence", type=float, default=0.55)
    p.add_argument(
        "--also-gate",
        action="store_true",
        help="Also require legacy strict_psa_rejection_reason is None",
    )
    return p.parse_args()


def primary_text(row: dict) -> str:
    en = (row.get("English_norm") or row.get("English") or "").strip()
    sw = (row.get("Kiswahili_norm") or row.get("Kiswahili") or "").strip()
    return en if len(en.split()) >= len(sw.split()) else sw


def title_hint(text: str) -> str:
    t = " ".join((text or "").split())
    if ". " in t[:160]:
        return t.split(". ", 1)[0]
    return t[:100]


def main() -> None:
    args = parse_args()
    src = args.input
    if src is None:
        src = SRC_READY if SRC_READY.exists() else SRC_CLEANED
    if not src.exists():
        raise SystemExit(f"Missing input corpus: {src}")

    rows = list(csv.DictReader(src.open(encoding="utf-8", newline="")))
    audit_rows = []
    strict_rows = []
    quar_rows = []
    by_label: Counter[str] = Counter()
    by_domain_psa: Counter[str] = Counter()
    by_domain_all: Counter[str] = Counter()
    reasons: Counter[str] = Counter()

    for row in rows:
        text = primary_text(row)
        title = title_hint(text)
        fw = classify_psa_framework(text, title=title)
        _is, legacy_score = classify_psa(title, text)
        gate_reason = strict_psa_rejection_reason(text, source=row.get("Source") or "")

        domain = row.get("Domain") or "Unknown"
        by_domain_all[domain] += 1
        by_label[fw["framework_label"]] += 1
        reasons[fw["framework_reason"]] += 1

        keep = fw["framework_label"] == "psa" and fw["framework_confidence"] >= args.min_confidence
        if args.also_gate and gate_reason is not None:
            keep = False

        if keep:
            by_domain_psa[domain] += 1

        try:
            meta = json.loads(row.get("Metadata") or "{}")
        except json.JSONDecodeError:
            meta = {}
        meta.update(
            {
                "framework_label": fw["framework_label"],
                "framework_confidence": fw["framework_confidence"],
                "framework_reason": fw["framework_reason"],
                "legacy_classifier_score": legacy_score,
                "legacy_gate_reason": gate_reason,
                "framework_keep": keep,
            }
        )

        export = {k: row.get(k, "") for k in EXPORT_FIELDS}
        # Prefer English body from cleaned sheet
        if not export.get("English"):
            export["English"] = row.get("English_norm") or text
        export["Target Languages"] = export.get("Target Languages") or '["Kikuyu"]'
        export["Metadata"] = json.dumps(meta, ensure_ascii=False)

        audit_rows.append(
            {
                **export,
                "framework_label": fw["framework_label"],
                "framework_confidence": fw["framework_confidence"],
                "framework_reason": fw["framework_reason"],
                "action_hits": fw["action_hits"],
                "press_hits": fw["press_hits"],
                "other_hits": fw["other_hits"],
                "token_count": fw["token_count"],
                "legacy_classifier_score": legacy_score,
                "legacy_gate_reason": gate_reason or "",
                "keep_strict_psa": str(keep).lower(),
            }
        )
        if keep:
            strict_rows.append(export)
        else:
            quar_rows.append(export)

    # Write outputs
    AUDIT_CSV.parent.mkdir(parents=True, exist_ok=True)
    audit_fields = list(audit_rows[0].keys()) if audit_rows else []
    with AUDIT_CSV.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=audit_fields)
        w.writeheader()
        w.writerows(audit_rows)

    STRICT.parent.mkdir(parents=True, exist_ok=True)
    with STRICT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=EXPORT_FIELDS)
        w.writeheader()
        w.writerows(strict_rows)
    with QUAR.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=EXPORT_FIELDS)
        w.writeheader()
        w.writerows(quar_rows)

    kept = len(strict_rows)
    total = len(rows)
    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "framework_doc": "DOCS/PSA FRAMEWORK.pdf",
        "input": str(src.relative_to(ROOT)),
        "total_rows": total,
        "strict_psa_kept": kept,
        "quarantined": len(quar_rows),
        "keep_rate": round(kept / total, 4) if total else 0.0,
        "min_confidence": args.min_confidence,
        "also_legacy_gate": args.also_gate,
        "by_framework_label": dict(by_label),
        "by_framework_reason_top": reasons.most_common(20),
        "by_domain_all": dict(by_domain_all),
        "by_domain_strict_psa": dict(by_domain_psa),
        "outputs": {
            "audit": str(AUDIT_CSV.relative_to(ROOT)),
            "strict_psas": str(STRICT.relative_to(ROOT)),
            "quarantine": str(QUAR.relative_to(ROOT)),
        },
        "verdict": (
            "poor_needs_clean"
            if (kept / total if total else 0) < 0.45
            else "mixed_review"
            if (kept / total if total else 0) < 0.7
            else "mostly_psa"
        ),
        "next_steps": [
            "Review sample rows in datasets/interim/psa_framework_audit.csv",
            "Use datasets/processed/week2_strict_psas.csv as the training/seed corpus",
            "python scripts/prepare_week2_baseline.py  # after copying strict → week2_ready if approved",
        ],
    }
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    print(f"\nStrict PSAs -> {STRICT} ({kept}/{total})")
    print(f"Quarantine  -> {QUAR} ({len(quar_rows)})")
    print(f"Audit       -> {AUDIT_CSV}")
    print(f"Verdict     -> {stats['verdict']}")


if __name__ == "__main__":
    main()
