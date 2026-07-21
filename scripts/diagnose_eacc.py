import feedparser
from bs4 import BeautifulSoup

from services.preprocessing.cleaning import clean_raw_content
from services.metadata.classifier import classify_psa
from services.metadata.enrichment import infer_domain, infer_urgency
from services.models import PSARecord
from services.validation.engine import validate_psa
from services.database import content_hash, get_connection

feed = feedparser.parse("https://eacc.go.ke/en/default/feed/")
conn = get_connection()
print("entries", len(feed.entries))

for i, e in enumerate(feed.entries[:10], 1):
    title = getattr(e, "title", "Untitled")
    summary = getattr(e, "summary", "") or getattr(e, "description", "")
    text = BeautifulSoup(summary, "lxml").get_text("\n", strip=True)
    cleaned = clean_raw_content(text)
    is_psa, score = classify_psa(title, cleaned["text"])
    domain, sub = infer_domain(cleaned["text"], default="governance")
    h = content_hash(cleaned["text"])
    dup = conn.execute("SELECT psa_id FROM psas WHERE content_hash=?", (h,)).fetchone()
    record = PSARecord(
        psa_id="tmp",
        title=title,
        text=cleaned["text"],
        language=cleaned["language"] or "en",
        domain=domain,
        urgency=infer_urgency(cleaned["text"]),
        organization="EACC",
        source_id="eacc_kenya",
        source_url=getattr(e, "link", ""),
        trust_score=100,
        is_psa=is_psa,
        classification_confidence=score,
        token_count=cleaned["token_count"],
        content_hash=h,
    )
    val = validate_psa(record)
    if dup:
        reason = "duplicate"
    elif not val.valid:
        reason = "reject:" + ",".join(val.errors)
    else:
        reason = "WOULD_STORE"
    safe_title = title.encode("ascii", "ignore").decode()[:70]
    print(f"{i}. score={score:.2f} is_psa={is_psa} tokens={cleaned['token_count']} -> {reason}")
    print(f"   title: {safe_title}")
    print(f"   errors={val.errors}")
    print(f"   text[:120]={cleaned['text'][:120]!r}")
