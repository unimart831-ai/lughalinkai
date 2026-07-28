"""NLLB zero-shot seeding helpers (Week 2)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

import yaml

from services.translation.models import TranslationMethod, TranslationRecord

ROOT = Path(__file__).resolve().parents[2]
LANG_CONFIG = ROOT / "configs" / "languages.yaml"


def load_language_config(path: Path = LANG_CONFIG) -> dict:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def nllb_code_for(lang_id: str, cfg: dict | None = None) -> str:
    cfg = cfg or load_language_config()
    for lang in cfg.get("languages", []):
        if lang.get("id") == lang_id:
            return lang["nllb"]
    raise KeyError(f"Unknown language id: {lang_id}")


def build_seed_record(
    *,
    translation_id: str,
    psa_id: str,
    domain: str,
    source_text: str,
    translated_text: str,
    target_lang: str,
    source_url: str = "",
    confidence: float | None = None,
    dry_run: bool = False,
) -> TranslationRecord:
    return TranslationRecord(
        translation_id=translation_id,
        psa_id=psa_id,
        domain=domain,
        source_lang="en",
        target_lang=target_lang,
        source_text=source_text,
        translated_text=translated_text,
        method=TranslationMethod.NLLB_ZERO_SHOT,
        confidence=confidence,
        verified=False,
        source_url=source_url,
        metadata={"dry_run": dry_run},
    )


def records_to_csv_rows(records: Iterable[TranslationRecord]) -> list[dict]:
    rows = []
    for r in records:
        rows.append(
            {
                "pair_id": r.translation_id,
                "psa_id": r.psa_id,
                "Domain": r.domain,
                "source_lang": r.source_lang,
                "target_lang": r.target_lang,
                "source_text": r.source_text,
                "target_text": r.translated_text,
                "method": r.method.value,
                "confidence": "" if r.confidence is None else r.confidence,
                "verified": str(r.verified).lower(),
                "Source": r.source_url,
                "Metadata": json.dumps(r.metadata, ensure_ascii=False),
            }
        )
    return rows
