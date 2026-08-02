# LughaLink AI

**Every Public Message. Every Kenyan. Every Language.**

LughaLink AI is a Public Information Translation Platform — not a semester translation homework. We build the infrastructure that makes Kenyan public service announcements (PSAs) accessible in every language.

## What We're Building

| Product | Week | Purpose |
|---------|------|---------|
| **P1: PSA Intelligence Platform** | 1 | Discover, ingest, validate, enrich, store PSAs |
| **P2: Translation Engine** | 2–3 | NLLB/mT5 inference, fine-tuning, confidence |
| **P3: Monitoring Agent** | 2–3 | Continuous PSA discovery from gov/NGO sources |
| **P4: Translation API** | 2 | Single backend for all clients |
| **P5: Web Portal** | 3 | Public interface + feedback |
| **P6–P8: Mobile, WhatsApp, Community** | 4 | Client surfaces on shared API |

## Course Alignment (DSA 4020)

This project satisfies Dr. Ombui's requirements while building startup-grade infrastructure:

- ≥5,000 sentences per language pair (via EN/SW collection + NLLB seeding + human validation)
- ≥10 reliable sources with documented scraping
- Structured dataset with required columns
- Few-shot cross-lingual transfer (NLLB, mT5, mBART)
- Evaluation beyond BLEU + human review
- Deployable digital public good

## Repository Layout

```
lughalink-ai/
├── apps/                  # Deployable applications (Week 2+)
├── services/              # Product 1 core: scraper, validation, metadata
├── datasets/              # raw → interim → processed → gold
├── database/              # Schema, migrations, seeds
├── configs/               # Domains, languages, source taxonomy
├── docs/                  # Architecture, data dictionary, reports
├── tests/
└── scripts/
```

## Week 1 (complete)

**Product 1: PSA Intelligence Platform** — clean corpus + quarantine + report.

- Report: [DOCS/WEEK1_REPORT.md](DOCS/WEEK1_REPORT.md)
- Clean sheet: `datasets/processed/week1_psa_merged.csv`
- Playbook: [DOCS/architecture/PRODUCT1_WEEK1.md](DOCS/architecture/PRODUCT1_WEEK1.md)

## Week 2

**Product 2: Translation Engine** — PSA freeze, EDA, Kikuyu target, seed candidates.

- Report: [DOCS/WEEK2_REPORT.md](DOCS/WEEK2_REPORT.md)
- Languages: [configs/languages.yaml](configs/languages.yaml) (EN · SW · Kikuyu)

## Week 3–4 (modeling, eval, demo)

Final write-up: [DOCS/FINAL_REPORT.md](DOCS/FINAL_REPORT.md)  
Navon scale + train: [DOCS/NAVON_TRAINING_READY.md](DOCS/NAVON_TRAINING_READY.md)

```bash
# On Navon A100 (JupyterLab project) — scale to ~5k/pair then train NLLB + mT5
git pull
bash scripts/navon_scale_and_train.sh
# Download ~/lughalink_mt_scaled.tar.gz before stopping the pod

# Evaluate (silver references — relative scores only)
python scripts/evaluate_mt.py --pair en-kik --model nllb --write-ablation
python scripts/infer_mt.py --pair en-kik --text "Register to vote at your nearest centre."

# Human eval pack (reviewers fill scores later)
python scripts/prepare_human_eval.py
# See DOCS/HUMAN_EVAL_GUIDE.md

# Local Streamlit demo (point at extracted checkpoints)
pip install -e ".[demo]"
set LUGHALINK_MODEL_DIR=path\to\lugha_ckpt
streamlit run app/streamlit_mt.py
```

**Do not commit** `model/`, `artifacts/`, or `*.safetensors` — weights stay local/Navon only.

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -e ".[dev]"

# Initialize local SQLite for development (PostgreSQL for production)
python scripts/init_db.py

# Run source registry validation
python -m services.cli validate-sources

# Run a single-source scrape (example)
python -m services.cli scrape --source moh_kenya
```

## Team Roles

| Role | Owner | Week 1 Deliverable |
|------|-------|-------------------|
| Product Lead | TBD | Roadmap, GitHub, Week 1 report |
| Data Engineer | TBD | Scraper adapters, cleaning pipeline |
| ML Engineer | TBD | PSA classifier rules, language detection |
| Backend Engineer | TBD | Database schema, ingestion CLI |
| Frontend/UX | TBD | Manual upload UI stub, validation forms |

## License

CC-BY 4.0 (dataset and documentation). Code: MIT.
