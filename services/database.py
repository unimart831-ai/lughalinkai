from typing import Optional
import hashlib
import json
import re
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = PROJECT_ROOT / "database" / "lughalink.db"
SCHEMA_PATH = PROJECT_ROOT / "database" / "schema" / "001_initial.sql"
SOURCE_REGISTRY_PATH = PROJECT_ROOT / "database" / "seeds" / "source_registry.json"


def get_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database(db_path: Optional[Path] = None) -> None:
    conn = get_connection(db_path)
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema)
    conn.commit()
    seed_sources(conn)
    conn.close()


def seed_sources(conn: sqlite3.Connection) -> None:
    if not SOURCE_REGISTRY_PATH.exists():
        return
    data = json.loads(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
    for source in data.get("sources", []):
        scrape_config = source.pop("scrape_config", {})
        conn.execute(
            """
            INSERT OR REPLACE INTO sources (
                source_id, organization, country, source_type, domains_covered,
                website, rss_feed, twitter_handle, primary_language,
                secondary_languages, trust_score, priority, adapter,
                scrape_config, robots_txt_respected, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                source["source_id"],
                source["organization"],
                source.get("country", "Kenya"),
                source["source_type"],
                json.dumps(source.get("domains_covered", [])),
                source.get("website"),
                source.get("rss_feed"),
                source.get("twitter_handle"),
                source.get("primary_language", "en"),
                json.dumps(source.get("secondary_languages", [])),
                source.get("trust_score", 80),
                source.get("priority", "medium"),
                source.get("adapter", "generic_html"),
                json.dumps(scrape_config),
                int(source.get("robots_txt_respected", True)),
                int(source.get("active", True)),
            ),
        )
    conn.commit()


def content_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def next_psa_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT COUNT(*) AS c FROM psas").fetchone()
    seq = (row["c"] if row else 0) + 1
    return f"psa_2026_{seq:06d}"
