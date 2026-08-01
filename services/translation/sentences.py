"""Sentence splitting for MT pair construction."""

from __future__ import annotations

import re

SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"'(])")
WS_RE = re.compile(r"\s+")


def split_sentences(text: str, *, min_tokens: int = 6, max_tokens: int = 80) -> list[str]:
    """Split PSA body into sentence-ish units suitable for MT."""
    text = WS_RE.sub(" ", (text or "").strip())
    if not text:
        return []
    parts = SENT_SPLIT_RE.split(text)
    out: list[str] = []
    for part in parts:
        s = part.strip(" \t\n\"'")
        if not s:
            continue
        # Drop pure hashtag / URL lines.
        if s.startswith("#") or s.startswith("http"):
            continue
        n = len(s.split())
        if n < min_tokens:
            continue
        if n > max_tokens:
            # Hard-wrap long sentences on commas/semicolons.
            chunks = re.split(r"(?<=[,;:])\s+", s)
            buf: list[str] = []
            for ch in chunks:
                buf.append(ch)
                joined = " ".join(buf)
                if len(joined.split()) >= min_tokens and (
                    len(joined.split()) >= max_tokens // 2 or ch == chunks[-1]
                ):
                    if min_tokens <= len(joined.split()) <= max_tokens:
                        out.append(joined.strip())
                    buf = []
            if buf:
                joined = " ".join(buf).strip()
                if min_tokens <= len(joined.split()) <= max_tokens:
                    out.append(joined)
            continue
        out.append(s)
    return out
