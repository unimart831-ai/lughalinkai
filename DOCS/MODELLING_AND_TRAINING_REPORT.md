# LughaLink AI — Modelling, Training and Evaluation Report

**Course:** DSA 4020A Natural Language Processing  
**Institution:** United States International University–Africa  
**Project:** Machine Translation of Kenyan Public Service Announcements  
**Product:** LughaLink AI  
**Platform:** Navon / Kinesis Shared JupyterLab — NVIDIA A100-SXM4-80GB (Helsinki)  
**Languages:** English (source) · Kiswahili (pivot) · Kikuyu (indigenous, NLLB-native) · Ekegusii (indigenous, NLLB-extended)  
**Report date:** 12 August 2026  

---

## 1. Introduction

### 1.1 Problem

Public service announcements (PSAs) in Kenya—covering health, elections, agriculture, security and governance—are frequently issued first in English. Citizens who prefer Kiswahili or indigenous languages such as Kikuyu and Ekegusii therefore receive weaker, delayed or incomplete access to actionable public information.

### 1.2 Objective

LughaLink builds a transferable machine translation (MT) pipeline for English PSAs into Kiswahili and selected indigenous languages. The work follows the course requirements of curated PSA data, few-shot / transfer learning, automatic evaluation, and a deployable demonstration.

### 1.3 Scope of this report

This report describes:

1. Construction of the English PSA corpus and parallel training data.  
2. Fine-tuning of NLLB-200 for English→Kiswahili and English→Kikuyu.  
3. Extension of NLLB to Ekegusii via a custom language token `guz_Latn`, with zero-shot and few-shot experiments.  
4. Automatic evaluation (BLEU and chrF), interpretation of scores, and deployment status.  

Throughout, we distinguish **human gold** from **machine silver** data and metrics.

---

## 2. Language design

| Role | Language | ISO 639-3 | NLLB code | Status in this project |
|------|----------|-----------|-----------|-------------------------|
| Source | English | eng | `eng_Latn` | Native in NLLB-200 |
| Pivot | Kiswahili | swh | `swh_Latn` | Native; fine-tuned on PSA silver |
| Indigenous (supported) | Kikuyu | kik | `kik_Latn` | Native; fine-tuned on PSA silver |
| Indigenous (extended) | Ekegusii | guz | `guz_Latn` | **Not** in stock NLLB-200; added by vocab extension |

Kiswahili is retained as the national pivot required by the course. Kikuyu was adopted as a fully supported indigenous target. Ekegusii was later required for the indigenous track; because Meta’s NLLB-200 release does not include Ekegusii, a separate technical path was required (Section 5).

---

## 3. Data pipeline

### 3.1 English PSA corpus

English notices were scraped from Kenyan sources (including IEBC, Ministry of Health and related government / NGO channels) and filtered with the PSA Framework classifier (`services/metadata/psa_framework.py`), which separates true public advisories from press releases, tenders and other government text.

| Quantity | Meaning |
|---------:|---------|
| **5,000** | Final English PSA documents (`week2_ready_psas.csv`) |
| **1,615** | Real scraped texts that passed strict PSA rules |
| **3,385** | Framework-valid synthetic PSAs used only to reach course volume (`synthetic=true`) |
| **8,409** | Sentence units prepared for MT (`week2_mt_sentences.csv`) |

Synthetic English rows are documented in `DOCS/SYNTHETIC_PSA_NOTE.md` and are never labelled as human-verified field data.

### 3.2 Parallel data for Kiswahili and Kikuyu

Base NLLB-200 was used in **zero-shot seeding** (not yet fine-tuning) to produce English→Kiswahili and English→Kikuyu pairs from PSA sentences:

| Item | Value |
|------|--------|
| Script | `scripts/seed_nllb_sample.py` |
| Limit | 5,200 English sentences × 2 targets → **10,400** raw pairs |
| Method | `nllb_zero_shot`, `verified=false` |
| After auto-QC | **9,077** kept (SW **4,588** · Kikuyu **4,489**) |
| Splits (historical NLLB-only freeze) | train / dev / test ≈ 7,261 / 906 / 910 |

