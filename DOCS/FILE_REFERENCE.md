# LughaLink AI — File Reference Guide

**Audience:** All team members (Iranzi, Angela, Leona, Jesca)  
**Purpose:** Explain every important file under `configs/`, `database/`, `datasets/`, `scripts/`, and `services/` — what it is, what it does, and when you touch it.  
**Last updated:** 21 July 2026

---

## How to use this document

1. New to the project? Read [Section 1](#1-how-the-folders-fit-together) first.
2. Need to fix a broken scrape? Jump to [source_registry.json](#322-databaseseedssource_registryjson).
3. Need to understand a Python function? Use the [services section](#5-services--the-processing-code).
4. For step-by-step collect commands, see also `docs/DATA_COLLECTION_RUNBOOK.md`.

---

## Table of contents

1. [How the folders fit together](#1-how-the-folders-fit-together)
2. [configs/](#2-configs--rules-and-keywords)
3. [database/](#3-database--schema-sources-and-live-storage)
4. [datasets/](#4-datasets--files-on-disk)
5. [scripts/](#5-scripts--one-button-starters)
6. [services/](#6-services--the-processing-code)
7. [Which file to open when something breaks](#7-which-file-to-open-when-something-breaks)
8. [What to commit vs never commit](#8-what-to-commit-vs-never-commit)

---

## 1. How the folders fit together

```
configs/          → keyword rules (domain, urgency, audience)
database/seeds/   → list of websites + scrape settings
database/schema/  → table blueprints
scripts/          → start the database
services/         → scrape → clean → classify → enrich → validate → store
database/*.db     → live local warehouse
datasets/         → CSV exports and future raw/gold folders
```

**One scrape path:**

```
source_registry.json
        │
        ▼
   init_db / seed → sources table
        │
        ▼
   cli scrape → adapters → cleaning → classifier → enrichment → validation
        │
        ▼
   psas table (lughalink.db)
        │
        ▼
   export → datasets/processed/*.csv
```

---

## 2. `configs/` — rules and keywords

### 2.1 `configs/domains.yaml`

| | |
|--|--|
| **Type** | YAML configuration (not Python) |
| **Purpose** | Tell the system how to tag PSAs after they are scraped |
| **Used by** | `services/metadata/enrichment.py` |
| **Who edits** | Anyone proposing better keywords (via PR); Lead may merge |

**What is inside:**

| Section | Meaning |
|---------|---------|
| `domains` | Five course domains: health, agriculture, education, security, governance |
| `sub_categories` | Finer topics under each domain (from the PSA Categories PDF) |
| `keywords` | Words that signal that sub-category (e.g. `malaria`, `iebc`, `flood`) |
| `urgency_rules` | Words that map to emergency / high / medium / low |
| `audience_keywords` | Words that map to parents, students, farmers, etc. |

**Example (simplified):**

```yaml
domains:
  health:
    sub_categories:
      disease_prevention_and_control:
        keywords: [malaria, vaccination, ebola, cholera]
urgency_rules:
  emergency:
    keywords: [emergency, outbreak, evacuate]
```

**When to edit:**

- Scraped text is tagged with the wrong domain
- You want a new keyword (e.g. `by-election` under governance)

**When not to edit:**

- You only need to change a website URL or CSS selector → that is `source_registry.json`, not this file

---

## 3. `database/` — schema, sources, and live storage

```
database/
├── schema/
│   └── 001_initial.sql
├── seeds/
│   └── source_registry.json
└── lughalink.db          ← created on your machine (not in Git)
```

---

### 3.1 `database/schema/001_initial.sql`

| | |
|--|--|
| **Type** | SQL |
| **Purpose** | Creates all database tables and indexes |
| **Used by** | `services/database.py` → `init_database()` |
| **Who edits** | Lead / backend only (schema changes affect everyone) |

**Tables created:**

| Table | Purpose |
|-------|---------|
| `sources` | Registered websites and scrape settings |
| `psas` | Collected public service announcements |
| `translations` | Future translated text (Week 2+) |
| `scrape_logs` | History of each scrape run |
| `psa_pairs` | Future EN↔SW (or other) aligned pairs |
| `feedback` | Future community correct/incorrect feedback |

**Important `psas` columns:**

| Column | Meaning |
|--------|---------|
| `psa_id` | Unique ID, e.g. `psa_2026_000087` |
| `title` | Headline |
| `text` | Clean body text |
| `language` | `en`, `sw`, etc. |
| `domain` | health / education / … |
| `urgency` | emergency / high / medium / low |
| `source_id` | Which registry source it came from |
| `source_url` | Original web URL |
| `content_hash` | Fingerprint used to detect duplicates |
| `status` | `active`, `quarantined`, or `archived` |
| `is_psa` | Whether the classifier said yes |
| `classification_confidence` | Score from the classifier |

**Indexes:** Speed up queries by domain, language, source, date, and hash.

---

### 3.2 `database/seeds/source_registry.json`

| | |
|--|--|
| **Type** | JSON |
| **Purpose** | Master list of all PSA sources and how to scrape them |
| **Used by** | `seed_sources()` in `services/database.py` |
| **Who edits** | Each person edits **only their own** `source_id` blocks |

**Top-level structure:**

```json
{
  "version": "1.0.0",
  "updated_at": "2026-07-11",
  "sources": [ { ... }, { ... } ]
}
```

**Fields on each source:**

| Field | Meaning | Example |
|-------|---------|---------|
| `source_id` | Short ID used in CLI | `"iebc"` |
| `organization` | Full organisation name | `"Independent Electoral and Boundaries Commission"` |
| `country` | Country | `"Kenya"` |
| `source_type` | government / un_agency / ngo / media | `"government"` |
| `domains_covered` | Domains this source usually covers | `["governance"]` |
| `website` | Homepage | `"https://www.iebc.or.ke"` |
| `rss_feed` | RSS URL if using RSS adapter | `null` or a feed URL |
| `twitter_handle` | Optional social handle | `"@IEBCKenya"` |
| `primary_language` | Main language on the site | `"en"` |
| `secondary_languages` | Other languages | `["sw"]` |
| `trust_score` | Reliability 0–100 | `100` |
| `priority` | Scraping priority | `"high"` |
| `adapter` | Which scraper to use | `"generic_html"` or `"rss_feed"` |
| `scrape_config` | How to find articles on the page | see below |
| `robots_txt_respected` | Try to honour robots.txt | `true` |
| `active` | Include in scrapes | `true` / `false` |

**Fields inside `scrape_config`:**

| Field | Meaning | Example |
|-------|---------|---------|
| `listing_url` | Page that lists many announcements | `"https://www.iebc.or.ke/news/"` |
| `article_selector` | CSS for article containers / links on listing | `"article, a"` |
| `title_selector` | CSS for the headline on an article page | `"h3, h1, h2"` |
| `body_selector` | CSS for the main text | `"article, .post"` |
| `date_selector` | CSS for the date | `"time, .date"` |
| `link_href_contains` | Only keep links containing this string | `"/news/?"` |
| `max_items` | Max articles per scrape run | `200` |
| `rate_limit_seconds` | Seconds to wait between requests | `1.2` |
| `requires_psa_filter` | Extra filter flag for noisy media sites | `false` |

**After every edit to this file:**

```powershell
python scripts/init_db.py
```

**Ownership (do not edit other people's blocks):**

| source_id | Owner |
|-----------|-------|
| `iebc`, `huduma` | Iranzi |
| `moh_kenya`, `who_kenya`, `unicef_kenya` | Angela |
| `moe_kenya`, `kuccps`, `helb` | Leona |
| `ndma`, `met_kenya`, `nps`, `kenya_red_cross` | Jesca (security) |
| `kilimo`, `fao_kenya` | Jesca (agriculture) |

---

### 3.3 `database/lughalink.db`

| | |
|--|--|
| **Type** | SQLite database file |
| **Purpose** | Live local storage of sources + PSAs + logs |
| **Created by** | `init_database()` |
| **Committed to Git?** | **No** (local only) |

Each teammate has their own copy on their laptop.  
Team work is shared via code + `source_registry.json` + exported CSV, not by sharing this `.db` file.

---

## 4. `datasets/` — files on disk

```
datasets/
├── raw/           ← original downloads / manual text
├── interim/       ← optional middle stage
├── processed/     ← CSV exports for course / modeling
├── gold/          ← future high-quality checked set
└── validation/    ← future evaluation subset
```

Empty folders may only contain `.gitkeep` so Git keeps the folder.

---

### 4.1 `datasets/raw/`

| | |
|--|--|
| **Purpose** | Store original HTML/PDF text before cleaning |
| **Committed?** | Usually **no** (large / machine-specific) |
| **When used** | Manual uploads, debugging a bad scrape |

Suggested naming for manual files:

```
datasets/raw/manual/iebc_20260721.txt
```

---

### 4.2 `datasets/interim/`

| | |
|--|--|
| **Purpose** | Halfway-cleaned data (optional; reserved for later pipelines) |
| **Committed?** | Usually no |

---

### 4.3 `datasets/processed/`

| | |
|--|--|
| **Purpose** | Clean exports ready to share or submit |
| **Example** | `governance_psa_export.csv` |
| **Created by** | `python -m services.cli export` |
| **Committed?** | Yes, when the team agrees (e.g. Week 1 submission file) |

---

### 4.4 `datasets/gold/`

| | |
|--|--|
| **Purpose** | Best PSAs that a team member has carefully checked |
| **When** | Later (after spot-checks). Not claimed as native-speaker validated unless that actually happens |

---

### 4.5 `datasets/validation/`

| | |
|--|--|
| **Purpose** | Held-out samples for evaluation (Week 2–4) |
| **When** | Modeling / evaluation phase |

---

## 5. `scripts/` — one-button starters

### 5.1 `scripts/init_db.py`

| | |
|--|--|
| **Type** | Python script |
| **Purpose** | Create tables and load sources from JSON |
| **Run** | `python scripts/init_db.py` |

**What the file does line by line:**

1. Adds the project root to Python’s path so `services` can be imported  
2. Imports `init_database` from `services.database`  
3. Calls `init_database()`  
4. Prints `LughaLink database ready.`

**When to run:**

- After cloning the repo  
- After editing `source_registry.json`  
- After deleting a broken local `lughalink.db` and starting fresh  

---

## 6. `services/` — the processing code

```
services/
├── __init__.py
├── models.py
├── database.py
├── cli.py
├── scraper/
│   ├── __init__.py
│   └── adapters.py
├── preprocessing/
│   ├── __init__.py
│   └── cleaning.py
├── metadata/
│   ├── __init__.py
│   ├── classifier.py
│   └── enrichment.py
└── validation/
    ├── __init__.py
    └── engine.py
```

`__init__.py` files are empty (or nearly empty). They exist so Python treats the folder as a **package** you can import.

---

### 6.1 `services/models.py`

| | |
|--|--|
| **Purpose** | Define the shape of every important object |
| **Library** | Pydantic |

**Classes:**

#### `Urgency` (enum)

Allowed values: `emergency`, `high`, `medium`, `low`.

#### `SourceType` (enum)

Allowed values: `government`, `un_agency`, `ngo`, `media`.

#### `ScrapeConfig`

How to scrape one website.

| Field | Default | Meaning |
|-------|---------|---------|
| `listing_url` | none | Listing page URL |
| `article_selector` | `"article"` | CSS for listing items |
| `title_selector` | `"h1"` | CSS for title |
| `body_selector` | `".entry-content"` | CSS for body |
| `date_selector` | `"time"` | CSS for date |
| `rate_limit_seconds` | `2.0` | Delay between requests |
| `requires_psa_filter` | `false` | Extra filter flag |
| `link_href_contains` | none | Keep only matching links |
| `max_items` | `50` | Cap per scrape run |

#### `SourceRecord`

Full source definition (maps to one row in `sources` + JSON config).

#### `RawScrapedItem`

What the scraper returns **before** cleaning:

- `source_id`, `source_url`, `title`
- `raw_html` and/or `raw_text`
- `published_at`, `scraped_at`

#### `PSARecord`

Final structured PSA ready for the database (all metadata fields).

#### `ValidationResult`

- `valid` — true/false  
- `errors` — hard failures  
- `warnings` — soft issues  

---

### 6.2 `services/database.py`

| | |
|--|--|
| **Purpose** | Open the DB, create tables, seed sources, helper IDs/hashes |

**Constants / paths:**

| Name | Points to |
|------|-----------|
| `PROJECT_ROOT` | Repo root folder |
| `DEFAULT_DB_PATH` | `database/lughalink.db` |
| `SCHEMA_PATH` | `database/schema/001_initial.sql` |
| `SOURCE_REGISTRY_PATH` | `database/seeds/source_registry.json` |

**Functions:**

| Function | What it does |
|----------|--------------|
| `get_connection(db_path=None)` | Opens SQLite; enables foreign keys; returns connection |
| `init_database(db_path=None)` | Runs schema SQL, then `seed_sources()`, closes connection |
| `seed_sources(conn)` | Reads JSON registry; `INSERT OR REPLACE` into `sources` |
| `content_hash(text)` | Normalizes text (lowercase, collapse spaces) → SHA-256 string for dedup |
| `next_psa_id(conn)` | Counts rows in `psas` → returns `psa_2026_000001` style ID |

---

### 6.3 `services/cli.py`

| | |
|--|--|
| **Purpose** | Command-line interface (Typer + Rich) |
| **Run as** | `python -m services.cli <command>` |

**Startup:**

- `load_dotenv()` — loads `.env` (including `SCRAPER_SSL_VERIFY`)

**Helper functions:**

#### `_load_source(conn, source_id)`

- Reads one row from `sources`  
- Builds a `SourceRecord` (including nested `ScrapeConfig`)  
- Raises an error if `source_id` is unknown  

#### `_process_item(conn, source, item)`

Full pipeline for **one** scraped article:

1. `clean_raw_content(...)` → cleaned text + language + token count  
2. If empty → `"rejected"`  
3. `classify_psa(title, text)` → `is_psa`, confidence  
4. Enrichment: domain, urgency, audience, keywords  
5. `content_hash(text)` — if hash exists → `"duplicate"`  
6. Build `PSARecord` with `next_psa_id()`  
7. `validate_psa(record)`  
8. Insert into `psas` as `active` or `quarantined`  
9. Return `"stored"` or `"quarantined"`  

**CLI commands:**

| Command | Function | What it does |
|---------|----------|--------------|
| `init-db` | `init_db()` | Initialize DB + seed sources |
| `validate-sources` | `validate_sources()` | Print source table |
| `scrape` | `scrape(...)` | Scrape one source or all active |
| `stats` | `stats()` | Count active PSAs by domain/language |
| `export` | `export(...)` | Write CSV under `datasets/processed/` |

**`scrape` details:**

1. Load source(s)  
2. `ScraperOrchestrator().scrape(src)` → list of `RawScrapedItem`  
3. For each item, `_process_item(...)`  
4. Write a row to `scrape_logs`  
5. Print `stored=X, rejected=Y`  

Note: in the printed summary, `"rejected"` includes duplicates, empty items, and quarantined outcomes that were not `"stored"`.

---

### 6.4 `services/scraper/adapters.py`

| | |
|--|--|
| **Purpose** | Download content from websites or RSS feeds |

**Functions / classes:**

#### `_ssl_verify() -> bool`

- Reads env var `SCRAPER_SSL_VERIFY`  
- Returns `False` if set to `false` / `0` / `no`  
- Needed on many Windows machines for Kenyan gov HTTPS sites  

#### `BaseAdapter` (abstract)

- Requires subclasses to implement `fetch(source) -> list[RawScrapedItem]`

#### `GenericHtmlAdapter`

Used for most government HTML sites (`adapter: "generic_html"`).

| Method | What it does |
|--------|--------------|
| `fetch(source)` | GET listing page → extract links → GET each article → parse title/body/date → return items |
| `_extract_article_links(soup, config, base_url)` | Collect unique links; filter by `link_href_contains` if set |
| `_check_robots(source, url)` | Try to read robots.txt; skip hard-fail if unreachable |

**Libraries:** `httpx` (HTTP), `BeautifulSoup` (HTML).

**Guards:**

- Skips articles with body shorter than 10 words  
- Sleeps `rate_limit_seconds` between requests  
- Caps at `max_items`  

#### `RssFeedAdapter`

Used when `adapter: "rss_feed"` (e.g. WHO).

| Method | What it does |
|--------|--------------|
| `fetch(source)` | Parse `rss_feed` with `feedparser`; build items from title + summary |

#### `ManualUploadAdapter`

| Method | What it does |
|--------|--------------|
| `fetch(source)` | Currently returns `[]` (placeholder for future manual upload CLI) |

#### `ADAPTERS`

Dictionary mapping adapter name → instance.

#### `ScraperOrchestrator`

| Method | What it does |
|--------|--------------|
| `__init__(adapters=None)` | Uses default `ADAPTERS` if none given |
| `scrape(source)` | Picks adapter by `source.adapter`, calls `fetch` |

---

### 6.5 `services/preprocessing/cleaning.py`

| | |
|--|--|
| **Purpose** | Turn raw HTML/text into clean PSA text |

| Function | What it does |
|----------|--------------|
| `extract_text(raw_text, raw_html)` | Prefer `raw_text`; else strip text from HTML |
| `strip_boilerplate(text)` | Drop lines like Home / Share / Copyright / Advertisement |
| `normalize_whitespace(text)` | Collapse multiple spaces into one |
| `fix_unicode(text)` | Unicode NFKC normalization |
| `detect_language(text)` | Guess language with `langdetect` (`en`, `sw`, `som`, …) |
| `token_count(text)` | Number of whitespace-separated words |
| `clean_raw_content(raw_text, raw_html)` | Runs all steps; returns `{text, language, token_count}` |

---

### 6.6 `services/metadata/classifier.py`

| | |
|--|--|
| **Purpose** | Decide whether text is a real PSA |

**Constants:**

| Name | Role |
|------|------|
| `PSA_POSITIVE_PATTERNS` | Regexes that look like advisories / notices |
| `PSA_NEGATIVE_PATTERNS` | Regexes that look like sports/opinion junk |
| `AUTHORITY_PREFIX` | Title starting with Ministry / IEBC / Public Notice, etc. |

**Function:**

#### `classify_psa(title, text) -> (is_psa, score)`

1. Combine title + text  
2. Add score for positive pattern matches  
3. Subtract for negative matches  
4. Boost if title matches authority prefix  
5. Boost for imperative words (`must`, `prohibited`, …)  
6. Adjust by length (very long texts penalized)  
7. Clamp score to 0.0–1.0  
8. `is_psa = score >= 0.55`  

---

### 6.7 `services/metadata/enrichment.py`

| | |
|--|--|
| **Purpose** | Attach domain, urgency, audience, keywords |
| **Reads** | `configs/domains.yaml` |

| Function | What it does |
|----------|--------------|
| `_load_config()` | Load YAML into a dict |
| `infer_domain(text, default="governance")` | Count keyword hits; return best domain + sub-category |
| `infer_urgency(text)` | Return `Urgency` enum from urgency keyword rules |
| `infer_audience(text)` | Return list of audiences, or `["everyone"]` |
| `extract_keywords(text, limit=5)` | Return up to 5 matched keywords |

---

### 6.8 `services/validation/engine.py`

| | |
|--|--|
| **Purpose** | Final quality gate before marking a PSA active |

#### `validate_psa(record) -> ValidationResult`

| Condition | Type |
|-----------|------|
| Empty text | Error |
| Fewer than 10 tokens | Error |
| More than 500 tokens | Warning |
| `is_psa` is False | Error |
| Missing `source_url` | Error |
| Trust score &lt; 50 | Warning |
| Missing publish date | Warning |
| Unexpected language code | Warning |

- **Any error** → `valid=False` → stored as `quarantined`  
- **No errors** → `valid=True` → stored as `active`  

---

## 7. Which file to open when something breaks

| Problem | Open this file | What to change |
|---------|----------------|----------------|
| SSL certificate error | `.env` | `SCRAPER_SSL_VERIFY=false` |
| Listing URL 404 | `database/seeds/source_registry.json` | Fix `listing_url` |
| Titles are `"Untitled"` | `source_registry.json` | Fix `title_selector` |
| Empty / tiny body | `source_registry.json` | Fix `body_selector` |
| Wrong links scraped | `source_registry.json` | Set `link_href_contains` |
| Too few items per run | `source_registry.json` | Raise `max_items` |
| Wrong domain tag | `configs/domains.yaml` | Add/fix keywords |
| Too many quarantined | `services/metadata/classifier.py` | Patterns/threshold (discuss with team) |
| Duplicate storm | (normal) | `content_hash` in `database.py` already dedups |
| DB missing sources | Run `scripts/init_db.py` | Reloads registry |
| Need CSV for report | `python -m services.cli export` | Writes under `datasets/processed/` |

---

## 8. What to commit vs never commit

### Commit these

| Path | Why |
|------|-----|
| `configs/domains.yaml` | Shared tagging rules |
| `database/schema/*.sql` | Shared schema |
| `database/seeds/source_registry.json` | Shared source configs |
| `services/**/*.py` | Shared code |
| `scripts/init_db.py` | Shared starter |
| `datasets/processed/*.csv` | When team agrees to publish an export |
| `docs/**` | Guides |

### Never commit these

| Path | Why |
|------|-----|
| `database/lughalink.db` | Local database |
| `.env` | Local secrets / SSL flag |
| `.venv/` | Local Python environment |
| Most of `datasets/raw/**` | Large / personal scrape dumps |

---

## Quick command map (tied to files)

| You type | Code path that runs |
|----------|---------------------|
| `python scripts/init_db.py` | `scripts/init_db.py` → `database.init_database` → schema + `source_registry.json` |
| `python -m services.cli validate-sources` | `cli.validate_sources` → reads `sources` table |
| `python -m services.cli scrape --source iebc` | `cli.scrape` → `adapters` → `cleaning` → `classifier` → `enrichment` → `validation` → `psas` |
| `python -m services.cli stats` | `cli.stats` → counts `psas` where `status='active'` |
| `python -m services.cli export` | `cli.export` → CSV in `datasets/processed/` |

---

## Related docs

| Doc | Use it for |
|-----|------------|
| `docs/DATA_COLLECTION_RUNBOOK.md` | Step-by-step collect workflow |
| `docs/TEAM_ROSTER.md` | Who owns which branch/source |
| `docs/TEAM_OPERATIONS.md` | GitHub collaboration rules |
| `docs/data_dictionary/PSA_SCHEMA.md` | Field meanings for PSA records |
| `docs/architecture/PRODUCT1_WEEK1.md` | Week 1 product plan |

---

*Maintained by Iranzi Innocent. Propose updates via Pull Request to `docs/FILE_REFERENCE.md`.*
