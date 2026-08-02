"""LughaLink PSA translation API (FastAPI).

Loads fine-tuned NLLB checkpoints from Hugging Face Hub (or local paths).

Env:
  LUGHALINK_MODEL_KIK=user/lughalink-nllb-psa-en-kik
  LUGHALINK_MODEL_SW=user/lughalink-nllb-psa-en-sw
  HF_TOKEN=...   # only if repos are private
  LUGHALINK_CORS_ORIGINS=*   # or comma-separated origins

Run locally:
  uvicorn apps.api.main:app --host 0.0.0.0 --port 7860
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.translation.nllb_infer import get_cached_nllb, translate_nllb  # noqa: E402

TargetLang = Literal["kik", "sw"]


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    target: TargetLang
    max_new_tokens: int = Field(default=128, ge=16, le=256)


class TranslateResponse(BaseModel):
    translation: str
    target: TargetLang
    model: str
    source_lang: str = "en"


def _model_id(target: TargetLang) -> str:
    if target == "kik":
        return os.environ.get("LUGHALINK_MODEL_KIK", "").strip()
    return os.environ.get("LUGHALINK_MODEL_SW", "").strip()


def _cors_origins() -> list[str]:
    raw = os.environ.get("LUGHALINK_CORS_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(
    title="LughaLink PSA MT API",
    description="English → Kiswahili / Kikuyu PSA translation (fine-tuned NLLB).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "lughalink-mt-api",
        "docs": "/docs",
        "health": "/health",
        "translate": "POST /translate",
    }


@app.get("/health")
def health():
    kik = _model_id("kik")
    sw = _model_id("sw")
    return {
        "status": "ok" if (kik or sw) else "misconfigured",
        "device_hint": "cuda_if_available",
        "models": {
            "kik": kik or None,
            "sw": sw or None,
        },
        "loaded_cache_size": get_cached_nllb.cache_info().currsize,
    }


@app.post("/translate", response_model=TranslateResponse)
def translate(req: TranslateRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is empty")
    model_id = _model_id(req.target)
    if not model_id:
        env = "LUGHALINK_MODEL_KIK" if req.target == "kik" else "LUGHALINK_MODEL_SW"
        raise HTTPException(status_code=503, detail=f"Set {env} to a Hub repo or local path")
    try:
        tok, model, device = get_cached_nllb(model_id)
        hyp = translate_nllb(
            tok, model, device, text, req.target, max_new_tokens=req.max_new_tokens
        )
    except Exception as exc:  # noqa: BLE001 — surface load/gen errors to client
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return TranslateResponse(translation=hyp, target=req.target, model=model_id)
