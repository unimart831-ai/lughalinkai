# LughaLink AI — Complete Data Collection Runbook

**Repository:** https://github.com/unimart831-ai/lughalinkai  
**Audience:** Iranzi Innocent, Angela Irungu, Leona Kamau, Jesca Kimani  
**Goal:** Collect ≥1,000 PSAs per domain (≥5,000 total) with clean metadata  
**Start here if:** You are setting up for the first time or fixing a broken scraper

---

## Table of Contents

1. [Overview — What You Are Doing](#1-overview--what-you-are-doing)
2. [Phase 1 — Clone the Repository](#2-phase-1--clone-the-repository)
3. [Phase 2 — Python Environment Setup](#3-phase-2--python-environment-setup)
4. [Phase 3 — Environment Variables (.env)](#4-phase-3--environment-variables-env)
5. [Phase 4 — Initialize the Database](#5-phase-4--initialize-the-database)
6. [Phase 5 — Checkout Your Branch](#6-phase-5--checkout-your-branch)
7. [Phase 6 — Validate Sources in the Browser](#7-phase-6--validate-sources-in-the-browser)
8. [Phase 7 — Add or Fix URLs in source_registry.json](#8-phase-7--add-or-fix-urls-in-source_registryjson)
9. [Phase 8 — Reload Config and Run the Scraper](#9-phase-8--reload-config-and-run-the-scraper)
10. [Phase 9 — Read Results (stored / rejected / quarantined)](#10-phase-9--read-results-stored--rejected--quarantined)
11. [Phase 10 — Inspect and Fix Data Quality](#11-phase-10--inspect-and-fix-data-quality)
12. [Phase 11 — Manual PSA Upload (when scraping fails)](#12-phase-11--manual-psa-upload-when-scraping-fails)
13. [Phase 12 — Commit, Push, and Open a Pull Request](#13-phase-12--commit-push-and-open-a-pull-request)
14. [Phase 13 — Team Lead: Export and Week 1 Report (Iranzi only)](#14-phase-13--team-lead-export-and-week-1-report-iranzi-only)
15. [Per-User Command Reference](#15-per-user-command-reference)
16. [Challenges and Solutions](#16-challenges-and-solutions)
17. [Data Quality Checklist (before you commit)](#17-data-quality-checklist-before-you-commit)
18. [Daily Workflow Summary](#18-daily-workflow-summary)

---

## 1. Overview — What You Are Doing

You are **not** typing PSAs into a spreadsheet. You are:

1. Configuring **where** PSAs come from (`database/seeds/source_registry.json`)
2. Running the **scraper** to fetch and clean them
3. Checking **quality** in the local database
4. Committing **source config fixes** to GitHub (not the database file)

```
source_registry.json  →  scraper  →  cleaning  →  classifier  →  database  →  export CSV
     (you edit)           (CLI)      (auto)        (auto)         (local)      (lead only)
```

**Important files**

| File | Who edits | Committed to GitHub? |
|------|-----------|----------------------|
| `database/seeds/source_registry.json` | Domain owner only | Yes |
| `database/lughalink.db` | Created by scraper | **Never** |
| `.env` | Each person locally | **Never** |
| `datasets/raw/` | Scraper output | **Never** (too large) |
| `datasets/processed/psa_week1.csv` | Iranzi at end of week | Yes |

---

## 2. Phase 1 — Clone the Repository

Everyone runs this once:

```powershell
git clone https://github.com/unimart831-ai/lughalinkai.git
cd lughalinkai
```

Verify you see folders: `services/`, `database/`, `configs/`, `docs/`.

---

## 3. Phase 2 — Python Environment Setup

**Requirements:** Python 3.9 or newer.

```powershell
python -m venv .venv
.venv\Scripts\activate
```

You should see `(.venv)` at the start of your prompt.

Install dependencies:

```powershell
pip install --upgrade pip
pip install pandas beautifulsoup4 lxml httpx langdetect pydantic pydantic-settings sqlalchemy python-dotenv feedparser trafilatura rapidfuzz typer rich pyyaml pytest
```

Verify install:

```powershell
python -m pytest tests/ -q
```

Expected: `3 passed`

---

## 4. Phase 3 — Environment Variables (.env)

Copy the example file:

```powershell
copy .env.example .env
```

Open `.env` in a text editor. **Required on most Windows machines:**

```env
SCRAPER_SSL_VERIFY=false
```

### Why?

Kenyan government sites often fail with:

```
SSL: CERTIFICATE_VERIFY_FAILED
```

Setting `SCRAPER_SSL_VERIFY=false` lets the scraper connect. This file stays on your machine only — it is in `.gitignore`.

Optional settings:

```env
DATABASE_URL=sqlite:///database/lughalink.db
SCRAPER_RATE_LIMIT=2
LOG_LEVEL=INFO
```

---

## 5. Phase 4 — Initialize the Database

```powershell
python scripts/init_db.py
python -m services.cli validate-sources
```

You should see a table of **15 sources**. If the table is empty, check that `database/seeds/source_registry.json` exists.

This creates `database/lughalink.db` locally and loads all sources from the registry.

**Run again whenever you change `source_registry.json`** so your local DB picks up new URLs:

```powershell
python scripts/init_db.py
```

---

## 6. Phase 5 — Checkout Your Branch

Never work directly on `main`. Use your assigned branch:

| Name | Branch |
|------|--------|
| Iranzi Innocent | `data/governance` |
| Angela Irungu | `data/health` |
| Leona Kamau | `data/education` |
| Jessica Kimani | `data/security` or `data/agriculture` |

```powershell
git checkout data/governance
git pull origin develop
git merge develop
```

Replace `data/governance` with your branch name.

---

## 7. Phase 6 — Validate Sources in the Browser

Before changing any code, open your assigned websites manually.

### Step-by-step (every domain owner)

1. Open `database/seeds/source_registry.json`
2. Find your `source_id` (see [Section 15](#15-per-user-command-reference))
3. Copy the `listing_url` value
4. Paste it in Chrome/Edge
5. Check:
   - [ ] Page loads (not 404)
   - [ ] Page shows announcements / press releases / notices
   - [ ] Items look like **PSAs** (short, advisory) not long news articles
   - [ ] Click 2–3 individual items — note where **title**, **body**, and **date** appear

### Use Chrome Inspect to find selectors

1. On an article page, right-click the **title** → **Inspect**
2. Note the HTML tag and class, e.g. `<h1 class="entry-title">`
3. Right-click the **body text** → **Inspect**, e.g. `<div class="entry-content">`
4. Find the **date**, e.g. `<time datetime="2026-01-15">`

Write these down — you will put them in `source_registry.json` in Phase 7.

### What a good PSA looks like

- "IEBC reminds voters to verify their details via SMS."
- "Ministry of Health advises the public to avoid unnecessary travel."
- "NDMA warns residents of impending floods in Garissa County."

### What is NOT a PSA (will be rejected)

- Long news analysis ("Experts say economy will...")
- Sports results
- Celebrity gossip
- Pages with fewer than 10 words

---

## 8. Phase 7 — Add or Fix URLs in source_registry.json

**File path:** `database/seeds/source_registry.json`

**Rule:** Edit **only your own** `source_id` blocks. Do not change other team members' sources.

### Anatomy of a source entry

```json
{
  "source_id": "iebc",
  "organization": "Independent Electoral and Boundaries Commission",
  "country": "Kenya",
  "source_type": "government",
  "domains_covered": ["governance"],
  "website": "https://www.iebc.or.ke",
  "rss_feed": null,
  "twitter_handle": "@IEBCKenya",
  "primary_language": "en",
  "secondary_languages": ["sw"],
  "trust_score": 100,
  "priority": "high",
  "adapter": "generic_html",
  "scrape_config": {
    "listing_url": "https://www.iebc.or.ke/news/",
    "article_selector": "article",
    "title_selector": "h1",
    "body_selector": ".entry-content",
    "date_selector": "time",
    "rate_limit_seconds": 2
  },
  "robots_txt_respected": true,
  "active": true
}
```

### Field guide — what each setting does

| Field | Purpose | Example |
|-------|---------|---------|
| `source_id` | Unique ID — used in CLI | `"iebc"` |
| `website` | Organisation homepage | `"https://www.iebc.or.ke"` |
| `listing_url` | Page with links to many announcements | News/press page |
| `article_selector` | CSS selector for article containers on listing page | `"article"`, `".post"` |
| `title_selector` | CSS selector for headline on article page | `"h1"`, `"h1.entry-title"` |
| `body_selector` | CSS selector for main text | `".entry-content"`, `".post-content"` |
| `date_selector` | CSS selector for publish date | `"time"`, `".date"` |
| `rate_limit_seconds` | Wait between requests (be polite) | `2` |
| `adapter` | Scraper type | `"generic_html"` or `"rss_feed"` |
| `rss_feed` | RSS URL (if adapter is rss_feed) | WHO Kenya feed URL |
| `active` | `true` = scraper will run this source | `true` / `false` |

### How to fix a wrong listing URL

1. Find the correct announcements page on the organisation website
2. Update `listing_url` in your source block
3. Save the file

Example — if Huduma notices moved:

```json
"scrape_config": {
  "listing_url": "https://www.hudumakenya.go.ke/en/notices",
  ...
}
```

### How to fix selectors (most common fix)

If scraper returns **"Untitled"** titles or **empty body**, update selectors from Phase 6 Inspect notes:

```json
"title_selector": "h1.entry-title, h1.page-title",
"body_selector": ".entry-content, .field-body, article .content",
"date_selector": "time[datetime], .posted-on, .date"
```

**Tip:** Multiple selectors separated by commas — the scraper uses the **first match**.

### How to add comma-separated fallback selectors

```json
"title_selector": "h1, h2.entry-title, .page-header h1",
"body_selector": ".entry-content, .article-body, main p"
```

### How to add a NEW source (optional — Week 1 stretch)

Add a new object inside the `"sources": [ ... ]` array:

```json
{
  "source_id": "eacc_kenya",
  "organization": "Ethics and Anti-Corruption Commission",
  "country": "Kenya",
  "source_type": "government",
  "domains_covered": ["governance"],
  "website": "https://eacc.go.ke",
  "rss_feed": null,
  "twitter_handle": null,
  "primary_language": "en",
  "secondary_languages": ["sw"],
  "trust_score": 100,
  "priority": "medium",
  "adapter": "generic_html",
  "scrape_config": {
    "listing_url": "https://eacc.go.ke/news/",
    "article_selector": "article",
    "title_selector": "h1",
    "body_selector": ".content",
    "date_selector": "time",
    "rate_limit_seconds": 2
  },
  "robots_txt_respected": true,
  "active": true
}
```

**Only Iranzi** should add governance sources. Other members add only within their domain. Message the team before adding a new source.

### RSS sources (WHO Kenya example)

If a site has RSS instead of HTML listing:

```json
"adapter": "rss_feed",
"rss_feed": "https://www.afro.who.int/rss/countries/kenya/news",
"scrape_config": {
  "rate_limit_seconds": 3
}
```

No `listing_url` needed for RSS adapter.

### Disable a broken source temporarily

```json
"active": false
```

---

## 9. Phase 8 — Reload Config and Run the Scraper

After **every** edit to `source_registry.json`:

```powershell
python scripts/init_db.py
```

Run scraper for **one** source:

```powershell
python -m services.cli scrape --source iebc
```

Replace `iebc` with your `source_id`.

Run **all your sources** one after another:

```powershell
# Iranzi — Governance
python -m services.cli scrape --source iebc
python -m services.cli scrape --source huduma

# Angela — Health
python -m services.cli scrape --source moh_kenya
python -m services.cli scrape --source who_kenya
python -m services.cli scrape --source unicef_kenya

# Leona — Education
python -m services.cli scrape --source moe_kenya
python -m services.cli scrape --source kuccps
python -m services.cli scrape --source helb

# Jessica — Security
python -m services.cli scrape --source ndma
python -m services.cli scrape --source met_kenya
python -m services.cli scrape --source nps
python -m services.cli scrape --source kenya_red_cross

# Jessica — Agriculture
python -m services.cli scrape --source kilimo
python -m services.cli scrape --source fao_kenya
```

Check totals:

```powershell
python -m services.cli stats
```

---

## 10. Phase 9 — Read Results (stored / rejected / quarantined)

After scraping, the CLI prints:

```
iebc: stored=3, rejected=44
```

| Term | Meaning |
|------|---------|
| **stored** | Passed classifier + validation → status `active` → **counts toward your 1,000** |
| **rejected** | Failed before storage (duplicate, empty, not a PSA) |
| **quarantined** | Stored but failed quality gate → status `quarantined` → **does not count yet** |

### Check active vs quarantined

```powershell
.venv\Scripts\python -c "import sqlite3; c=sqlite3.connect('database/lughalink.db'); print(c.execute('SELECT status, COUNT(*) FROM psas GROUP BY status').fetchall())"
```

Expected output example: `[('active', 3), ('quarantined', 44)]`

### View your collected PSAs

```powershell
.venv\Scripts\python -c "import sqlite3; c=sqlite3.connect('database/lughalink.db'); [print(r) for r in c.execute('SELECT psa_id, title, domain, token_count, classification_confidence, status FROM psas WHERE domain=\"governance\" LIMIT 10').fetchall()]"
```

Change `governance` to your domain: `health`, `education`, `security`, `agriculture`.

---

## 11. Phase 10 — Inspect and Fix Data Quality

Work through this list when `stored` is low or titles show **"Untitled"**.

### Problem: Titles are "Untitled"

**Cause:** `title_selector` does not match the website HTML.  
**Fix:** Update `title_selector` in `source_registry.json` using Chrome Inspect (Phase 6).  
**Re-run:** `python scripts/init_db.py` then scrape again.

### Problem: Body text is empty or too short

**Cause:** `body_selector` is wrong.  
**Fix:** Inspect article page, update `body_selector`. Try broader selectors like `article`, `main`.

### Problem: stored=0, rejected=50

**Cause:** Pages are not PSAs (news articles) or classifier score < 0.6.  
**Fix:**
- Check if listing page links to news instead of announcements — find a better `listing_url`
- Open a few scraped pages manually — are they actually PSAs?

### Problem: Many quarantined, few active

**Cause:** Classifier confidence too low, or text too long (>500 tokens).  
**Fix:**
- Improve title/body extraction first
- If content is valid PSAs but long, note in GitHub Issue for team discussion

### Problem: Duplicates

**Cause:** Same text scraped twice.  
**Fix:** Normal — duplicates are auto-rejected. No action needed.

### Problem: Wrong domain tagged

**Cause:** Keyword rules in `configs/domains.yaml` matched wrong domain.  
**Fix:** Note in GitHub Issue. Iranzi or team can add keywords. Your PSAs still store — domain tag may be wrong.

### Delete local DB and start fresh (if data is messy)

```powershell
Remove-Item database\lughalink.db
python scripts/init_db.py
python -m services.cli scrape --source YOUR_SOURCE
```

Only delete **your local** database. Never delete other people's work on GitHub.

---

## 12. Phase 11 — Manual PSA Upload (when scraping fails)

Some government sites block scrapers or only publish PDFs. Fallback:

1. Copy PSA text manually from the website or PDF
2. Save to: `datasets/raw/manual/{source_id}_{YYYYMMDD}.txt`
3. Log it in a **GitHub Issue**: `[Governance] Manual PSA batch from IEBC PDF`
4. Iranzi tracks manual entries for the Week 1 report

**Do not commit** large batches of raw files unless agreed by the team.

Format for manual file:

```
Title: IEBC reminds voters to verify details
Date: 2026-03-01
Source: https://www.iebc.or.ke/...
Language: en

IEBC reminds all registered voters to verify their registration details via SMS by sending ID number to 70000.
```

---

## 13. Phase 12 — Commit, Push, and Open a Pull Request

### What to commit

```powershell
git status
```

You should commit **only**:

- `database/seeds/source_registry.json` (your source blocks)

You should **never** commit:

- `database/lughalink.db`
- `.env`
- `.venv/`
- `datasets/raw/**`

### Commit workflow

```powershell
git add database/seeds/source_registry.json
git commit -m "fix(governance): update IEBC title and body selectors"
git push origin data/governance
```

Use your branch name instead of `data/governance`.

**Commit message format:**

```
fix(health): update MOH listing URL
fix(education): add KUCCPS body selector
fix(security): enable NDMA source
```

### Open Pull Request on GitHub

1. Go to https://github.com/unimart831-ai/lughalinkai
2. Click **Pull requests** → **New pull request**
3. Base: `develop` ← Compare: `data/governance` (your branch)
4. Title: `fix(governance): IEBC and Huduma scrape config`
5. Description: what you changed, how many PSAs you now get
6. Request review from **Iranzi Innocent**
7. Iranzi merges when approved

### Before opening PR — pull latest develop

```powershell
git checkout develop
git pull origin develop
git checkout data/governance
git merge develop
# fix any conflicts in source_registry.json — keep BOTH people's sources
git push origin data/governance
```

---

## 14. Phase 13 — Team Lead: Export and Week 1 Report (Iranzi only)

After all team PRs are merged into `develop`:

```powershell
git checkout develop
git pull origin develop
python scripts/init_db.py
python -m services.cli scrape --all-active
python -m services.cli stats
python -m services.cli export --output datasets/processed/psa_week1.csv
```

Create report at `docs/reports/week1_dataset_summary.md` with:

- Total PSAs per domain
- Sources working / broken
- 10 sample PSA entries
- Challenges encountered
- Week 2 plan

Commit export + report:

```powershell
git add datasets/processed/psa_week1.csv docs/reports/week1_dataset_summary.md
git commit -m "data: Week 1 PSA export and summary report"
git push origin develop
```

Merge `develop` → `main` when the team agrees the week is complete.

---

## 15. Per-User Command Reference

### Iranzi Innocent — Governance

| Item | Value |
|------|-------|
| Branch | `data/governance` |
| Domain | Governance |
| Target | ≥1,000 PSAs |
| Sources | `iebc`, `huduma` |

```powershell
git checkout data/governance
python scripts/init_db.py
python -m services.cli scrape --source iebc
python -m services.cli scrape --source huduma
python -m services.cli stats
```

**Sub-topics to cover:** elections, voter registration, Huduma, eCitizen, public participation.

---

### Angela Irungu — Health

| Item | Value |
|------|-------|
| Branch | `data/health` |
| Domain | Health |
| Target | ≥1,000 PSAs |
| Sources | `moh_kenya`, `who_kenya`, `unicef_kenya` |

```powershell
git checkout data/health
python scripts/init_db.py
python -m services.cli scrape --source moh_kenya
python -m services.cli scrape --source who_kenya
python -m services.cli scrape --source unicef_kenya
python -m services.cli stats
```

**Note:** `who_kenya` uses RSS adapter — if it fails, check `rss_feed` URL in registry.

---

### Leona Kamau — Education

| Item | Value |
|------|-------|
| Branch | `data/education` |
| Domain | Education |
| Target | ≥1,000 PSAs |
| Sources | `moe_kenya`, `kuccps`, `helb` |

```powershell
git checkout data/education
python scripts/init_db.py
python -m services.cli scrape --source moe_kenya
python -m services.cli scrape --source kuccps
python -m services.cli scrape --source helb
python -m services.cli stats
```

---

### Jesca Kimani — Security + Agriculture

| Item | Value |
|------|-------|
| Branches | `data/security`, `data/agriculture` |
| Domains | Security (≥1,000) + Agriculture (≥1,000) |
| Security sources | `ndma`, `met_kenya`, `nps`, `kenya_red_cross` |
| Agriculture sources | `kilimo`, `fao_kenya` |

**Security:**

```powershell
git checkout data/security
python scripts/init_db.py
python -m services.cli scrape --source ndma
python -m services.cli scrape --source met_kenya
python -m services.cli scrape --source nps
python -m services.cli scrape --source kenya_red_cross
python -m services.cli stats
```

**Agriculture:**

```powershell
git checkout data/agriculture
git pull origin develop
python scripts/init_db.py
python -m services.cli scrape --source kilimo
python -m services.cli scrape --source fao_kenya
python -m services.cli stats
```

---

## 16. Challenges and Solutions

| # | Error / Symptom | Cause | Solution |
|---|-----------------|-------|----------|
| 1 | `SSL: CERTIFICATE_VERIFY_FAILED` | Windows Python SSL certs | Add `SCRAPER_SSL_VERIFY=false` to `.env` |
| 2 | `ModuleNotFoundError: No module named 'services'` | Wrong directory or venv not active | `cd lughalinkai`, then `.venv\Scripts\activate` |
| 3 | `ModuleNotFoundError: No module named 'typer'` | Dependencies not installed | Run pip install command from Phase 2 |
| 4 | `stored=0, rejected=0` + SSL error | Same as #1 | Fix `.env` |
| 5 | `stored=0`, high rejected | Wrong selectors or not PSAs | Fix selectors (Phase 7), check listing URL |
| 6 | Titles show **"Untitled"** | `title_selector` wrong | Inspect HTML, update selector |
| 7 | Empty body / too short | `body_selector` wrong | Inspect HTML, update selector |
| 8 | `404` or page not found | `listing_url` outdated | Find new URL on organisation website |
| 9 | Many **quarantined**, few **active** | Low classifier score or bad extraction | Fix title/body first; re-scrape |
| 10 | `duplicate` silently skipped | Same PSA scraped twice | Normal — no fix needed |
| 11 | Scrape very slow | Rate limit + many pages | Normal — 2s delay per page is intentional |
| 12 | `PermissionError: robots.txt disallows` | Site blocks scraping | Respect it; use manual upload (Phase 11) |
| 13 | Git merge conflict in `source_registry.json` | Two people edited same file | Keep **both** source blocks; remove `<<<<<<<` markers |
| 14 | Pushed `.db` file by mistake | Wrong git add | `git reset HEAD database/lughalink.db` — file is gitignored |
| 15 | `name 'hashlib' is not defined` | Old code bug | Pull latest `develop` — fixed in repo |
| 16 | Stats show 0 after successful scrape | Checking wrong domain filter | Use SQL query in Phase 9 without domain filter |
| 17 | WHO RSS returns nothing | RSS URL changed | Update `rss_feed` in registry |
| 18 | Less than 50 items per run | Scraper caps at 50 per run | Re-run scraper; add pagination URLs if available |

---

## 17. Data Quality Checklist (before you commit)

Before opening a Pull Request, confirm:

- [ ] `listing_url` opens correctly in browser
- [ ] At least **10 active PSAs** stored locally (stretch: 100+)
- [ ] Titles are **real headlines**, not "Untitled"
- [ ] Body text reads like a PSA (short, advisory, actionable)
- [ ] `python -m services.cli stats` shows your domain count going up
- [ ] Only **your** source blocks changed in `source_registry.json`
- [ ] No `.db`, `.env`, or `.venv` files in `git status`
- [ ] Commit message says which source you fixed: `fix(health): MOH selectors`

---

## 18. Daily Workflow Summary

**Every session — all members:**

```powershell
cd lughalinkai
.venv\Scripts\activate
git checkout YOUR_BRANCH
git pull origin develop
git merge develop
# ... work on sources ...
python scripts/init_db.py
python -m services.cli scrape --source YOUR_SOURCE
python -m services.cli stats
git add database/seeds/source_registry.json
git commit -m "fix(YOUR_DOMAIN): describe change"
git push origin YOUR_BRANCH
```

**WhatsApp standup (copy daily):**

```
Name:
Branch:
Yesterday:
Today:
Blockers:
PSA count: X / 1000 (Domain)
Active / Quarantined: X / Y
```

---

## Quick Reference — All CLI Commands

| Command | Purpose |
|---------|---------|
| `python scripts/init_db.py` | Create/reset DB, load sources |
| `python -m services.cli validate-sources` | List all 15 sources |
| `python -m services.cli scrape --source ID` | Scrape one source |
| `python -m services.cli scrape --all-active` | Scrape all active sources |
| `python -m services.cli stats` | Count PSAs by domain/language |
| `python -m services.cli export` | Export CSV for submission |
| `python -m pytest tests/ -q` | Run tests before PR |

---

## Source ID Quick Lookup

| source_id | Domain | Owner |
|-----------|--------|-------|
| `iebc` | governance | Iranzi |
| `huduma` | governance | Iranzi |
| `moh_kenya` | health | Angela |
| `who_kenya` | health | Angela |
| `unicef_kenya` | health/education | Angela |
| `moe_kenya` | education | Leona |
| `kuccps` | education | Leona |
| `helb` | education | Leona |
| `ndma` | security | Jesca |
| `met_kenya` | security | Jesca |
| `nps` | security | Jesca |
| `kenya_red_cross` | security | Jesca |
| `kilimo` | agriculture | Jesca |
| `fao_kenya` | agriculture | Jesca |

---

*Maintained by Iranzi Innocent. Update via Pull Request to `docs/DATA_COLLECTION_RUNBOOK.md`.*
