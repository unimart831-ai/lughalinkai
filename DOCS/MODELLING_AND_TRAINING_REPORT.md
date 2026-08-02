# LughaLink AI — Modelling and Training Report

**Course:** DSA 4020A Natural Language Processing  
**Project:** Machine Translation of Public Service Announcements (Kenya)  
**Report type:** Week 3 modelling & training (detailed)  
**Platform:** Navon / Kinesis Shared — JupyterLab, NVIDIA A100-SXM4-80GB (Helsinki)  
**Languages:** English (source) · Kiswahili (pivot) · Kikuyu (indigenous target)  
**Status date:** 3 August 2026  

---

## 1. Executive summary

This report documents how LughaLink built and fine-tuned multilingual machine translation models for Kenyan Public Service Announcements (PSAs). We:

1. Froze a **framework-strict** English PSA corpus (5,000 documents).
2. Split it into MT sentence units (~8,409).
3. Generated **PSA-only silver parallel data** with pretrained NLLB-200 (EN→SW, EN→Kikuyu).
4. Auto-QC filtered and split into train/dev/test.
5. **Fine-tuned** `facebook/nllb-200-distilled-600M` separately for `en-kik` and `en-sw`.
6. Verified both checkpoints with CLI inference on real PSA-style prompts.
7. Packaged checkpoints for backup (`lughalink_mt_scaled.tar.gz`, ~4.3 GB).

**Important honesty:** parallel targets are **machine silver** (`verified=false`), not native-speaker gold. Automatic metrics (BLEU/chrF) therefore compare a fine-tuned model against silver references and must be read as **relative** quality signals, not human adequacy.

A second pretrained family (mT5) and a custom product UI are **out of scope for this report’s completed work** and are planned next.

---

## 2. Objectives (mapped to the course brief)

| Course sub-objective | What we did in this phase |
|----------------------|---------------------------|
| Curate multilingual PSA data | Scaled PSA silver pairs toward ~5k/language after QC |
| Few-shot / transfer learning | Fine-tuned NLLB-200 distilled 600M on PSA bitext |
| Evaluate accuracy | CLI smoke tests + automatic metrics (SacreBLEU/chrF) |
| Deployable public good | Working CLI inference; polished UI deferred |

**Language choice:** Kikuyu (`kik_Latn`) replaced earlier Ekegusii/Dholuo/Somali candidates because Kikuyu is properly supported in NLLB-200, enabling reliable zero-shot seeding and fine-tuning.

---

## 3. Data pipeline (what the model was trained on)

### 3.1 English PSA freeze (upstream)

| Item | Path / value |
|------|----------------|
| Frozen corpus | `datasets/processed/week2_ready_psas.csv` |
| Total rows | **5,000** |
| Real strict PSAs | **1,615** (`synthetic=false`) |
| Framework-valid synthetic | **3,385** (`synthetic=true`; see `DOCS/SYNTHETIC_PSA_NOTE.md`) |
| Filter | PSA Framework scorer (`services/metadata/psa_framework.py`) |

Synthetic rows were used only to reach course volume after strict filtering cut the scraped set; they are labeled and reported separately. They are **not** claimed as scraped field data.

### 3.2 Sentence sheet for MT

| Item | Value |
|------|--------|
| File | `datasets/interim/week2_mt_sentences.csv` |
| Rows | **8,409** sentences (+ header → 8410 lines) |
| Origin | Sentence-split of the same strict PSA freeze |
| Policy | PSA text only |

Navon briefly had a corrupted shorter copy (3410 lines); it was restored from git (`git checkout HEAD -- …`) before large-scale seeding.

### 3.3 Silver parallel seeding (Stage A — not fine-tuning)

| Item | Value |
|------|--------|
| Script | `scripts/seed_nllb_sample.py` |
| Base model | `facebook/nllb-200-distilled-600M` |
| Source code | `eng_Latn` |
| Targets | `swh_Latn` (sw), `kik_Latn` (kik) |
| Limit | **5200** English sentences |
| Output | `datasets/parallel/nllb_psa_silver.csv` |
| Rows written | **10,400** (5200 × 2) |
| Method | `nllb_zero_shot` |
| Verified | all `false` |

