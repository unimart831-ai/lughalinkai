"""Week 2 preprocessing pipeline over PSA CSV rows."""

from __future__ import annotations

import json
from collections import Counter
from typing import Any, Iterable, Optional

from services.preprocessing.normalize import preprocess_psa_text, word_tokens


CLEAN_FIELDS = [
    "PSA_ID",
    "Domain",
    "English",
    "English_norm",
    "Kiswahili",
    "Kiswahili_norm",
    "Target Languages",
    "Source",
    "Date",
    "Metadata",
    "token_count",
    "char_count",
    "sentence_count",
    "lang_primary",
    "code_switch",
    "sw_cue_count",
    "has_kiswahili",
    "glossary_hits",
    "glossary_hit_count",
    "url_count",
    "hashtag_count",
    "mention_count",
    "split",
    "validation_subset",
]


def _parse_metadata(raw: Any) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(str(raw))
    except (TypeError, json.JSONDecodeError):
        return {}


def process_psa_row(row: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Return enriched cleaned row, or None if English body is empty after normalize."""
    english = row.get("English") or ""
    kiswahili = row.get("Kiswahili") or ""
    feats = preprocess_psa_text(english)
    if not feats["text_norm"]:
        return None

    sw_feats = preprocess_psa_text(kiswahili) if str(kiswahili).strip() else None
    has_sw = bool(sw_feats and sw_feats["text_norm"])
    meta = _parse_metadata(row.get("Metadata"))
    meta = {
        **meta,
        "week2_preprocessed": True,
        "lang_primary": feats["lang_primary"],
        "code_switch": feats["code_switch"],
        "glossary_hits": feats["glossary_hits"],
    }

    return {
        "PSA_ID": row.get("PSA_ID") or "",
        "Domain": row.get("Domain") or "Unknown",
        "English": english,
        "English_norm": feats["text_norm"],
        "Kiswahili": kiswahili if has_sw else "",
        "Kiswahili_norm": sw_feats["text_norm"] if has_sw else "",
        "Target Languages": row.get("Target Languages") or "",
        "Source": row.get("Source") or "",
        "Date": row.get("Date") or "",
        "Metadata": json.dumps(meta, ensure_ascii=False),
        "token_count": feats["token_count"],
        "char_count": feats["char_count"],
        "sentence_count": feats["sentence_count"],
        "lang_primary": feats["lang_primary"] or "",
        "code_switch": bool(feats["code_switch"]),
        "sw_cue_count": feats["sw_cue_count"],
        "has_kiswahili": has_sw,
        "glossary_hits": "|".join(feats["glossary_hits"]),
        "glossary_hit_count": feats["glossary_hit_count"],
        "url_count": feats["url_count"],
        "hashtag_count": feats["hashtag_count"],
        "mention_count": feats["mention_count"],
        "split": "",
        "validation_subset": False,
    }


def process_corpus(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        processed = process_psa_row(row)
        if processed:
            out.append(processed)
    return out


def compute_eda_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate stats for the Week 2 EDA report / notebook."""
    by_domain: Counter[str] = Counter()
    token_counts: list[int] = []
    vocab: Counter[str] = Counter()
    glossary: Counter[str] = Counter()
    lang: Counter[str] = Counter()
    code_switch = 0
    with_sw = 0

    for row in rows:
        domain = str(row.get("Domain") or "Unknown")
        by_domain[domain] += 1
        tc = int(row.get("token_count") or 0)
        token_counts.append(tc)
        vocab.update(word_tokens(str(row.get("English_norm") or "")))
        hits = [h for h in str(row.get("glossary_hits") or "").split("|") if h]
        glossary.update(hits)
        lang[str(row.get("lang_primary") or "unknown")] += 1
        if row.get("code_switch") in (True, "True", "true", 1, "1"):
            code_switch += 1
        if row.get("has_kiswahili") in (True, "True", "true", 1, "1"):
            with_sw += 1

    token_counts_sorted = sorted(token_counts)
    n = len(token_counts_sorted)

    def pct(p: float) -> float:
        if not n:
            return 0.0
        idx = min(n - 1, max(0, int(round((p / 100.0) * (n - 1)))))
        return float(token_counts_sorted[idx])

    return {
        "rows": len(rows),
        "by_domain": dict(by_domain),
        "rows_with_kiswahili": with_sw,
        "code_switch_rows": code_switch,
        "lang_primary": dict(lang),
        "token_count": {
            "min": token_counts_sorted[0] if n else 0,
            "p25": pct(25),
            "median": pct(50),
            "p75": pct(75),
            "max": token_counts_sorted[-1] if n else 0,
            "mean": round(sum(token_counts) / n, 2) if n else 0.0,
        },
        "vocabulary_size": len(vocab),
        "top_tokens": vocab.most_common(40),
        "top_glossary_hits": glossary.most_common(20),
        "language_pair_notes": {
            "en_psas": len(rows),
            "en_sw_pairs_present": with_sw,
            "target_lang_placeholders": ["Dholuo", "Ekegusii", "Somali"],
            "gap": "Almost all rows are English-only; EN↔SW harvest still required for true parallel stats.",
        },
    }
