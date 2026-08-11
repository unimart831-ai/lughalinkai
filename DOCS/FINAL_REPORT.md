# LughaLink AI — Final Project Report (DSA 4020)

**Course:** DSA 4020A Natural Language Processing  
**Project:** Machine Translation of Public Service Announcements (Kenya)  
**Team product:** LughaLink AI  
**Languages:** English (source) · Kiswahili (pivot) · Kikuyu · Ekegusii  

**Detailed modelling write-up:** [MODELLING_AND_TRAINING_REPORT.md](MODELLING_AND_TRAINING_REPORT.md)

---

## 1. Problem and impact

Kenyan PSAs (health, elections, agriculture, security, governance) are often published in English. Citizens who prefer Kiswahili or indigenous languages need accurate, action-oriented translations. LughaLink is a proof-of-concept **digital public good**: scrape/curate PSAs → build parallel data → few-shot fine-tune multilingual MT → evaluate → deploy a web demo.

---

## 2. Dataset

| Item | Result |
|------|--------|
| English PSA freeze | **5,000** (`week2_ready_psas.csv`) |
| Real strict PSAs | **1,615** |
| Framework-valid synthetic | **3,385** (see `SYNTHETIC_PSA_NOTE.md`) |
| MT sentence candidates | **8,409** |
| Policy | PSA-only (no OPUS/news in training) |
| SW/Kikuyu silver after QC | **9,077** pairs (historical NLLB seed) |
| Ekegusii template pairs after QC | **4,288** (`guz_psa_template`) |

Machine targets remain **silver** (`verified=false`) until human review.

---

## 3. Modelling

| Direction | Approach |
|-----------|----------|
| EN→Kiswahili | NLLB-200 fine-tuned on PSA silver (`swh_Latn`) |
| EN→Kikuyu | NLLB-200 fine-tuned on PSA silver (`kik_Latn`) |
| EN→Ekegusii | NLLB **vocab extension** with custom token **`guz_Latn`** (init from `kik_Latn`); zero-shot neural baseline; few-shot NLLB pending GPU; mT5 few-shot attempted |

**What `guz_Latn` is:** our extended NLLB language token for Ekegusii (ISO `guz`) in Latin script. Stock NLLB-200 has no Ekegusii code; we register the token, resize embeddings, copy Kikuyu’s vector as initialisation, and force it as decoder BOS. Zero-shot outputs therefore resemble Kikuyu until few-shot fine-tuning on Ekegusii pairs succeeds. Full explanation: modelling report §5.

Secondary family: `google/mt5-small` (used in Ekegusii zero-/few-shot experiments).

---

## 4. Evaluation

### 4.1 Kiswahili and Kikuyu (fine-tuned NLLB vs silver refs)

| Pair | BLEU | chrF | n |
|------|-----:|-----:|--:|
| en-kik | **72.5** | **84.5** | 450 |
| en-sw | **89.6** | **94.7** | 460 |

### 4.2 Ekegusii (vs template silver refs)

| Setting | Model | BLEU | chrF | n |
|---------|--------|-----:|-----:|--:|
| Zero-shot | mT5-small | 0.007 | 0.95 | 50 |
| Zero-shot | NLLB + `guz_Latn` (init `kik_Latn`) | **0.26** | **13.0** | 50 |
| Zero-shot ablation | NLLB + `guz_Latn` (init `swh_Latn`) | 0.16 | 11.9 | 50 |
| Few-shot | mT5 1 epoch | 0.003 | 1.05 | 430 |
| Few-shot | NLLB | *not completed (GPU OOM on shared A100)* | — | — |

**Meaning of scores:** BLEU/chrF measure overlap with **silver** references, not human gold. High SW/Kikuyu figures show agreement with the NLLB teacher; low Ekegusii figures are expected for an unsupported language in zero-shot. See modelling report §6.

Human pack: `datasets/gold/human_eval_100.csv`, `DOCS/HUMAN_EVAL_GUIDE.md`.

---

## 5. Deployment

| Piece | Location |
|-------|----------|
| EN→Kikuyu | Hub / local `en-kik` NLLB |
| EN→Kiswahili | Hub / local `en-sw` NLLB |
| EN→Ekegusii (live demo) | Neural zero-shot NLLB + `guz_Latn` |
| API + UI | `apps/api/` — targets `sw` \| `kik` \| `guz` |
| Notes | `DOCS/EKEGUSII_NOTE.md`, `DOCS/DEPLOY_HF.md` |

Demo: FastAPI on Navon + public tunnel (ngrok) when Spaces PRO is unavailable.

---

## 6. Limitations

1. Silver targets and silver/template evaluation refs.  
2. Synthetic English PSAs labelled separately from real scrapes.  
3. Ekegusii outside stock NLLB-200; zero-shot tracks Kikuyu prior.  
4. Ekegusii few-shot NLLB blocked by shared-GPU memory.  
5. Human cultural review still pending.  
6. Large weights on Hub / Navon artefacts, not in Git.

---

## 7. Conclusions

LughaLink demonstrates a full PSA MT pipeline: curated data, few-shot NLLB for Kiswahili and Kikuyu with a working three-language UI, and a documented Ekegusii extension (`guz_Latn`) with honest zero-shot scores and unfinished few-shot NLLB. Low Ekegusii automatic metrics are reported as baselines, not concealed.

---

## 8. Demo checklist

- [x] Fine-tuned NLLB for SW and Kikuyu  
- [x] FastAPI UI with three targets  
- [x] Ekegusii `guz_Latn` extension + zero-shot metrics  
- [x] Honesty about silver refs and Kikuyu-like zero-shot  
- [ ] Human eval scores filled  
- [ ] Ekegusii few-shot NLLB when GPU is free  
