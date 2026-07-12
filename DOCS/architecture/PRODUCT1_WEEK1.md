# PSA Intelligence Platform — Week 1 Execution Playbook

> **Week 1 is not "data collection." Week 1 is building the company's data infrastructure.**

## 1. Strategic Alignment

### What the course asks for (DSA 4020 PDF)

| Requirement | Course wording | Our startup interpretation |
|-------------|----------------|---------------------------|
| Dataset size | ≥5,000 sentences per language pair | Week 1: EN/SW collection + alignment; Week 2+: NLLB seeding for luo/guz/som |
| Sources | ≥10 reliable sources documented | Source Registry with trust scores, adapters, scrape logs |
| Structure | CSV/JSON: PSA_ID, Domain, EN, SW, targets, Source, Date, Metadata | PostgreSQL knowledge objects + exportable CSV for submission |
| Cleaning | Dedup, langdetect, relevance filter | 8-module pipeline (see below) |
| Domains | Education, Health, Security, Agriculture, Governance | Full taxonomy from PSA Categories PDF (25 sub-categories) |
| Deliverable | Week 1 report + GitHub upload | Platform + dataset stats + sample entries |

### The one sentence that matters

**Every downstream product (monitoring agent, translation API, web app, WhatsApp, feedback loop) reads from the same PSA knowledge base. If Week 1 is a CSV file, everything else breaks.**

---

## 2. Product 1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PSA INTELLIGENCE PLATFORM                     │
├─────────────────────────────────────────────────────────────────┤
│  M1 Source Registry    →  M2 Trust Scoring                    │
│  M3 Scraper Engine     →  M4 PSA Classifier                   │
│  M5 Cleaning Pipeline    →  M6 Metadata Enrichment              │
│  M7 Validation Engine    →  M8 Knowledge Database               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │  Export Layer    │
                    │  CSV / JSON /    │
                    │  Parquet for ML  │
                    └──────────────────┘