Seeding uses `src_lang=eng_Latn` and `forced_bos_token_id` for `swh_Latn` or `kik_Latn`. Auto-QC (`silver_qc.py`) removes dry-run placeholders, near-copies and extreme length ratios. OPUS and news bitext were excluded under a PSA-only policy.

### 3.3 Parallel data for Ekegusii

Because NLLB cannot zero-shot seed into a missing language code, EN↔Ekegusii pairs were built from **PSA-oriented Ekegusii templates** and a lexicon (`configs/ekegusii_psa_lexicon.yaml`, `scripts/generate_ekegusii_parallel.py`):

| Item | Value |
|------|--------|
| Output | `datasets/parallel/guz_psa_template.csv` |
| Method | `guz_psa_template`, `verified=false`, `synthetic=true` |
| After QC (merged splits) | **4,288** Ekegusii pairs (with SW/Kikuyu silver retained on Navon) |

These pairs are **silver / template** references: suitable for training and relative evaluation, not native-speaker gold.

When SW, Kikuyu and Ekegusii silver were merged on Navon, kept totals were approximately **SW 4,588 · Kikuyu 5,085 · Ekegusii 4,288** (13,961 pairs overall).

---

## 4. Modelling for Kiswahili and Kikuyu (few-shot / transfer)

### 4.1 Architecture

The primary model is **NLLB-200 distilled 600M** (`facebook/nllb-200-distilled-600M`), an encoder–decoder seq2seq system with strong African-language coverage and native codes for Kiswahili and Kikuyu.

### 4.2 Fine-tuning protocol

| Setting | Value |
|---------|--------|
| Script | `scripts/train_baseline.py` |
| Epochs | 1 |
| Learning rate | 2×10⁻⁵ |
| Batch / accumulation | 4 / 4 (effective 16) |
| Max lengths | 128 / 128 |
| Precision | FP16 on CUDA |
| Seed | 42 |

Fine-tuning adapts pretrained NLLB to the **PSA register** (advisories, IEBC/MoH-style directives). It is transfer / few-shot domain adaptation, not training from random weights.

### 4.3 Training outcomes

| Pair | Train size (approx.) | Train loss (avg) | Eval loss | Checkpoint |
|------|---------------------:|-----------------:|----------:|------------|
| en-kik | ~3,591 | ~3.37 | ~0.19 | `artifacts/mt_baseline/en-kik/final` (~2.3 GB) |
| en-sw | ~3,670 | ~1.82 | ~0.07 | `artifacts/mt_baseline/en-sw/final` (~2.3 GB) |

CLI smoke tests (`scripts/infer_mt.py`) confirmed on-domain Kiswahili and Kikuyu outputs for PSA prompts (for example, hand-washing and IEBC voter notices).

Public Hub mirrors used in deployment documentation:

- `iranzi/lughalink-nllb-psa-en-sw`  
- `iranzi/lughalink-nllb-psa-en-kik`  

---

## 5. Modelling for Ekegusii: the `guz_Latn` token

### 5.1 Why a custom token is required

NLLB-200 associates each supported language with a **language token** of the form `{code}_{Script}` (for example `kik_Latn`). Decoding is steered by setting `forced_bos_token_id` to that token’s vocabulary id.

Ekegusii (ISO 639-3 **guz**) does **not** appear in the FLORES-200 / NLLB-200 language list. There is therefore no stock token that means “generate Ekegusii.” Without intervention, NLLB cannot be asked for EN→Ekegusii in the same way as EN→Kikuyu.

### 5.2 What `guz_Latn` is

We define:

> **`guz_Latn`** = language token for **Ekegusii** (`guz`), **Latin** script (`Latn`).

This string is our project convention, aligned with NLLB’s naming scheme. It is not an official Meta code.

### 5.3 How the token was created (implementation)

Implementation lives in `services/translation/nllb_extend.py` and is used by training, zero-shot evaluation and inference:

