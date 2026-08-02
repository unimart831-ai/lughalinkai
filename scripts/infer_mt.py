"""CLI inference for fine-tuned NLLB / mT5 PSA translators.

Examples:
  python scripts/infer_mt.py --pair en-kik --text "Register to vote at your nearest centre."
  python scripts/infer_mt.py --model mt5 --pair en-sw --text "Wash hands regularly."
  python scripts/infer_mt.py --pair en-kik --input datasets/mt/test.csv --limit 5
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CFG_PATH = ROOT / "configs" / "mt_train.yaml"
TARGET_NAMES = {"sw": "Swahili", "kik": "Kikuyu"}
NLLB_CODES = {"sw": "swh_Latn", "kik": "kik_Latn"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="LughaLink MT inference")
    p.add_argument("--config", type=Path, default=CFG_PATH)
    p.add_argument("--pair", type=str, default="en-kik")
    p.add_argument("--model", type=str, default="nllb", choices=["nllb", "mt5"])
    p.add_argument("--checkpoint", type=Path, default=None, help="Override model dir")
    p.add_argument("--text", type=str, default=None)
    p.add_argument("--input", type=Path, default=None, help="CSV with source_text column")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--max-new-tokens", type=int, default=128)
    return p.parse_args()


def default_checkpoint(cfg: dict, family: str, pair: str) -> Path:
    base = ROOT / cfg["train"]["output_dir"]
    if family == "nllb":
        return base / pair / "final"
    return base / f"{family}-{pair}" / "final"


def load_model(path: Path):
    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as exc:
        raise SystemExit(f"Missing MT deps: pip install -e \".[mt]\"\n{exc}") from exc

    if not path.exists():
        raise SystemExit(f"Checkpoint not found: {path}")
    tok = AutoTokenizer.from_pretrained(str(path))
    model = AutoModelForSeq2SeqLM.from_pretrained(str(path))
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    return tok, model, device


def translate_one(tok, model, device, text: str, family: str, tgt: str, max_new: int) -> str:
    if family == "mt5":
        prompt = f"translate English to {TARGET_NAMES.get(tgt, tgt)}: {text}"
        inputs = tok(prompt, return_tensors="pt", truncation=True, max_length=256)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        out = model.generate(**inputs, max_new_tokens=max_new)
    else:
        tok.src_lang = "eng_Latn"
        inputs = tok(text, return_tensors="pt", truncation=True, max_length=256)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        bos = tok.convert_tokens_to_ids(NLLB_CODES[tgt])
        out = model.generate(**inputs, forced_bos_token_id=bos, max_new_tokens=max_new)
    return tok.batch_decode(out, skip_special_tokens=True)[0]


def main() -> None:
    args = parse_args()
    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    if "-" not in args.pair:
        raise SystemExit("--pair must look like en-kik")
    _, tgt = args.pair.split("-", 1)
    if tgt not in NLLB_CODES:
        raise SystemExit(f"Unsupported target in pair: {tgt}")

    ckpt = args.checkpoint or default_checkpoint(cfg, args.model, args.pair)
    tok, model, device = load_model(ckpt)

    texts: list[str] = []
    if args.text:
        texts = [args.text.strip()]
    elif args.input and args.input.exists():
        with args.input.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                if row.get("target_lang") and row["target_lang"] != tgt:
                    continue
                src = (row.get("source_text") or "").strip()
                if src:
                    texts.append(src)
                if len(texts) >= args.limit:
                    break
    else:
        raise SystemExit("Provide --text or --input CSV")

    for i, text in enumerate(texts, 1):
        hyp = translate_one(tok, model, device, text, args.model, tgt, args.max_new_tokens)
        print(f"[{i}] SRC: {text}")
        print(f"    TGT: {hyp}")
        print()


if __name__ == "__main__":
    main()
