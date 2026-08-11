"""Baseline MT fine-tune / dry-run for NLLB or mT5 (Week 3).

Examples:
  python scripts/train_baseline.py --dry-run --pair en-kik
  python scripts/train_baseline.py --pair en-kik --epochs 1
  python scripts/train_baseline.py --model mt5 --pair en-kik --epochs 1
"""

from __future__ import annotations

import argparse
import csv
import inspect
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CFG_PATH = ROOT / "configs" / "mt_train.yaml"
EXPERIMENT_LOG = ROOT / "datasets" / "interim" / "experiment_log.csv"

TARGET_NAMES = {"sw": "Swahili", "kik": "Kikuyu", "guz": "Ekegusii"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LughaLink MT baseline train / dry-run")
    p.add_argument("--config", type=Path, default=CFG_PATH)
    p.add_argument("--pair", type=str, default="en-kik", help="e.g. en-kik / en-sw")
    p.add_argument(
        "--model",
        type=str,
        default="nllb",
        choices=["nllb", "mt5"],
        help="Pretrained family: nllb (default) or mt5",
    )
    p.add_argument("--dry-run", action="store_true", help="Validate data only; no model")
    p.add_argument("--epochs", type=int, default=None)
    p.add_argument("--max-train-samples", type=int, default=None)
    p.add_argument("--output-dir", type=Path, default=None)
    return p.parse_args()


def load_cfg(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def resolve_model_name(cfg: dict, family: str) -> str:
    if family == "nllb":
        return cfg["model"]["name"]
    alts = cfg["model"].get("alt_models") or []
    for name in alts:
        if "mt5" in name.lower():
            return name
    return "google/mt5-small"


def mt5_prefix(source_text: str, tgt: str) -> str:
    name = TARGET_NAMES.get(tgt, tgt)
    return f"translate English to {name}: {source_text}"


def load_split(path: Path, src: str, tgt: str) -> list[dict]:
    if not path.exists():
        raise SystemExit(
            f"Missing {path}. Run PSA NLLB seed on Navon, then:\n"
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


def append_experiment_log(row: dict) -> None:
    EXPERIMENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "timestamp",
        "pair",
        "model_family",
        "model_name",
        "train_rows",
        "dev_rows",
        "epochs",
        "device",
        "output_dir",
        "notes",
    ]
    write_header = not EXPERIMENT_LOG.exists()
    with EXPERIMENT_LOG.open("a", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        if write_header:
            writer.writeheader()
        writer.writerow({k: row.get(k, "") for k in fields})


def dry_run_report(train, dev, test, pair: str, out_dir: Path, model_family: str) -> dict:
    report = {
        "mode": "dry_run",
        "pair": pair,
        "model_family": model_family,
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


def _training_arguments(
    Seq2SeqTrainingArguments,
    tcfg,
    out_dir,
    epochs,
    use_fp16,
    *,
    use_bf16: bool = False,
    model_family: str = "nllb",
):
    ta_params = inspect.signature(Seq2SeqTrainingArguments.__init__).parameters
    eval_key = "eval_strategy" if "eval_strategy" in ta_params else "evaluation_strategy"
    lr = float(tcfg["learning_rate"])
    if model_family == "mt5":
        # Slightly higher LR is common for mT5; keep modest to avoid NaNs
        lr = max(lr, 5.0e-5)
    train_args = {
        "output_dir": str(out_dir),
        "num_train_epochs": epochs,
        "learning_rate": lr,
        "per_device_train_batch_size": int(tcfg["train_batch_size"]),
        "per_device_eval_batch_size": int(tcfg["eval_batch_size"]),
        "weight_decay": float(tcfg["weight_decay"]),
        "warmup_ratio": float(tcfg["warmup_ratio"]),
        "gradient_accumulation_steps": int(tcfg["gradient_accumulation_steps"]),
        "fp16": use_fp16,
        "predict_with_generate": False,
        eval_key: "steps",
        "eval_steps": int(tcfg["eval_steps"]),
        "save_steps": int(tcfg["save_steps"]),
        "logging_steps": int(tcfg["logging_steps"]),
        "save_total_limit": 2,
        "seed": int(tcfg["seed"]),
        "report_to": [],
    }
    if "bf16" in ta_params:
        train_args["bf16"] = use_bf16
    if "save_strategy" in ta_params:
        train_args["save_strategy"] = "steps"
    return Seq2SeqTrainingArguments(**train_args)


def _make_trainer(Seq2SeqTrainer, model, args_tr, train_ds, dev_ds, collator, tokenizer):
    trainer_kwargs = {
        "model": model,
        "args": args_tr,
        "train_dataset": train_ds,
        "eval_dataset": dev_ds,
        "data_collator": collator,
    }
    trainer_params = inspect.signature(Seq2SeqTrainer.__init__).parameters
    if "processing_class" in trainer_params:
        trainer_kwargs["processing_class"] = tokenizer
    else:
        trainer_kwargs["tokenizer"] = tokenizer
    return Seq2SeqTrainer(**trainer_kwargs)


def train_real(
    cfg: dict,
    train_rows,
    dev_rows,
    pair: str,
    args: argparse.Namespace,
    model_family: str,
) -> None:
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

    model_name = resolve_model_name(cfg, model_family)
    default_out = Path(cfg["train"]["output_dir"]) / (
        pair if model_family == "nllb" else f"{model_family}-{pair}"
    )
    out_dir = args.output_dir or default_out
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    max_src = int(cfg["model"]["max_source_length"])
    max_tgt = int(cfg["model"]["max_target_length"])
    epochs = args.epochs or int(cfg["train"]["num_epochs"])
    max_train = args.max_train_samples or cfg["train"].get("max_train_samples")
    max_eval = cfg["train"].get("max_eval_samples")

    if max_train:
        train_rows = train_rows[: int(max_train)]
    if max_eval:
        dev_rows = dev_rows[: int(max_eval)]

    src_code = cfg["languages"]["source_nllb"]
    tgt_code = pair_cfg.get("target_nllb")
    extend = bool(pair_cfg.get("nllb_vocab_extend"))
    init_from = pair_cfg.get("nllb_init_from") or "swh_Latn"

    if model_family == "nllb" and extend:
        if not tgt_code:
            raise SystemExit(f"Pair {pair} needs target_nllb for NLLB vocab extend")
        print(f"Loading {model_name} with vocab extend {tgt_code} (init {init_from}) …")
        from services.translation.nllb_extend import ensure_nllb_lang_token

        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
        ensure_nllb_lang_token(
            tokenizer, model, lang_token=tgt_code, init_from=init_from
        )
    elif model_family == "nllb" and not tgt_code:
        raise SystemExit(
            f"Pair {pair} has no target_nllb. Use --model mt5 or set nllb_vocab_extend."
        )
    else:
        print(f"Loading {model_name} ({model_family}) for {pair} …")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

    if model_family == "nllb":
        tokenizer.src_lang = src_code

    def to_ds(rows):
        if model_family == "mt5":
            sources = [mt5_prefix(r["source_text"], tgt) for r in rows]
        else:
            sources = [r["source_text"] for r in rows]
        return Dataset.from_dict(
            {
                "source_text": sources,
                "target_text": [r["target_text"] for r in rows],
            }
        )

    def preprocess(batch):
        if model_family == "nllb":
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
        label_ids = labels["input_ids"]
        pad_id = tokenizer.pad_token_id
        if pad_id is not None:
            label_ids = [
                [(tok if tok != pad_id else -100) for tok in seq] for seq in label_ids
            ]
        model_inputs["labels"] = label_ids
        return model_inputs

    train_ds = to_ds(train_rows).map(
        preprocess, batched=True, remove_columns=["source_text", "target_text"]
    )
    dev_ds = to_ds(dev_rows).map(
        preprocess, batched=True, remove_columns=["source_text", "target_text"]
    )

    tcfg = cfg["train"]
    # mT5 is unstable in fp16 on many stacks (loss 0 / grad_norm nan). Prefer bf16 or fp32.
    use_fp16 = bool(tcfg.get("fp16")) and torch.cuda.is_available() and model_family != "mt5"
    use_bf16 = (
        model_family == "mt5"
        and torch.cuda.is_available()
        and hasattr(torch.cuda, "is_bf16_supported")
        and torch.cuda.is_bf16_supported()
    )
    args_tr = _training_arguments(
        Seq2SeqTrainingArguments,
        tcfg,
        out_dir,
        epochs,
        use_fp16,
        use_bf16=use_bf16,
        model_family=model_family,
    )
    collator = DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, label_pad_token_id=-100)
    if model_family == "nllb":
        model.generation_config.forced_bos_token_id = tokenizer.convert_tokens_to_ids(tgt_code)

    trainer = _make_trainer(
        Seq2SeqTrainer, model, args_tr, train_ds, dev_ds, collator, tokenizer
    )
    train_out = trainer.train()
    trainer.save_model(str(out_dir / "final"))
    tokenizer.save_pretrained(str(out_dir / "final"))
    meta = {
        "pair": pair,
        "model_family": model_family,
        "model": model_name,
        "train_rows": len(train_rows),
        "dev_rows": len(dev_rows),
        "epochs": epochs,
        "device": "cuda" if torch.cuda.is_available() else "cpu",
        "silver_only": True,
        "nllb_vocab_extend": extend if model_family == "nllb" else False,
        "target_nllb": tgt_code,
        "train_loss": getattr(train_out, "training_loss", None),
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }
    (out_dir / "train_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    append_experiment_log(
        {
            "timestamp": meta["saved_at"],
            "pair": pair,
            "model_family": model_family,
            "model_name": model_name,
            "train_rows": len(train_rows),
            "dev_rows": len(dev_rows),
            "epochs": epochs,
            "device": meta["device"],
            "output_dir": str(out_dir / "final"),
            "notes": "silver_psa_only",
        }
    )
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
    family = args.model
    default_out = ROOT / cfg["train"]["output_dir"] / (
        args.pair if family == "nllb" else f"{family}-{args.pair}"
    )
    out_dir = args.output_dir or default_out

    if args.dry_run:
        dry_run_report(train, dev, test, args.pair, out_dir, family)
        return

    if len(train) < 50:
        raise SystemExit(f"Only {len(train)} train rows for {args.pair}; harvest more data first.")
    train_real(cfg, train, dev, args.pair, args, family)


if __name__ == "__main__":
    main()