**What this stage is:** using a **pretrained** multilingual model to generate first-pass translations.  
**What it is not:** updating NLLB weights yet.

Mechanism: tokenizer `src_lang=eng_Latn`, generation with `forced_bos_token_id` set to the target language ID, beam search (`num_beams=4`).

### 3.4 Auto-QC and splits (PSA-only)

Command: `python scripts/prepare_mt_training_data.py`

| Stat | Value |
|------|--------|
| Policy | `psa_only` (OPUS `en_sw_pairs.csv` skipped) |
| Parallel raw | 10,400 |
| Rejected / filtered | 1,323 |
| Kept pairs | **9,077** |
| By method | `nllb_zero_shot`: 9077 |
| Kikuyu kept | **4,489** |
| Kiswahili kept | **4,588** |
| Train / dev / test | **7261 / 906 / 910** |
| Sentence sheet after prepare | still **8409** rows (keep-existing fix) |

Outputs: `datasets/mt/{train,dev,test,all_pairs}.csv`.

Auto-QC rejects dry-run placeholders, near-copies, and pathological length ratios (`services/translation/silver_qc.py`).

---

## 4. Modelling approach

### 4.1 Base architecture

| Field | Choice |
|-------|--------|
| Primary model | NLLB-200 distilled 600M |
| HF id | `facebook/nllb-200-distilled-600M` |
| Type | Encoder–decoder seq2seq |
| Why | Strong African-language coverage; official Kikuyu + Kiswahili codes; fits A100 fine-tune |

Config: `configs/mt_train.yaml`, languages: `configs/languages.yaml`.

### 4.2 Fine-tuning setup (Stage B)

| Hyperparameter | Value |
|----------------|--------|
| Script | `scripts/train_baseline.py` |
| Epochs (this run) | **1** |
| Learning rate | 2e-5 |
| Train batch size | 4 |
| Grad accumulation | 4 |
| Effective batch | 16 |
| Max source / target length | 128 / 128 |
| FP16 | enabled on CUDA |
| Seed | 42 |
| Eval / save | steps (200) |
| Report to | none (local `train_meta.json` + `experiment_log.csv`) |

**Hugging Face API compatibility** (Navon transformers): script uses `eval_strategy` / `processing_class` when available so training works on current `Seq2SeqTrainer`.

### 4.3 What “fine-tuning” means here

```text
Pretrained NLLB weights
        +
PSA silver bitext (EN→SW or EN→Kikuyu)
        ↓
Gradient updates for 1 epoch
        ↓
Domain-adapted checkpoint in artifacts/mt_baseline/<pair>/final
```

We are **not** training Kikuyu or Swahili MT from random initialization. We are adapting a general multilingual translator to **PSA register** (advisories, IEBC/MoH-style directives).

---

## 5. Training runs (completed)

### 5.1 Dry-run validation (before GPU train)

| Pair | Train | Dev | Test | `ready_for_gpu` |
|------|------:|----:|-----:|-----------------|
| en-kik | ~3591 used in map* | 200 eval cap | (from split) | **true** |
| en-sw | 3670 | 458 | 460 | **true** |

\*Trainer may cap eval samples via `max_eval_samples: 200` in config.

Samples confirmed `method: nllb_zero_shot` with real SW/Kikuyu text (not dry-run placeholders).

### 5.2 Fine-tune: English → Kikuyu

| Field | Result |
|-------|--------|
| Command | `python scripts/train_baseline.py --model nllb --pair en-kik --epochs 1` |
| Train examples mapped | 3,591 |
| Eval examples mapped | 200 |
| Train runtime | ~107 s |
| Train loss (avg) | ~3.37 |
| Final logged loss | ~1.05 (late steps; early ~16) |
| Eval loss | ~0.188 |
| Checkpoint | `artifacts/mt_baseline/en-kik/final` |
| Weights file | `model.safetensors` **2.3 GB** |

