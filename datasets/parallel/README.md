# Parallel data

## Language plan

| Language | Role |
|----------|------|
| English | Source (PSA corpus) |
| Kiswahili | Pivot (`sw`) |
| Kikuyu | Indigenous target (`kik`) |

## Use for training (PSA only)

| File | Role |
|------|------|
| `nllb_psa_silver.csv` | NLLB drafts of **our PSA sentences** (`psa_id` set). Train on this after auto-QC. |

Generate on Navon:

```bash
python scripts/seed_nllb_sample.py \
  --input datasets/interim/week2_mt_sentences.csv \
  --targets sw,kik --limit 820 \
  --output datasets/parallel/nllb_psa_silver.csv
```

## Do NOT use for LughaLink training

| File | Why |
|------|-----|
| `en_sw_pairs.csv` | OPUS GlobalVoices — general news, **not PSAs**. Excluded by PSA-only prepare. |
| `nllb_seeded_sample.csv` | Old dry-run placeholders. |

All training rows stay `verified=false` until a human reviews them.
