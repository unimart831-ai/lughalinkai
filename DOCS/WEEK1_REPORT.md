# Week 1 Report — Data Collection & Curation

**Project:** LughaLink AI (DSA 4020 NLP — Public Service Announcement MT for Kenyan languages)  
**Focus:** Sub-objective 1 — Parallel dataset foundation  
**Period:** 12–27 July 2026  
**Repo:** https://github.com/unimart831-ai/lughalinkai  
**Branch (integration export):** `data/governance`  
**Clean dataset:** `datasets/processed/week1_psa_merged.csv`  
**Quarantine sheet (non-PSA / junk):** `datasets/processed/week1_psa_quarantined.csv`

---

## 1. Executive summary

Week 1 delivered a working **hybrid PSA data infrastructure** and a **cleaned structured corpus** covering Education, Health, Security, Agriculture, and Governance. Non-PSA scrapes were moved to a separate quarantine sheet.

| Metric | Value |
|--------|------:|
| Clean PSA records (after dedupe + quarantine) | **3,539** |
| Quarantined non-PSA / junk rows | **1,106** |
| Approx. English sentences in clean corpus | **~51,500** |
| Domains covered | 5 / 5 |
| Documented active sources in registry | **53** (≥10 required) |
| Rows with Kiswahili text filled | 11 (mostly placeholders ahead) |
| Target-language columns | Dholuo / Ekegusii / Somali placeholders |

**Course threshold:** ≥5,000 parallel sentences — met at the **sentence** level (~51.5k English sentences in the clean sheet). Kiswahili and community-language *pairs* remain Week 2+ work.

---

## 2. Milestone checklist

| Milestone | Status | Evidence |
|-----------|--------|----------|
| Identify and document ≥10 reliable sources | **Done** | `database/seeds/source_registry.json` — 53 active sources (gov, UN/ReliefWeb, NGOs, media) |
| Hybrid scraping pipeline (manual + automated; robots.txt + rate limits) | **Done** | `services/scraper/adapters.py` (BeautifulSoup/httpx/RSS); notebooks + manual CSVs from teammates; `SCRAPER_SSL_VERIFY`, rate limits, robots checks |
| Collect raw PSAs across 5 domains | **Done** | Domain breakdown below |
| Structured CSV/JSON with required columns | **Done** | `week1_psa_merged.csv` + quarantine sheet |
| Initial cleaning: dedupe, langdetect, relevance filter | **Done** | Merge + quarantine of non-PSA / junk rows |
| ≥5,000 parallel sentences (or equivalent) | **Done (sentences)** | ~51.5k EN sentences in clean sheet |
| Week 1 report | **Done** | This document |

---

## 3. Team contributions (who pushed what)

| Contributor | Branch / channel | Kept in clean sheet | Quarantined |
|-------------|------------------|--------------------:|------------:|
| Iranzi Innocent (Lead) | `data/governance` | 3,187 | 853 |
| Leona Kamau | `data/education` | 113 | 40 |
| Jessica Kimani (`kimj073`) | `data/agriculture` | 156 | 145 |
| `michenitumaini-ux` | `main` (media archives) | 83 | 29 |
| Angela Irungu (`Irungu05`) | `main` upload | 0 | 39 |

Quarantine reasons (top): very long reports (589), nav/boilerplate (264), short NGO non-PSA (79), Angela raw scrape (39), NGO about pages (32), off-topic news (37), too short (42), non-EN/SW language (14). Full sheet: `week1_psa_quarantined.csv`.

---

## 4. Sources documented (≥10)

Representative sources from the registry (not exhaustive):

**Government / constitutional bodies**  
1. IEBC — elections & public notices  
2. Kenya Revenue Authority — public notices & press releases  
3. Ministry of Health / Education (listing URLs registered)  
4. EACC — anti-corruption RSS  
5. Huduma Kenya — service notices  
6. Public Service Commission  
7. National Drought Management Authority  
8. Kenya Meteorological Department  
9. Kenya National Examinations Council  

**UN / humanitarian / NGO**  
10. WHO Afro (Kenya + regional news)  
11. ReliefWeb Kenya (reports, disasters, health, refugees, food security)  
12. UNICEF Kenya (press centre)  
13. Kenya Red Cross  

