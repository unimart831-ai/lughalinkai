"""Baseline MT fine-tune / dry-run for NLLB (Week 3).

Examples:
  python scripts/train_baseline.py --dry-run
  python scripts/train_baseline.py --pair en-sw --epochs 1 --max-train-samples 500
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CFG_PATH = ROOT / "configs" / "mt_train.yaml"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LughaLink MT baseline train / dry-run")
    p.add_argument("--config", type=Path, default=CFG_PATH)
    p.add_argument("--pair", type=str, default="en-sw", help="e.g. en-sw / en-luo")
    p.add_argument("--dry-run", action="store_true", help="Validate data only; no model")
    p.add_argument("--epochs", type=int, default=None)
    p.add_argument("--max-train-samples", type=int, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def load_cfg(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def load_split(path: Path, src: str, tgt: str) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"Missing {path}. Run:\n"
            "  python scripts/harvest_external_en_sw.py\n"
            "  python scripts/prepare_mt_training_data.py"
        )
    rows = []
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("source_lang") != src or row.get("target_lang") != tgt:
                continue
            if str(row.get("auto_qc_pass", "true")).lower() != "true":
                continue
            if str(row.get("target_text", "")).startswith("[DRY_RUN"):
                continue
            rows.append(row)
    return rows


def dry_run_report(train, dev, test, pair: str, out_dir: Path) -> dict:
    report = {
        "mode": "dry_run",
        "pair": pair,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "counts": {"train": len(train), "dev": len(dev), "test": len(test)},
        "sample_train": [
            {"src": r["source_text"][:160], "tgt": r["target_text"][:160], "method": r["method"]}
            for r in train[:3]
        ],
        "ready_for_gpu": len(train) >= 50 and len(dev) >= 5,
        "notes": [
            "Silver/auto-QC data only — no human review in this run.",
            "On Navon: install [mt], re-run without --dry-run on Shared grid first.",
        ],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "dry_run_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ready_for_gpu"]:
        raise SystemExit("Not enough pairs for a meaningful baseline (need ≥50 train, ≥5 dev).")
    return report


def _import_hf_dataset_class():
    """Import HF Dataset without being shadowed by local datasets/ folder."""
    import site

    filtered = []
    for p in sys.path:
        try:
            resolved = Path(p).resolve() if p else Path.cwd().resolve()
        except OSError:
            filtered.append(p)
            continue
        if resolved == ROOT or resolved == Path.cwd().resolve():
            continue
        filtered.append(p)
    sys.path = filtered
    for sp in site.getsitepackages() + [site.getusersitepackages()]:
        if sp and sp not in sys.path:
            sys.path.insert(0, sp)
    for key in list(sys.modules):
        if key == "datasets" or key.startswith("datasets."):
            mod = sys.modules[key]
            f = getattr(mod, "__file__", "") or ""
            if "site-packages" not in f.replace("\\", "/"):
                del sys.modules[key]
    from datasets import Dataset  # noqa: WPS433

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    return Dataset


def train_real(cfg: dict, train_rows, dev_rows, pair: str, args: argparse.Namespace) -> None:
    try:
        import torch
        from transformers import (
            AutoModelForSeq2SeqLM,
            AutoTokenizer,
            DataCollatorForSeq2Seq,
            Seq2SeqTrainer,
            Seq2SeqTrainingArguments,
        )

        Dataset = _import_hf_dataset_class()
    except ImportError as exc:
        raise SystemExit(
            "Missing MT deps. On Navon run: pip install -e \".[mt]\" datasets\n"
            f"Original error: {exc}"
        ) from exc

    src, tgt = pair.split("-", 1)
    pair_cfg = None
    for p in cfg["languages"]["pairs"]:
        if p["source"] == src and p["target"] == tgt:
            pair_cfg = p
            break
    if not pair_cfg:
        raise SystemExit(f"Pair {pair} not in configs/mt_train.yaml")

    model_name = cfg["model"]["name"]
    out_dir = args.output_dir or Path(cfg["train"]["output_dir"]) / pair
    max_src = int(cfg["model"]["max_source_length"])
    max_tgt = int(cfg["model"]["max_target_length"])
    epochs = args.epochs or int(cfg["train"]["num_epochs"])
    max_train = args.max_train_samples or cfg["train"].get("max_train_samples")
    max_eval = cfg["train"].get("max_eval_samples")

    if max_train:
        train_rows = train_rows[: int(max_train)]
    if max_eval:
        dev_rows = dev_rows[: int(max_eval)]

    print(f"Loading {model_name} for {pair} …")
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    src_code = cfg["languages"]["source_nllb"]
    tgt_code = pair_cfg["target_nllb"]
    tokenizer.src_lang = src_code

    def to_ds(rows):
        return Dataset.from_dict(
            {
                "source_text": [r["source_text"] for r in rows],
                "target_text": [r["target_text"] for r in rows],
            }
        )

    def preprocess(batch):
        tokenizer.src_lang = src_code
        model_inputs = tokenizer(
            batch["source_text"], max_length=max_src, truncation=True, padding=False
        )
        labels = tokenizer(
            text_target=batch["target_text"],
            max_length=max_tgt,
            truncation=True,
            padding=False,
        )
        model_inputs["labels"] = labels["input_ids"]
        return model_inputs

    train_ds = to_ds(train_rows).map(preprocess, batched=True, remove_columns=["source_text", "target_text"])
    dev_ds = to_ds(dev_rows).map(preprocess, batched=True, remove_columns=["source_text", "target_text"])

    tcfg = cfg["train"]
    use_fp16 = bool(tcfg.get("fp16")) and torch.cuda.is_available()
    args_tr = Seq2SeqTrainingArguments(
        output_dir=str(out_dir),
        num_train_epochs=epochs,
        learning_rate=float(tcfg["learning_rate"]),
        per_device_train_batch_size=int(tcfg["train_batch_size"]),
        per_device_eval_batch_size=int(tcfg["eval_batch_size"]),
        weight_decay=float(tcfg["weight_decay"]),
        warmup_ratio=float(tcfg["warmup_ratio"]),
        gradient_accumulation_steps=int(tcfg["gradient_accumulation_steps"]),
        fp16=use_fp16,
        predict_with_generate=True,
        evaluation_strategy="steps",
        eval_steps=int(tcfg["eval_steps"]),
        save_steps=int(tcfg["save_steps"]),
        logging_steps=int(tcfg["logging_steps"]),
        save_total_limit=2,
        seed=int(tcfg["seed"]),
        report_to=[],
    )
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model)
    # Forced BOS for NLLB generations during eval
    model.generation_config.forced_bos_token_id = tokenizer.convert_tokens_to_ids(tgt_code)

    trainer = Seq2SeqTrainer(
        model=model,
        args=args_tr,
        train_dataset=train_ds,
        eval_dataset=dev_ds,
        data_collator=collator,
        tokenizer=tokenizer,
    )
    trainer.train()
    trainer.save_model(str(out_dir / "final"))
    tokenizer.save_pretrained(str(out_dir / "final"))
    meta = {
        "pair": pair,
        "model": model_name,
        "train_rows": len(train_rows),
        "dev_rows": len(dev_rows),
        "epochs": epochs,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "silver_only": True,
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "train_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"Saved checkpoint -> {out_dir / 'final'}")


def main() -> None:
    args = parse_args()
    cfg = load_cfg(args.config)
    if "-" not in args.pair:
        raise SystemExit("--pair must look like en-sw")
    src, tgt = args.pair.split("-", 1)
    train = load_split(ROOT / cfg["data"]["train"], src, tgt)
    dev = load_split(ROOT / cfg["data"]["dev"], src, tgt)
    test = load_split(ROOT / cfg["data"]["test"], src, tgt)
    out_dir = args.output_dir or ROOT / cfg["train"]["output_dir"] / args.pair

    if args.dry_run:
        dry_run_report(train, dev, test, args.pair, out_dir)
        return

    if len(train) < 50:
        raise SystemExit(f"Only {len(train)} train rows for {args.pair}; harvest more data first.")
    train_real(cfg, train, dev, args.pair, args)


if __name__ == "__main__":
    main()