### 5.3 Fine-tune: English → Kiswahili

| Field | Result |
|-------|--------|
| Command | `python scripts/train_baseline.py --model nllb --pair en-sw --epochs 1` |
| Train examples mapped | 3,670 |
| Eval examples mapped | 200 |
| Train runtime | ~110 s |
| Train loss (avg) | ~1.82 |
| Late step loss | ~0.36 |
| Eval loss | ~0.074 |
| Checkpoint | `artifacts/mt_baseline/en-sw/final` |
| Weights file | `model.safetensors` **2.3 GB** |

### 5.4 Qualitative CLI smoke tests (`scripts/infer_mt.py`)

**Kikuyu (`en-kik`):**

| Source | Hypothesis (model) |
|--------|--------------------|
| The public is advised to follow official health guidelines. | Andũ aingĩ nĩ maraheo ũtaaro wa kũrũmĩrĩra ũtaaro wa thirikari wĩgiĩ ũgima wa mwĩrĩ. |
| IEBC reminds voters to verify their details on the official portal. | IEBC nĩ ĩririkanaga ateti kũmenyeria ũhoro wao kĩhũngĩro-inĩ kĩa thirikari. |

**Kiswahili (`en-sw`):**

| Source | Hypothesis (model) |
|--------|--------------------|
| The public is advised to follow official health guidelines. | Umma unashauriwa kufuata miongozo rasmi ya afya. |
| IEBC reminds voters to verify their details on the official portal. | IEBC inawakumbusha wapiga kura kuthibitisha maelezo yao kwenye portal rasmi. |

Smoke tests confirm: checkpoints load, forced language codes work, outputs are target-language PSA-style text (not English echo / dry-run tags).

---

## 6. Automatic evaluation (SacreBLEU / chrF)

Evaluation command pattern:

```bash
pip install sacrebleu evaluate
python scripts/evaluate_mt.py --pair en-kik --model nllb --write-ablation
python scripts/evaluate_mt.py --pair en-sw --model nllb --write-ablation
```

Results are written to `datasets/interim/mt_eval_results.json` and optional ablation CSV `datasets/interim/ablation_zero_vs_ft.csv`.

### 6.1 Metrics table (completed 2026-08-02 Navon)

| Pair | Model | n (test) | BLEU | chrF | Checkpoint |
|------|-------|---------:|-----:|-----:|------------|
| en-kik | nllb fine-tuned | 450 | **72.54** | **84.55** | `artifacts/mt_baseline/en-kik/final` |
| en-sw | nllb fine-tuned | 460 | **89.58** | **94.75** | `artifacts/mt_baseline/en-sw/final` |

Raw logs also landed in `datasets/interim/mt_eval_results.json` on Navon; ablation rows in `datasets/interim/ablation_zero_vs_ft.csv`.

### 6.2 How to read these scores

- Test **references are silver NLLB** (same generation family as the seed), not human translations.
- **Why scores look very high:** the fine-tuned model is evaluated against references that were themselves produced by NLLB-style silver seeding. BLEU/chrF therefore largely measure **agreement with the silver teacher**, not native-speaker adequacy.
- **en-sw > en-kik** is expected: Kiswahili is much stronger in NLLB pretraining than Kikuyu, so silver refs and the fine-tuned student align more tightly.
- Still useful for: run-to-run comparison (small seed vs scaled seed; later mT5 vs NLLB) and confirming the checkpoint generates stably on the held-out split.
- **Not sufficient alone for the course “cultural appropriateness” claim** — that needs `datasets/gold/human_eval_100.csv` + `DOCS/HUMAN_EVAL_GUIDE.md` when reviewers arrive.

---

## 7. Engineering issues encountered and fixes

