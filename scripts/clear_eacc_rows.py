"""Delete previous EACC rows so we can re-scrape with full-article extraction."""

from services.database import get_connection

conn = get_connection()
deleted = conn.execute("DELETE FROM psas WHERE source_id = ?", ("eacc_kenya",)).rowcount
conn.commit()
conn.close()
print(f"Deleted {deleted} eacc_kenya rows.")