1. Load `facebook/nllb-200-distilled-600M` and its tokenizer.  
2. **Register** the new special token `"guz_Latn"` (`add_special_tokens` / `add_tokens`).  
3. **Resize** input (and output) embeddings so the new token has a learnable vector.  
4. **Initialize** that vector by **copying** the embedding of a related language already in NLLB—primarily **`kik_Latn` (Kikuyu)**.  
5. At generation time, force the decoder BOS id to `guz_Latn`.

An ablation that initialized from **`swh_Latn` (Kiswahili)** was also measured; it caused zero-shot outputs to collapse toward Kiswahili and is not the preferred live setting.

### 5.4 Why zero-shot Ekegusii can look like Kikuyu

In **zero-shot** (no gradient updates on Ekegusii pairs), the only Ekegusii-specific information in the network is the new token whose weights were copied from Kikuyu. The decoder therefore tends to produce **Kikuyu-like** text. That behaviour is expected for this baseline; it is not a labelling error in the UI. True Ekegusii specialization requires **few-shot fine-tuning** on EN↔Ekegusii pairs so the `guz_Latn` direction can leave the Kikuyu basin.

---

## 6. Ekegusii experiments: zero-shot and few-shot

### 6.1 Definitions used in this project

| Setting | Meaning in this work |
|---------|----------------------|
| **Zero-shot** | Generate EN→Ekegusii with base mT5 or with NLLB + newly added `guz_Latn` (init from `kik_Latn`), **without** PSA fine-tuning |
| **Few-shot / transfer** | Fine-tune on PSA template EN↔Ekegusii pairs (order of thousands of examples, typically 1 epoch)—same framing as SW/Kikuyu PSA adaptation |

### 6.2 Automatic metrics — what BLEU and chrF mean

- **BLEU** (0–100): overlap of word *n*-grams between system output and a reference translation. Higher means closer to the reference.  
- **chrF** (0–100): similar idea at **character** level; often more informative for morphologically rich Bantu languages.  

**Critical caveat:** for Ekegusii (and for SW/Kikuyu silver eval), references are **not human gold**. Ekegusii references are template silver; SW/Kikuyu test refs are NLLB silver. Scores therefore measure **agreement with silver teachers / templates**, not certified native adequacy. They remain useful for relative comparison (zero-shot vs few-shot; init ablations).

### 6.3 Ekegusii results (Navon, August 2026)

**Primary zero-shot table** (preferred init = `kik_Latn`; file `datasets/interim/mt_eval_ekegusii_zeroshot.json`, first completed run):

| Setting | Model | Detail | BLEU | chrF | n |
|---------|--------|--------|-----:|-----:|--:|
| Zero-shot | mT5-small | Prompt `translate English to Ekegusii:` | **0.007** | **0.95** | 50 |
| Zero-shot | NLLB-200 600M | `guz_Latn` extended, init **`kik_Latn`** | **0.26** | **13.0** | 50 |

**Init ablation** (same protocol, init from Swahili):

| Setting | Model | Detail | BLEU | chrF | n |
|---------|--------|--------|-----:|-----:|--:|
| Zero-shot | NLLB-200 600M | `guz_Latn` init **`swh_Latn`** | 0.16 | 11.9 | 50 |

**Few-shot mT5** (1 epoch on PSA template pairs; `mt_eval_results.json`):

| Setting | Model | BLEU | chrF | n |
|---------|--------|-----:|-----:|--:|
| Few-shot | mT5 `artifacts/mt_baseline/mt5-en-guz/final` | **0.003** | **1.05** | 430 |

**Few-shot NLLB (en-guz):** not completed. Shared A100 memory was occupied by other tenants (often &lt;10 MB free after model load), so Adam state allocation failed with CUDA OOM. CPU fine-tuning was judged too slow for the deadline.

### 6.4 Interpretation

