"""Strict PSA quality gate for clean-sheet curation.

Keeps public advisories / notices; rejects news fluff, long reports,
nav dumps, and partnership PR that is not a public instruction.
"""

from __future__ import annotations

import re
from typing import Optional

from services.metadata.classifier import classify_psa

# Soft PSA length band (tokens). Longer bodies are usually articles/reports.
MIN_TOKENS = 12
MAX_TOKENS = 350
MIN_SHORT_ADVISORY = 8
MIN_CLASSIFIER_SCORE = 0.28
MIN_CLASSIFIER_SCORE_WITH_FORCE = 0.20

PSA_FORCE = re.compile(
    r"\b(public notice|press release|advisory|alert|"
    r"members of the public|general public|citizens? are (advised|reminded)|"
    r"the commission (reminds|urges|advises|informs)|"
    r"prohibited|must present|deadline|register (to|for|by)|"
    r"vaccinat|immuni|evacuate|curfew|boil water|wash (your )?hands)\b",
    re.I,
)

NAV_JUNK = re.compile(
    r"(main navigation|home about us|quick links|copyright|"
    r"all rights reserved|facebook|twitter tweets|staff mail|"
    r"organogram|cookie|subscribe to|current page \d|next page|"
    r"last page|skip to content)",
    re.I,
)
LISTING_DUMP = re.compile(
    r"(SNo Notice Description|Notice Description Notice Year Notice Link)",
    re.I,
)
NGO_STUB = re.compile(
    r"(pray with us|click on the link to view|become a force for positive|"
    r"get involved|our structure|our vision and values|take action today|"
    r"follow us on twitter|download publication|annual reports?/)",
    re.I,
)
OFF_TOPIC = re.compile(
    r"\b(stadium|indoor games|football|celebrity|gossip|goonism|"
    r"bhang trafficking|transfer rumour|trending|premier league)\b",
    re.I,
)
LISTICLE = re.compile(
    r"\b(full list|list of (public )?universities|courses in kenya|"
    r"how to apply for)\b",
    re.I,
)
# Institutional news / PR — not a public advisory unless PSA_FORCE also matches.
GENRE_NOISE = re.compile(
    r"\b(explore (partnership|closer cooperation|cooperation)|"
    r"signed an? (mou|memorandum)|capacity-?building|"
    r"breakfast meeting|country brief|situation report|format situation|"
    r"strengthen (collaboration|partnership)|"
    r"hosts? .{0,40}(for talks|stakeholders)|"
    r"presents? .{0,40}to (senate|committee)|"
    r"engages? .{0,40}associations?|"
    r"joins multi-agency|"
    r"reviews? (isms|ict policies)|"
    r"circular bioeconomy|resilient livelihoods|"
    r"originally published|posted \d)\b",
    re.I,
)

ALLOWED_LANGS = {"en", "sw"}


def _title_and_body(text: str) -> tuple[str, str]:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return "", ""
    # Many exports are "Title. Body…"
    if ". " in text[:180]:
        title, _, rest = text.partition(". ")
        if 3 <= len(title.split()) <= 25:
            return title, rest or text
    return text[:120], text


def strict_psa_rejection_reason(
    text: str,
    *,
    source: str = "",
    lang: str = "en",
    contributor: str = "",
    origin_file: str = "",
) -> Optional[str]:
    """Return quarantine reason, or None if the row may stay in the clean sheet."""
    primary = re.sub(r"\s+", " ", (text or "").strip())
    source_l = (source or "").lower()
    contrib = (contributor or "").lower()
    tokens = len(primary.split())

    if tokens == 0:
        return "empty_text"
    if "angela" in contrib or origin_file == "psa_dataset.csv":
        return "angela_raw_scrape"
    if NAV_JUNK.search(primary):
        return "nav_boilerplate"
    if LISTING_DUMP.search(primary):
        return "listing_page_dump"
    if primary.count("Home") >= 3 and "About" in primary:
        return "menu_like"
    if NGO_STUB.search(primary) and not PSA_FORCE.search(primary):
        return "ngo_website_stub"
    if any(
        x in source_l
        for x in ("/get-involved", "/about-us/", "/role-faith", "/annual-reports", "/faq")
    ):
        if not PSA_FORCE.search(primary) or tokens < 40:
            return "ngo_about_page"
    if OFF_TOPIC.search(primary) and not PSA_FORCE.search(primary):
        return "off_topic_news"
    if LISTICLE.search(primary) and not PSA_FORCE.search(primary):
        return "listicle_not_psa"
    if tokens < MIN_TOKENS:
        if PSA_FORCE.search(primary) and tokens >= MIN_SHORT_ADVISORY:
            return None
        return "too_short"
    if tokens > MAX_TOKENS:
        return "too_long_for_psa"
    if lang not in ALLOWED_LANGS and lang not in {"", "unknown"}:
        return f"non_target_language:{lang}"
    if tokens < 25 and not PSA_FORCE.search(primary):
        if any(
            h in source_l
            for h in ("wvi.org", "amref.org", "vsointernational", "actionagainsthunger")
        ):
            return "short_ngo_non_psa"

    # Hard reject report genres even if a weak PSA keyword appears.
    if re.search(
        r"\b(country brief|situation report|format situation|key message update)\b",
        primary,
        re.I,
    ):
        return "report_not_psa"

    if GENRE_NOISE.search(primary) and not PSA_FORCE.search(primary):
        return "genre_news_not_psa"

    title, body = _title_and_body(primary)
    _is_psa, score = classify_psa(title, body)
    has_force = bool(PSA_FORCE.search(primary))
    min_score = MIN_CLASSIFIER_SCORE_WITH_FORCE if has_force else MIN_CLASSIFIER_SCORE
    if score < min_score and not has_force:
        return f"low_psa_score:{score:.2f}"
    if has_force and score < 0.15 and tokens > 220:
        return f"weak_forced_narrative:{score:.2f}"
    # Even with a force phrase, reject if score is extremely weak and text is long narrative
    if score < 0.18 and tokens > 250:
        return f"weak_long_narrative:{score:.2f}"
    return None
