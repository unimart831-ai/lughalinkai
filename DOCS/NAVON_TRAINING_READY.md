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
5. On Navon: NLLB seeds **EN → SW** and **EN → Kikuyu** from PSA sentences (**scale to ~5200 sources**).  
6. Fine-tune **NLLB + mT5** on that PSA silver data.

```text
English PSA  →  Kiswahili   (pivot)
English PSA  →  Kikuyu      (indigenous target)
```

---

## Use the correct Kinesis project

Use **My First Project → JupyterLab** (A100). Ignore blocked apps with “no suitable node”.  
Jupyter token is often shown by `jupyter server list` (e.g. `token=hello`).

---

## Ready checklist

| Gate | Requirement |
|------|-------------|
| PSA sentences | `datasets/interim/week2_mt_sentences.csv` (8409) |
| Scale seed | `--limit 5200` → `nllb_psa_silver.csv` |
| MT splits | `python scripts/prepare_mt_training_data.py` |
| Dry-run | `python scripts/train_baseline.py --dry-run --pair en-kik` |
| Models | NLLB + mT5 for `en-kik` and `en-sw` |

---

## One-shot scale + train (recommended)

On Navon, in `~/lughalinkai` (use `tmux`):

```bash
git pull
bash scripts/navon_scale_and_train.sh
```

This will:

1. Seed **5200** EN sentences × SW + Kikuyu  
2. Rebuild PSA-only MT splits  
3. Fine-tune NLLB `en-kik` / `en-sw`  
4. Fine-tune mT5 `en-kik` / `en-sw`  
5. Pack `~/lughalink_mt_scaled.tar.gz` for Jupyter download  

**Download the tar before Stop/Restart** — `/tmp` and ephemeral disks wipe.

Manual equivalent:

```bash
pip install -e ".[mt]"
pip install accelerate evaluate sacrebleu datasets

python scripts/seed_nllb_sample.py \
  --input datasets/interim/week2_mt_sentences.csv \
  --targets sw,kik \
  --limit 5200 \
  --output datasets/parallel/nllb_psa_silver.csv

python scripts/prepare_mt_training_data.py
python scripts/train_baseline.py --dry-run --pair en-kik
python scripts/train_baseline.py --model nllb --pair en-kik --epochs 1
python scripts/train_baseline.py --model nllb --pair en-sw --epochs 1
python scripts/train_baseline.py --model mt5 --pair en-kik --epochs 1
python scripts/train_baseline.py --model mt5 --pair en-sw --epochs 1
```

After train:

```bash
python scripts/evaluate_mt.py --pair en-kik --model nllb --write-ablation
python scripts/infer_mt.py --pair en-kik --text "The public is advised to follow official health guidelines."
```

---

## Verify the model (after train — CLI only)

```bash
python scripts/infer_mt.py --pair en-kik --text "The public is advised to follow official health guidelines."
python scripts/infer_mt.py --pair en-sw --text "The public is advised to follow official health guidelines."
python scripts/evaluate_mt.py --pair en-kik --model nllb --write-ablation
```

Product UI comes later. Do not block on Streamlit.

---

## High-Performance grid

Only after Shared scale train works: book HP slot, raise epochs in `configs/mt_train.yaml`.
