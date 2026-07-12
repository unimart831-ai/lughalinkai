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

Mapped to the project brief in `DOCS/DSA4020 Summer2026 Project.pdf`:

- ≥5,000 sentences per language pair — Week 1: collect EN/SW PSAs; Week 2+: NLLB seeding for low-resource targets
- ≥10 reliable sources with documented scraping
- Structured dataset with required columns
- Few-shot cross-lingual transfer (NLLB, mT5, mBART) — Week 3
- Automatic + manual evaluation — Week 4 (no native-speaker pipeline in place yet)
- Deployable digital public good — Week 4

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

## Team

| Name | Domain | Branch |
|------|--------|--------|
| Iranzi Innocent (L) | Governance + Lead | `data/governance` |
| Angela Irungu | Health | `data/health` |
| Leona Kamau | Education | `data/education` |
| Jesca Kimani | Security + Agriculture | `data/security`, `data/agriculture` |

See [docs/TEAM_ROSTER.md](docs/TEAM_ROSTER.md) for full assignments.

## License

CC-BY 4.0 (dataset and documentation). Code: MIT.
