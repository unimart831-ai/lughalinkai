# Product 2 — Week 2: Data Processing & EDA

**Project:** LughaLink AI (DSA 4020)  
**Official focus (course PDF):** Data Processing & Exploratory Data Analysis (Sub-objectives 1 & 2)  
**Main deliverables:** Cleaned dataset + EDA report  
**Frozen Week 1 input:** `datasets/processed/week2_ready_psas.csv` (**4,152** PSAs)

Stretch (feeds Week 3, do not block EDA): EN↔SW harvest + NLLB seeding — see §8.

---

## 1. Goal

Take the frozen English PSA corpus through a **reusable preprocessing pipeline**, produce **EDA visuals/insights**, cut a **~500 native-speaker validation subset**, and write **train/dev/test** splits for modeling.

---

## 2. Course checklist → our paths

| Course milestone | Our deliverable |
|------------------|-----------------|
| Preprocessing pipeline (tokenize, normalize, code-switch, glossary) | `services/preprocessing/` + `configs/glossary.yaml` |
| Full EDA | `notebooks/week2_eda.ipynb` + `datasets/interim/week2_eda_stats.json` |
| Native-speaker validation (~500) | `datasets/gold/native_validation_500.csv` |
| Handle missing translations / imbalance / orthography | Documented in `DOCS/WEEK2_REPORT.md`; glossary + stratified splits |
| Version cleaned dataset | `datasets/processed/week2_cleaned_psas.csv` (+ splits) in git |
| EDA notebook/report | notebook + `DOCS/WEEK2_REPORT.md` |
| Train/dev/test | `datasets/splits/{train,dev,test}.csv` |

---

## 3. Commands

```bash
# Build cleaned corpus, EDA stats, validation sheet, splits
python scripts/prepare_week2_processing.py

# Optional: seed-candidate freeze for later MT
python scripts/prepare_week2_baseline.py

# Unit tests
python -m pytest tests/services/test_week2_preprocessing.py -q
```

Then open `notebooks/week2_eda.ipynb` (kernel cwd = `notebooks/`).

---

## 4. Output schemas

### Cleaned PSA row (`week2_cleaned_psas.csv`)

Original PSA columns plus: `English_norm`, `Kiswahili_norm`, `token_count`, `char_count`, `sentence_count`, `lang_primary`, `code_switch`, `has_kiswahili`, `glossary_hits`, `split`, `validation_subset`, …

### Native validation row

Same features + empty review fields: `reviewer`, `is_valid_psa`, `fluency_ok`, `adequacy_ok`, `cultural_ok`, `review_notes`, `verified`.

---

## 5. Current freeze snapshot

After `prepare_week2_processing.py`:

- Cleaned: **4,149** EN rows (3 empty-English dropped)
- Splits: train **3318** / dev **412** / test **419**
- Validation: **500** stratified (prefer held-out)
- Domains: Governance 1949 · Health 838 · Security 837 · Education 340 · Agriculture 185

---

## 6. Rules

1. Do not mix quarantine rows into the cleaned sheet.  
2. Native validation feedback must set `verified=true` only after human review.  
3. NLLB / machine output never goes in `datasets/gold/` without review.  
4. Keep Cursor co-author trailers out of commits.

---

## 7. Definition of done (Week 2 / PDF)

- [x] Cleaned dataset versioned  
- [x] Preprocessing code reusable  
- [x] EDA notebook + stats  
- [x] train/dev/test written  
- [x] 500 validation sheet exported  
- [ ] Native-speaker feedback collected on the 500  
- [x] `DOCS/WEEK2_REPORT.md` drafted  
- [ ] Supervisor check-in

---

## 8. Stretch → Week 3 prep (silver path — no human review)

See `DOCS/NAVON_TRAINING_READY.md`.

| Milestone | Path |
|-----------|------|
| External EN↔SW (OPUS silver) | `scripts/harvest_external_en_sw.py` → `datasets/parallel/en_sw_pairs.csv` |
| MT merges + splits | `scripts/prepare_mt_training_data.py` → `datasets/mt/` |
| Train dry-run | `scripts/train_baseline.py --dry-run` |
| PSA NLLB silver (on Navon GPU) | `scripts/seed_nllb_sample.py --targets sw,kik` |
| Auto-QC validation sheet | `scripts/auto_qc_validation.py` (`verified` stays false) |
| Human gold (when reviewers exist) | `datasets/gold/gold_translations.csv` |