**Media archives**  
14. AllAfrica Kenya  
15. Capital FM / Citizen Digital / Tuko (education & public-interest items)  
16. Team media-archives upload (KNQA/UNHCR and related public notices)

Full machine-readable list: `database/seeds/source_registry.json`.

---

## 5. Pipeline implemented

```
Source Registry → Scraper adapters (HTML / RSS)
      → Cleaning (whitespace, empty body filter)
      → PSA classifier (keyword + authority scoring)
      → Domain enrichment (domains.yaml)
      → SQLite knowledge base (lughalink.db)
      → CSV exports per collector
      → week1 merge (dedupe + langdetect + schema normalize)
```

**Hybrid elements**
- **Automated:** httpx + BeautifulSoup + feedparser; pagination; skip-known-URL re-scrapes; SSL toggle for `.go.ke` hosts.  
- **Manual / notebook:** education KNA notebook; agriculture NGO scrape; media-archives curated CSV; Angela raw text upload.

**Compliance practices**
- Optional robots.txt check per source  
- Configurable `rate_limit_seconds`  
- Duplicate skip by `source_url` / content hash  

---

## 6. Merged dataset schema

File: `datasets/processed/week1_psa_merged.csv`

| Column | Description |
|--------|-------------|
| `PSA_ID` | Canonical ID `psa_2026_######` |
| `Domain` | Health / Education / Security / Agriculture / Governance |
| `English` | Primary English PSA text |
| `Kiswahili` | Swahili text when available (mostly empty in Week 1) |
| `Target Languages` | JSON list placeholder: Dholuo, Ekegusii, Somali |
| `Source` | Canonical URL or source reference |
| `Date` | Publication date when available |
| `Metadata` | JSON: contributor, origin file, lang_detected, token/sentence counts, hash |

Also written: `datasets/processed/week1_psa_quarantined.csv`, `datasets/processed/week1_merge_stats.json`.  
Regenerate with: `python scripts/merge_week1_dataset.py`

### Cleaning applied at merge
- Whitespace normalization  
- SHA-256 content-hash deduplication (**100** duplicates removed)  
- `langdetect` on primary text (keep `en` / `sw` only in clean sheet)  
- Domain label normalization  
- Quarantine of non-PSA rows: nav/boilerplate, listing dumps, NGO about-pages, off-topic news, listicles, empty/too-short stubs, non-target languages, and very long reports (>800 tokens)

---

## 7. Dataset summary statistics

### 7.1 Volume

| Stage | Count |
|-------|------:|
| Rows loaded from all inputs | 4,745 |
| Duplicates removed | 100 |
| Quarantined (non-PSA / junk) | 1,106 |
| **Final clean PSA records** | **3,539** |
| Approx. English sentences (clean) | **~51,500** |
| Records with Kiswahili body | 11 |

### 7.2 By domain (clean sheet)

| Domain | Records | Share |
|--------|--------:|------:|
| Governance | 1,242 | 35.1% |
| Security | 1,150 | 32.5% |
| Health | 775 | 21.9% |
| Education | 224 | 6.3% |
| Agriculture | 148 | 4.2% |
| **Total** | **3,539** | 100% |

### 7.3 Language detection (clean sheet)

| Detected | Records |
|----------|--------:|
| English (`en`) | 3,528 |
| Swahili (`sw`) | 11 |

### 7.4 Balance notes
- Security/Governance dominate because IEBC, KRA, and public-notice sources are high-yield.  
- Education and Agriculture need focused Week-2 collection.  
- True EN↔SW parallel pairs are still sparse; community-language columns are placeholders.

---

## 8. Sample entries (clean sheet)

### Governance — IEBC public notice
- **PSA_ID:** `psa_2026_000001`  
- **Source:** https://www.iebc.or.ke/news/?PUBLIC_NOTICE  
- **English (excerpt):** “The Commission reminds all voters that taking photographs or recording images of marked ballot papers inside the polling booth is strictly prohibited…”

### Health — WHO Kenya
- **PSA_ID:** `psa_2026_000925`  
- **Source:** https://www.afro.who.int/countries/kenya/news/mobile-health-services-kenya-reduce-risk-stillbirths  
- **English (excerpt):** “Mobile health services in Kenya reduce the risk of stillbirths…”

