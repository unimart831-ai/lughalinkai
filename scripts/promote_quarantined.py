"""Re-score quarantined PSAs and promote those that now pass the classifier."""

from services.database import get_connection
from services.metadata.classifier import classify_psa
from services.validation.engine import validate_psa
from services.models import PSARecord, Urgency
import json

conn = get_connection()
rows = conn.execute("SELECT * FROM psas WHERE status = 'quarantined'").fetchall()
promoted = 0
for row in rows:
    is_psa, score = classify_psa(row["title"], row["text"])
    record = PSARecord(
        psa_id=row["psa_id"],
        title=row["title"],
        text=row["text"],
        language=row["language"],
        domain=row["domain"],
        sub_category=row["sub_category"],
        urgency=Urgency(row["urgency"] or "medium"),
        audience=json.loads(row["audience"] or "[]"),
        organization=row["organization"],
        source_id=row["source_id"],
        source_url=row["source_url"],
        trust_score=row["trust_score"],
        is_psa=is_psa,
        classification_confidence=score,
        keywords=json.loads(row["keywords"] or "[]"),
        token_count=row["token_count"],
        content_hash=row["content_hash"],
    )
    result = validate_psa(record)
    if result.valid:
        conn.execute(
            "UPDATE psas SET status='active', is_psa=1, classification_confidence=? WHERE psa_id=?",
            (score, row["psa_id"]),
        )
        promoted += 1
conn.commit()
active = conn.execute("SELECT COUNT(*) AS c FROM psas WHERE status='active'").fetchone()["c"]
conn.close()
print(f"Promoted {promoted} quarantined -> active. Active total now: {active}")
