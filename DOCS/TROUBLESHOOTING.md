# LughaLink AI — Data Collection Troubleshooting Playbook

**Audience:** Iranzi, Angela, Leona, Jesca  
**Purpose:** Solve scrape/collection failures the same way every time  
**Related docs:** `DATA_COLLECTION_RUNBOOK.md`, `FILE_REFERENCE.md`, `TEAM_ROSTER.md`

---

## 1. Mindset

You will hit challenges on almost every new source. That is normal.

Treat failures as a **checklist**, not as a dead end:

```text
collect → inspect failure → fix ONE thing → re-test → repeat
```

**Golden rule:** change only one variable at a time  
(URL **or** selector **or** adapter **or** classifier), then scrape again.

---

## 2. Read the scrape result first

```text
source_id: stored=X, rejected=Y
```

| Result | Meaning | First question |
|--------|---------|----------------|
| `stored > 0` | Working | Are titles/text good quality? |
| `stored = 0`, `rejected > 0` | Found pages, but rejected | Classifier? duplicates? weak text? |
| `stored = 0`, `rejected = 0` + error | Could not fetch | SSL? URL? robots? adapter? |
| SSL / certificate error | Network/config issue | Fix `.env` |

### Important meaning of `rejected`

In the CLI summary, `rejected` can include:

- empty text
- duplicates
- quarantined items (failed validation/classifier)

So `stored=0, rejected=10` often means: **10 items were found, none became active.**

---

## 3. Standard solve loop (use every time)

```text
1. Browser: does the page have PSA-like posts?
2. Inspect: find title tag + body container
3. Edit database/seeds/source_registry.json (ONLY your source_id)
4. python scripts/init_db.py
5. python -m services.cli scrape --source YOUR_ID
6. Read stored / rejected
7. Identify the challenge using Section 4
8. Fix ONE thing
9. Re-scrape
10. python -m services.cli stats
```

---

## 4. Challenge map — symptom → cause → fix

### Challenge 1 — SSL certificate error

**Symptom**

```text
CERTIFICATE_VERIFY_FAILED
```

**Cause**  
Windows Python cannot verify some Kenyan government HTTPS certificates.

**Fix**

1. Create/open `.env` in project root  
2. Set:

```env
SCRAPER_SSL_VERIFY=false
```

3. Re-run scrape

**Files involved:** `.env`, `.env.example`

---

### Challenge 2 — Page works in browser, scraper finds no links

**Symptom**
- Chrome shows many articles
- Scrape returns `stored=0, rejected=0` or finds nothing useful

**Cause**  
Listing page is loaded with JavaScript. BeautifulSoup only sees raw HTML.

**Fix (in order)**

1. Look for an **RSS/Atom feed** (`/feed/`, “RSS”, “News feed”)
2. Set:

```json
"adapter": "rss_feed",
"rss_feed": "https://example.go.ke/.../feed/"
```

3. If no feed, find another HTML listing URL
4. Only if still blocked: plan Selenium/Playwright later

**Example:** EACC news listing looked full in browser, but HTML scrape missed links. RSS + full-article fetch worked.

**Files involved:** `database/seeds/source_registry.json`

---

### Challenge 3 — Titles are `"Untitled"`

**Symptom**  
Items appear, but title is `"Untitled"`.

**Cause**  
Wrong `title_selector`.

**Fix**

1. Open one article in Chrome  
2. Right-click headline → **Inspect**  
3. Note tag/class (`h1`, `h3`, `h1.section-title`, …)  
4. Update `title_selector` in your source block  
5. Run:

```powershell
python scripts/init_db.py
python -m services.cli scrape --source YOUR_ID
```

**Example:** IEBC needed `h3`, not `h1`.

**Files involved:** `database/seeds/source_registry.json`

---

### Challenge 4 — Empty body / text too short

**Symptom**
- Rejected for being too short
- Or text is a tiny blurb / caption

**Cause**
- Wrong `body_selector`, or
- RSS summary only (not full article)

**Fix**

1. Inspect a paragraph of main article text  
2. Set `body_selector` to the container (e.g. `.article-box`, `article`, `.entry-content`)  
3. If using RSS, also set:

```json
"fetch_full_article": true,
"title_selector": "h1",
"body_selector": ".article-box"
```

4. Reload DB and scrape again

**Example:** EACC RSS summaries were weak; full page `.article-box` text fixed quality.

**Files involved:** `source_registry.json`, `services/scraper/adapters.py` (RSS full-article support)

---

### Challenge 5 — `stored=0`, `rejected=N` (found items, none active)

**Symptom**  
Exactly like first EACC attempt: `stored=0, rejected=10`.

**Likely causes**

1. Classifier: `not_classified_as_psa`
2. Duplicates from a previous run
3. Empty/weak text

**Fix steps**

1. Confirm source exists:

```powershell
python -m services.cli validate-sources
python -m services.cli stats
```

2. Improve text quality first (Challenge 4)  
3. If domain words are missing from classifier (e.g. `eacc`, `corruption`), update classifier patterns with team agreement  
4. If old bad rows block retries, clear that source’s rows then re-scrape  
5. Re-run scrape and check `stored`

**Files involved:**
- `source_registry.json`
- `services/metadata/classifier.py`
- `services/validation/engine.py`

---

### Challenge 6 — Wrong links scraped

**Symptom**  
Scraper opens menus, “Read more”, homepage, unrelated pages.

**Cause**  
Link filter too broad.

**Fix**  
Set `link_href_contains`:

