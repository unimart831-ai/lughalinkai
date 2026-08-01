# Week 2 Report — Data Processing & EDA

**Project:** LughaLink AI (DSA 4020)  
**Team focus:** Sub-objectives 1 & 2 (cleaned dataset + EDA)  
**Date:** 29 July 2026  
**Frozen input:** `datasets/processed/week2_ready_psas.csv` (4,152 rows)

---

## 1. Deliverables

| Item | Path | Status |
|------|------|--------|
| Cleaned corpus | `datasets/processed/week2_cleaned_psas.csv` | Done (4,149 usable EN rows) |
| Preprocessing code | `services/preprocessing/` + `configs/glossary.yaml` | Done |
| EDA notebook | `notebooks/week2_eda.ipynb` | Done |
| EDA stats JSON | `datasets/interim/week2_eda_stats.json` | Done |
| Native validation subset (~500) | `datasets/gold/native_validation_500.csv` | Sheet ready — reviews pending |
| Train / dev / test | `datasets/splits/{train,dev,test}.csv` | Done (3318 / 412 / 419) |
| This report | `DOCS/WEEK2_REPORT.md` | Draft |

Reproduce:

```bash
python scripts/prepare_week2_processing.py
# then open notebooks/week2_eda.ipynb
```

---

## 2. Preprocessing pipeline

Reusable steps in `services/preprocessing/`:

1. **Unicode + whitespace normalization** (`normalize_psa_text`)
2. **Alnum boundary repair** (e.g. `NOTICE15th` → `NOTICE 15th`; ordinals preserved)
3. **Glossary rewrite** for Kenyan institutional / cultural terms (`configs/glossary.yaml`)
4. **Token / length features** for EDA
5. **Code-switch heuristic** (EN/SW cue mix)
6. **Stratified splits** + held-out-preferring validation sample

---

## 3. Corpus summary

| Metric | Value |
|--------|-------|
| Input rows | 4,152 |
| Cleaned rows (non-empty English) | 4,149 |
| Dropped empty English | 3 |
| Rows with Kiswahili text | 0 in cleaned sheet (3 SW-only / empty-EN rows dropped) |
| Vocabulary size | ~24.8k word types |
| Median token count | ~286 |
| Code-switch flagged | 26 |

### Domain distribution

| Domain | Count |
|--------|------:|
| Governance | 1,949 |
| Health | 838 |
| Security | 837 |
| Education | 340 |
| Agriculture | 185 |

### Splits (stratified by domain, seed=42)

| Split | Rows |
|-------|-----:|
| train | 3,318 |
| dev | 412 |
| test | 419 |

### Native validation (~500)

Stratified sample preferring **test + dev**, exported with empty review columns (`reviewer`, `is_valid_psa`, `fluency_ok`, `adequacy_ok`, `cultural_ok`, `review_notes`, `verified`).

| Domain | Validation rows |
|--------|----------------:|
| Governance | 235 |
| Health | 101 |
| Security | 101 |
| Education | 41 |
| Agriculture | 22 |

---

## 4. EDA insights

1. **Domain imbalance** — Governance ≈ 47% of the corpus; Education and Agriculture are under-represented for balanced MT evaluation.
2. **Length** — Token counts cluster high (many full public notices). For Week 3 few-shot MT, prefer sentence-level / seed-candidate cuts (`scripts/prepare_week2_baseline.py`).
3. **Missing translations** — Cleaned sheet is English-first; true EN↔SW parallel harvest is still required for language-pair statistics and modeling.
4. **Orthography / culture** — Glossary covers IEBC, EACC, NHIF/SHA, M-PESA, Huduma, county/ward, etc. Expand as reviewers flag terms.
5. **Language detection** — Nearly all rows tagged `en` (2 false `fr` possibles to spot-check).

Charts: run `notebooks/week2_eda.ipynb` → writes under `datasets/interim/week2_eda_figures/`.

---

## 5. Challenges

- Week 1 volume prioritized **English PSA quality**; Kiswahili alignment lagged.
- Some “PSAs” are long official notices — gate already removed nav junk / country briefs, but lengths remain high for classic MT sentence pairs.
- Native-speaker review capacity is the bottleneck for the ~500 validation subset (and later gold translations).

---

## 6. Next steps (still Week 2 / into Week 3)

- [x] Silver EN↔SW harvest (OPUS GlobalVoices, no human review) → `datasets/parallel/en_sw_pairs.csv`
- [x] MT splits → `datasets/mt/{train,dev,test}.csv` (2000/250/250)
- [x] Train dry-run ready → `python scripts/train_baseline.py --dry-run`
- [x] Auto-QC validation sheet (still `verified=false`) → `native_validation_500_autoqc.csv`
- [ ] On Navon Shared: real NLLB PSA silver seed + 1-epoch train (see `DOCS/NAVON_TRAINING_READY.md`)
- [ ] Supervisor check-in with this report + EDA notebook
- [ ] When humans available: promote a gold sample from silver test/NLLB PSA rows

---

## 7. Sample cleaned entries

See first rows of `datasets/processed/week2_cleaned_psas.csv` (`English_norm`, `glossary_hits`, `split`, `validation_subset`).
