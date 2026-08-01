# Navon Cloud / Kinesis — Training Readiness

**Project:** LughaLink AI  
**Policy:** No human reviewers available → use **silver** data only (`verified=false`, `auto_qc_pass=true`). Never label machine output as gold.

Related platform docs:
- `DOCS/Navon-Cloud-Getting-Started.pdf`
- `DOCS/Navon-Cloud-Connect-via-SSH.pdf`
- [Kinesis: Running LLMs](https://docs.kinesis.network/getting-started/running-llms-with-kinesis-network)

---

## 1. What “ready” means (without humans)

| Gate | Requirement |
|------|-------------|
| Parallel data | `datasets/mt/train.csv` has ≥50 EN↔SW silver pairs |
| Auto-QC | Dry-run / near-copy / bad-ratio rows rejected |
| Training script | `python scripts/train_baseline.py --dry-run` passes |
| Platform | Navon Shared app can see GPU + load NLLB |
| Honesty | Report states silver-only / no native review |

---

## 2. Local prerequisites (run before GPU)

```bash
# 1) Week 2 freeze + sentence candidates
python scripts/prepare_week2_baseline.py
python scripts/prepare_week2_processing.py

# 2) External EN↔SW silver (OPUS GlobalVoices, auto-QC)
python scripts/harvest_external_en_sw.py --limit 2500

# 3) Merge → datasets/mt/{train,dev,test}.csv
python scripts/prepare_mt_training_data.py

# 4) Validate training I/O without torch
python scripts/train_baseline.py --dry-run --pair en-sw

# 5) Auto-QC the 500 validation sheet (still verified=false)
python scripts/auto_qc_validation.py
```

---

## 3. Navon Shared grid smoke test

1. Sign in at **portal.navon.africa** → create project `lughalink-mt`.
2. App Gallery → **JupyterLab** or **code-server** → **Shared** grid → Quick Launch.
3. Optional SSH: follow `Navon-Cloud-Connect-via-SSH.pdf`.
4. In Terminal:

```bash
nvidia-smi
git clone <your-fork-or-repo> lughalink && cd lughalink
pip install -e ".[mt]"
pip install datasets accelerate evaluate sacrebleu
```

5. Set Hugging Face token in app **Runtime** as `HF_TOKEN` (never commit it).
6. Upload/sync `datasets/mt/` + configs (or `git pull`). Prefer **MinIO** / Stateful for checkpoints.
7. Seed PSA-domain silver (machine only):

```bash
python scripts/prepare_week2_baseline.py
python scripts/seed_nllb_sample.py --targets sw,luo,guz,som --limit 200 \
  --output datasets/parallel/nllb_psa_silver.csv
python scripts/prepare_mt_training_data.py
python scripts/train_baseline.py --dry-run --pair en-sw
```

8. Short real train on Shared:

```bash
python scripts/train_baseline.py --pair en-sw --epochs 1 --max-train-samples 500
```

Confirm `artifacts/mt_baseline/en-sw/final/` exists.

---

## 4. High-Performance grid (only after Shared works)

- Ask admin to book a High-Performance slot.
- Raise `--max-train-samples` / epochs in `configs/mt_train.yaml`.
- Save checkpoints + `train_meta.json` to MinIO.
- Keep evaluating on `datasets/mt/test.csv` (silver test — report limitation).

---

## 5. Grid rule of thumb

| Grid | Use for |
|------|---------|
| Shared | Install, NLLB seed, dry-run, 1-epoch smoke train |
| High-Performance | Full fine-tunes / ablations |

---

## 6. What we deliberately skip without humans

- Promoting rows to `datasets/gold/gold_translations.csv` with `verified=true`
- Claiming cultural accuracy / native adequacy scores
- Treating OPUS general-domain pairs as Kenyan PSA gold

When reviewers appear later: re-label a sample of `datasets/mt/test.csv` + NLLB PSA silver into true gold.
