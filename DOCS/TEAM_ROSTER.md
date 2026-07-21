# LughaLink AI — Team Roster & Branch Assignments

**Repository:** https://github.com/unimart831-ai/lughalinkai  
**Updated:** 12 July 2026

---

## Team members (4)

| Code | Name | Role | Domain(s) | Git branch | GitHub username |
|------|------|------|-----------|------------|-----------------|
| **A** | **Iranzi Innocent (L)** | Product & Project Lead | Governance | `data/governance` | *(fill in)* |
| **B** | **Angela Irungu** | Health Domain Lead | Health | `data/health` | *(fill in)* |
| **C** | **Leona Kamau** | Education Domain Lead | Education | `data/education` | *(fill in)* |
| **D** | **Jesca Kimani** | Security + Agriculture Lead | Security, Agriculture | `data/security`, `data/agriculture` | *(fill in)* |

> **Note:** We have 4 members and 5 course domains. Jesca owns **two domains** (Security + Agriculture). Target: ≥1,000 PSAs per domain.

---

## Branch map

```
main                              ← stable (Iranzi merges only)
  └── develop                     ← integration (all PRs merge here first)
        ├── data/governance       ← Iranzi Innocent
        ├── data/health           ← Angela Irungu
        ├── data/education        ← Leona Kamau
        ├── data/security         ← Jesca Kimani
        └── data/agriculture      ← Jesca Kimani
```

---

## Source ownership

| Name | Branch | `source_id` entries they may edit |
|------|--------|-----------------------------------|
| Iranzi Innocent | `data/governance` | `iebc`, `huduma` |
| Angela Irungu | `data/health` | `moh_kenya`, `who_kenya`, `unicef_kenya` |
| Leona Kamau | `data/education` | `moe_kenya`, `kuccps`, `helb` |
| Jesca Kimani | `data/security` | `ndma`, `met_kenya`, `nps`, `kenya_red_cross` |
| Jesca Kimani | `data/agriculture` | `kilimo`, `fao_kenya` |

---

## Week 1 PSA targets

| Name | Domain | Target |
|------|--------|--------|
| Iranzi Innocent | Governance | ≥1,000 |
| Angela Irungu | Health | ≥1,000 |
| Leona Kamau | Education | ≥1,000 |
| Jesca Kimani | Security | ≥1,000 |
| Jesca Kimani | Agriculture | ≥1,000 |
| **Team total** | **All 5 domains** | **≥5,000** |

---

## Clone & checkout your branch

**Full guide:** [DATA_COLLECTION_RUNBOOK.md](DATA_COLLECTION_RUNBOOK.md) — step-by-step from clone to export.

**When scraping fails:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — challenge map and fix loop.

```powershell
git clone https://github.com/unimart831-ai/lughalinkai.git
cd lughalinkai
python -m venv .venv
.venv\Scripts\activate
pip install pandas beautifulsoup4 lxml httpx langdetect pydantic pydantic-settings sqlalchemy python-dotenv feedparser trafilatura rapidfuzz typer rich pyyaml pytest
python scripts/init_db.py

# Checkout YOUR branch (pick one):
git checkout data/governance    # Iranzi
git checkout data/health        # Angela
git checkout data/education     # Leona
git checkout data/security      # Jesca
git checkout data/agriculture   # Jesca
```

---

## Daily standup template

Post in team WhatsApp/Discord:

```
Name: Angela Irungu
Branch: data/health
Yesterday: Fixed MOH listing URL
Today: Running who_kenya scraper
Blockers: none
PSA count: 127 / 1000 (Health)
```
