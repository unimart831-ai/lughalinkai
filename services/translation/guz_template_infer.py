"""Ekegusii PSA template translation (pre-few-shot demo path).

Used when NLLB zero-shot collapses to Kikuyu/Swahili because guz_Latn
is vocab-extended from a related language. Honest: template silver, not gold.
"""

from __future__ import annotations

import random
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LEXICON = ROOT / "configs" / "ekegusii_psa_lexicon.yaml"

ORG_RE = re.compile(
    r"\b("
    r"IEBC|EACC|Huduma Kenya|Kenya Revenue Authority|Public Service Commission|"
    r"Ministry of Health|Social Health Authority|County Department of Health|"
    r"Kenya Red Cross|WHO Kenya|National Police Service|NDMA|"
    r"Kenya Meteorological Department|NTSA|Ministry of Interior|"
    r"Kenya Wildlife Service|Ministry of Education|KNEC|HELB|KUCCPS|TSC|"
    r"Ministry of Agriculture|KEPHIS|KALRO|County Department of Agriculture|"
    r"Communications Authority of Kenya|The National Treasury"
    r")\b",
    re.I,
)

DOMAIN_CUES = {
    "Health": ("health", "wash", "hospital", "vaccin", "soap", "water", "sha", "immun"),
    "Governance": ("iebc", "voter", "election", "licence", "tax", "huduma", "portal", "register"),
    "Agriculture": ("farm", "crop", "livestock", "drought", "kephis", "plant"),
    "Education": ("school", "student", "helb", "exam", "knec", "learner"),
    "Security": ("police", "road", "flood", "evacuate", "ntsa", "weather"),
}


@lru_cache(maxsize=1)
def load_lexicon(path: str | None = None) -> dict[str, Any]:
    p = Path(path) if path else DEFAULT_LEXICON
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def guess_domain(english: str) -> str:
    low = (english or "").lower()
    for domain, cues in DOMAIN_CUES.items():
        if any(c in low for c in cues):
            return domain
    return "Governance"


def match_verb(english: str, verb_map: dict[str, str]) -> str | None:
    low = english.lower()
    for en, guz in sorted(verb_map.items(), key=lambda kv: -len(kv[0])):
        if en.lower() in low:
            return guz
    return None


def translate_guz_template(
    english: str,
    *,
    domain: str | None = None,
    seed: int | None = None,
    lexicon_path: str | None = None,
) -> tuple[str, str]:
    """Return (ekegusii_text, match_mode)."""
    lex = load_lexicon(lexicon_path)
    rng = random.Random(seed if seed is not None else (hash(english) & 0xFFFFFFFF))
    domain = domain or guess_domain(english)
    if domain not in (lex.get("orgs") or {}):
        domain = "Governance"

    verb = match_verb(english, lex.get("verb_map") or {})
    mode = "verb_map" if verb else "domain_fallback"
    if not verb:
        verb = (lex.get("domain_fallback_verbs") or {}).get(domain) or (
            "gokora amachiko a goseka"
        )

    m = ORG_RE.search(english or "")
    if m:
        org = m.group(1)
    else:
        org = rng.choice((lex.get("orgs") or {}).get(domain) or ["IEBC"])

    audience = rng.choice((lex.get("audiences") or {}).get(domain) or ["abanto bonsi"])
    stem = rng.choice(lex.get("action_stems") or ["{org} nigo ekoransia {audience} go {verb}."])
    location = rng.choice(lex.get("locations") or ["Kisii County"])
    deadline = rng.choice(lex.get("deadlines") or ["Ororagererio rwa rero rwatangire buna."])
    closer = rng.choice(lex.get("closers") or [""])
    month = rng.choice(lex.get("months") or ["August"])
    day = rng.randint(1, 28)

    body = stem.format(org=org, audience=audience, verb=verb, location=location)
    deadline = deadline.format(day=day, month=month)
    parts = [body.strip(), deadline.strip(), closer.strip()]
    guz = re.sub(r"\s+", " ", " ".join(p for p in parts if p)).strip()
    return guz, mode
