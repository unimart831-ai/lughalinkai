"""Ingest a PSA export CSV into the strict-clean Week 1 sheet."""

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
from services.metadata.psa_framework import classify_psa_framework  # noqa: E402
from services.metadata.psa_gate import strict_psa_rejection_reason  # noqa: E402

CLEAN = ROOT / "datasets" / "processed" / "week1_psa_merged.csv"
QUAR = ROOT / "datasets" / "processed" / "week1_psa_quarantined.csv"
STATS = ROOT / "datasets" / "processed" / "week1_merge_stats.json"
EXPORT = ROOT / "datasets" / "processed" / "all_psa_export.csv"

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


def main() -> None:
    export_path = EXPORT
    if len(sys.argv) > 1:
        export_path = Path(sys.argv[1])

    clean = _load(CLEAN)
    quarantine = _load(QUAR)
    export_rows = _load(export_path)
    seen = {_norm(r.get("English") or "") for r in clean}
    seen |= {_norm(r.get("English") or "") for r in quarantine}
    seen.discard("")

    added = 0
    rejected = 0
    by_domain = Counter(r.get("Domain") or "Governance" for r in clean)

    for r in export_rows:
        title = (r.get("title") or "").strip()
        body = (r.get("text") or "").strip()
        if not body and not title:
            continue
        full = f"{title}. {body}".strip(". ").strip() if title else body
        tokens = len(full.split())
        if tokens > 320:
            core = extract_psa_core(title, full, max_tokens=340)
            if core and len(core.split()) >= 12:
                full = core
        reason = strict_psa_rejection_reason(
            full,
            source=r.get("source_url") or "",
            lang=(r.get("language") or "en")[:2],
            contributor="scrape_export",
        )
        fw = classify_psa_framework(full, title=title)
        key = _norm(full)
        reject_reason = reason
        if not reject_reason and not fw["is_strict_psa"]:
            reject_reason = f"framework_{fw['framework_label']}:{fw['framework_reason']}"
        if reject_reason or not key or key in seen:
            rejected += 1
            if reject_reason and key and key not in seen:
                quarantine.append(
                    {
                        "PSA_ID": "",
                        "Domain": (r.get("domain") or "governance").title(),
                        "English": full,
                        "Kiswahili": "",
                        "Target Languages": '["Kikuyu"]',
                        "Source": r.get("source_url") or "",
                        "Date": r.get("published_at") or "",
                        "Metadata": json.dumps(
                            {
                                "origin": "scrape_export",
                                "quarantine_reason": reject_reason,
                                "framework_label": fw["framework_label"],
                            },
                            ensure_ascii=False,
                        ),
                        "Quarantine_Reason": reject_reason,
                    }
                )
                seen.add(key)
            continue

        seen.add(key)
        domain = (r.get("domain") or "governance").replace("_", " ").title()
        if domain.lower() == "security & safety":
            domain = "Security"
        clean.append(
            {
                "PSA_ID": "",
                "Domain": domain,
                "English": full,
                "Kiswahili": "",
                "Target Languages": '["Kikuyu"]',
                "Source": r.get("source_url") or "",
                "Date": r.get("published_at") or "",
                "Metadata": json.dumps(
                    {
                        "origin": "scrape_export",
                        "source_id": r.get("source_id"),
                        "organization": r.get("organization"),
                        "token_count": len(full.split()),
                        "strict_psa_pass": True,
                        "framework_label": fw["framework_label"],
                        "framework_confidence": fw["framework_confidence"],
                    },
                    ensure_ascii=False,
                ),
            }
        )
        by_domain[domain] += 1
        added += 1

    year = datetime.now(timezone.utc).year
    for i, row in enumerate(clean, start=1):
        meta = json.loads(row.get("Metadata") or "{}")
        meta["original_psa_id"] = row.get("PSA_ID") or meta.get("original_psa_id")
        row["PSA_ID"] = f"psa_{year}_{i:06d}"
        row["Metadata"] = json.dumps(meta, ensure_ascii=False)
    for i, row in enumerate(quarantine, start=1):
        row["PSA_ID"] = f"qpsa_{year}_{i:06d}"

    with CLEAN.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(clean)

    q_fields = FIELDS + ["Quarantine_Reason"]
    with QUAR.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=q_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(quarantine)

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ingest_export": str(export_path),
        "rows_final_clean": len(clean),
        "rows_added_from_export": added,
        "rows_rejected_from_export": rejected,
        "rows_quarantined": len(quarantine),
        "by_domain": dict(by_domain),
    }
    if STATS.exists():
        try:
            prev = json.loads(STATS.read_text(encoding="utf-8"))
            prev.update(stats)
            stats = prev
        except json.JSONDecodeError:
            pass
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))
    print(f"Clean: {len(clean)} (+{added} from export)")


if __name__ == "__main__":
    main()
