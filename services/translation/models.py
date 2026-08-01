"""Translation records and enums for Week 2+."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class TranslationMethod(str, Enum):
    HUMAN = "human"
    URL_ALIGNED = "url_aligned"
    NLLB_ZERO_SHOT = "nllb_zero_shot"
    NLLB_FINETUNED = "nllb_finetuned"
    MT5 = "mt5"
    EXTERNAL_OPUS = "external_opus"
    SYNTHETIC_TEMPLATE = "synthetic_template"


class TranslationRecord(BaseModel):
    translation_id: str
    psa_id: str
    domain: str = "Governance"
    source_lang: str
    target_lang: str
    source_text: str
    translated_text: str
    method: TranslationMethod = TranslationMethod.NLLB_ZERO_SHOT
    confidence: Optional[float] = None
    verified: bool = False
    reviewer: Optional[str] = None
    source_url: str = ""
    metadata: dict = Field(default_factory=dict)
