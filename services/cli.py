from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from services.database import (
    PROJECT_ROOT,
    content_hash,
    get_connection,
    init_database,
    next_psa_id,
)
from services.metadata.classifier import classify_psa
from services.metadata.enrichment import (
    extract_keywords,
    infer_audience,
    infer_domain,
    infer_urgency,
)
from services.models import PSARecord, ScrapeConfig, SourceRecord, SourceType
from services.preprocessing.cleaning import clean_raw_content
from services.scraper.adapters import ScraperOrchestrator
from services.validation.engine import validate_psa

app = typer.Typer(help="LughaLink AI — PSA Intelligence Platform CLI")
console = Console()


def _load_source(conn, source_id: str) -> SourceRecord:
    row = conn.execute("SELECT * FROM sources WHERE source_id = ?", (source_id,)).fetchone()
    if not row:
        raise typer.BadParameter(f"Unknown source: {source_id}")
    return SourceRecord(
        source_id=row["source_id"],
        organization=row["organization"],
        country=row["country"],
        source_type=SourceType(row["source_type"]),
        domains_covered=json.loads(row["domains_covered"]),
        website=row["website"],
        rss_feed=row["rss_feed"],
        twitter_handle=row["twitter_handle"],
        primary_language=row["primary_language"],
        secondary_languages=json.loads(row["secondary_languages"] or "[]"),
        trust_score=row["trust_score"],
        priority=row["priority"],
        adapter=row["adapter"],
        scrape_config=ScrapeConfig(**json.loads(row["scrape_config"] or "{}")),
        robots_txt_respected=bool(row["robots_txt_respected"]),
        active=bool(row["active"]),
    )


def _process_item(conn, source: SourceRecord, item) -> str:
    cleaned = clean_raw_content(item.raw_text, item.raw_html)
    text = cleaned["text"]
    if not text:
        return "rejected"

    is_psa, confidence = classify_psa(item.title, text)
    domain, sub_category = infer_domain(text, default=source.domains_covered[0])
    urgency = infer_urgency(text)
    audience = infer_audience(text)
    keywords = extract_keywords(text)
    lang = cleaned["language"] or source.primary_language
    hash_val = content_hash(text)

    existing = conn.execute(
        "SELECT psa_id FROM psas WHERE content_hash = ?", (hash_val,)
    ).fetchone()
    if existing:
        return "duplicate"

    record = PSARecord(
        psa_id=next_psa_id(conn),
        title=item.title,
        text=text,
        language=lang,
        domain=domain,
        sub_category=sub_category,
        urgency=urgency,
        audience=audience,
        organization=source.organization,
        published_at=item.published_at,
        scraped_at=item.scraped_at,
        source_id=source.source_id,
        source_url=item.source_url,
        trust_score=source.trust_score,
        is_psa=is_psa,
        classification_confidence=confidence,
        keywords=keywords,
        token_count=cleaned["token_count"],
        content_hash=hash_val,
        metadata={"adapter": source.adapter},
    )

    result = validate_psa(record)
    status = "active" if result.valid else "quarantined"

    conn.execute(
        """
        INSERT INTO psas (
            psa_id, title, text, language, domain, sub_category, urgency,
            audience, location, organization, published_at, scraped_at,
            source_id, source_url, trust_score, verified, is_psa,
            classification_confidence, keywords, token_count, content_hash,
            metadata, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.psa_id,
            record.title,
            record.text,
            record.language,
            record.domain,
            record.sub_category,
            record.urgency.value,
            json.dumps(record.audience),
            json.dumps(record.location),
            record.organization,
            record.published_at.isoformat() if record.published_at else None,
            record.scraped_at.isoformat(),
            record.source_id,
            record.source_url,
            record.trust_score,
            int(record.verified),
            int(record.is_psa),
            record.classification_confidence,
            json.dumps(record.keywords),
            record.token_count,
            record.content_hash,
            json.dumps(record.metadata),
            status,
        ),
    )
    return "stored" if result.valid else "quarantined"


@app.command()
def init_db():
    """Initialize database schema and seed sources."""
    init_database()
    console.print("[green]Database initialized.[/green]")


@app.command()
def validate_sources():
    """List all registered sources."""
    conn = get_connection()
    rows = conn.execute("SELECT source_id, organization, active, trust_score FROM sources").fetchall()
    table = Table(title="Source Registry")
    table.add_column("ID")
    table.add_column("Organization")
    table.add_column("Active")
    table.add_column("Trust")
    for row in rows:
        table.add_row(row["source_id"], row["organization"], str(bool(row["active"])), str(row["trust_score"]))
    console.print(table)
    conn.close()


@app.command()
def scrape(
    source: str = typer.Option(None, help="Source ID to scrape"),
    all_active: bool = typer.Option(False, "--all-active", help="Scrape all active sources"),
):
    """Scrape PSA content from registered sources."""
    conn = get_connection()
    orchestrator = ScraperOrchestrator()

    if all_active:
        source_ids = [
            r["source_id"]
            for r in conn.execute("SELECT source_id FROM sources WHERE active = 1").fetchall()
        ]
    elif source:
        source_ids = [source]
    else:
        console.print("[red]Provide --source or --all-active[/red]")
        raise typer.Exit(1)

    for sid in source_ids:
        src = _load_source(conn, sid)
        started = datetime.utcnow().isoformat()
        stored = rejected = 0
        try:
            items = orchestrator.scrape(src)
            for item in items:
                outcome = _process_item(conn, src, item)
                if outcome == "stored":
                    stored += 1
                else:
                    rejected += 1
            status = "success"
            error = None
        except Exception as exc:
            items = []
            status = "failed"
            error = str(exc)
            console.print(f"[red]{sid}: {exc}[/red]")

        conn.execute(
            """
            INSERT INTO scrape_logs (source_id, started_at, finished_at, status,
                items_found, items_stored, items_rejected, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                sid,
                started,
                datetime.utcnow().isoformat(),
                status,
                len(items) if status != "failed" else 0,
                stored,
                rejected,
                error,
            ),
        )
        conn.commit()
        console.print(f"[cyan]{sid}[/cyan]: stored={stored}, rejected={rejected}")

    conn.close()


@app.command()
def stats():
    """Print dataset statistics."""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) AS c FROM psas WHERE status = 'active'").fetchone()["c"]
    by_domain = conn.execute(
        "SELECT domain, COUNT(*) AS c FROM psas WHERE status='active' GROUP BY domain"
    ).fetchall()
    by_lang = conn.execute(
        "SELECT language, COUNT(*) AS c FROM psas WHERE status='active' GROUP BY language"
    ).fetchall()

    console.print(f"\n[bold]Active PSAs:[/bold] {total}\n")
    console.print("[bold]By domain[/bold]")
    for row in by_domain:
        console.print(f"  {row['domain']}: {row['c']}")
    console.print("[bold]By language[/bold]")
    for row in by_lang:
        console.print(f"  {row['language']}: {row['c']}")
    conn.close()


@app.command()
def export(
    output: Path = typer.Option(
        PROJECT_ROOT / "datasets" / "processed" / "psa_export.csv",
        help="Output CSV path",
    ),
):
    """Export active PSAs to course-format CSV."""
    import pandas as pd

    conn = get_connection()
    rows = conn.execute(
        """
        SELECT psa_id, domain, title, text, language, source_url,
               published_at, urgency, organization, metadata
        FROM psas WHERE status = 'active'
        """
    ).fetchall()
    conn.close()

    df = pd.DataFrame([dict(r) for r in rows])
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    console.print(f"[green]Exported {len(df)} rows to {output}[/green]")


if __name__ == "__main__":
    app()
