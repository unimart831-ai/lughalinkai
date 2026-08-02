"""LughaLink PSA translator demo (Streamlit).

Run (after checkpoints exist):
  pip install streamlit
  set LUGHALINK_MODEL_DIR=path/to/artifacts/mt_baseline   # optional
  streamlit run app/streamlit_mt.py
"""

from __future__ import annotations

import csv
import os
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_ROOT = Path(os.environ.get("LUGHALINK_MODEL_DIR", ROOT / "artifacts" / "mt_baseline"))
FEEDBACK = ROOT / "datasets" / "interim" / "demo_feedback.csv"

EXAMPLES = [
    "The public is advised to follow official health guidelines.",
    "IEBC reminds voters to verify their details via the official portal.",
    "Ministry of Health: Avoid unnecessary travel to affected areas.",
    "Farmers are urged to plant drought-resistant crops this season.",
]

NLLB_CODES = {"sw": "swh_Latn", "kik": "kik_Latn"}
LANG_LABELS = {"sw": "Kiswahili", "kik": "Kikuyu"}


@st.cache_resource(show_spinner="Loading translation model…")
def load_checkpoint(path: str):
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSeq2SeqLM.from_pretrained(path)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device)
    return tok, model, device


def resolve_ckpt(model_root: Path, family: str, tgt: str) -> Path:
    pair = f"en-{tgt}"
    if family == "nllb":
        return model_root / pair / "final"
    return model_root / f"{family}-{pair}" / "final"


def translate(tok, model, device, text: str, family: str, tgt: str) -> str:
    if family == "mt5":
        name = LANG_LABELS[tgt]
        prompt = f"translate English to {name}: {text}"
        inputs = tok(prompt, return_tensors="pt", truncation=True, max_length=256)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        out = model.generate(**inputs, max_new_tokens=128)
    else:
        tok.src_lang = "eng_Latn"
        inputs = tok(text, return_tensors="pt", truncation=True, max_length=256)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        bos = tok.convert_tokens_to_ids(NLLB_CODES[tgt])
        out = model.generate(**inputs, forced_bos_token_id=bos, max_new_tokens=128)
    return tok.batch_decode(out, skip_special_tokens=True)[0]


def save_feedback(row: dict) -> None:
    FEEDBACK.parent.mkdir(parents=True, exist_ok=True)
    fields = list(row.keys())
    write_header = not FEEDBACK.exists()
    with FEEDBACK.open("a", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        if write_header:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    st.set_page_config(page_title="LughaLink PSA Translator", layout="centered")
    st.title("LughaLink AI")
    st.subheader("Public Service Announcement translator")
    st.caption(
        "English → Kiswahili / Kikuyu. Fine-tuned on PSA silver data — not human gold."
    )

    model_root = Path(
        st.sidebar.text_input("Model root", str(DEFAULT_MODEL_ROOT))
    )
    family = st.sidebar.selectbox("Model family", ["nllb", "mt5"], index=0)
    tgt = st.sidebar.selectbox(
        "Target language",
        options=list(LANG_LABELS.keys()),
        format_func=lambda x: LANG_LABELS[x],
    )

    ckpt = resolve_ckpt(model_root, family, tgt)
    st.sidebar.write(f"Checkpoint: `{ckpt}`")
    if not ckpt.exists():
        st.error(
            f"Checkpoint not found at `{ckpt}`.\n\n"
            "Train on Navon or point Model root at your extracted backup "
            "(e.g. `lugha_ckpt` folder)."
        )
        st.stop()

    example = st.selectbox("Example PSA", ["(type your own)"] + EXAMPLES)
    text = st.text_area(
        "English PSA",
        value="" if example == "(type your own)" else example,
        height=140,
    )

    if st.button("Translate", type="primary") and text.strip():
        tok, model, device = load_checkpoint(str(ckpt))
        hyp = translate(tok, model, device, text.strip(), family, tgt)
        st.session_state["last_hyp"] = hyp
        st.session_state["last_src"] = text.strip()
        st.session_state["last_tgt"] = tgt
        st.session_state["last_family"] = family

    if "last_hyp" in st.session_state:
        st.markdown("### Translation")
        st.success(st.session_state["last_hyp"])
        st.caption(
            f"{LANG_LABELS[st.session_state['last_tgt']]} · "
            f"{st.session_state['last_family']} · silver-domain model"
        )

    st.markdown("---")
    st.markdown("### Feedback")
    score = st.slider("Quality (1=poor, 5=excellent)", 1, 5, 3)
    comment = st.text_input("Optional comment")
    if st.button("Submit feedback") and "last_hyp" in st.session_state:
        save_feedback(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source_text": st.session_state.get("last_src", ""),
                "target_lang": st.session_state.get("last_tgt", ""),
                "hypothesis": st.session_state.get("last_hyp", ""),
                "model_family": st.session_state.get("last_family", ""),
                "score": score,
                "comment": comment,
            }
        )
        st.info(f"Saved to {FEEDBACK}")


if __name__ == "__main__":
    main()
