"""Extend NLLB-200 with a custom language token (e.g. guz_Latn for Ekegusii).

Stock NLLB has no Ekegusii code. We add guz_Latn and initialize its embedding
from a related Bantu language (default kik_Latn) for zero-shot and few-shot use.
"""

from __future__ import annotations

from typing import Any


GUZ_TOKEN = "guz_Latn"
DEFAULT_INIT_FROM = "kik_Latn"


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

    existing = tokenizer.convert_tokens_to_ids(lang_token)
    unk = getattr(tokenizer, "unk_token_id", None)
    # convert_tokens_to_ids returns unk when missing
    if existing is not None and existing != unk and tokenizer.convert_ids_to_tokens(existing) == lang_token:
        return int(existing)

    special = list(tokenizer.additional_special_tokens or [])
    if lang_token not in special:
        special.append(lang_token)
    tokenizer.add_special_tokens({"additional_special_tokens": special})

    # Some NLLB tokenizers also track lang codes separately
    if hasattr(tokenizer, "add_tokens"):
        # already added via additional_special_tokens; ensure id resolves
        pass

    model.resize_token_embeddings(len(tokenizer))
    new_id = tokenizer.convert_tokens_to_ids(lang_token)
    if new_id is None or new_id == unk:
        raise RuntimeError(f"Failed to register language token {lang_token}")

    init_id = tokenizer.convert_tokens_to_ids(init_from)
    if init_id is None or init_id == unk:
        raise RuntimeError(f"Init token {init_from} not found in NLLB tokenizer")

    with torch.no_grad():
        emb = model.get_input_embeddings()
        emb.weight[new_id] = emb.weight[init_id].clone()
        # Tie / output embeddings if present
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

    from services.translation.nllb_infer import BASE_NLLB_TOKENIZER, _load_tokenizer

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
        # Prefer base tokenizer vocab for init_from if loading a fresh hub model
        if model_id_or_path != BASE_NLLB_TOKENIZER:
            # Ensure init_from exists — if loading already-extended ckpt, skip resize
            tid = tok.convert_tokens_to_ids(extend_lang)
            unk = getattr(tok, "unk_token_id", None)
            if tid is not None and tid != unk and tok.convert_ids_to_tokens(tid) == extend_lang:
                bos_id = int(tid)
            else:
                bos_id = ensure_nllb_lang_token(
                    tok, model, lang_token=extend_lang, init_from=init_from
                )
        else:
            bos_id = ensure_nllb_lang_token(
                tok, model, lang_token=extend_lang, init_from=init_from
            )

    device = "cuda" if use_cuda else "cpu"
    model = model.to(device)
    model.eval()
    return tok, model, device, bos_id
