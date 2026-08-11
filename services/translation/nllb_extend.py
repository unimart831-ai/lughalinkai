"""Extend NLLB-200 with a custom language token (e.g. guz_Latn for Ekegusii).

Stock NLLB has no Ekegusii code. We add guz_Latn and initialize its embedding
from a related Bantu language (default kik_Latn) for zero-shot and few-shot use.
"""

from __future__ import annotations

from typing import Any


GUZ_TOKEN = "guz_Latn"
DEFAULT_INIT_FROM = "swh_Latn"


def _token_id(tokenizer: Any, token: str) -> int | None:
    unk = getattr(tokenizer, "unk_token_id", None)
    tid = tokenizer.convert_tokens_to_ids(token)
    if tid is None or tid == unk:
        return None
    # Some tokenizers map unknown strings to unk without raising
    try:
        if tokenizer.convert_ids_to_tokens(tid) != token:
            return None
    except Exception:  # noqa: BLE001
        return None
    return int(tid)


def ensure_nllb_lang_token(
    tokenizer: Any,
    model: Any,
    *,
    lang_token: str = GUZ_TOKEN,
    init_from: str = DEFAULT_INIT_FROM,
) -> int:
    """Add lang_token if missing; resize embeddings; copy weights from init_from.

    Returns the token id for lang_token.
    """
    import torch

    existing = _token_id(tokenizer, lang_token)
    if existing is not None:
        return existing

    # NllbTokenizer may not expose .additional_special_tokens as an attribute;
    # add_special_tokens / add_tokens are the supported APIs.
    added = 0
    try:
        added = int(tokenizer.add_special_tokens({"additional_special_tokens": [lang_token]}))
    except Exception:  # noqa: BLE001
        added = 0
    if added == 0 and _token_id(tokenizer, lang_token) is None:
        added = int(tokenizer.add_tokens([lang_token], special_tokens=True))

    model.resize_token_embeddings(len(tokenizer))
    new_id = _token_id(tokenizer, lang_token)
    if new_id is None:
        raise RuntimeError(f"Failed to register language token {lang_token}")

    init_id = _token_id(tokenizer, init_from)
    if init_id is None:
        raise RuntimeError(f"Init token {init_from} not found in NLLB tokenizer")

    with torch.no_grad():
        emb = model.get_input_embeddings()
        emb.weight[new_id] = emb.weight[init_id].clone()
        out_emb = model.get_output_embeddings()
        if out_emb is not None and out_emb.weight.shape[0] > new_id:
            out_emb.weight[new_id] = out_emb.weight[init_id].clone()

    return int(new_id)


def load_nllb_maybe_extended(
    model_id_or_path: str,
    *,
    extend_lang: str | None = None,
    init_from: str = DEFAULT_INIT_FROM,
) -> tuple[Any, Any, str, int | None]:
    """Load NLLB; optionally extend with a custom language token.

    Returns tokenizer, model, device, bos_token_id_for_extend (or None).
    """
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    from services.translation.nllb_infer import _load_tokenizer

    try:
        tok = AutoTokenizer.from_pretrained(model_id_or_path)
    except (AttributeError, TypeError, ValueError, OSError):
        tok = _load_tokenizer(model_id_or_path)

    use_cuda = torch.cuda.is_available()
    dtype = torch.float16 if use_cuda else torch.float32
    model = AutoModelForSeq2SeqLM.from_pretrained(
        model_id_or_path,
        low_cpu_mem_usage=True,
        torch_dtype=dtype,
    )
    bos_id = None
    if extend_lang:
        existing = _token_id(tok, extend_lang)
        if existing is not None:
            bos_id = existing
        else:
            bos_id = ensure_nllb_lang_token(
                tok, model, lang_token=extend_lang, init_from=init_from
            )

    device = "cuda" if use_cuda else "cpu"
    model = model.to(device)
    model.eval()
    return tok, model, device, bos_id
