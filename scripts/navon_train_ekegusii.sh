#!/usr/bin/env bash
# Navon — Ekegusii zero-shot baselines + few-shot mT5 + few-shot NLLB (guz_Latn).
# Keeps existing EN→SW / EN→Kikuyu artifacts untouched.
# Run from repo root: bash scripts/navon_train_ekegusii.sh
set -euo pipefail

cd "$(dirname "$0")/.."
echo "== LughaLink Ekegusii (guz) pipeline =="
echo "cwd: $(pwd)"

git pull || true
pip install -e ".[mt]"
pip install accelerate evaluate sacrebleu datasets sentencepiece protobuf pyyaml

# 1) Template silver EN↔Ekegusii pairs
python scripts/generate_ekegusii_parallel.py --limit 5200

# Keep existing SW/Kikuyu silver if present (do not wipe on prepare)
if [[ ! -f datasets/parallel/nllb_psa_silver.csv ]]; then
  echo "WARN: datasets/parallel/nllb_psa_silver.csv missing — prepare will only keep guz pairs."
  echo "      Copy Navon backup / re-seed SW+Kikuyu if you need those rows in datasets/mt/."
fi

# 2) Rebuild MT splits (merges guz with existing sw/kik parallel CSVs)
python scripts/prepare_mt_training_data.py

python - <<'PY'
import json
from collections import Counter
from pathlib import Path
import csv
stats = json.loads(Path("datasets/interim/mt_training_ready_stats.json").read_text(encoding="utf-8"))
print(json.dumps(stats, indent=2))
by = Counter()
for split in ("train", "dev", "test"):
    p = Path(f"datasets/mt/{split}.csv")
    if not p.exists():
        continue
    for row in csv.DictReader(p.open(encoding="utf-8", newline="")):
        by[row.get("target_lang")] += 1
print("by_target_lang_all_splits:", dict(by))
n = int(by.get("guz", 0))
print("CHECK guz:", n, "OK" if n >= 3000 else "BELOW_3000_SCALE_MORE")
PY

python scripts/train_baseline.py --dry-run --model mt5 --pair en-guz
python scripts/train_baseline.py --dry-run --model nllb --pair en-guz

# 3) Zero-shot baselines (no fine-tune)
python scripts/eval_ekegusii_zeroshot.py --family both --limit 50 || true

# 4) Few-shot mT5
python scripts/train_baseline.py --model mt5 --pair en-guz --epochs 1
python scripts/evaluate_mt.py --pair en-guz --model mt5 --write-ablation || true

# 5) Few-shot NLLB with guz_Latn vocab extension
python scripts/train_baseline.py --model nllb --pair en-guz --epochs 1
python scripts/evaluate_mt.py --pair en-guz --model nllb --write-ablation || true

# Backup
mkdir -p /tmp/lugha_guz
cp -r artifacts/mt_baseline/mt5-en-guz/final /tmp/lugha_guz/mt5-en-guz 2>/dev/null || true
cp -r artifacts/mt_baseline/en-guz/final /tmp/lugha_guz/nllb-en-guz 2>/dev/null || true
cp datasets/parallel/guz_psa_template.csv /tmp/lugha_guz/ 2>/dev/null || true
cp datasets/interim/mt_eval_ekegusii_zeroshot.json /tmp/lugha_guz/ 2>/dev/null || true
cp datasets/interim/mt_eval_results.json /tmp/lugha_guz/ 2>/dev/null || true
cd /tmp
tar -czf lughalink_mt_ekegusii.tar.gz lugha_guz
cp -f lughalink_mt_ekegusii.tar.gz /home/jovyan/lughalink_mt_ekegusii.tar.gz 2>/dev/null \
  || cp -f lughalink_mt_ekegusii.tar.gz "$HOME/lughalink_mt_ekegusii.tar.gz"
ls -lh lughalink_mt_ekegusii.tar.gz
echo "DONE — download lughalink_mt_ekegusii.tar.gz before stopping the pod"
echo "Next: push Hub models, then set LUGHALINK_MODEL_GUZ / LUGHALINK_MODEL_GUZ_MT5"
