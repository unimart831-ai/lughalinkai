# LughaLink AI — Team Operations Guide

**Version:** 1.0  
**Date:** 11 July 2026  
**Audience:** Iranzi Innocent, Angela Irungu, Leona Kamau, Jesca Kimani  
**Repository:** https://github.com/unimart831-ai/lughalinkai  
**Roster:** See [TEAM_ROSTER.md](TEAM_ROSTER.md) for branch assignments

---

## Table of Contents

1. [What We Have Built So Far](#1-what-we-have-built-so-far)
2. [How the System Works (Simple Explanation)](#2-how-the-system-works-simple-explanation)
3. [Team Roles](#3-team-roles)
4. [Domain Ownership — Who Collects What](#4-domain-ownership--who-collects-what)
5. [Step-by-Step: How to Collect Data](#5-step-by-step-how-to-collect-data)
6. [GitHub Collaboration Rules](#6-github-collaboration-rules)
7. [Branch Strategy](#7-branch-strategy)
8. [File Ownership — Who Edits What](#8-file-ownership--who-edits-what)
9. [Daily Workflow Checklist](#9-daily-workflow-checklist)
10. [What to Commit vs What NOT to Commit](#10-what-to-commit-vs-what-not-to-commit)
11. [Handling Merge Conflicts](#11-handling-merge-conflicts)
12. [Weekly Targets by Person](#12-weekly-targets-by-person)
13. [Reporting Progress to the Team](#13-reporting-progress-to-the-team)
14. [Quick Reference Commands](#14-quick-reference-commands)

---

## 1. What We Have Built So Far

We are **not** starting from zero. The following is already in the repository at `a:\SYSTEMS_2026\LUGHALINK`.

### 1.1 Strategic foundation

| Item | Status | Location |
|------|--------|----------|
| Course requirements mapped to startup vision | Done | `DOCS/` PDFs + `docs/architecture/PRODUCT1_WEEK1.md` |
| Week 1 execution playbook (7-day plan) | Done | `docs/architecture/PRODUCT1_WEEK1.md` |
| PSA data dictionary | Done | `docs/data_dictionary/PSA_SCHEMA.md` |
| Domain taxonomy (5 domains, 25 sub-categories) | Done | `configs/domains.yaml` |

### 1.2 Product 1 — PSA Intelligence Platform (code)

| Module | What it does | File(s) | Status |
|--------|--------------|---------|--------|
| **M1** Source Registry | Lists all websites we scrape | `database/seeds/source_registry.json` | 15 sources configured |
| **M2** Trust Scoring | Rates source reliability (60–100) | Embedded in source registry | Ready |
| **M3** Scraper Engine | Fetches PSAs from websites | `services/scraper/adapters.py` | Built, needs live tuning |
| **M4** PSA Classifier | Filters news vs real PSAs | `services/metadata/classifier.py` | Ready |
| **M5** Cleaning Pipeline | Cleans raw text | `services/preprocessing/cleaning.py` | Ready |
| **M6** Metadata Enrichment | Tags domain, urgency, audience | `services/metadata/enrichment.py` | Ready |
| **M7** Validation Engine | Rejects bad records | `services/validation/engine.py` | Ready |
| **M8** Knowledge Database | Stores all PSAs | `database/schema/001_initial.sql` | Initialized locally |

### 1.3 Tools ready to use

| Tool | Command | Purpose |
|------|---------|---------|
| Initialize DB | `python scripts/init_db.py` | Create database + load 15 sources |
| List sources | `python -m services.cli validate-sources` | See all registered sources |
| Scrape one source | `python -m services.cli scrape --source moh_kenya` | Collect PSAs from one site |
| Scrape all | `python -m services.cli scrape --all-active` | Collect from all active sources |
| View stats | `python -m services.cli stats` | Count PSAs by domain/language |
| Export CSV | `python -m services.cli export` | Generate course submission file |

### 1.4 What we have NOT done yet

- **0 PSAs collected** — scraper has not been run on live government sites
- Source selectors (CSS paths) are **guesses** — each domain owner must validate and fix theirs
- Week 1 report not written
- GitHub remote may not be set up yet

**Bottom line:** The factory is built. Now each person runs their part of the production line.

---

## 2. How the System Works (Simple Explanation)

Every PSA goes through the same pipeline:

```
Government Website
        │
        ▼
   [Scraper]          ← Person B–E run this for their sources
        │
        ▼
   Raw HTML/Text      ← Saved locally (not committed to GitHub)
        │
        ▼
   [Cleaning]         ← Automatic: remove nav, fix spacing, detect language
        │
        ▼
   [PSA Classifier]   ← Automatic: is this a PSA or news article?
        │
        ▼
   [Enrichment]       ← Automatic: assign domain, urgency, keywords
        │
        ▼
   [Validation]      ← Automatic: reject empty, duplicate, too short
        │
        ▼
   [Database]         ← Stored as structured PSA object
        │
        ▼
   [Export CSV]       ← Person A exports for course submission
```

**Important:** You do not manually create CSV rows. You scrape → the system stores → Person A exports.

---

## 3. Team Roles

| Code | Name | Role | Branch |
|------|------|------|--------|
| **A** | **Iranzi Innocent (L)** | Product & Project Lead + Governance | `data/governance` |
| **B** | **Angela Irungu** | Health Domain Lead | `data/health` |
| **C** | **Leona Kamau** | Education Domain Lead | `data/education` |
| **D** | **Jesca Kimani** | Security + Agriculture Domain Lead | `data/security`, `data/agriculture` |

### Shared responsibilities (everyone)

- Pull latest code **before** starting work each day
- Work only on your assigned branch and files
- Never push directly to `main`
- Report daily PSA count in the team channel
- Log broken sources as GitHub Issues

### Contact roster

| Name | Role | GitHub username |
|------|------|-----------------|
| Iranzi Innocent (L) | Lead + Governance | *(add after invite)* |
| Angela Irungu | Health | *(add after invite)* |
| Leona Kamau | Education | *(add after invite)* |
| Jesca Kimani | Security + Agriculture | *(add after invite)* |

---

## 4. Domain Ownership — Who Collects What

The course requires all **5 domains**. With 4 members, **Jesca Kimani** covers Security and Agriculture.

| Name | Domain | Target PSAs | Primary sources (`source_id`) | Branch |
|------|--------|-------------|-------------------------------|--------|
| **Iranzi Innocent** | **Governance** | ≥1,000 | `iebc`, `huduma` | `data/governance` |
| **Angela Irungu** | **Health** | ≥1,000 | `moh_kenya`, `who_kenya`, `unicef_kenya` | `data/health` |
| **Leona Kamau** | **Education** | ≥1,000 | `moe_kenya`, `kuccps`, `helb` | `data/education` |
| **Jesca Kimani** | **Security** | ≥1,000 | `ndma`, `met_kenya`, `nps`, `kenya_red_cross` | `data/security` |
| **Jesca Kimani** | **Agriculture** | ≥1,000 | `kilimo`, `fao_kenya` | `data/agriculture` |

### 4.2 Shared / overflow sources

These sources cover multiple domains. **Do not scrape them without coordinating.**

| Source | Domains | Primary owner | Rule |
|--------|---------|---------------|------|
| `unicef_kenya` | Health + Education | Person B leads | Person C scrapes only if B confirms education filter works |
| `kenya_red_cross` | Security + Health | Person D leads | Person B may take health-tagged items after D's first pass |
| `citizen_tv` | All domains | **Inactive** — do not enable until Week 2 | Requires strict PSA filter |

### 4.3 Sub-category checklist (from course PDF)

Each domain owner should ensure coverage across sub-categories:

**Person B — Health**
- [ ] Disease prevention (malaria, vaccination, Ebola, cholera)
- [ ] Maternal and child health
- [ ] Public health campaigns (hygiene, sanitation)
- [ ] Mental health awareness
- [ ] Healthcare access (NHIF, SHA, medical camps)

**Person C — Education**
- [ ] Access to education (enrollment, literacy)
- [ ] Vocational training (TVET)
- [ ] Civic education
- [ ] Educational resources (scholarships, HELB, KUCCPS)
- [ ] School safety and inclusion

**Person D — Security & Safety**
- [ ] Public safety (road safety, fire, flood, drought)
- [ ] Crime prevention
- [ ] National security
- [ ] Gender-based violence
- [ ] Cybersecurity (M-Pesa scams, online safety)

**Person E — Agriculture**
- [ ] Crop production (fertilizer, pest control)
- [ ] Livestock management
- [ ] Agribusiness and market access
- [ ] Sustainable farming
- [ ] Agricultural training

**Person A — Governance**
- [ ] Anti-corruption (EACC campaigns)
- [ ] Public participation
- [ ] Elections and voter education (IEBC)
- [ ] Public service delivery (Huduma, eCitizen)
- [ ] Devolution and local governance

---

## 5. Step-by-Step: How to Collect Data

### 5.1 First-time setup (everyone, once)

```powershell
# 1. Clone the repo (after Person A creates GitHub remote)
git clone https://github.com/YOUR_ORG/lughalink-ai.git
cd lughalink-ai

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate

# 3. Install dependencies
pip install pandas beautifulsoup4 lxml httpx langdetect pydantic pydantic-settings sqlalchemy python-dotenv feedparser trafilatura rapidfuzz typer rich pyyaml pytest

# 4. Initialize database
python scripts/init_db.py

# 5. Verify sources load
python -m services.cli validate-sources
```

### 5.2 Domain owner workflow (Person B–E, daily)

**Step 1 — Pull latest code**
```powershell
git checkout develop
git pull origin develop
git checkout your-feature-branch   # e.g. data/health-scraping
git merge develop
```

**Step 2 — Validate your sources (browser check)**

Open each assigned website. Confirm:
- Does the listing URL load?
- Are there press releases / announcements / notices?
- Do the pages look like PSAs (short, advisory) or long news articles?

**Step 3 — Fix selectors if needed**

Edit **only your sources** in `database/seeds/source_registry.json`:

```json
"scrape_config": {
  "listing_url": "https://...",      ← fix if 404
  "article_selector": "article",     ← fix if no articles found
  "title_selector": "h1",
  "body_selector": ".entry-content", ← fix if empty body
  "date_selector": "time",
  "rate_limit_seconds": 2
}
```

**Step 4 — Re-seed database after registry changes**
```powershell
python scripts/init_db.py
```

**Step 5 — Run scraper for your sources**

Person B example (Health):
```powershell
python -m services.cli scrape --source moh_kenya
python -m services.cli scrape --source who_kenya
python -m services.cli scrape --source unicef_kenya
```

Person D example (Security):
```powershell
python -m services.cli scrape --source ndma
python -m services.cli scrape --source met_kenya
python -m services.cli scrape --source nps
python -m services.cli scrape --source kenya_red_cross
```

**Step 6 — Check your numbers**
```powershell
python -m services.cli stats
```

**Step 7 — Manual supplement (if scraper yields too few)**

If a government site blocks scraping or has PDF-only circulars:
1. Download the PDF / copy the PSA text manually
2. Save raw text to `datasets/raw/manual/{source_id}_{date}.txt`
3. Log it in a GitHub Issue — Person A tracks manual entries

**Step 8 — Commit your source fixes and push**
```powershell
git add database/seeds/source_registry.json
git commit -m "fix(health): update MOH listing URL and body selector"
git push origin data/health-scraping
```

Then open a **Pull Request** on GitHub → Person A reviews → merge to `develop`.

### 5.3 Person A workflow (Lead)

1. Merge approved PRs from B–E into `develop`
2. Run full scrape weekly: `python -m services.cli scrape --all-active`
3. Export dataset: `python -m services.cli export --output datasets/processed/psa_week1.csv`
4. Write Week 1 report using stats + sample entries
5. Only Person A merges `develop` → `main` at end of week

---

## 6. GitHub Collaboration Rules

These rules exist so **nobody deletes or overwrites another person's work**.

### Rule 1 — Never push directly to `main`

`main` = stable, demo-ready code. Only Person A merges into it.

### Rule 2 — Everyone works on branches

No exceptions. Even small fixes go through a branch + PR.

### Rule 3 — Pull before you push

```powershell
git pull origin develop
```
Do this every time you sit down to work.

### Rule 4 — One person per file at a time

If two people edit `source_registry.json` at the same time, you **will** get conflicts. Coordinate in WhatsApp/Discord before editing shared files.

### Rule 5 — Use GitHub Issues for tasks

Person A creates issues like:
- `[Health] Fix MOH scraper — 0 results`
- `[Education] Add manual KUCCPS PDF batch`
- `[Security] NDMA selector broken`

Assign each issue to one person. Close it when done.

### Rule 6 — Use Pull Requests, not direct merges

Every change goes: **branch → PR → review → merge**.

Minimum 1 approval before merge (Person A or domain peer).

### Rule 7 — Communicate before touching shared code

Shared code = anything in `services/` that is not your domain-specific config.

If Person D needs to change the scraper engine (`services/scraper/adapters.py`), they message the team first.

---

## 7. Branch Strategy

```
main                              ← stable (Iranzi merges only)
  └── develop                     ← integration (all PRs merge here first)
        ├── data/governance       ← Iranzi Innocent
        ├── data/health           ← Angela Irungu
        ├── data/education        ← Leona Kamau
        ├── data/security         ← Jesca Kimani
        ├── data/agriculture      ← Jesca Kimani
        └── docs/week1-report     ← Iranzi Innocent
```

### Branch naming convention

| Pattern | Example | Owner |
|---------|---------|-------|
| `data/{domain}` | `data/health` | Domain leads B–E, A |
| `fix/{short-desc}` | `fix/moh-selector` | Whoever fixes the bug |
| `docs/{desc}` | `docs/week1-report` | Person A |
| `feat/{desc}` | `feat/manual-upload` | Agreed by team |

### Creating your branch (first time)

```powershell
git checkout develop
git pull origin develop
git checkout -b data/health        # Person B example
git push -u origin data/health
```

---

## 8. File Ownership — Who Edits What

### 8.1 Exclusive ownership (only one person edits)

| File / folder | Owner | Others may... |
|---------------|-------|---------------|
| `database/seeds/source_registry.json` | Split by source_id (see below) | Read only |
| `docs/reports/week1_report.md` | Person A | Suggest via PR comments |
| `datasets/processed/*.csv` | Person A (exports) | Read only |

### 8.2 Source registry — split by `source_id`

Each person edits **only their source blocks** in `source_registry.json`:

| Name | May edit these `source_id` entries |
|------|-------------------------------------|
| Iranzi Innocent | `iebc`, `huduma` |
| Angela Irungu | `moh_kenya`, `who_kenya`, `unicef_kenya` |
| Leona Kamau | `moe_kenya`, `kuccps`, `helb` |
| Jesca Kimani | `ndma`, `met_kenya`, `nps`, `kenya_red_cross`, `kilimo`, `fao_kenya` |

**How to avoid conflicts:** Before editing the registry, message the team: *"Editing moh_kenya config now."* Keep edits small and push within 30 minutes.

### 8.3 Shared ownership (coordinate before editing)

| File / folder | Primary | Notes |
|---------------|---------|-------|
| `services/scraper/adapters.py` | Person A + first requester | Discuss in chat before changes |
| `services/metadata/classifier.py` | Person B (ML-oriented) | Tune PSA detection rules together |
| `configs/domains.yaml` | Person A | Domain owners propose keywords via Issues |
| `tests/` | Whoever changes related code | Run tests before every PR |

### 8.4 Never edit without team agreement

- `database/schema/001_initial.sql` — schema changes affect everyone
- `services/cli.py` — core pipeline commands
- `pyproject.toml` — dependencies

---

## 9. Daily Workflow Checklist

### Everyone (15 min start of session)

- [ ] `git pull origin develop`
- [ ] Activate venv: `.venv\Scripts\activate`
- [ ] Check assigned GitHub Issues
- [ ] Post in team chat: *"Starting work on [domain], targeting [source]"*

### Domain owners B–E (1–2 hours)

- [ ] Validate one source in browser
- [ ] Fix selectors if needed → commit → PR
- [ ] Run scraper on your sources
- [ ] Run `python -m services.cli stats` — post domain count in chat
- [ ] Log problems as GitHub Issues

### Person A (30 min daily)

- [ ] Review and merge open PRs
- [ ] Check total PSA count across all domains
- [ ] Flag domains below target
- [ ] Update team progress tracker (see Section 13)

### End of session (5 min)

- [ ] Push your branch
- [ ] Open PR if feature is complete
- [ ] Post: *"Done for today. [Domain]: X PSAs total."*

---

## 10. What to Commit vs What NOT to Commit

### Commit these

| Item | Why |
|------|-----|
| `database/seeds/source_registry.json` | Source config fixes |
| `services/` code changes | Pipeline improvements |
| `configs/domains.yaml` | Keyword additions |
| `docs/` | Reports, documentation |
| `tests/` | Test updates |
| `datasets/processed/psa_week1.csv` | Course export (Person A only, end of week) |

### NEVER commit these

| Item | Why | Where it lives |
|------|-----|----------------|
| `.venv/` | Local Python environment | Each machine |
| `database/lughalink.db` | Local database — everyone has their own | Local only |
| `datasets/raw/**` | Large scraped HTML files | Local / DVC later |
| `.env` | Secrets | Local only |
| `__pycache__/` | Python cache | Auto-generated |

**Important:** Each person runs their own local database. The **export CSV** is how we combine everyone's work for submission — not by sharing `.db` files.

### How we combine everyone's data for submission

Person A runs the final export after merging all source fixes to `develop`:

```powershell
python scripts/init_db.py
python -m services.cli scrape --all-active
python -m services.cli export --output datasets/processed/psa_week1.csv
git add datasets/processed/psa_week1.csv
git commit -m "data: Week 1 PSA export (5000+ sentences)"
```

---

## 11. Handling Merge Conflicts

Conflicts will happen — especially in `source_registry.json`. Here is how to resolve them safely.

### Most common conflict: `source_registry.json`

**Prevention:** Each person edits only their own `source_id` blocks.

**Resolution if it happens:**

```powershell
git pull origin develop
# Git marks conflicts with <<<<<<< ======= >>>>>>>

# Open source_registry.json
# Keep BOTH people's source blocks — never delete someone else's source_id
# Remove conflict markers (<<<<<<< etc.)
# Save file

git add database/seeds/source_registry.json
git commit -m "merge: resolve source registry conflict"
git push
```

**Golden rule:** In a conflict, **keep both people's sources**. Never pick "mine" or "theirs" for the whole file.

### If you accidentally deleted someone's work

```powershell
git log --oneline          # find last good commit
git checkout <commit-hash> -- path/to/file
git commit -m "restore: recover deleted source config"
```

Person A should enable branch protection on `main` and `develop` to require PR reviews.

---

## 12. Weekly Targets by Person

### Week 1 targets (minimum to pass course)

| Name | Domain | PSA target | Source fixes | Deliverable |
|------|--------|------------|--------------|-------------|
| Iranzi Innocent | Governance | ≥1,000 | `iebc`, `huduma` working | Week 1 report + final CSV export |
| Angela Irungu | Health | ≥1,000 | `moh_kenya`, `who_kenya` working | Domain stats + 3 sample PSAs |
| Leona Kamau | Education | ≥1,000 | `moe_kenya`, `kuccps`, `helb` working | Domain stats + 3 sample PSAs |
| Jesca Kimani | Security | ≥1,000 | `ndma`, `met_kenya`, `nps` working | Domain stats + 3 sample PSAs |
| Jesca Kimani | Agriculture | ≥1,000 | `kilimo`, `fao_kenya` working | Domain stats + 3 sample PSAs |
| **Team total** | **All 5** | **≥5,000** | **≥10 sources documented** | **GitHub repo + report** |

### Daily pace (to hit 5,000 by Day 5)

| Day | Team cumulative target |
|-----|------------------------|
| Day 1 | 100 PSAs (setup + first scrapes) |
| Day 2 | 500 PSAs |
| Day 3 | 1,500 PSAs |
| Day 4 | 3,000 PSAs |
| Day 5 | 5,000 PSAs |
| Day 6–7 | Quality audit + export + report |

---

## 13. Reporting Progress to the Team

Person A maintains a simple progress table (Google Sheet or GitHub Project board):

| Name | Domain | PSAs collected | Sources working | Sources broken | Last updated |
|------|--------|----------------|-----------------|----------------|--------------|
| Iranzi Innocent | Governance | 0 | 0/2 | iebc (untested) | — |
| Angela Irungu | Health | 0 | 0/3 | moh (untested) | — |
| Leona Kamau | Education | 0 | 0/3 | moe (untested) | — |
| Jesca Kimani | Security | 0 | 0/4 | ndma (untested) | — |
| Jesca Kimani | Agriculture | 0 | 0/2 | kilimo (untested) | — |

### Daily standup format (5 minutes, async or WhatsApp)

Each person posts:
```
Person B — Health
- Yesterday: Fixed MOH listing URL
- Today: Running who_kenya + unicef scrapers
- Blockers: MOH body selector returns empty on 3 pages
- PSA count: 127 / 1000
```

---

## 14. Quick Reference Commands

```powershell
# Setup (once)
python -m venv .venv
.venv\Scripts\activate
pip install pandas beautifulsoup4 lxml httpx langdetect pydantic pydantic-settings sqlalchemy python-dotenv feedparser trafilatura rapidfuzz typer rich pyyaml pytest
python scripts/init_db.py

# Daily
git pull origin develop
python -m services.cli scrape --source YOUR_SOURCE_ID
python -m services.cli stats

# End of week (Person A)
python -m services.cli scrape --all-active
python -m services.cli export --output datasets/processed/psa_week1.csv

# Tests (before every PR)
python -m pytest tests/ -q
```

### Source IDs cheat sheet

| source_id | Domain | Owner |
|-----------|--------|-------|
| `moh_kenya` | Health | Angela Irungu |
| `who_kenya` | Health | Angela Irungu |
| `unicef_kenya` | Health/Education | Angela Irungu (lead) |
| `moe_kenya` | Education | Leona Kamau |
| `kuccps` | Education | Leona Kamau |
| `helb` | Education | Leona Kamau |
| `ndma` | Security | Jesca Kimani |
| `met_kenya` | Security | Jesca Kimani |
| `nps` | Security | Jesca Kimani |
| `kenya_red_cross` | Security | Jesca Kimani |
| `kilimo` | Agriculture | Jesca Kimani |
| `fao_kenya` | Agriculture | Jesca Kimani |
| `iebc` | Governance | Iranzi Innocent |
| `huduma` | Governance | Iranzi Innocent |

---

## Appendix A — First Team Meeting Agenda (30 min)

1. Assign real names to Person A–E (5 min)
2. Person A creates GitHub repo + adds all members (5 min)
3. Everyone clones and runs setup (10 min)
4. Each person opens their primary source in a browser — live check (5 min)
5. Agree daily standup time and WhatsApp/Discord group (5 min)

## Appendix B — GitHub Repo Setup (Person A only)

```powershell
# On GitHub: create repo "lughalink-ai" (private)
# Add all team members as collaborators

git init
git add .
git commit -m "feat: Product 1 PSA Intelligence Platform foundation"
git branch -M main
git remote add origin https://github.com/YOUR_ORG/lughalink-ai.git
git push -u origin main

git checkout -b develop
git push -u origin develop

# Enable branch protection on GitHub:
# Settings → Branches → Add rule for "main" and "develop"
#   ☑ Require pull request before merging
#   ☑ Require 1 approval
```

---

*Document maintained by Iranzi Innocent. Propose changes via PR to `docs/TEAM_OPERATIONS.md`.*