### Education — Kenya News Agency
- **PSA_ID:** `psa_2026_003205`  
- **Source:** https://www.kenyanews.go.ke/kiambu-students-receive-bursaries-ahead-of-school-reopening/  
- **English (excerpt):** “Kiambu Students Receive Bursaries Ahead of School Reopening…”

### Security / humanitarian — WFP Kenya brief
- **PSA_ID:** `psa_2026_000786`  
- **Source:** https://reliefweb.int/report/kenya/wfp-kenya-country-brief-july-2026  
- **English (excerpt):** “WFP Kenya Country Brief July 2026…”

### Agriculture / food systems — ReliefWeb
- **PSA_ID:** `psa_2026_000793`  
- **Source:** https://reliefweb.int/report/kenya/circular-bioeconomy-approaches-resilient-livelihoods-and-peacebui  
- **English (excerpt):** “Circular Bioeconomy Approaches for Resilient Livelihoods and Peacebuilding…”

---

## 9. Challenges faced

1. **Broken / JS-heavy government portals** — MoH, HELB, NPS, Kilimo listings often 404 or client-rendered; selectors needed repeated probing.  
2. **Windows SSL failures** on `.go.ke` — mitigated with `SCRAPER_SSL_VERIFY=false` for local collection.  
3. **Schema drift across teammates** — different column names (`text` vs `English`, `Target Languages` vs `Target_Languages`); solved by merge normalization.  
4. **Domain misclassification** — keyword enrichment can tag IEBC/KRA items into Health/Education; needs stricter source-prioritized domain rules in Week 2.  
5. **Uneven domain volume** — Agriculture/Education lag Security/Governance.  
6. **Near-zero Kiswahili & no community-language translations yet** — Week 1 is English-heavy foundation; parallel pairs are the next bottleneck.  
7. **Media noise** — some entertainment/politics pages pass soft PSA thresholds; classifier tuning continues.  
8. **Dedup across collectors** — 100 overlapping rows removed when combining branch exports.

---

## 10. Honest gaps vs course wording

| Expectation | Week 1 reality |
|-------------|----------------|
| ≥5,000 parallel sentences | Met as **English sentence volume** (~51.5k clean). Not yet 5,000 EN↔SW or EN↔Dholuo aligned pairs. |
| Kiswahili column filled | Almost empty (11 rows). |
| Target languages filled | Placeholders only (`Dholuo`, `Ekegusii`, `Somali`). |
| ≥1,000 PSAs per domain | Governance/Security strong; Health close; Education/Agriculture below 1,000. |
| Selenium | Not required for current adapters; BeautifulSoup/httpx/RSS used. |

---

## 11. Week 2 priorities

1. Boost **Education** and **Agriculture** to ≥1,000 records each.  
2. Collect / align **Kiswahili** PSA variants where official SW pages exist.  
3. Begin NLLB zero-shot drafts into Dholuo / Ekegusii / Somali + human review sample.  
4. Tighten domain inference (prefer source `domains_covered`).  
5. Merge health/security branch exports when Angela/Jessica push them.  
6. Publish one canonical file on `develop`/`main` for submission.

---

## 12. How to reproduce

```bash
# from repo root
python scripts/merge_week1_dataset.py
# outputs:
#   datasets/processed/week1_psa_merged.csv
#   datasets/processed/week1_psa_merged.json
#   datasets/processed/week1_merge_stats.json
```

---

## 13. Deliverable pointers

| Deliverable | Path |
|-------------|------|
| Clean Week 1 CSV | `datasets/processed/week1_psa_merged.csv` |
| Quarantine (non-PSA) CSV | `datasets/processed/week1_psa_quarantined.csv` |
| Merge / quarantine stats | `datasets/processed/week1_merge_stats.json` |
| Source registry | `database/seeds/source_registry.json` |
| Pipeline code | `services/scraper/`, `services/metadata/`, `services/cli.py` |
| This report | `DOCS/WEEK1_REPORT.md` |

---

*Prepared for DSA 4020 Week 1 submission — LughaLink AI team.*
