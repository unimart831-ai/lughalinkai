-- LughaLink AI — Initial Schema (Product 1: PSA Intelligence Platform)
-- Compatible with PostgreSQL; SQLite subset used for local dev

CREATE TABLE IF NOT EXISTS sources (
    source_id           TEXT PRIMARY KEY,
    organization        TEXT NOT NULL,
    country             TEXT NOT NULL DEFAULT 'Kenya',
    source_type         TEXT NOT NULL,  -- government, un_agency, ngo, media
    domains_covered     TEXT NOT NULL,  -- JSON array
    website             TEXT,
    rss_feed            TEXT,
    twitter_handle      TEXT,
    primary_language    TEXT NOT NULL DEFAULT 'en',
    secondary_languages TEXT,           -- JSON array
    trust_score         INTEGER NOT NULL DEFAULT 80,
    priority            TEXT NOT NULL DEFAULT 'medium',
    adapter             TEXT NOT NULL DEFAULT 'generic_html',
    scrape_config       TEXT,           -- JSON
    robots_txt_respected BOOLEAN NOT NULL DEFAULT TRUE,
    active              BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS psas (
    psa_id                      TEXT PRIMARY KEY,
    title                       TEXT NOT NULL,
    text                        TEXT NOT NULL,
    language                    TEXT NOT NULL,
    domain                      TEXT NOT NULL,
    sub_category                TEXT,
    urgency                     TEXT NOT NULL DEFAULT 'medium',
    audience                    TEXT,           -- JSON array
    location                    TEXT,           -- JSON object
    organization                TEXT NOT NULL,
    published_at                TEXT,
    scraped_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    source_id                   TEXT NOT NULL REFERENCES sources(source_id),
    source_url                  TEXT NOT NULL,
    trust_score                 INTEGER NOT NULL,
    verified                    BOOLEAN NOT NULL DEFAULT FALSE,
    is_psa                      BOOLEAN NOT NULL DEFAULT TRUE,
    classification_confidence   REAL,
    keywords                    TEXT,           -- JSON array
    token_count                 INTEGER NOT NULL,
    content_hash                TEXT NOT NULL UNIQUE,
    metadata                    TEXT,           -- JSON
    status                      TEXT NOT NULL DEFAULT 'active',  -- active, quarantined, archived
    created_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at                  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS translations (
    translation_id      TEXT PRIMARY KEY,
    psa_id              TEXT NOT NULL REFERENCES psas(psa_id),
    source_language     TEXT NOT NULL,
    target_language     TEXT NOT NULL,
    translated_text     TEXT NOT NULL,
    method              TEXT NOT NULL DEFAULT 'human',
    confidence          REAL,
    verified            BOOLEAN NOT NULL DEFAULT FALSE,
    reviewer_notes      TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(psa_id, target_language, method)
);

CREATE TABLE IF NOT EXISTS scrape_logs (
    log_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id           TEXT NOT NULL REFERENCES sources(source_id),
    started_at          TEXT NOT NULL,
    finished_at         TEXT,
    status              TEXT NOT NULL,  -- success, partial, failed
    items_found         INTEGER DEFAULT 0,
    items_stored        INTEGER DEFAULT 0,
    items_rejected      INTEGER DEFAULT 0,
    error_message       TEXT,
    metadata            TEXT
);

CREATE TABLE IF NOT EXISTS psa_pairs (
    pair_id             TEXT PRIMARY KEY,
    psa_id_a            TEXT NOT NULL REFERENCES psas(psa_id),
    psa_id_b            TEXT NOT NULL REFERENCES psas(psa_id),
    language_a          TEXT NOT NULL,
    language_b          TEXT NOT NULL,
    alignment_method    TEXT NOT NULL,  -- url_match, date_title_fuzzy, manual
    alignment_score     REAL,
    verified            BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(psa_id_a, psa_id_b)
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id         TEXT PRIMARY KEY,
    psa_id              TEXT REFERENCES psas(psa_id),
    translation_id      TEXT REFERENCES translations(translation_id),
    feedback_type       TEXT NOT NULL,  -- correct, incorrect, suggest_edit
    suggested_text      TEXT,
    reviewer_language   TEXT,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_psas_domain ON psas(domain);
CREATE INDEX IF NOT EXISTS idx_psas_language ON psas(language);
CREATE INDEX IF NOT EXISTS idx_psas_source ON psas(source_id);
CREATE INDEX IF NOT EXISTS idx_psas_published ON psas(published_at);
CREATE INDEX IF NOT EXISTS idx_psas_hash ON psas(content_hash);
CREATE INDEX IF NOT EXISTS idx_translations_psa ON translations(psa_id);
CREATE INDEX IF NOT EXISTS idx_scrape_logs_source ON scrape_logs(source_id);
