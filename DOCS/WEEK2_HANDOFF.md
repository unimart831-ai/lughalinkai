# Week 1 → Week 2 Handoff

**Date:** 27 July 2026  
**From:** Week 1 Data Collection & Curation  
**To:** Week 2 Translation Engine & Parallel Data

---

## What is locked

| Item | Location | Notes |
|------|----------|-------|
| **Week 2 ready PSAs (USE THIS)** | `datasets/processed/week2_ready_psas.csv` | **Frozen clean corpus for Product 2** |
| Stats | `datasets/processed/week2_ready_psas_stats.json` | Row/domain counts at freeze |
| Working clean sheet | `datasets/processed/week1_psa_merged.csv` | Same content; may be regenerated later |
| Baseline mirror | `datasets/processed/week1_baseline_psa.csv` | Synced copy of the freeze |
| Quarantine (non-PSA) | `datasets/processed/week1_psa_quarantined.csv` | Do **not** use for translation |

**Gate before Product 2:** use only `week2_ready_psas.csv`. Do not seed NLLB from quarantine or raw teammate dumps.

```bash
# recreate freeze from current clean sheet if needed
python -c "import shutil; shutil.copy('datasets/processed/week1_psa_merged.csv','datasets/processed/week2_ready_psas.csv')"
python scripts/prepare_week2_baseline.py
```

---

## Known gaps to carry forward

1. **Strict clean volume is 559** — quality-first cut; Education (25) and Agriculture (7) need real PSA collection, not gate loosening.  
2. **Kiswahili** almost empty (3 rows in clean sheet).  
3. **~2,700 rows** were long articles/reports (`too_long_for_psa`); **~379** were country briefs/situation reports; **~145** were institutional news PR.  
4. Domain mislabels may still exist inside the clean set — spot-check before seeding.  
5. Raw teammate files remain gitignored; only clean + quarantine sheets are public.

---

## Week 2 starting checklist

- [x] Read [PRODUCT2_WEEK2.md](architecture/PRODUCT2_WEEK2.md) — aligned to course EDA week  
- [x] Run `python scripts/prepare_week2_processing.py` (cleaned + splits + 500 validation + EDA stats)  
- [x] Open `notebooks/week2_eda.ipynb` / draft `DOCS/WEEK2_REPORT.md`  
- [ ] Collect native-speaker feedback on `datasets/gold/native_validation_500.csv`  
- [ ] Optional stretch: `python scripts/prepare_week2_baseline.py` + EN↔SW harvest / NLLB seed  
- [ ] Install MT extras only when ready to seed: `pip install -e ".[mt]"`  

---

## Do not

- Re-scrape junk NGO about-pages or Treasury nav dumps into the clean sheet  
- Commit `Co-authored-by: Cursor` trailers  
- Publish NLLB output as “human parallel data”  
- Force-push `main`  

---

## Contacts / owners

| Track | Owner |
|-------|--------|
| Baseline + pipeline | Iranzi Innocent |
| Health EN/SW | Angela Irungu |
| Education volume + review | Leona Kamau |
| Security / Agriculture + review | Jesca Kimani |
