"""Smoke tests for MT helpers that do not need GPU weights."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str, rel: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / rel)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_mt5_prefix():
    tb = _load("train_baseline", "scripts/train_baseline.py")
    assert tb.mt5_prefix("Hello", "kik").startswith("translate English to Kikuyu:")
    assert tb.mt5_prefix("Hello", "sw").startswith("translate English to Swahili:")


def test_resolve_model_name():
    tb = _load("train_baseline", "scripts/train_baseline.py")
    cfg = {
        "model": {
            "name": "facebook/nllb-200-distilled-600M",
            "alt_models": ["google/mt5-small"],
        }
    }
    assert "nllb" in tb.resolve_model_name(cfg, "nllb")
    assert "mt5" in tb.resolve_model_name(cfg, "mt5")


def test_human_eval_sheet_exists():
    sheet = ROOT / "datasets" / "gold" / "human_eval_100.csv"
    assert sheet.exists(), "Run: python scripts/prepare_human_eval.py"
    text = sheet.read_text(encoding="utf-8")
    assert "fluency_kik" in text
    assert "adequacy_sw" in text