```

### Module ownership (Team of 5)

| Module | Primary owner | Support |
|--------|---------------|---------|
| M1 Source Registry | Product Lead | Data Engineer |
| M2 Trust Scoring | Data Engineer | Product Lead |
| M3 Scraper Engine | Data Engineer | Backend Engineer |
| M4 PSA Classifier | ML Engineer | Data Engineer |
| M5 Cleaning Pipeline | Data Engineer | ML Engineer |
| M6 Metadata Enrichment | ML Engineer | Data Engineer |
| M7 Validation Engine | Backend Engineer | ML Engineer |
| M8 Knowledge Database | Backend Engineer | Data Engineer |

---

## 3. The PSA Knowledge Object

Every ingested item becomes this — not a spreadsheet row.

```json
{
  "psa_id": "psa_2026_000001",
  "title": "Ministry of Health: Avoid unnecessary travel to Ebola hotspots",
  "text": "Ministry of Health advises the public to avoid unnecessary travel...",
  "language": "en",
  "domain": "health",
  "sub_category": "disease_prevention_and_control",
  "urgency": "high",
  "audience": ["everyone", "travelers"],
  "location": {"country": "Kenya", "county": null, "region": "national"},
  "organization": "Ministry of Health",
  "published_at": "2026-01-15T09:00:00Z",
  "source_url": "https://www.health.go.ke/...",
  "source_id": "moh_kenya",
  "trust_score": 100,
  "verified": true,
  "is_psa": true,
  "classification_confidence": 0.91,
  "keywords": ["ebola", "travel", "health advisory"],
  "token_count": 42,
  "content_hash": "sha256:...",
  "metadata": {
    "scrape_method": "beautifulsoup",
    "raw_html_path": "datasets/raw/moh_20260115_abc.html"
  }
}
```

**Course CSV export** is a *view* of this object — not the source of truth.

---

## 4. Module Specifications

### M1 — Source Discovery Engine

**Purpose:** Know where PSAs come from before writing a single scraper.

**Deliverable:** `database/seeds/source_registry.json` (≥15 sources Week 1)

**Source record schema:**

```json
{
  "source_id": "moh_kenya",
  "organization": "Ministry of Health",
  "country": "Kenya",
  "type": "government",
  "domains_covered": ["health"],
  "website": "https://www.health.go.ke",
  "rss_feed": null,
  "twitter_handle": "@MOH_Kenya",
  "primary_language": "en",
  "secondary_languages": ["sw"],
  "trust_score": 100,
  "priority": "high",
  "adapter": "generic_html",
  "scrape_config": {
    "listing_url": "https://www.health.go.ke/...",
    "article_selector": "article.post",
    "title_selector": "h1",
    "body_selector": ".entry-content",
    "date_selector": "time",
    "rate_limit_seconds": 2
  },
  "robots_txt_respected": true,
  "active": true
}
```

**Week 1 target sources (minimum 10, stretch 20):**

| # | Source | Domain | Trust |
|---|--------|--------|-------|
| 1 | Ministry of Health | Health | 100 |
| 2 | Ministry of Education | Education | 100 |
| 3 | IEBC | Governance | 100 |
| 4 | NDMA | Security/Disaster | 100 |
| 5 | Kenya Met Department | Disaster | 100 |
| 6 | National Police Service | Security | 100 |
| 7 | Ministry of Agriculture | Agriculture | 100 |
| 8 | Huduma Kenya / eCitizen | Governance | 95 |
| 9 | WHO Kenya | Health | 95 |
| 10 | UNICEF Kenya | Health/Education | 90 |
| 11 | KUCCPS | Education | 100 |
| 12 | HELB | Education | 100 |
| 13 | FAO Kenya | Agriculture | 90 |
| 14 | Kenya Red Cross | Disaster | 90 |
| 15 | Citizen TV (verified alerts) | Multi | 80 |

### M2 — Source Quality Score

Automatic at ingest time. Used to sort search results and weight training data.

| Source type | Base score |
|-------------|------------|
| Official national government | 100 |
| UN agency | 95 |
| International NGO | 90 |
| County government | 85 |
| National media (verified) | 80 |
| Local media | 70 |
| Community org | 60 |

Modifiers: `-10` if no publish date, `-20` if scrape fails 3×, `+5` if manually verified.

### M3 — Scraper Engine

**Design pattern:** Adapter registry. One orchestrator, many adapters.

```
ScraperOrchestrator
├── GenericHtmlAdapter      (most gov sites)
├── RssFeedAdapter          (WHO, news feeds)
├── TwitterAdapter          (Phase 2 — Week 2)
├── PdfAdapter              (gov PDF circulars)
└── ManualUploadAdapter     (team manual uploads for PDFs / blocked sources)
```

**Rules (non-negotiable):**
- Respect `robots.txt`
- Rate limit: default 2s between requests per domain
- Store raw HTML/PDF in `datasets/raw/{source_id}/{date}/`
- Log every run to `scrape_logs` table
- Fail gracefully — one broken source must not stop the pipeline

**Week 1 goal:** 3 working adapters (GenericHtml, RssFeed, ManualUpload) covering ≥5 sources.

### M4 — PSA Detection Engine

**Problem:** Most scraped pages are news, not PSAs.

**Week 1 approach (rule-based + keyword scoring):**

PSA signals (+):
- Imperative verbs: "avoid", "report", "register", "vaccinate", "boil", "evacuate"
- Authority prefix: "Ministry of", "IEBC reminds", "NDMA warns"
- Deadline language: "by [date]", "before", "deadline"
- Advisory tone markers: "advises", "urges", "encourages"

Non-PSA signals (−):
- Opinion/analysis: "experts say", "commentary"
- Sports/entertainment keywords
- Length > 2,000 tokens (likely article, not PSA)

**Threshold:** `classification_score >= 0.6` → store as PSA candidate.

**Week 2 upgrade:** Fine-tune a small classifier on 200 manually labeled examples.

### M5 — Cleaning Pipeline

Each step is a pure function — independently testable.

```
raw_content
  → extract_text()          # trafilatura / BeautifulSoup
  → strip_boilerplate()     # nav, footer, ads
  → normalize_whitespace()
  → fix_unicode()
  → detect_language()
  → deduplicate_by_hash()   # SHA-256 of normalized text
  → length_filter()         # 10–500 tokens for PSA
  → store_interim()
