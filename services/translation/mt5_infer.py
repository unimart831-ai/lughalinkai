"""Shared mT5 load + translate helpers for API and CLI."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

TARGET_NAMES = {
    "sw": "Swahili",
    "kik": "Kikuyu",
    "guz": "Ekegusii",
}


def mt5_prefix(text: str, target: str) -> str:
    name = TARGET_NAMES.get(target, target)
    return f"translate English to {name}: {text}"


def load_mt5(model_id_or_path: str) -> tuple[Any, Any, str]:
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id_or_path)
    use_cuda = torch.cuda.is_available()
    dtype = torch.float16 if use_cuda else torch.float32
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_id_or_path,
        low_cpu_mem_usage=True,
        torch_dtype=dtype,
    )
    device = "cuda" if use_cuda else "cpu"
    model = model.to(device)
    model.eval()
    return tok, model, device


def translate_mt5(
    tok: Any,
    model: Any,
    device: str,
    text: str,
    target: str,
    *,
    max_new_tokens: int = 64,
) -> str:
    import torch

    prompt = mt5_prefix(text, target)
    inputs = tok(prompt, return_tensors="pt", truncation=True, max_length=192)
    inputs = {k: v.to(device) for k, v in inputs.items()}
    with torch.inference_mode():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            num_beams=1,
            do_sample=False,
            use_cache=True,
        )
    return tok.batch_decode(out, skip_special_tokens=True)[0]


@lru_cache(maxsize=4)
def get_cached_mt5(model_id_or_path: str) -> tuple[Any, Any, str]:
    return load_mt5(model_id_or_path)
