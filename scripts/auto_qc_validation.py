"""Auto-QC the native validation sheet when no human reviewers are available.

Fills is_valid_psa / fluency_ok / cultural_ok with heuristic values.
Leaves verified=false (never claims human gold).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.metadata.classifier import classify_psa
from services.preprocessing.normalize import preprocess_psa_text

DEFAULT = ROOT / "datasets" / "gold" / "native_validation_500.csv"
OUT = ROOT / "datasets" / "gold" / "native_validation_500_autoqc.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=DEFAULT)
    p.add_argument("--output", type=Path, default=OUT)
    return p.parse_args()


def main() -> None:
    args = parse_args()
    rows = list(csv.DictReader(args.input.open(encoding="utf-8", newline="")))
    out = []
    pass_n = 0
    for row in rows:
        text = (row.get("English_norm") or row.get("English") or "").strip()
        feats = preprocess_psa_text(text)
        is_psa, score = classify_psa("", feats["text_norm"] or text)
        ok = bool(is_psa and feats["token_count"] >= 12)
        if ok:
            pass_n += 1
        row = dict(row)
        row["reviewer"] = "auto_qc_bot"
        row["is_valid_psa"] = "true" if ok else "false"
        row["fluency_ok"] = "true" if feats["token_count"] >= 12 else "false"
        row["adequacy_ok"] = ""  # no reference translation
        row["cultural_ok"] = "unknown"
        row["review_notes"] = json.dumps(
            {
                "mode": "auto_qc_no_human",
                "classifier_score": score,
                "token_count": feats["token_count"],
                "glossary_hits": feats["glossary_hits"],
            },
            ensure_ascii=False,
        )
        row["verified"] = "false"
        out.append(row)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = list(out[0].keys()) if out else []
    with args.output.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out)
    print(f"Wrote {len(out)} rows ({pass_n} auto-pass) -> {args.output}")
    print("verified remains false — not human gold.")


if __name__ == "__main__":
    main()
