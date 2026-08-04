"""Shared NLLB load + translate helpers for CLI and API."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

NLLB_CODES = {"sw": "swh_Latn", "kik": "kik_Latn"}
SRC_CODE = "eng_Latn"
# Fine-tunes keep the base NLLB vocabulary; load tokenizer from here when Hub
# tokenizer_config is incompatible with the installed transformers version.
BASE_NLLB_TOKENIZER = "facebook/nllb-200-distilled-600M"


def _load_tokenizer(model_id_or_path: str) -> Any:
    from transformers import AutoTokenizer

    try:
        return AutoTokenizer.from_pretrained(model_id_or_path)
    except (AttributeError, TypeError, ValueError, OSError):
        # Hub cards saved under newer transformers may store extra_special_tokens
        # as a list; some clients then fail with "'list' object has no attribute 'keys'".
        return AutoTokenizer.from_pretrained(BASE_NLLB_TOKENIZER)


def load_nllb(model_id_or_path: str) -> tuple[Any, Any, str]:
    import torch
    from transformers import AutoModelForSeq2SeqLM

    tok = _load_tokenizer(model_id_or_path)
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_id_or_path,
        low_cpu_mem_usage=True,
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    model.eval()
    return tok, model, device


def translate_nllb(
    tok: Any,
    model: Any,
    device: str,
    text: str,
    target: str,
    *,
    max_new_tokens: int = 128,
) -> str:
    if target not in NLLB_CODES:
        raise ValueError(f"Unsupported target '{target}'. Use one of: {sorted(NLLB_CODES)}")
    tok.src_lang = SRC_CODE
    inputs = tok(text, return_tensors="pt", truncation=True, max_length=256)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    bos = tok.convert_tokens_to_ids(NLLB_CODES[target])
    out = model.generate(**inputs, forced_bos_token_id=bos, max_new_tokens=max_new_tokens)
    return tok.batch_decode(out, skip_special_tokens=True)[0]


@lru_cache(maxsize=4)
def get_cached_nllb(model_id_or_path: str) -> tuple[Any, Any, str]:
    return load_nllb(model_id_or_path)
