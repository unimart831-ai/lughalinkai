"""Automatic MT metrics (SacreBLEU + chrF) on PSA test split.

References are silver NLLB unless human gold exists — report relative scores only.

Examples:
  python scripts/evaluate_mt.py --pair en-kik --model nllb
  python scripts/evaluate_mt.py --pair en-sw --model mt5 --limit 100
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import importlib.util

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_infer_spec = importlib.util.spec_from_file_location(
    "infer_mt", ROOT / "scripts" / "infer_mt.py"
)
_infer = importlib.util.module_from_spec(_infer_spec)
assert _infer_spec.loader is not None
_infer_spec.loader.exec_module(_infer)
default_checkpoint = _infer.default_checkpoint
load_model = _infer.load_model
translate_one = _infer.translate_one

CFG_PATH = ROOT / "configs" / "mt_train.yaml"
OUT_JSON = ROOT / "datasets" / "interim" / "mt_eval_results.json"
ABLATION_CSV = ROOT / "datasets" / "interim" / "ablation_zero_vs_ft.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Evaluate fine-tuned MT checkpoint")
    p.add_argument("--config", type=Path, default=CFG_PATH)
    p.add_argument("--pair", type=str, default="en-kik")
    p.add_argument("--model", type=str, default="nllb", choices=["nllb", "mt5"])
    p.add_argument("--checkpoint", type=Path, default=None)
    p.add_argument("--test", type=Path, default=None)
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--write-ablation", action="store_true", help="Also dump hyp vs ref CSV")
    return p.parse_args()


def load_test_rows(path: Path, src: str, tgt: str, limit: int | None) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("source_lang") != src or row.get("target_lang") != tgt:
                continue
            if str(row.get("auto_qc_pass", "true")).lower() != "true":
                continue
            rows.append(row)
            if limit and len(rows) >= limit:
                break
    return rows


def compute_metrics(hyps: list[str], refs: list[str]) -> dict:
    try:
        import sacrebleu
    except ImportError as exc:
        raise SystemExit(
            "Install metrics: pip install sacrebleu evaluate\n" f"{exc}"
        ) from exc

    bleu = sacrebleu.corpus_bleu(hyps, [refs])
    chrf = sacrebleu.corpus_chrf(hyps, [refs])
    return {
        "bleu": float(bleu.score),
        "chrf": float(chrf.score),
        "n": len(hyps),
    }


def main() -> None:
    args = parse_args()
    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    src, tgt = args.pair.split("-", 1)
    test_path = args.test or ROOT / cfg["data"]["test"]
    if not test_path.exists():
        raise SystemExit(f"Missing test split: {test_path}")

    rows = load_test_rows(test_path, src, tgt, args.limit)
    if len(rows) < 5:
        raise SystemExit(f"Need ≥5 test rows for {args.pair}; found {len(rows)}")

    ckpt = args.checkpoint or default_checkpoint(cfg, args.model, args.pair)
    tok, model, device = load_model(ckpt)

    hyps, refs, ablation = [], [], []
    for row in rows:
        hyp = translate_one(
            tok, model, device, row["source_text"], args.model, tgt, max_new=128
        )
        hyps.append(hyp)
        refs.append(row["target_text"])
        ablation.append(
            {
                "pair_id": row.get("pair_id", ""),
                "psa_id": row.get("psa_id", ""),
                "source_text": row["source_text"],
                "reference_silver": row["target_text"],
                "hypothesis_finetuned": hyp,
                "model_family": args.model,
                "pair": args.pair,
                "note": "reference_is_silver_nllb_not_human_gold",
            }
        )

    metrics = compute_metrics(hyps, refs)
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pair": args.pair,
        "model_family": args.model,
        "checkpoint": str(ckpt),
        "metrics": metrics,
        "caveat": (
            "References are PSA silver (NLLB zero-shot / auto-QC), not human gold. "
            "Use scores for relative model comparison only."
        ),
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    prev = []
    if OUT_JSON.exists():
        try:
            prev = json.loads(OUT_JSON.read_text(encoding="utf-8"))
            if isinstance(prev, dict):
                prev = [prev]
        except json.JSONDecodeError:
            prev = []
    if not isinstance(prev, list):
        prev = []
    prev.append(report)
    OUT_JSON.write_text(json.dumps(prev, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))

    if args.write_ablation:
        fields = list(ablation[0].keys())
        with ABLATION_CSV.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(ablation)
        print(f"Wrote ablation rows -> {ABLATION_CSV}")


if __name__ == "__main__":
    main()
