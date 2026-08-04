#!/usr/bin/env python3
"""Create / update the LughaLink FastAPI Docker Space on Hugging Face.

Requires: hf auth login (write token for user iranzi).

Usage:
  python scripts/create_hf_space.py
  python scripts/create_hf_space.py --space-id iranzi/lughalink-mt-api
"""

from __future__ import annotations

import argparse
import sys

from huggingface_hub import HfApi, whoami


DEFAULT_SPACE = "iranzi/lughalink-mt-api"
GITHUB_REPO = "https://github.com/unimart831-ai/lughalinkai"
VARS = {
    "LUGHALINK_MODEL_KIK": "iranzi/lughalink-nllb-psa-en-kik",
    "LUGHALINK_MODEL_SW": "iranzi/lughalink-nllb-psa-en-sw",
    "LUGHALINK_CORS_ORIGINS": "*",
}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--space-id", default=DEFAULT_SPACE)
    p.add_argument("--private", action="store_true")
    args = p.parse_args()

    try:
        me = whoami()
    except Exception as exc:  # noqa: BLE001
        print("Not logged in. Run: hf auth login", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1

    print(f"Logged in as: {me.get('name') or me}")
    api = HfApi()
    space_id = args.space_id

    try:
        api.repo_info(repo_id=space_id, repo_type="space")
        print(f"Space already exists: https://huggingface.co/spaces/{space_id}")
    except Exception:
        print(f"Creating Docker Space {space_id} ...")
        api.create_repo(
            repo_id=space_id,
            repo_type="space",
            space_sdk="docker",
            private=args.private,
            exist_ok=True,
        )
        print(f"Created: https://huggingface.co/spaces/{space_id}")

    print("Setting Space variables ...")
    for key, value in VARS.items():
        api.add_space_variable(space_id, key, value)
        print(f"  {key}={value}")

    print(
        "\nNext (one-time in the Space UI if not already linked):\n"
        f"  1. Open https://huggingface.co/spaces/{space_id}/settings\n"
        f"  2. Connect GitHub repo {GITHUB_REPO} (root Dockerfile)\n"
        "  3. Prefer GPU hardware for demos (CPU is slow for 600M)\n"
        "  4. Wait for build → open the Space URL and translate a PSA\n"
    )
    slug = space_id.replace("/", "-").lower()
    print(f"Expected UI: https://{slug}.hf.space/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
