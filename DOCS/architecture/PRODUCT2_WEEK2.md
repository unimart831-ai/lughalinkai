# Product 2 — Week 2: Translation Engine & Parallel Data

**Project:** LughaLink AI (DSA 4020)  
**Focus:** Sub-objective 2 — EN/SW alignment + NLLB seeding for Dholuo / Ekegusii / Somali  
**Frozen Week 1 input:** `datasets/processed/week2_ready_psas.csv` (**4,152** clean PSAs)  
**Branch suggestion:** `week2/translation` (cut from `data/governance` or `develop`)

---

## 1. Goal

Turn the cleaned Week 1 English PSA corpus into a **parallel / seeded multilingual dataset** ready for evaluation and light fine-tuning — without pretending we scraped 5,000 native Dholuo PSAs.

Honest strategy (same as Product 1 architecture):

1. Collect / align real **EN↔SW** pairs where they exist  
2. **NLLB-200 zero-shot** seed EN → Dholuo / Ekegusii / Somali  
3. **Native-speaker review** of a gold sample → `datasets/gold/`

---

## 2. Week 1 freeze (do not overwrite)

| File | Role |
|------|------|
| `datasets/processed/week2_ready_psas.csv` | **Canonical frozen clean PSAs for Week 2** |
| `datasets/processed/week2_ready_psas_stats.json` | Freeze stats |
| `datasets/processed/week1_psa_merged.csv` | Working clean sheet (may change) |
| `datasets/processed/week1_psa_quarantined.csv` | Rejected non-PSA / junk (audit only) |
| `datasets/processed/week1_merge_stats.json` | Latest cleaning counts |

Baseline stats (at freeze): **4,152** clean PSAs · domains: Governance 1951, Security 837, Health 838, Education 341, Agriculture 185.

---

## 3. Milestone checklist

| # | Milestone | Owner (suggested) | Done when |
|---|-----------|-------------------|-----------|
| 1 | Freeze Week 1 baseline | Iranzi | `week1_baseline_psa.csv` exists + documented |
| 2 | Fix domain labels on baseline subset | Iranzi + domain leads | Source-prioritized domain rules; spot-check 100 |
| 3 | Boost Education & Agriculture (≥1,000 each, optional parallel track) | Leona / Jesca | New clean rows merged without quarantine junk |
| 4 | EN↔SW parallel harvest | Data + Angela | CSV of true pairs in `datasets/parallel/en_sw_pairs.csv` |
| 5 | Sentence-split seed candidates | Iranzi | `datasets/interim/week2_seed_candidates.csv` |
| 6 | NLLB zero-shot sample (100–500 PSAs) | ML lead | `datasets/parallel/nllb_seeded_sample.csv` with `method=nllb_zero_shot` |
| 7 | Human review gold set (100–500) | Native speakers | `datasets/gold/gold_translations.csv` with `verified=true` |
| 8 | Week 2 report | Iranzi | `DOCS/WEEK2_REPORT.md` — stats, samples, challenges |

---

## 4. Target language codes

See `configs/languages.yaml`.

| Language | NLLB code | Column / field |
|----------|-----------|----------------|
| English | `eng_Latn` | `English` / source |
| Kiswahili | `swh_Latn` | `Kiswahili` |
| Dholuo | `luo_Latn` | target |
| Ekegusii | `guz_Latn` | target |
| Somali | `som_Latn` | target |

---

## 5. Output schemas

### 5.1 Parallel pair row (`datasets/parallel/`)

| Column | Description |
|--------|-------------|
| `pair_id` | `pair_2026_######` |
| `psa_id` | FK to baseline PSA |
| `Domain` | Health / Education / … |
| `source_lang` | `en` or `sw` |
| `target_lang` | `sw` / `luo` / `guz` / `som` |
| `source_text` | Source sentence or PSA body |
| `target_text` | Aligned or seeded text |
| `method` | `human` / `url_aligned` / `nllb_zero_shot` |
| `confidence` | float or empty |
| `verified` | `true` / `false` |
| `Source` | URL |
| `Metadata` | JSON |

### 5.2 Gold row (`datasets/gold/`)

Same as parallel, plus:

| Column | Description |
|--------|-------------|
| `reviewer` | Name / initials |
| `review_notes` | Optional |
| `verified` | Must be `true` |

---

## 6. Repo layout (Week 2)

```
configs/languages.yaml
services/translation/          # seeder + translation record models
scripts/prepare_week2_baseline.py
scripts/seed_nllb_sample.py
datasets/
  processed/week1_baseline_psa.csv
  interim/week2_seed_candidates.csv   # generated
  parallel/                           # EN-SW + NLLB seeds
  gold/                               # human-verified only
DOCS/
  architecture/PRODUCT2_WEEK2.md      # this file
  WEEK2_HANDOFF.md
  WEEK2_REPORT.md                     # end of week
```

---

## 7. Day-by-day (suggested)

| Day | Focus |
|-----|--------|
| 1 | Freeze baseline, cut `week2/translation`, install `[mt]` extras, confirm NLLB loads on one sentence |
| 2 | Domain-label audit + Education/Agriculture gap plan |
| 3 | EN↔SW URL / title alignment script; harvest first 200 pairs |
| 4 | Build seed candidate list (short PSA sentences, balanced domains) |
| 5 | NLLB batch seed 100–500 → Dholuo / Ekegusii / Somali |
| 6 | Human review pass (split by language among teammates / volunteers) |
| 7 | Export gold + draft Week 2 report |

---

## 8. Commands

```bash
# Freeze Week 1 → Week 2 baseline + seed candidates
python scripts/prepare_week2_baseline.py

# Optional: install MT deps (large)
pip install -e ".[mt]"

# Dry-run seeder (no model download)
python scripts/seed_nllb_sample.py --dry-run --limit 5

# Real sample (downloads NLLB — needs disk + RAM/GPU)
python scripts/seed_nllb_sample.py --limit 50 --targets luo,guz,som
```

---

## 9. Rules (non-negotiable)

1. Never put NLLB output into `datasets/gold/` without human `verified=true`.  
2. Never mix quarantine rows back into baseline.  
3. Mark every machine row with `method=nllb_zero_shot`.  
4. Prefer short PSA-length text for seeding (avoid long ReliefWeb reports — already quarantined).  
5. Keep Cursor / AI co-author trailers out of git commits on submission branches.

---

## 10. Definition of done (Week 2)

A teammate can:

```bash
pip install -e ".[dev]"
python scripts/prepare_week2_baseline.py
python scripts/seed_nllb_sample.py --dry-run --limit 5
```

…and find:

- Frozen baseline  
- Seed candidate sheet  
- Parallel + gold folder conventions  
- This plan + handoff doc  

Plus, by end of week: NLLB sample file + ≥100 verified gold rows + `DOCS/WEEK2_REPORT.md`.