| Issue | Fix |
|-------|-----|
| `evaluation_strategy` unexpected kwarg | Use `eval_strategy` when present (transformers ≥4.41) |
| `tokenizer=` unexpected on Trainer | Use `processing_class` when present |
| `git pull` blocked by local Navon patches | `git checkout -- scripts/train_baseline.py` then pull |
| Sentence sheet shrunk to 3410 after prepare | Restored from git; prepare now **keeps** existing sheet unless `--refresh-sentences` |
| Blocked Kinesis app (`lughalink-mt`) | Use **My First Project → JupyterLab** instead |
| Ephemeral `/tmp` / pod risk | Archive to `~/lughalink_mt_scaled.tar.gz` (~4.3 GB) and download |

---

## 8. Artifacts and reproducibility

### 8.1 Key artifacts

| Artifact | Location |
|----------|----------|
| Silver pairs | `datasets/parallel/nllb_psa_silver.csv` |
| MT splits | `datasets/mt/` |
| Kikuyu checkpoint | `artifacts/mt_baseline/en-kik/final` |
| Swahili checkpoint | `artifacts/mt_baseline/en-sw/final` |
| Backup archive | `~/lughalink_mt_scaled.tar.gz` (~4.3 GB) |
| Experiment log | `datasets/interim/experiment_log.csv` |
| Human eval sheet | `datasets/gold/human_eval_100.csv` |

Large weights are **gitignored** (`artifacts/`, `model/`, `*.safetensors`).

### 8.2 Reproduce training (Navon)

```bash
cd ~/lughalinkai
git pull
pip install -e ".[mt]"

# (already done) seed + prepare + train
python scripts/seed_nllb_sample.py \
  --input datasets/interim/week2_mt_sentences.csv \
  --targets sw,kik --limit 5200 \
  --output datasets/parallel/nllb_psa_silver.csv
python scripts/prepare_mt_training_data.py
python scripts/train_baseline.py --model nllb --pair en-kik --epochs 1
python scripts/train_baseline.py --model nllb --pair en-sw --epochs 1

# verify
python scripts/infer_mt.py --model nllb --pair en-kik --text "..."
python scripts/evaluate_mt.py --pair en-kik --model nllb --write-ablation
```

---

## 9. Limitations

1. **Silver targets** — no human gold in the training loop yet.  
2. **Synthetic English PSAs** inflate monolingual volume; reported separately from real scrapes.  
3. **One epoch** — more epochs may help but risk overfitting to silver teacher style.  
4. **Eval vs silver** — automatic metrics are relative.  
5. **Single model family completed** — mT5 second baseline still pending.  
6. **UI deferred** — product interface will be designed after modelling is solid; CLI is the verification surface.

---

## 10. Conclusions

- We successfully moved from a small pilot (~500 seed sentences) to a **scaled PSA silver set (~9k kept pairs)** and **fine-tuned NLLB** for both Kiswahili and Kikuyu.
- CLI inference shows the models produce on-domain translations for PSA-style English inputs.
- Automatic eval on silver test refs: **en-kik BLEU 72.5 / chrF 84.5** (n=450); **en-sw BLEU 89.6 / chrF 94.7** (n=460). These validate training stability and teacher agreement; they are **not** human-gold quality scores.
- Modelling + automatic evaluation for NLLB are complete for this phase. Human review remains pending; mT5 and custom UI are next phases.

---

## 11. Appendix — Stage timeline (this Navon session)

1. Sync repo; resolve local `train_baseline.py` conflict; restore 8410-line sentence sheet.  
2. Seed NLLB `--limit 5200` → 10,400 silver rows.  
3. `prepare_mt_training_data.py` → 9,077 kept; splits 7261/906/910.  
4. Dry-run `en-kik` / `en-sw` → `ready_for_gpu: true`.  
5. Fine-tune `en-kik` → checkpoint 2.3 GB; smoke OK.  
6. Fine-tune `en-sw` → checkpoint 2.3 GB; smoke OK.  
7. Package `lughalink_mt_scaled.tar.gz` (4.3 GB).  
8. Run automatic evaluation → §6.1 filled (en-kik + en-sw).  

---

*End of modelling and training report.*
