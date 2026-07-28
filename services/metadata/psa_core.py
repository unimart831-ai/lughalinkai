"""Extract a short PSA core from a long article/notice body."""

from __future__ import annotations

import re

from services.metadata.psa_gate import MAX_TOKENS, PSA_FORCE, strict_psa_rejection_reason

STOP_MARKERS = re.compile(
    r"\n\s*(related (articles|posts|news)|share this|leave a (reply|comment)|"
    r"tags?:|categories?:|copyright|all rights reserved|subscribe|"
    r"about the author|also read|you may also like)\b",
    re.I,
)


def extract_psa_core(title: str, text: str, max_tokens: int = MAX_TOKENS) -> str:
    """Keep title + leading advisory paragraphs up to max_tokens."""
    title = re.sub(r"\s+", " ", (title or "").strip())
    body = (text or "").replace("\r", "\n")
    body = STOP_MARKERS.split(body, maxsplit=1)[0]
    body = re.sub(r"\n{3,}", "\n\n", body).strip()

    # Prefer paragraphs that look instructional / notice-like
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
    if not paras:
        paras = [re.sub(r"\s+", " ", body).strip()] if body else []

    chosen: list[str] = []
    if title and not (paras and paras[0].lower().startswith(title.lower()[:40].lower())):
        chosen.append(title.rstrip(".") + ".")

    for p in paras:
        if len(p.split()) < 5:
            continue
        # Skip pure nav crumbs
        if p.count("Home") >= 2 and "About" in p:
            continue
        provisional = " ".join(chosen + [p]).strip()
        if len(provisional.split()) > max_tokens:
            # take partial paragraph if we still have room
            room = max_tokens - len(" ".join(chosen).split())
            if room >= 20:
                words = p.split()[:room]
                chosen.append(" ".join(words))
            break
        chosen.append(p)
        # Early stop once we have a solid advisory block
        joined = " ".join(chosen)
        if len(joined.split()) >= 80 and PSA_FORCE.search(joined):
            break
        if len(joined.split()) >= 160:
            break

    core = " ".join(chosen).strip()
    if not core and body:
        core = " ".join(body.split()[:max_tokens])
    return core


def core_passes_gate(core: str, source: str = "", lang: str = "en") -> bool:
    return strict_psa_rejection_reason(core, source=source, lang=lang) is None
