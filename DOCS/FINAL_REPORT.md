# LughaLink AI — Final Project Report (DSA 4020)

**Course:** DSA 4020A Natural Language Processing  
**Project:** Machine Translation of Public Service Announcements (Kenya)  
**Team product:** LughaLink AI  
**Languages:** English (source) · Kiswahili (pivot) · Kikuyu (indigenous target)

---

## 1. Problem and impact

Kenyan PSAs (health, elections, agriculture, security, governance) are often published in English. Citizens who prefer Kiswahili or indigenous languages need accurate, action-oriented translations. LughaLink is a proof-of-concept **digital public good**: scrape/curate PSAs → build parallel data → few-shot fine-tune multilingual MT → evaluate → deploy a web demo.

## 2. Sub-objective 1 — Dataset

| Item | Result |
|------|--------|
| English PSA freeze | **5,000** rows (`datasets/processed/week2_ready_psas.csv`) |
| Real strict PSAs | **1,615** (`synthetic=false`) |
| Framework-valid synthetic PSAs | **3,385** (documented in `DOCS/SYNTHETIC_PSA_NOTE.md`) |
| MT sentence candidates | **8,409** (`week2_mt_sentences.csv`) |
| Parallel policy | **PSA-only** (OPUS / news bitext excluded from training) |
| Indigenous language | **Kikuyu** (`kik_Latn` in NLLB-200) |

**Scale-up target:** seed `--limit 5200` on Navon for EN→SW and EN→Kikuyu to approach ≥5,000 pairs per language after auto-QC (`scripts/navon_scale_and_train.sh`).

**Honesty:** Machine translations are **silver** (`verified=false`) until human reviewers complete `datasets/gold/human_eval_100.csv`.

## 3. Sub-objective 2 — Modeling (few-shot transfer)

| Model | Role | Train entrypoint |
|-------|------|------------------|
| `facebook/nllb-200-distilled-600M` | Primary multilingual MT | `python scripts/train_baseline.py --model nllb --pair en-kik` |
| `google/mt5-small` | Second pretrained family | `python scripts/train_baseline.py --model mt5 --pair en-kik` |

- Platform: Navon / Kinesis Shared A100 (Helsinki).
- Checkpoints: `artifacts/mt_baseline/{en-kik,en-sw,mt5-en-kik,mt5-en-sw}/final` (not in git; local backup under `model/`).
- Tracking: `artifacts/*/train_meta.json` + `datasets/interim/experiment_log.csv`.
- Inference CLI: `python scripts/infer_mt.py --pair en-kik --text "..."`.

**Ablation:** zero-shot NLLB silver references vs fine-tuned hypotheses via `evaluate_mt.py --write-ablation`.

## 4. Sub-objective 3 — Evaluation

| Track | Method |
|-------|--------|
| Automatic | SacreBLEU + chrF (`scripts/evaluate_mt.py`) → `mt_eval_results.json` |
| Human | Sheet + guide ready; scores filled when reviewers available |
| Caveat | Test references are silver unless humans edit — scores are **relative** |

Human pack:

- `datasets/gold/human_eval_100.csv`
- `DOCS/HUMAN_EVAL_GUIDE.md` (fluency / adequacy / cultural accuracy, 1–5)

## 5. Sub-objective 4 — Deployment

```bash
pip install streamlit transformers torch sentencepiece
streamlit run app/streamlit_mt.py
```

Set `LUGHALINK_MODEL_DIR` to the folder that contains `en-kik/final` (extracted backup or `artifacts/mt_baseline`). Demo features: example PSAs, language select, model family select, feedback CSV.

## 6. Limitations

1. Parallel Kikuyu/SW data before scale-up was few-shot (~hundreds of pairs); full brief volume needs Navon `--limit 5200` run.
2. Synthetic English PSAs inflate monolingual count; reported separately from real scrapes.
3. No human gold at training time — do not claim production-quality indigenous MT.
4. Ekegusii/Dholuo/Somali examples in the brief were replaced by Kikuyu for NLLB support.
5. Large weights must stay out of GitHub (~2.3 GB each).

## 7. Reproducibility (short)

```bash
git pull
pip install -e ".[mt]"
# On Navon GPU:
bash scripts/navon_scale_and_train.sh
python scripts/evaluate_mt.py --pair en-kik --model nllb --write-ablation
python scripts/prepare_human_eval.py
streamlit run app/streamlit_mt.py
```

## 8. Demo-day checklist

- [ ] Scaled silver + retrained NLLB/mT5 checkpoints loaded
- [ ] Live Streamlit translate of a real IEBC/MoH-style PSA → SW and Kikuyu
- [ ] Metrics table (BLEU/chrF) + honesty about silver refs
- [ ] Human eval sheet status (pending / in progress / done)
- [ ] Q&A: PSA Framework filter, synthetic fill, why Kikuyu
