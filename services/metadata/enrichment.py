from pathlib import Path
from typing import Dict, Optional, Tuple

import yaml

from services.models import Urgency

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOMAINS_PATH = PROJECT_ROOT / "configs" / "domains.yaml"


def _load_config() -> dict:
    if not DOMAINS_PATH.exists():
        return {}
    return yaml.safe_load(DOMAINS_PATH.read_text(encoding="utf-8")) or {}


def infer_domain(text: str, default: str = "governance") -> Tuple[str, Optional[str]]:
    cfg = _load_config()
    lowered = text.lower()
    best_domain = default
    best_sub = None
    best_hits = 0
    default_hits = 0
    default_sub = None

    for domain_key, domain_data in cfg.get("domains", {}).items():
        for sub_key, sub_data in domain_data.get("sub_categories", {}).items():
            hits = sum(1 for kw in sub_data.get("keywords", []) if kw in lowered)
            if domain_key == default and hits > default_hits:
                default_hits = hits
                default_sub = sub_key
            if hits > best_hits:
                best_hits = hits
                best_domain = domain_key
                best_sub = sub_key

    # Keep source-declared domain unless another domain clearly wins.
    if best_domain != default and best_hits < max(2, default_hits + 1):
        return default, default_sub
    return best_domain, best_sub


def infer_urgency(text: str) -> Urgency:
    cfg = _load_config()
    lowered = text.lower()
    for level in ("emergency", "high", "medium", "low"):
        keywords = cfg.get("urgency_rules", {}).get(level, {}).get("keywords", [])
        if any(kw in lowered for kw in keywords):
            return Urgency(level)
    return Urgency.MEDIUM


def infer_audience(text: str) -> list[str]:
    cfg = _load_config()
    lowered = text.lower()
    audiences = []
    for audience, keywords in cfg.get("audience_keywords", {}).items():
        if any(kw in lowered for kw in keywords):
            audiences.append(audience)
    return audiences or ["everyone"]


def extract_keywords(text: str, limit: int = 5) -> list[str]:
    cfg = _load_config()
    lowered = text.lower()
    found: list[str] = []
    for domain_data in cfg.get("domains", {}).values():
        for sub_data in domain_data.get("sub_categories", {}).values():
            for kw in sub_data.get("keywords", []):
                if kw in lowered and kw not in found:
                    found.append(kw)
                if len(found) >= limit:
                    return found
    return found