| Source type | Example filter |
|-------------|----------------|
| IEBC | `"/news/?"` |
| Huduma | `"newsdetails"` |
| Article blogs | `"/en/default/"` or `"/news/"` |

**Files involved:** `source_registry.json`

---

### Challenge 7 — Too few items per run

**Symptom**  
Only 10–50 items though site has hundreds.

**Cause**
- `max_items` cap
- RSS feed only has latest N entries

**Fix**

1. Raise `max_items`  
2. Re-run scrape (duplicates skipped; new ones added)  
3. Add more sources in the same domain  
4. For RSS: accept limited feed size, or add HTML/pagination later

**Files involved:** `source_registry.json`

---

### Challenge 8 — Many quarantined, few active

**Symptom**  
DB has rows, but `stats` active count barely moves.

**Cause**
- Low classifier score
- Long/noisy articles
- Content is news/PR more than classic PSA

**Fix options**

1. Improve extraction (better body text)  
2. Add better keywords to classifier (team discussion)  
3. Prefer notice/advisory pages when available  
4. Manually review quarantined items later  
5. Keep collecting from cleaner PSA sources in parallel

**Files involved:** `classifier.py`, `source_registry.json`

---

### Challenge 9 — Content is news, not PSA

**Symptom**  
Ceremony/partnership stories, not public advisories.

**Cause**  
Official sites mix news and PSAs.

**Fix**

- Prefer “Public Notice”, “Alerts”, “Report corruption”, “Advisories”
- Keep high-trust sources, but expect some quarantine
- Add additional sources for volume

---

### Challenge 10 — 404 / moved page

**Symptom**  
Listing URL fails in browser or scrape.

**Fix**

1. Find the new official URL  
2. Update `listing_url` or `rss_feed`  
3. `python scripts/init_db.py`  
4. Scrape again

**Example:** Huduma `/en/notices` was 404 → `/news` worked.

---

## 5. Decision tree

```text
Did scrape fail with SSL?
  YES → Challenge 1 (.env)
  NO ↓

Did it find items (rejected>0 or stored>0)?
  NO → Challenge 2/10 (JS listing, bad URL, wrong adapter)
       try RSS or different listing URL
  YES ↓

Are titles real (not "Untitled")?
  NO → Challenge 3 (title_selector)
  YES ↓

Is body long enough and meaningful?
  NO → Challenge 4 (body_selector / fetch_full_article)
  YES ↓

Is stored > 0 (active)?
  NO → Challenge 5/8/9 (classifier, duplicates, news-like content)
  YES → Success
       → raise max_items / add next source / export CSV
```

---

## 6. Which file to edit for which problem

| Problem type | File to open |
|--------------|--------------|
| URL, selectors, RSS, max_items, link filter | `database/seeds/source_registry.json` |
| SSL | `.env` |
| “Is this a PSA?” rules | `services/metadata/classifier.py` (discuss with team) |
| Scraper behavior (RSS full article, adapters) | `services/scraper/adapters.py` |
| Domain/urgency keyword tagging | `configs/domains.yaml` |
| Accept/quarantine rules | `services/validation/engine.py` |

**Most common day-to-day edits:** only `source_registry.json`.

---

## 7. Commands cheat sheet

```powershell
cd a:\SYSTEMS_2026\LUGHALINK
.venv\Scripts\activate

python scripts/init_db.py
python -m services.cli validate-sources
python -m services.cli scrape --source YOUR_SOURCE_ID
python -m services.cli stats
python -m services.cli export --output datasets/processed/YOUR_DOMAIN_export.csv
```

After registry edits, always run `init_db.py` before scraping.

---

## 8. Worked examples from this project

### IEBC (HTML)

| Issue | Fix |
|-------|-----|
| Untitled titles | `title_selector: "h3, h1, h2"` |
| Wrong/noisy links | `link_href_contains: "/news/?"` |
| Need more volume | raise `max_items` |

### Huduma (HTML)

| Issue | Fix |
|-------|-----|
| `/en/notices` 404 | use `https://www.hudumakenya.go.ke/news` |
| Article pages | `link_href_contains: "newsdetails"` |

### EACC (RSS + full article)

| Issue | Fix |
|-------|-----|
| JS listing hard to scrape | use `adapter: "rss_feed"` |
| Short weak RSS text | `fetch_full_article: true` + `.article-box` |
| `stored=0` / low classifier score | add EACC/anti-corruption keywords; re-scrape |

---

## 9. Quality checklist before you say “it works”

- [ ] Scrape runs without SSL crash  
- [ ] `stored > 0`  
- [ ] Titles are real headlines  
- [ ] Body looks like usable public information  
- [ ] `stats` domain count increased  
- [ ] You only edited your own `source_id` block  
- [ ] You did **not** commit `lughalink.db` or `.env`

---

## 10. How to report a blocker to the team

Use this template in WhatsApp/GitHub Issue:

```text
Source: eacc_kenya
Command: python -m services.cli scrape --source eacc_kenya
Result: stored=0, rejected=10
Challenge #: 5 (found items, none active)
What I tried: init_db + scrape twice
What I need: help checking classifier / full-article fetch
```

---

## 11. Remember

| Goal | Metric |
|------|--------|
| Scraper works | items found |
| Pipeline works | `stored > 0` |
| Dataset grows | `stats` active count up |
| Course progress | domain totals toward 1,000 each / 5,000 team |

You are doing data engineering: **find → diagnose → fix → verify**.

---

*Maintained by Iranzi Innocent. Update via PR to `docs/TROUBLESHOOTING.md`.*
