# Ekegusii (guz) — zero-shot + few-shot notes

**Status:** Ekegusii added **alongside** Kiswahili and Kikuyu (Kikuyu not replaced).

## Why NLLB zero-shot is special for Ekegusii

Ekegusii (`guz`) is **not** in stock NLLB-200 / FLORES-200 (no native `guz_Latn`).  
We still use **NLLB-200** by:

1. Adding a language token `guz_Latn`
2. Initializing its embedding from related Bantu `kik_Latn`
3. Measuring **zero-shot** (no PSA fine-tune) then **few-shot** (1-epoch PSA fine-tune)

This is vocabulary extension + transfer — not Meta-native Ekegusii support.

## Parallel data

| Item | Value |
|------|--------|
| Script | `scripts/generate_ekegusii_parallel.py` |
| Lexicon | `configs/ekegusii_psa_lexicon.yaml` |
| Output | `datasets/parallel/guz_psa_template.csv` |
| Method | `guz_psa_template` |
| Verified | `false` (template silver, not human gold) |

English sources reuse `datasets/interim/week2_mt_sentences.csv`.

## Experiments (course framing)

| Setting | Command sketch |
|---------|----------------|
| Zero-shot mT5 | `python scripts/eval_ekegusii_zeroshot.py --family mt5` |
| Zero-shot NLLB+`guz_Latn` | `python scripts/eval_ekegusii_zeroshot.py --family nllb` |
| Few-shot mT5 | `python scripts/train_baseline.py --model mt5 --pair en-guz --epochs 1` |
| Few-shot NLLB | `python scripts/train_baseline.py --model nllb --pair en-guz --epochs 1` |

One-shot Navon: `bash scripts/navon_train_ekegusii.sh`

## Hub / UI (after train)

- Prefer: `LUGHALINK_MODEL_GUZ=iranzi/lughalink-nllb-psa-en-guz`
- Fallback: `LUGHALINK_MODEL_GUZ_MT5=iranzi/lughalink-mt5-psa-en-guz`
- Backend: `LUGHALINK_GUZ_BACKEND=nllb` or `mt5`
- UI pills: Kiswahili · Kikuyu · Ekegusii

## Live UI note (pre-few-shot)

Live Ekegusii uses **neural** NLLB zero-shot with vocab-extended `guz_Latn` (init from `swh_Latn` or `kik_Latn`). Scores may be near zero / output may resemble the init language — that is an honest baseline until few-shot NLLB finishes.

```bash
export LUGHALINK_GUZ_BACKEND=nllb
export LUGHALINK_MODEL_GUZ=facebook/nllb-200-distilled-600M
```

Optional demo-only: `LUGHALINK_GUZ_BACKEND=template` (not the preferred product path).

