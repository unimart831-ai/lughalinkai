"""Load and match cultural / institutional glossary terms."""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GLOSSARY = ROOT / "configs" / "glossary.yaml"


@lru_cache(maxsize=4)
def load_glossary(path: str | None = None) -> list[dict[str, Any]]:
    glossary_path = Path(path) if path else DEFAULT_GLOSSARY
    if not glossary_path.exists():
        return []
    data = yaml.safe_load(glossary_path.read_text(encoding="utf-8")) or {}
    return list(data.get("terms") or [])


def _surface_forms(entry: dict[str, Any]) -> list[str]:
    forms = [str(entry.get("term") or "").strip()]
    forms.extend(str(a).strip() for a in (entry.get("aliases") or []) if str(a).strip())
    keep = str(entry.get("keep_form") or "").strip()
    if keep:
        forms.append(keep)
    # Longer forms first so "boda boda" wins over "boda".
    return sorted({f for f in forms if f}, key=len, reverse=True)


def find_glossary_hits(text: str, glossary: list[dict[str, Any]] | None = None) -> list[str]:
    """Return preferred keep_forms found in text (case-insensitive, word-ish match)."""
    if not text:
        return []
    entries = glossary if glossary is not None else load_glossary()
    hits: list[str] = []
    seen: set[str] = set()
    for entry in entries:
        keep = str(entry.get("keep_form") or entry.get("term") or "").strip()
        if not keep or keep.lower() in seen:
            continue
        for form in _surface_forms(entry):
            pattern = rf"(?<![A-Za-z0-9]){re.escape(form)}(?![A-Za-z0-9])"
            if re.search(pattern, text, flags=re.IGNORECASE):
                hits.append(keep)
                seen.add(keep.lower())
                break
    return hits


def apply_glossary_normalization(text: str, glossary: list[dict[str, Any]] | None = None) -> str:
    """Rewrite aliases to keep_form where configured."""
    if not text:
        return ""
    entries = glossary if glossary is not None else load_glossary()
    out = text
    for entry in entries:
        keep = str(entry.get("keep_form") or entry.get("term") or "").strip()
        if not keep:
            continue
        for form in _surface_forms(entry):
            if form == keep:
                continue
            pattern = rf"(?<![A-Za-z0-9]){re.escape(form)}(?![A-Za-z0-9])"
            out = re.sub(pattern, keep, out, flags=re.IGNORECASE)
    return out
