# Ekegusii (guz) — technical note

**Status:** Ekegusii is added **alongside** Kiswahili and Kikuyu (Kikuyu is not replaced).  
**Full report:** [MODELLING_AND_TRAINING_REPORT.md](MODELLING_AND_TRAINING_REPORT.md) (§5–§6).

## The `guz_Latn` token

Stock NLLB-200 has no Ekegusii language id. We register **`guz_Latn`** (Ekegusii + Latin script), resize embeddings, initialise from **`kik_Latn`**, and force that id as decoder BOS. Implementation: `services/translation/nllb_extend.py`.

Zero-shot outputs resemble Kikuyu because the new token starts as a copy of Kikuyu’s embedding. That is expected until few-shot NLLB on EN↔Ekegusii completes.

## Parallel data

| Item | Value |
|------|--------|
| Script | `scripts/generate_ekegusii_parallel.py` |
| Lexicon | `configs/ekegusii_psa_lexicon.yaml` |
| Output | `datasets/parallel/guz_psa_template.csv` |
| Method | `guz_psa_template` · `verified=false` |
| Kept after QC | ~4,288 pairs |

## Recorded scores (silver / template refs)

| Setting | Model | BLEU | chrF |
|---------|--------|-----:|-----:|
| Zero-shot | mT5-small | 0.007 | 0.95 |
| Zero-shot | NLLB + `guz_Latn` (init `kik_Latn`) | **0.26** | **13.0** |
| Zero-shot ablation | NLLB (init `swh_Latn`) | 0.16 | 11.9 |
| Few-shot | mT5 1 epoch | 0.003 | 1.05 |
| Few-shot | NLLB | *blocked — shared A100 OOM* | |

## Commands

```bash
python scripts/eval_ekegusii_zeroshot.py --family nllb
python scripts/train_baseline.py --model nllb --pair en-guz --epochs 1
bash scripts/navon_train_ekegusii.sh
```

## Live UI

Prefer neural zero-shot NLLB (not templates):

```bash
export LUGHALINK_GUZ_BACKEND=nllb
export LUGHALINK_MODEL_GUZ=facebook/nllb-200-distilled-600M
# nllb_vocab_extend.init_from: kik_Latn in configs/mt_train.yaml
```
