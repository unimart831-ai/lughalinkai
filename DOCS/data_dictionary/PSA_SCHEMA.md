# LughaLink PSA Data Dictionary

## Core Entity: PSA

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `psa_id` | string | yes | Unique ID: `psa_{year}_{sequence}` |
| `title` | string | yes | Headline or first-line summary |
| `text` | string | yes | Clean PSA body text |
| `language` | ISO 639-1 | yes | `en`, `sw`, `luo`, `guz`, `som` |
| `domain` | enum | yes | Top-level category (see domains.yaml) |
| `sub_category` | enum | no | From PSA Categories PDF |
| `urgency` | enum | yes | `emergency`, `high`, `medium`, `low` |
| `audience` | string[] | no | Target groups |
| `location` | JSON | no | `{country, county, subcounty, region}` |
| `organization` | string | yes | Publishing body |
| `published_at` | datetime | no | Original publication date |
| `scraped_at` | datetime | yes | When we ingested it |
| `source_id` | FK | yes | Reference to sources table |
| `source_url` | URL | yes | Canonical source link |
| `trust_score` | int 0–100 | yes | From source + modifiers |
| `verified` | bool | yes | Human-verified flag |
| `is_psa` | bool | yes | Passed PSA classifier |
| `classification_confidence` | float | no | 0.0–1.0 |
| `keywords` | string[] | no | Extracted keywords |
| `token_count` | int | yes | Word/token count |
| `content_hash` | string | yes | SHA-256 for dedup |
| `metadata` | JSON | no | Scrape method, raw file path, etc. |

## Course Export View (CSV)

Required by DSA 4020 submission:

| Column | Maps to |
|--------|---------|
| PSA_ID | `psa_id` |
| Domain | `domain` |
| English | `text` where language=en, or aligned pair |
| Kiswahili | `text` where language=sw, or aligned pair |
| Dholuo | translation where target=luo (Week 2+) |
| Ekegusii | translation where target=guz (Week 2+) |
| Somali | translation where target=som (Week 2+) |
| Source | `source_url` |
| Date | `published_at` |
| Urgency | `urgency` |
| Metadata | JSON blob |

## Translation Record (Week 2+)

| Field | Type | Description |
|-------|------|-------------|
| `translation_id` | string | Unique ID |
| `psa_id` | FK | Source PSA |
| `source_language` | ISO 639-1 | Origin language |
| `target_language` | ISO 639-1 | Target language |
| `translated_text` | string | Output text |
| `method` | enum | `human`, `nllb_zero_shot`, `nllb_finetuned`, `mt5` |
| `confidence` | float | Model confidence if applicable |
| `verified` | bool | Team member has manually checked this record (`false` by default) |
| `reviewer_id` | FK | Optional user reference |

## Domain Taxonomy

From `configs/domains.yaml` — aligned with PSA Categories PDF:

### Health
- disease_prevention_and_control
- maternal_and_child_health
- public_health_campaigns
- mental_health_awareness
- healthcare_access

### Agriculture
- crop_production
- livestock_management
- agribusiness_and_market_access
- sustainable_farming
- agricultural_training

### Education
- access_to_education
- vocational_training
- civic_education
- educational_resources
- school_safety_and_inclusion

### Security & Safety
- public_safety_awareness
- crime_prevention
- national_security
- gender_based_violence
- cybersecurity

### Governance
- anti_corruption_initiatives
- public_participation
- elections_and_voter_education
- public_service_delivery
- devolution_and_local_governance

## Urgency Classification Rules

| Level | Triggers |
|-------|----------|
| emergency | outbreak, evacuate, immediate danger, red alert |
| high | deadline within 7 days, warning, register by |
| medium | campaign, awareness, upcoming event |
| low | general information, reminder |

## Language Codes

| Language | ISO 639-1 | ISO 639-3 | NLLB Code |
|----------|-----------|-----------|-----------|
| English | en | eng | eng_Latn |
| Kiswahili | sw | swa | swh_Latn |
| Dholuo | luo | luo | luo_Latn |
| Ekegusii | guz | guz | guz_Latn |
| Somali | som | som | som_Latn |