1. **Near-zero mT5 scores** (zero- and few-shot) show that `mt5-small` did not acquire usable Ekegusii PSA translation under our one-epoch setup; interactive outputs often collapsed to sentinel tokens such as `<extra_id_0>`.  
2. **NLLB zero-shot with `guz_Latn`** is weak in absolute terms but **stronger than mT5** on the same silver test slice, and qualitatively produces Bantu-script output rather than English echo.  
3. **Kikuyu-like zero-shot text** follows directly from embedding initialisation (Section 5.4).  
4. Completing **NLLB few-shot on `en-guz`** remains the principal next step to move outputs away from the Kikuyu prior.

---

## 7. Evaluation for Kiswahili and Kikuyu (silver test)

| Pair | Model | n | BLEU | chrF |
|------|--------|--:|-----:|-----:|
| en-kik | NLLB fine-tuned | 450 | **72.5** | **84.5** |
| en-sw | NLLB fine-tuned | 460 | **89.6** | **94.7** |

These high figures indicate close agreement with **NLLB silver references**, not proven human quality. Kiswahili exceeds Kikuyu, consistent with stronger NLLB pretraining for Swahili. Human evaluation sheets (`human_eval_100.csv`, `HUMAN_EVAL_GUIDE.md`) remain the path to gold-standard claims.

---

## 8. Deployment

### 8.1 Serving architecture

A FastAPI application (`apps/api/main.py`) serves a browser UI (`apps/api/static/`). The browser only calls `POST /translate`; model weights stay on the server (Navon or Hub).

| UI target | Backend in production demo |
|-----------|----------------------------|
| Kiswahili | Fine-tuned NLLB (`en-sw` local or Hub) |
| Kikuyu | Fine-tuned NLLB (`en-kik` local or Hub) |
| Ekegusii | Neural **zero-shot NLLB** with extended `guz_Latn` (init from `kik_Latn`) |

Public access for demonstration used an ngrok tunnel to the Navon API when Hugging Face free Spaces were unavailable.

### 8.2 Honesty in the live product

The live Ekegusii path is deliberately the **neural zero-shot model**, even when scores are near zero and outputs resemble Kikuyu. Template-only rendering was explored for readability but is **not** the preferred scientific demonstration when the brief requires model-based translation.

---

## 9. Limitations

1. Parallel SW/Kikuyu/Ekegusii training and test material is **silver**, not native gold.  
2. Synthetic English PSAs increase volume and are labelled separately from real scrapes.  
3. Automatic metrics against silver refs are **relative**.  
4. Ekegusii is outside stock NLLB-200; `guz_Latn` is a project extension.  
5. Ekegusii **few-shot NLLB** was blocked by shared-GPU memory contention.  
6. Few-shot mT5 for Ekegusii did not yield usable interactive translations.  
7. Human cultural / fluency review is still pending.

---

## 10. Conclusions

LughaLink delivers an end-to-end PSA MT story for Kenya:

- A curated English PSA freeze with transparent real/synthetic labelling.  
- Few-shot NLLB adaptation for **Kiswahili** and **Kikuyu**, with strong silver-reference BLEU/chrF and a working web demo.  
- A documented path for **Ekegusii**: definition and implementation of **`guz_Latn`**, zero-shot and few-shot experiments, and clear explanation of why zero-shot outputs track Kikuyu until NLLB few-shot can finish.

The project prioritises methodological honesty: low Ekegusii automatic scores are reported as expected baselines for an unsupported language, not as failure of the overall pipeline.

---

## 11. References to project artefacts

| Artefact | Path / identifier |
|----------|-------------------|
| Language config | `configs/languages.yaml` |
| Ekegusii lexicon | `configs/ekegusii_psa_lexicon.yaml` |
| NLLB token extension | `services/translation/nllb_extend.py` |
| Zero-shot eval script | `scripts/eval_ekegusii_zeroshot.py` |
| Zero-shot results | `datasets/interim/mt_eval_ekegusii_zeroshot.json` |
| SW/Kikuyu / mT5 eval | `datasets/interim/mt_eval_results.json` |
| Ekegusii note | `DOCS/EKEGUSII_NOTE.md` |
| API / UI | `apps/api/` |

---

*End of report.*
