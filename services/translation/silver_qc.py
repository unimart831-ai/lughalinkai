"""Automatic quality checks for silver (unverified) parallel pairs."""

from __future__ import annotations

import re
from typing import Any

from services.preprocessing.cleaning import detect_language
from services.preprocessing.glossary import find_glossary_hits

WS_RE = re.compile(r"\s+")


def length_ratio(src: str, tgt: str) -> float:
    a = max(1, len(WS_RE.sub(" ", src).split()))
    b = max(1, len(WS_RE.sub(" ", tgt).split()))
    return b / a


def is_near_copy(src: str, tgt: str, *, threshold: float = 0.92) -> bool:
    """Reject targets that are almost identical to the source (failed translation)."""
    s = re.sub(r"[^a-z0-9]+", " ", (src or "").lower()).split()
    t = re.sub(r"[^a-z0-9]+", " ", (tgt or "").lower()).split()
    if not s or not t:
        return True
    overlap = len(set(s) & set(t)) / max(len(set(s)), 1)
    return overlap >= threshold and abs(len(s) - len(t)) <= 3


def glossary_preservation_score(src: str, tgt: str) -> float:
    """Fraction of do-not-break glossary hits from source that still appear in target."""
    hits = find_glossary_hits(src)
    if not hits:
        return 1.0
    tgt_l = tgt or ""
    kept = sum(1 for h in hits if re.search(rf"(?<![A-Za-z0-9]){re.escape(h)}(?![A-Za-z0-9])", tgt_l, re.I))
    return kept / len(hits)


def auto_qc_pair(
    source_text: str,
    target_text: str,
    *,
    expected_tgt_lang: str | None = "sw",
    min_src_tokens: int = 5,
    max_src_tokens: int = 100,
    min_ratio: float = 0.45,
    max_ratio: float = 2.2,
) -> dict[str, Any]:
    """Return QC bundle; pass=True means usable as silver training data."""
    src = WS_RE.sub(" ", (source_text or "").strip())
    tgt = WS_RE.sub(" ", (target_text or "").strip())
    reasons: list[str] = []

    # Template Ekegusii is often longer; glossary EN terms may not map 1:1.
    skip_glossary = expected_tgt_lang in {"guz", "kik"}
    if expected_tgt_lang == "guz":
        min_ratio, max_ratio = 0.35, 3.5

    src_tok = len(src.split())
    tgt_tok = len(tgt.split())
    if src_tok < min_src_tokens:
        reasons.append("src_too_short")
    if src_tok > max_src_tokens:
        reasons.append("src_too_long")
    if tgt_tok < 3:
        reasons.append("tgt_too_short")
    if not tgt or tgt.startswith("[DRY_RUN"):
        reasons.append("tgt_missing_or_dry_run")

    ratio = length_ratio(src, tgt) if tgt else 0.0
    if tgt and not (min_ratio <= ratio <= max_ratio):
        reasons.append("bad_length_ratio")

    if tgt and is_near_copy(src, tgt):
        reasons.append("near_copy")

    gloss = glossary_preservation_score(src, tgt) if tgt else 0.0
    if tgt and not skip_glossary and gloss < 0.5:
        reasons.append("glossary_dropped")

    lang = detect_language(tgt) if tgt and not tgt.startswith("[DRY_RUN") else None
    if expected_tgt_lang == "sw" and lang and lang not in ("sw", "en"):
        # langdetect often confuses SW; only hard-fail clear non-SW/EN.
        if lang in ("fr", "de", "es", "pt", "it"):
            reasons.append(f"unexpected_lang:{lang}")

    # Confidence heuristic in [0,1]
    conf = 1.0
    conf -= 0.15 * len(reasons)
    if 0.7 <= ratio <= 1.4:
        conf += 0.05
    conf = max(0.0, min(1.0, conf))

    return {
        "auto_qc_pass": len(reasons) == 0,
        "auto_qc_reasons": reasons,
        "length_ratio": round(ratio, 3),
        "glossary_preservation": round(gloss, 3),
        "tgt_lang_detected": lang or "",
        "confidence": round(conf, 3),
    }
