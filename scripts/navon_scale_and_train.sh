#!/usr/bin/env bash
# Navon / Kinesis JupyterLab — scale PSA silver to ~5k/pair and retrain.
# Run from repo root: bash scripts/navon_scale_and_train.sh
set -euo pipefail

cd "$(dirname "$0")/.."
echo "== LughaLink Navon scale + train =="
echo "cwd: $(pwd)"

git pull || true
pip install -e ".[mt]"
pip install accelerate evaluate sacrebleu datasets sentencepiece protobuf

# Phase 1: seed ~5200 EN sentences x SW + Kikuyu  (~10k pairs before QC)
python scripts/seed_nllb_sample.py \
  --input datasets/interim/week2_mt_sentences.csv \
  --targets sw,kik \
  --limit 5200 \
  --output datasets/parallel/nllb_psa_silver.csv

python scripts/prepare_mt_training_data.py

python - <<'PY'
import csv, json
from collections import Counter
from pathlib import Path
stats = json.loads(Path("datasets/interim/mt_training_ready_stats.json").read_text(encoding="utf-8"))
print(json.dumps(stats, indent=2))
by = stats.get("by_target_lang", {})
for lang in ("sw", "kik"):
    n = int(by.get(lang, 0))
    print(f"CHECK {lang}: {n} kept pairs", "OK" if n >= 4500 else "BELOW_4500_SCALE_MORE")
PY

python scripts/train_baseline.py --dry-run --pair en-kik
python scripts/train_baseline.py --dry-run --pair en-sw

# Phase 2: NLLB fine-tune
python scripts/train_baseline.py --model nllb --pair en-kik --epochs 1
python scripts/train_baseline.py --model nllb --pair en-sw --epochs 1

# Phase 3: mT5 second model
python scripts/train_baseline.py --model mt5 --pair en-kik --epochs 1
python scripts/train_baseline.py --model mt5 --pair en-sw --epochs 1

# Backup archive (download from Jupyter home)
mkdir -p /tmp/lugha_ckpt
cp -r artifacts/mt_baseline/en-kik/final /tmp/lugha_ckpt/en-kik 2>/dev/null || true
cp -r artifacts/mt_baseline/en-sw/final /tmp/lugha_ckpt/en-sw 2>/dev/null || true
cp -r artifacts/mt_baseline/mt5-en-kik/final /tmp/lugha_ckpt/mt5-en-kik 2>/dev/null || true
cp -r artifacts/mt_baseline/mt5-en-sw/final /tmp/lugha_ckpt/mt5-en-sw 2>/dev/null || true
cp datasets/parallel/nllb_psa_silver.csv /tmp/lugha_ckpt/ 2>/dev/null || true
cp -r datasets/mt /tmp/lugha_ckpt/mt 2>/dev/null || true
cd /tmp
tar -czf lughalink_mt_scaled.tar.gz lugha_ckpt
cp -f lughalink_mt_scaled.tar.gz /home/jovyan/lughalink_mt_scaled.tar.gz
ls -lh /home/jovyan/lughalink_mt_scaled.tar.gz
echo "DONE — download ~/lughalink_mt_scaled.tar.gz from Jupyter before stopping the pod"
