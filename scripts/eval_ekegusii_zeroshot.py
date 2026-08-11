"""Zero-shot baselines for Ekegusii (mT5 + NLLB with guz_Latn init, no PSA FT).

Examples:
  python scripts/eval_ekegusii_zeroshot.py --limit 50
  python scripts/eval_ekegusii_zeroshot.py --family mt5 --limit 100
  python scripts/eval_ekegusii_zeroshot.py --family nllb --limit 100
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

OUT_JSON = ROOT / "datasets" / "interim" / "mt_eval_ekegusii_zeroshot.json"
TEST = ROOT / "datasets" / "mt" / "test.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Ekegusii zero-shot eval (no PSA fine-tune)")
    p.add_argument("--family", choices=["mt5", "nllb", "both"], default="both")
    p.add_argument("--test", type=Path, default=TEST)
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--max-new-tokens", type=int, default=64)
    p.add_argument("--output", type=Path, default=OUT_JSON)
    return p.parse_args()


def load_guz_test(path: Path, limit: int) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"Missing {path}. Run:\n"
            "  python scripts/generate_ekegusii_parallel.py --limit 5200\n"
            "  python scripts/prepare_mt_training_data.py"
        )
    rows = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("target_lang") != "guz":
                continue
            if str(row.get("auto_qc_pass", "true")).lower() != "true":
                continue
            rows.append(row)
            if limit and len(rows) >= limit:
                break
    if not rows:
        raise SystemExit(f"No guz rows in {path}")
    return rows


def score(hyps: list[str], refs: list[str]) -> dict:
    import evaluate

    bleu = evaluate.load("sacrebleu")
    chrf = evaluate.load("chrf")
    b = bleu.compute(predictions=hyps, references=[[r] for r in refs])
    c = chrf.compute(predictions=hyps, references=[[r] for r in refs])
    return {
        "bleu": round(float(b["score"]), 3),
        "chrf": round(float(c["score"]), 3),
        "n": len(hyps),
    }


def run_mt5(rows: list[dict], max_new: int) -> dict:
    from services.translation.mt5_infer import load_mt5, translate_mt5

    tok, model, device = load_mt5("google/mt5-small")
    hyps, refs = [], []
    for row in rows:
        hyp = translate_mt5(
            tok, model, device, row["source_text"], "guz", max_new_tokens=max_new
        )
        hyps.append(hyp)
        refs.append(row["target_text"])
    metrics = score(hyps, refs)
    metrics.update({"family": "mt5", "setting": "zero_shot", "model": "google/mt5-small"})
    return metrics


def run_nllb(rows: list[dict], max_new: int) -> dict:
    from services.translation.nllb_extend import load_nllb_maybe_extended
    from services.translation.nllb_infer import translate_nllb

    tok, model, device, _bos = load_nllb_maybe_extended(
        "facebook/nllb-200-distilled-600M",
        extend_lang="guz_Latn",
        init_from="swh_Latn",
    )
    hyps, refs = [], []
    for row in rows:
        hyp = translate_nllb(
            tok, model, device, row["source_text"], "guz", max_new_tokens=max_new
        )
        hyps.append(hyp)
        refs.append(row["target_text"])
    metrics = score(hyps, refs)
    metrics.update(
        {
            "family": "nllb",
            "setting": "zero_shot",
            "model": "facebook/nllb-200-distilled-600M",
            "note": "guz_Latn vocab-extend init from swh_Latn; no PSA fine-tune",
        }
    )
    return metrics


def main() -> None:
    args = parse_args()
    rows = load_guz_test(args.test, args.limit)
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "test": str(args.test),
        "limit": args.limit,
        "runs": [],
        "errors": [],
    }
    if args.family in ("mt5", "both"):
        print("Zero-shot mT5 …")
        try:
            results["runs"].append(run_mt5(rows, args.max_new_tokens))
        except Exception as exc:  # noqa: BLE001
            results["errors"].append({"family": "mt5", "error": str(exc)})
            print(f"mT5 zero-shot FAILED: {exc}")
    if args.family in ("nllb", "both"):
        print("Zero-shot NLLB+guz_Latn …")
        try:
            results["runs"].append(run_nllb(rows, args.max_new_tokens))
        except Exception as exc:  # noqa: BLE001
            results["errors"].append({"family": "nllb", "error": str(exc)})
            print(f"NLLB zero-shot FAILED: {exc}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))
    print(f"Wrote {args.output}")
    if results["errors"] and not results["runs"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
