# Navon Cloud — PSA-only Training Readiness

**Project:** LughaLink AI  
**Languages:** English (source) · Kiswahili (pivot) · **Kikuyu** (indigenous target)  
**Policy:** Train on **Public Service Announcements only**. No OPUS / news bitext.  
Without human reviewers → PSA **silver** from NLLB (`verified=false`). Never call that gold.

Related platform docs:
- `DOCS/Navon-Cloud-Getting-Started.pdf`
- `DOCS/Navon-Cloud-Connect-via-SSH.pdf`
- [Kinesis: Running LLMs](https://docs.kinesis.network/getting-started/running-llms-with-kinesis-network)

---

## Plain-English flow

1. Week 1–2: English PSAs cleaned with PSA Framework → **1,615 real** strict PSAs.  
2. Volume gap filled with **framework-valid synthetic templates** → **5,000 total** (`synthetic=true` in Metadata).  
3. Kiswahili stays as the **pivot** (course requires EN/SW).  
4. Kikuyu is the **indigenous target** (NLLB code `kik_Latn`).  
5. On Navon: NLLB seeds **EN → SW** and **EN → Kikuyu** from PSA sentences.  
6. Fine-tune NLLB (and a second model later) on that PSA silver data.

```text
English PSA  →  Kiswahili   (pivot)
English PSA  →  Kikuyu      (indigenous target)
```

---

## Ready checklist

| Gate | Requirement |
|------|-------------|
| PSA sentences | `datasets/interim/week2_mt_sentences.csv` |
| PSA parallel silver | `datasets/parallel/nllb_psa_silver.csv` |
| MT splits | `datasets/mt/` via `--psa-only` (default) |
| Dry-run | `python scripts/train_baseline.py --dry-run --pair en-kik` |
| Platform | Navon Shared: GPU + NLLB |

---

## Local (before GPU)

```bash
python scripts/prepare_week2_baseline.py
python scripts/prepare_mt_training_data.py --allow-empty
```

---

## Navon Shared — PSA seed + train

```bash
pip install -e ".[mt]"
pip install accelerate evaluate sacrebleu

python scripts/seed_nllb_sample.py \
  --input datasets/interim/week2_mt_sentences.csv \
  --targets sw,kik \
  --limit 820 \
  --output datasets/parallel/nllb_psa_silver.csv

python scripts/prepare_mt_training_data.py

python scripts/train_baseline.py --dry-run --pair en-kik
python scripts/train_baseline.py --pair en-kik --epochs 1

# Optional pivot pair
python scripts/train_baseline.py --pair en-sw --epochs 1
```

Save checkpoints under `artifacts/mt_baseline/` (MinIO / Stateful).

---

## High-Performance grid

Only after Shared smoke train works: book HP slot, raise epochs in `configs/mt_train.yaml`.
