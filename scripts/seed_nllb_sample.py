"""Seed NLLB zero-shot translations for Week 2 sample runs.

Examples:
  python scripts/seed_nllb_sample.py --dry-run --limit 5
  # Preferred PSA-only path (sentence sheet):
  python scripts/seed_nllb_sample.py \\
    --input datasets/interim/week2_mt_sentences.csv \\
    --targets sw,kik --limit 820 \\
    --output datasets/parallel/nllb_psa_silver.csv

Silver only: outputs always verified=false. Re-run prepare_mt_training_data.py after seeding.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.translation.seeder import (
    build_seed_record,
    load_language_config,
    nllb_code_for,
    records_to_csv_rows,
)

CANDIDATES = ROOT / "datasets" / "interim" / "week2_seed_candidates.csv"
SENTENCES = ROOT / "datasets" / "interim" / "week2_mt_sentences.csv"
OUT = ROOT / "datasets" / "parallel" / "nllb_psa_silver.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="NLLB zero-shot PSA seed (PSA text only)")
    p.add_argument("--limit", type=int, default=20, help="Max source rows to seed")
    p.add_argument(
        "--targets",
        type=str,
        default="sw,kik",
        help="Comma-separated target ids (default: Kiswahili pivot + Kikuyu)",
    )
    p.add_argument("--dry-run", action="store_true", help="Write placeholder targets; no model")
    default_in = SENTENCES if SENTENCES.exists() else CANDIDATES
    p.add_argument("--input", type=Path, default=default_in)
    p.add_argument("--output", type=Path, default=OUT)
    return p.parse_args()


def _source_text(row: dict) -> str:
    return (row.get("source_text") or row.get("seed_text") or "").strip()


def _psa_id(row: dict) -> str:
    return (row.get("psa_id") or row.get("PSA_ID") or "").strip()


def load_model(model_name: str):
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        import torch
    except ImportError as exc:
        raise SystemExit(
            "Missing MT deps. Install with: pip install -e \".[mt]\"\n"
            f"Original error: {exc}"
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    return tokenizer, model, device


def translate_one(tokenizer, model, device, text: str, src_code: str, tgt_code: str) -> str:
    tokenizer.src_lang = src_code
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    forced_bos = tokenizer.convert_tokens_to_ids(tgt_code)
    generated = model.generate(
        **inputs,
        forced_bos_token_id=forced_bos,
        max_new_tokens=256,
        num_beams=4,
    )
    return tokenizer.batch_decode(generated, skip_special_tokens=True)[0]


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(
            f"Missing PSA input: {args.input}\n"
            "Run: python scripts/prepare_week2_baseline.py && "
            "python scripts/prepare_mt_training_data.py --allow-empty"
        )

    cfg = load_language_config()
    model_name = os.getenv("NLLB_MODEL") or cfg.get("nllb_model") or "facebook/nllb-200-distilled-600M"
    targets = [t.strip() for t in args.targets.split(",") if t.strip()]
    src_code = cfg.get("seed_defaults", {}).get("source_nllb") or "eng_Latn"

    rows = list(csv.DictReader(args.input.open(encoding="utf-8", newline="")))[: args.limit]
    tokenizer = model = device = None
    if not args.dry_run:
        print(f"Loading {model_name} …")
        tokenizer, model, device = load_model(model_name)

    records = []
    n = 0
    for row in rows:
        source_text = _source_text(row)
        psa_id = _psa_id(row)
        if not source_text or not psa_id:
            continue
        for tgt in targets:
            n += 1
            tgt_code = nllb_code_for(tgt, cfg)
            if args.dry_run:
                translated = f"[DRY_RUN {tgt_code}] {source_text[:80]}"
            else:
                translated = translate_one(
                    tokenizer, model, device, source_text, src_code, tgt_code
                )
            records.append(
                build_seed_record(
                    translation_id=f"seed_{n:06d}",
                    psa_id=psa_id,
                    domain=row.get("Domain") or "Governance",
                    source_text=source_text,
                    translated_text=translated,
                    target_lang=tgt,
                    source_url=row.get("Source") or "",
                    dry_run=args.dry_run,
                )
            )

    out_rows = records_to_csv_rows(records)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(out_rows[0].keys()) if out_rows else [
        "pair_id",
        "psa_id",
        "Domain",
        "source_lang",
        "target_lang",
        "source_text",
        "target_text",
        "method",
        "confidence",
        "verified",
        "Source",
        "Metadata",
    ]
    with args.output.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    mode = "dry-run" if args.dry_run else "nllb"
    print(f"Wrote {len(out_rows)} rows ({mode}) -> {args.output}")


if __name__ == "__main__":
    main()
