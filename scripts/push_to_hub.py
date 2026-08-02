"""Upload fine-tuned NLLB checkpoints to Hugging Face Hub.

Prereqs:
  pip install huggingface_hub
  huggingface-cli login   # or HF_TOKEN env

Examples (on Navon after training):
  python scripts/push_to_hub.py --hf-user YOUR_USER --pair en-kik
  python scripts/push_to_hub.py --hf-user YOUR_USER --pair en-sw
  python scripts/push_to_hub.py --hf-user YOUR_USER --all --private
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CARD_TEMPLATE = ROOT / "DOCS" / "model_cards" / "MODEL_CARD_TEMPLATE.md"
DEFAULT_LOCAL = {
    "en-kik": ROOT / "artifacts" / "mt_baseline" / "en-kik" / "final",
    "en-sw": ROOT / "artifacts" / "mt_baseline" / "en-sw" / "final",
}
PAIR_META = {
    "en-kik": {
        "target_name": "Kikuyu",
        "target_nllb": "kik_Latn",
        "repo_suffix": "lughalink-nllb-psa-en-kik",
    },
    "en-sw": {
        "target_name": "Kiswahili",
        "target_nllb": "swh_Latn",
        "repo_suffix": "lughalink-nllb-psa-en-sw",
    },
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Push LughaLink NLLB checkpoints to HF Hub")
    p.add_argument("--hf-user", type=str, required=True, help="HF username or org")
    p.add_argument("--pair", type=str, choices=sorted(PAIR_META), default=None)
    p.add_argument("--all", action="store_true", help="Upload both en-kik and en-sw")
    p.add_argument("--local-dir", type=Path, default=None, help="Override local checkpoint dir")
    p.add_argument("--repo-id", type=str, default=None, help="Override full repo id")
    p.add_argument("--private", action="store_true", help="Create private model repo")
    p.add_argument("--dry-run", action="store_true", help="Print actions only")
    return p.parse_args()


def render_card(pair: str, repo_id: str) -> str:
    meta = PAIR_META[pair]
    text = CARD_TEMPLATE.read_text(encoding="utf-8")
    return (
        text.replace("{{PAIR}}", pair)
        .replace("{{TARGET_NAME}}", meta["target_name"])
        .replace("{{TARGET_NLLB}}", meta["target_nllb"])
        .replace("{{REPO_ID}}", repo_id)
    )


def push_one(pair: str, hf_user: str, local_dir: Path, repo_id: str | None, private: bool, dry: bool) -> str:
    meta = PAIR_META[pair]
    rid = repo_id or f"{hf_user}/{meta['repo_suffix']}"
    readme = render_card(pair, rid)
    readme_path = local_dir / "README.md"
    if dry:
        print(f"[dry-run] would upload {local_dir} -> {rid} (private={private})")
        print(f"[dry-run] model card preview chars={len(readme)}")
        return rid

    if not local_dir.exists():
        raise SystemExit(f"Missing checkpoint: {local_dir}")
    weights = local_dir / "model.safetensors"
    if not weights.exists():
        raise SystemExit(f"Missing weights file: {weights}")

    readme_path.write_text(readme, encoding="utf-8")

    try:
        from huggingface_hub import HfApi, create_repo
    except ImportError as exc:
        raise SystemExit(
            "Install: pip install huggingface_hub\n"
            "Then: huggingface-cli login\n"
            f"Original: {exc}"
        ) from exc

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    api = HfApi(token=token)
    create_repo(rid, repo_type="model", private=private, exist_ok=True, token=token)
    api.upload_folder(
        folder_path=str(local_dir),
        repo_id=rid,
        repo_type="model",
        commit_message=f"Upload LughaLink PSA NLLB fine-tune ({pair})",
    )
    print(f"Uploaded {local_dir} -> https://huggingface.co/{rid}")
    return rid


def main() -> None:
    args = parse_args()
    pairs = list(PAIR_META) if args.all else ([args.pair] if args.pair else [])
    if not pairs:
        raise SystemExit("Pass --pair en-kik|en-sw or --all")

    uploaded = []
    for pair in pairs:
        local = args.local_dir or DEFAULT_LOCAL[pair]
        if args.local_dir and args.all:
            raise SystemExit("--local-dir cannot be combined with --all")
        uploaded.append(
            push_one(pair, args.hf_user, local, args.repo_id if not args.all else None, args.private, args.dry_run)
        )
    print("Done:", ", ".join(uploaded))


if __name__ == "__main__":
    main()
