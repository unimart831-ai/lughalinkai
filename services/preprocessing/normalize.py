"""Week 2 PSA text normalization, tokenization, and code-switch signals."""

from __future__ import annotations

import re
from typing import Optional

from services.preprocessing.cleaning import detect_language, fix_unicode, normalize_whitespace
from services.preprocessing.glossary import apply_glossary_normalization, find_glossary_hits, load_glossary

# Letter/digit stuck together (common scrape artifact): NOTICE15th -> NOTICE 15th
# Do not split ordinals like 15th / 1st / 2nd / 3rd.
LETTER_DIGIT_RE = re.compile(r"([A-Za-z])(\d)")
DIGIT_LETTER_RE = re.compile(r"(\d)(?!(?:st|nd|rd|th)\b)([A-Za-z])", re.IGNORECASE)
# Collapse repeated punctuation
MULTI_PUNCT_RE = re.compile(r"([!?.,:;])\1{2,}")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
HASHTAG_RE = re.compile(r"#[\w]+")
MENTION_RE = re.compile(r"@[\w]+")
TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)?|[^\sA-Za-z0-9]")

# Lightweight Kiswahili cue words (not a full detector).
SWAHILI_CUES = {
    "na",
    "ya",
    "wa",
    "kwa",
    "ni",
    "katika",
    "hii",
    "hizo",
    "tafadhali",
    "serikali",
    "afya",
    "elimu",
    "usalama",
    "kilimo",
    "raia",
    "ombi",
    "habari",
    "angalia",
    "epuka",
    "ripoti",
    "hospitali",
    "chanjo",
    "uchaguzi",
    "kura",
}


def insert_alnum_boundaries(text: str) -> str:
    text = LETTER_DIGIT_RE.sub(r"\1 \2", text)
    text = DIGIT_LETTER_RE.sub(r"\1 \2", text)
    return text


def normalize_psa_text(text: Optional[str], *, apply_glossary: bool = True) -> str:
    """Normalize PSA body for EDA / MT while keeping meaning intact."""
    if not text:
        return ""
    out = fix_unicode(str(text))
    out = insert_alnum_boundaries(out)
    out = MULTI_PUNCT_RE.sub(r"\1\1", out)
    out = normalize_whitespace(out)
    if apply_glossary:
        out = apply_glossary_normalization(out, load_glossary())
        out = normalize_whitespace(out)
    return out


def tokenize(text: str) -> list[str]:
    if not text:
        return []
    return TOKEN_RE.findall(text)


def word_tokens(text: str) -> list[str]:
    return [t.lower() for t in tokenize(text) if re.search(r"[A-Za-z0-9]", t)]


def detect_code_switching(text: str) -> dict:
    """Heuristic EN/SW mix signal for PSA lines."""
    words = word_tokens(text)
    if not words:
        return {
            "code_switch": False,
            "sw_cue_count": 0,
            "sw_cue_ratio": 0.0,
            "lang_primary": None,
        }
    sw_hits = sum(1 for w in words if w in SWAHILI_CUES)
    ratio = sw_hits / len(words)
    lang = detect_language(text)
    # Mixed if detector says one lang but the other has clear cues, or mid-range SW ratio.
    mixed = bool(0.08 <= ratio <= 0.55 and sw_hits >= 2)
    if lang == "en" and sw_hits >= 3:
        mixed = True
    if lang == "sw" and ratio < 0.5:
        mixed = True
    return {
        "code_switch": mixed,
        "sw_cue_count": sw_hits,
        "sw_cue_ratio": round(ratio, 4),
        "lang_primary": lang,
    }


def preprocess_psa_text(text: Optional[str]) -> dict:
    """Full Week 2 text feature bundle for one PSA body."""
    normalized = normalize_psa_text(text)
    tokens = word_tokens(normalized)
    cs = detect_code_switching(normalized)
    glossary_hits = find_glossary_hits(normalized)
    return {
        "text_norm": normalized,
        "token_count": len(tokens),
        "char_count": len(normalized),
        "sentence_count": len(re.findall(r"[.!?]+", normalized)) or (1 if normalized else 0),
        "vocab_tokens": tokens,
        "url_count": len(URL_RE.findall(normalized)),
        "hashtag_count": len(HASHTAG_RE.findall(normalized)),
        "mention_count": len(MENTION_RE.findall(normalized)),
        "glossary_hits": glossary_hits,
        "glossary_hit_count": len(glossary_hits),
        **cs,
    }
