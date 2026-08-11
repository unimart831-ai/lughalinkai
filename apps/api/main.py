"""LughaLink PSA translation API + web UI (FastAPI).

Loads fine-tuned NLLB / mT5 checkpoints from Hugging Face Hub (or local paths).
The browser only calls /translate — weights stay on the server.

Env:
  LUGHALINK_MODEL_KIK=iranzi/lughalink-nllb-psa-en-kik
  LUGHALINK_MODEL_SW=iranzi/lughalink-nllb-psa-en-sw
  LUGHALINK_MODEL_GUZ=facebook/nllb-200-distilled-600M
  LUGHALINK_MODEL_GUZ_MT5=iranzi/lughalink-mt5-psa-en-guz
  LUGHALINK_GUZ_BACKEND=nllb|mt5|template   # default: nllb (zero-shot / few-shot neural)
  HF_TOKEN=...   # only if repos are private
  LUGHALINK_CORS_ORIGINS=*

Run:
  uvicorn apps.api.main:app --host 0.0.0.0 --port 7860
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.translation.guz_template_infer import translate_guz_template  # noqa: E402
from services.translation.mt5_infer import get_cached_mt5, translate_mt5  # noqa: E402
from services.translation.nllb_infer import get_cached_nllb, translate_nllb  # noqa: E402

STATIC_DIR = Path(__file__).resolve().parent / "static"

DEFAULT_KIK = "iranzi/lughalink-nllb-psa-en-kik"
DEFAULT_SW = "iranzi/lughalink-nllb-psa-en-sw"
DEFAULT_GUZ_NLLB = "iranzi/lughalink-nllb-psa-en-guz"
DEFAULT_GUZ_MT5 = "iranzi/lughalink-mt5-psa-en-guz"

TargetLang = Literal["kik", "sw", "guz"]


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=2000)
    target: TargetLang
    max_new_tokens: int = Field(default=64, ge=16, le=256)


class TranslateResponse(BaseModel):
    translation: str
    target: TargetLang
    model: str
    source_lang: str = "en"
    backend: str = "nllb"


def _model_id(target: TargetLang) -> str:
    if target == "kik":
        return os.environ.get("LUGHALINK_MODEL_KIK", DEFAULT_KIK).strip()
    if target == "guz":
        backend = _guz_backend()
        if backend == "template":
            return "guz_psa_template"
        if backend == "mt5":
            return os.environ.get("LUGHALINK_MODEL_GUZ_MT5", DEFAULT_GUZ_MT5).strip()
        return os.environ.get("LUGHALINK_MODEL_GUZ", DEFAULT_GUZ_NLLB).strip()
    return os.environ.get("LUGHALINK_MODEL_SW", DEFAULT_SW).strip()


def _guz_backend() -> str:
    raw = os.environ.get("LUGHALINK_GUZ_BACKEND", "nllb").strip().lower()
    if raw in ("template", "nllb", "mt5"):
        return raw
    return "nllb"


def _cors_origins() -> list[str]:
    raw = os.environ.get("LUGHALINK_CORS_ORIGINS", "*").strip()
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(
    title="LughaLink PSA MT API",
    description="English → Kiswahili / Kikuyu / Ekegusii PSA translation.",
    version="0.3.0",
)

_origins = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.on_event("startup")
def _warmup_models() -> None:
    """Load configured Hub checkpoints once so the first UI request is not cold."""
    for target in ("sw", "kik"):
        mid = _model_id(target)  # type: ignore[arg-type]
        if not mid:
            continue
        try:
            get_cached_nllb(mid)
        except Exception:  # noqa: BLE001
            pass
    # Guz neural warmup optional; template backend needs no weights
    if _guz_backend() in ("nllb", "mt5"):
        try:
            mid = _model_id("guz")
            if mid and mid != "guz_psa_template":
                if _guz_backend() == "mt5":
                    get_cached_mt5(mid)
                else:
                    get_cached_nllb(mid)
        except Exception:  # noqa: BLE001
            pass


def _render_ui() -> str:
    """Inline CSS/JS so the Unimart-style layout always loads (even if /static 404s)."""
    index = STATIC_DIR / "index.html"
    css = (STATIC_DIR / "styles.css").read_text(encoding="utf-8") if (STATIC_DIR / "styles.css").exists() else ""
    js = (STATIC_DIR / "app.js").read_text(encoding="utf-8") if (STATIC_DIR / "app.js").exists() else ""
    html = index.read_text(encoding="utf-8")
    html = html.replace("<!--INJECT_CSS-->", f"<style>\n{css}\n</style>")
    html = html.replace(
        '<link rel="stylesheet" href="/static/styles.css" />',
        "<!-- styles inlined -->",
    )
    html = html.replace("<!--INJECT_JS-->", f"<script>\n{js}\n</script>")
    html = html.replace('<script src="/static/app.js"></script>', "<!-- script inlined -->")
    return html


@app.get("/", response_class=HTMLResponse)
def ui():
    index = STATIC_DIR / "index.html"
    if index.exists():
        return HTMLResponse(_render_ui())
    return HTMLResponse("<h1>LughaLink API</h1><p>UI assets missing. See /docs</p>")


@app.get("/api")
def api_info():
    return {
        "service": "lughalink-mt-api",
        "ui": "/",
        "docs": "/docs",
        "health": "/health",
        "translate": "POST /translate",
        "models": {
            "kik": _model_id("kik"),
            "sw": _model_id("sw"),
            "guz": _model_id("guz"),
            "guz_backend": _guz_backend(),
        },
    }


@app.get("/health")
def health():
    kik = _model_id("kik")
    sw = _model_id("sw")
    guz = _model_id("guz")
    return {
        "status": "ok" if (kik or sw or guz) else "misconfigured",
        "device_hint": "cuda_if_available",
        "models": {
            "kik": kik or None,
            "sw": sw or None,
            "guz": guz or None,
            "guz_backend": _guz_backend(),
        },
        "loaded_cache_size": get_cached_nllb.cache_info().currsize
        + get_cached_mt5.cache_info().currsize,
    }


@app.post("/translate", response_model=TranslateResponse)
def translate(req: TranslateRequest):
    text = req.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is empty")

    if req.target == "guz" and _guz_backend() == "template":
        try:
            hyp, mode = translate_guz_template(text)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return TranslateResponse(
            translation=hyp,
            target="guz",
            model=f"guz_psa_template:{mode}",
            backend="template",
        )

    model_id = _model_id(req.target)
    if not model_id:
        env = {
            "kik": "LUGHALINK_MODEL_KIK",
            "sw": "LUGHALINK_MODEL_SW",
            "guz": "LUGHALINK_MODEL_GUZ or LUGHALINK_MODEL_GUZ_MT5",
        }[req.target]
        raise HTTPException(status_code=503, detail=f"Set {env} to a Hub repo or local path")
    backend = "nllb"
    try:
        if req.target == "guz" and _guz_backend() == "mt5":
            backend = "mt5"
            tok, model, device = get_cached_mt5(model_id)
            hyp = translate_mt5(
                tok, model, device, text, "guz", max_new_tokens=req.max_new_tokens
            )
        else:
            tok, model, device = get_cached_nllb(model_id)
            hyp = translate_nllb(
                tok, model, device, text, req.target, max_new_tokens=req.max_new_tokens
            )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return TranslateResponse(
        translation=hyp, target=req.target, model=model_id, backend=backend
    )
