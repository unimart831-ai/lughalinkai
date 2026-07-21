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

## Week 1 Focus

**Build Product 1: PSA Intelligence Platform.**

See [docs/architecture/PRODUCT1_WEEK1.md](docs/architecture/PRODUCT1_WEEK1.md) for the full execution playbook.

**Repository:** https://github.com/unimart831-ai/lughalinkai

**Team guide:** [docs/TEAM_OPERATIONS.md](docs/TEAM_OPERATIONS.md) — roles, domain ownership, data collection workflow, GitHub collaboration rules.

**Team roster:** [docs/TEAM_ROSTER.md](docs/TEAM_ROSTER.md) — names, branches, source ownership.

**Data collection guide (start here):** [docs/DATA_COLLECTION_RUNBOOK.md](docs/DATA_COLLECTION_RUNBOOK.md) — clone to export, commands per user, troubleshooting.

**File reference:** [docs/FILE_REFERENCE.md](docs/FILE_REFERENCE.md) — what each file in `configs/`, `database/`, `datasets/`, `scripts/`, and `services/` does.

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
