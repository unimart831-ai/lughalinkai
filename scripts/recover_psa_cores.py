"""Recover short PSA cores from too-long quarantine rows."""

from __future__ import annotations

import csv
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.metadata.psa_core import extract_psa_core  # noqa: E402
from services.metadata.psa_gate import strict_psa_rejection_reason  # noqa: E402

CLEAN = ROOT / "datasets" / "processed" / "week1_psa_merged.csv"
QUAR = ROOT / "datasets" / "processed" / "week1_psa_quarantined.csv"
RECOVERED = ROOT / "datasets" / "processed" / "recovered_psa_cores.csv"
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


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def _title(text: str) -> str:
    t = re.sub(r"\s+", " ", (text or "").strip())
    if ". " in t[:160]:
        return t.split(". ", 1)[0]
    return t[:100]


def main() -> None:
    clean = _load(CLEAN)
    quarantine = _load(QUAR)
    seen = {_norm(r.get("English") or r.get("Kiswahili") or "") for r in clean}
    seen.discard("")

    recoverable = [
        r
        for r in quarantine
        if (r.get("Quarantine_Reason") or "") in {
            "too_long_for_psa",
            "very_long_report",
            "weak_long_narrative",
            "genre_news_not_psa",
        }
        or (r.get("Quarantine_Reason") or "").startswith(
            ("weak_long", "weak_forced", "core_failed", "low_psa_score:0.3", "low_psa_score:0.32", "low_psa_score:0.33", "low_psa_score:0.34")
        )
    ]

    recovered: list[dict] = []
    still_q: list[dict] = []
    reasons = Counter()

    # Keep non-recoverable quarantine as-is
    recover_ids = {id(r) for r in recoverable}
    for r in quarantine:
        if id(r) not in recover_ids:
            still_q.append(r)

    for row in recoverable:
        text = (row.get("English") or row.get("Kiswahili") or "").strip()
        title = _title(text)
        core = extract_psa_core(title, text, max_tokens=340)
        reason = strict_psa_rejection_reason(
            core,
            source=row.get("Source") or "",
            lang="en",
            contributor="recovered_core",
        )
        key = _norm(core)
        if reason or not key or key in seen:
            q = dict(row)
            if reason:
                q["Quarantine_Reason"] = f"core_failed:{reason}"
            still_q.append(q)
            reasons[reason or "duplicate_core"] += 1
            continue

        seen.add(key)
        try:
            meta = json.loads(row.get("Metadata") or "{}")
        except json.JSONDecodeError:
            meta = {}
        meta["recovered_from"] = row.get("PSA_ID")
        meta["recovery"] = "psa_core_extract"
        meta["token_count"] = len(core.split())
        meta["strict_psa_pass"] = True
        new = {
            "PSA_ID": "",
            "Domain": row.get("Domain") or "Governance",
            "English": core,
            "Kiswahili": "",
            "Target Languages": row.get("Target Languages") or '["Kikuyu"]',
            "Source": row.get("Source") or "",
            "Date": row.get("Date") or "",
            "Metadata": json.dumps(meta, ensure_ascii=False),
        }
        recovered.append(new)
        reasons["recovered"] += 1

    year = datetime.now(timezone.utc).year
    all_clean = clean + recovered
    for i, row in enumerate(all_clean, start=1):
        meta = json.loads(row.get("Metadata") or "{}")
        meta["original_psa_id"] = row.get("PSA_ID") or meta.get("original_psa_id")
        row["PSA_ID"] = f"psa_{year}_{i:06d}"
        row["Metadata"] = json.dumps(meta, ensure_ascii=False)

    for i, row in enumerate(still_q, start=1):
        row["PSA_ID"] = f"qpsa_{year}_{i:06d}"

    with CLEAN.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_clean)

    with RECOVERED.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(recovered)

    q_fields = FIELDS + ["Quarantine_Reason"]
    with QUAR.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=q_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(still_q)

    by_domain = Counter(r["Domain"] for r in all_clean)
    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "recovery_run": True,
        "rows_final_clean": len(all_clean),
        "rows_recovered_cores": len(recovered),
        "rows_quarantined": len(still_q),
        "by_domain": dict(by_domain),
        "recovery_notes": dict(reasons),
    }
    # merge into existing stats if present
    if STATS.exists():
        try:
            prev = json.loads(STATS.read_text(encoding="utf-8"))
            prev.update(stats)
            stats = prev
        except json.JSONDecodeError:
            pass
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(json.dumps(stats, indent=2))
    print(f"Clean now: {len(all_clean)} (+{len(recovered)} recovered cores)")


if __name__ == "__main__":
    main()