```

**Tests required:** One test per step in `tests/services/test_cleaning.py`.

### M6 — Metadata Enrichment

**Week 1: Rule-based enrichment** (no LLM dependency).

| Field | Method |
|-------|--------|
| domain | Keyword map from `configs/domains.yaml` |
| sub_category | Sub-keyword map from PSA Categories PDF |
| urgency | "emergency/warning/outbreak" → emergency; "deadline/register by" → high |
| audience | Keyword: "farmers", "students", "parents", "drivers" |
| location | County name dictionary (47 counties) |
| keywords | TF-IDF top-5 or simple keyword extraction |

### M7 — Validation Engine

Gate before database insert. Returns `{valid: bool, errors: [], warnings: []}`.

| Check | Type | Action |
|-------|------|--------|
| Empty text | Error | Reject |
| Duplicate hash | Error | Reject (or merge) |
| < 10 tokens | Error | Reject |
| > 500 tokens | Warning | Flag for review |
| Language mismatch | Warning | Flag |
| trust_score < 50 | Warning | Quarantine table |
| Missing date | Warning | Use scrape date |
| Invalid URL | Error | Reject |
| is_psa = false | Error | Reject |

### M8 — Knowledge Database

See `database/schema/001_initial.sql`.

**Week 1:** SQLite for dev, PostgreSQL schema ready for Week 2 deployment.

**Export commands for course submission:**
```bash
python -m services.cli export --format csv --output datasets/processed/psa_week1.csv
python -m services.cli stats --report docs/reports/week1_dataset_summary.md
```

---

## 5. Low-Resource Language Pairs — Current Plan

Parallel Dholuo/Ekegusii/Somali PSAs are not available online in the volumes the course requires. Our approach:

### Phase A — Collect monolingual PSAs (Week 1)
Target: as many **English and Kiswahili** PSAs as we can from official sources.

Many gov pages publish both languages → true parallel EN↔SW pairs.

### Phase B — Align EN↔SW (Week 1–2)
- Same URL with different language paths (`/en/`, `/sw/`)
- Same publish date + fuzzy title match (rapidfuzz ≥ 85)
- Manual alignment by the domain owner where needed

### Phase C — Seed target languages (Week 2+)
- NLLB-200 zero-shot: EN → luo, guz, som
- Mark records as `translation_method: nllb_zero_shot`
- Keep seeded translations separate from any future manually checked set

### Phase D — Manual review (team only, when available)
- Spot-check samples per domain (team members, not a native-speaker study)
- Flag obvious errors in GitHub Issues
- Set `verified: true` only after a team member has read and approved the entry
- **We do not currently have native-speaker validation.** Document whatever review we actually do in the Week 1/2 report and in commit/PR notes.

---

## 6. Seven-Day Execution Plan

### Day 1 — Foundation (All hands, 4 hours)

| Time | Task | Owner |
|------|------|-------|
| 0–1h | Team kickoff: roles, GitHub, branch strategy | Product Lead |
| 1–2h | Clone repo, install deps, run `init_db.py` | All |
| 2–3h | Review source registry, assign sources per person | Product Lead + Data |
| 3–4h | Each member validates 3 sources (URL works? PSAs present?) | All |

**Exit criteria:** Repo running locally, 15 sources validated, issues logged.

### Day 2 — Scraper Core

| Task | Owner |
|------|-------|
| Implement `GenericHtmlAdapter` | Data Engineer |
| Implement `ScraperOrchestrator` + scrape logs | Backend Engineer |
| Write adapter tests | Data Engineer |
| Scrape first 100 PSAs from MOH + IEBC | Data Engineer |

**Exit criteria:** ≥100 raw PSAs in `datasets/raw/`, scrape logs in DB.

### Day 3 — Cleaning + Classification

| Task | Owner |
|------|-------|
| Build cleaning pipeline (M5) | Data Engineer |
| Build PSA classifier rules (M4) | ML Engineer |
| Language detection integration | ML Engineer |
| Run pipeline on Day 2 raw data | Data Engineer |

**Exit criteria:** ≥500 clean PSA candidates in `datasets/interim/`.

### Day 4 — Database + Validation

| Task | Owner |
|------|-------|
| Finalize schema, migrations | Backend Engineer |
| Implement validation engine (M7) | Backend Engineer |
| Metadata enrichment rules (M6) | ML Engineer |
| Ingest validated PSAs to DB | Backend + Data |

**Exit criteria:** ≥2,000 PSAs in database with full metadata.

### Day 5 — Scale Collection

| Task | Owner |
|------|-------|
| Add 5 more source adapters | Data Engineer |
| Parallel scrape all active sources | All (each owns 3 sources) |
| Manual upload interface for PDFs | Frontend Engineer |
| Deduplication audit | ML Engineer |

**Exit criteria:** ≥5,000 PSAs in database across all 5 course domains.

### Day 6 — Quality + EN/SW Alignment

| Task | Owner |
|------|-------|
| Domain balance check (pie chart) | ML Engineer |
| EN↔SW parallel pair detection | Data Engineer |
| Quarantine review (false positives) | Product Lead + domain owner |
| Export course CSV | Backend Engineer |

**Exit criteria:** Domain distribution documented, ≥3,000 EN/SW pairs identified.

### Day 7 — Report + Demo

| Task | Owner |
|------|-------|
| Generate `week1_dataset_summary.md` | Product Lead |
| Record 5-min pipeline demo video | Product Lead |
| Code review + merge to main | All |
| Submit Week 1 report to supervisor | Product Lead |

**Exit criteria:** Report submitted, GitHub updated, supervisor-ready demo.

---

## 7. Week 1 Success Criteria

### Course minimum (must pass)
- [ ] ≥5,000 PSA sentences in structured export
- [ ] ≥10 documented sources with URLs
- [ ] All 5 domains represented (Health, Education, Security, Agriculture, Governance)
- [ ] Cleaning pipeline code in GitHub
- [ ] Week 1 report with stats + 10 sample entries + challenges

### Startup standard (what separates you)
- [ ] Source Registry with trust scores (≥15 sources)
- [ ] Modular scraper with ≥3 adapters
- [ ] PSA classifier filtering non-PSA content
- [ ] PostgreSQL/SQLite knowledge database (not CSV-first)
- [ ] Validation engine with quarantine workflow
- [ ] Metadata enrichment (domain, urgency, audience, keywords)
- [ ] Scrape logs for future monitoring agent
- [ ] Export pipeline for ML (Week 2 ready)
- [ ] Reproducible CLI: `scrape → clean → validate → store → export`

---

## 8. What NOT to Do in Week 1

| Trap | Why it fails |
|------|--------------|
| Start with NLLB translation | No clean data = garbage in, garbage out |
| Build Streamlit first | UI without data is a demo of nothing |
| One monolithic scraper script | Breaks when any site changes; not a platform |
| CSV as primary storage | Monitoring agent, API, feedback can't plug in |
| Scrape everything without PSA filter | 80% news articles pollute the dataset |
| Skip robots.txt / rate limits | Ethical failure + IP bans mid-project |
| Inventing parallel translations without recording method | Breaks reproducibility; eval results cannot be trusted |

---

## 9. Week 1 Report Template

Save as `docs/reports/week1_dataset_summary.md` in the repo. Dr. Ombui can review it there alongside the code and data export.

```markdown
# LughaLink AI — Week 1 Report

## 1. Summary
- Total PSAs collected: X
- Sources active: X/15
- Domain distribution: [chart]
- EN/SW parallel pairs: X

## 2. Source Documentation
[Table of 10+ sources with URLs, type, trust score]

## 3. Dataset Schema
[Link to data dictionary]

## 4. Sample Entries (10)
[Real PSA examples with metadata]

## 5. Pipeline Architecture
[Diagram + module descriptions]

## 6. Quality Measures
- Deduplication rate
- PSA classifier precision (manual check on 50 samples by team)
- Language detection accuracy

## 7. Challenges & Blockers
[What failed, what is not done yet — e.g. scraper selectors, low-resource pairs, no native-speaker review yet]

## 8. Week 2 Plan
[Preprocessing, NLLB seeding, team spot-checks on seeded translations]
```

---

## 10. Definition of Done

Week 1 is complete when a team member who was not involved can run:

```bash
git clone <repo>
pip install -e ".[dev]"
python scripts/init_db.py
python -m services.cli scrape --all-active
python -m services.cli process-pending
python -m services.cli export --format csv
python -m services.cli stats
```

...and get a valid dataset with ≥5,000 PSAs, full metadata, and a summary report — without asking anyone how the pipeline works.

That is a startup data foundation.
