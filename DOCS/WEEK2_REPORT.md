# Week 2 Report — Data Processing & EDA

**Project:** LughaLink AI (DSA 4020)  
**Team focus:** Sub-objectives 1 & 2 (cleaned dataset + EDA)  
**Updated:** 2 August 2026  
**Frozen corpus:** `datasets/processed/week2_ready_psas.csv` (**5,000** rows)

---

## 1. Deliverables

| Item | Path | Status |
|------|------|--------|
| Framework-strict + synthetic freeze | `datasets/processed/week2_ready_psas.csv` | **5,000** |
| Real strict PSAs only | counted inside freeze (`synthetic=false`) | **1,615** |
| Synthetic templates | `datasets/processed/week2_synthetic_psas.csv` | **3,385** |
| Cleaned + features | `datasets/processed/week2_cleaned_psas.csv` | 5,000 |
| Preprocessing | `services/preprocessing/` + `configs/glossary.yaml` | Done |
| PSA Framework scorer | `services/metadata/psa_framework.py` | Done |
| EDA notebook | `notebooks/week2_eda.ipynb` | Done |
| Native validation (500) | `datasets/gold/native_validation_500.csv` | Sheet ready |
| Auto-QC validation | `datasets/gold/native_validation_500_autoqc.csv` | Done (`verified=false`) |
| PSA splits | `datasets/splits/{train,dev,test}.csv` | 3998 / 498 / 504 |
| MT seed sentences | `datasets/interim/week2_mt_sentences.csv` | 8,409 |
| Seed candidates | `datasets/interim/week2_seed_candidates.csv` | 3,464 |
| Languages | EN source · SW pivot · **Kikuyu** target | `configs/languages.yaml` |
| Navon checklist | `DOCS/NAVON_TRAINING_READY.md` | Ready |

Reproduce locally:

```bash
python scripts/prepare_week2_processing.py
python scripts/prepare_week2_baseline.py
python scripts/prepare_mt_training_data.py --allow-empty
```

---

## 2. Corpus composition

| Origin | Rows | Notes |
|--------|-----:|-------|
| Real (scraped + PSA Framework strict) | 1,615 | From gov/notice sources |
| Synthetic (template, framework-filtered) | 3,385 | `Metadata.synthetic=true` |
| **Total** | **5,000** | Course volume target |

| Domain | Rows |
|--------|-----:|
| Agriculture | 1,524 |
| Governance | 1,066 |
| Education | 924 |
| Security | 762 |
| Health | 724 |

See `DOCS/SYNTHETIC_PSA_NOTE.md` and `DOCS/PSA_FRAMEWORK_AUDIT.md`.

---

## 3. Language plan

| Language | Role | NLLB |
|----------|------|------|
| English | source | `eng_Latn` |
| Kiswahili | pivot | `swh_Latn` |
| Kikuyu | indigenous target | `kik_Latn` |

---

## 4. Preprocessing

1. Unicode + whitespace normalization  
2. Alnum boundary repair  
3. Cultural glossary (`configs/glossary.yaml`)  
4. PSA Framework decision tree (`DOCS/PSA FRAMEWORK.pdf`)  
5. Stratified train/dev/test + 500 validation sheet  

---

## 5. Challenges

- Soft “PSA” scrapes included press releases and long reports → framework cut to 1,615 real  
- Further scraping was slow / low-yield → synthetic templates used for volume, clearly labeled  
- No human reviewers → silver / auto-QC only (`verified=false`)  
- Parallel EN↔SW / EN↔Kikuyu still needs **Navon NLLB seeding**  

---

## 6. Navon next (GPU)

```bash
pip install -e ".[mt]"
python scripts/seed_nllb_sample.py \
  --input datasets/interim/week2_mt_sentences.csv \
  --targets sw,kik --limit 2000 \
  --output datasets/parallel/nllb_psa_silver.csv
python scripts/prepare_mt_training_data.py
python scripts/train_baseline.py --dry-run --pair en-kik
python scripts/train_baseline.py --pair en-kik --epochs 1
```

Full checklist: `DOCS/NAVON_TRAINING_READY.md`.
