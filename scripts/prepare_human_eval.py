"""Build a 100+ row human evaluation sheet for later native reviewers.

Prefers real (non-synthetic) PSA sentences when Metadata is available.
Translation columns left blank for humans (or filled from silver if present).

  python scripts/prepare_human_eval.py
  python scripts/prepare_human_eval.py --n 120
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SENTENCES = ROOT / "datasets" / "interim" / "week2_mt_sentences.csv"
READY = ROOT / "datasets" / "processed" / "week2_ready_psas.csv"
SILVER = ROOT / "datasets" / "parallel" / "nllb_psa_silver.csv"
MT_TEST = ROOT / "datasets" / "mt" / "test.csv"
OUT = ROOT / "datasets" / "gold" / "human_eval_100.csv"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare human eval CSV")
    p.add_argument("--n", type=int, default=120)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output", type=Path, default=OUT)
    return p.parse_args()


def synthetic_flag(meta_raw: str) -> bool:
    try:
        meta = json.loads(meta_raw or "{}")
    except json.JSONDecodeError:
        return False
    return bool(meta.get("synthetic"))


def load_ready_flags() -> dict[str, bool]:
    flags = {}
    if not READY.exists():
        return flags
    with READY.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            pid = (row.get("PSA_ID") or "").strip()
            if pid:
                flags[pid] = synthetic_flag(row.get("Metadata") or "")
    return flags


def load_silver_by_psa() -> dict[tuple[str, str], str]:
    """(psa_id, target_lang) -> target_text"""
    out: dict[tuple[str, str], str] = {}
    for path in (SILVER, MT_TEST):
        if not path.exists():
            continue
        with path.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                pid = (row.get("psa_id") or "").strip()
                tgt = (row.get("target_lang") or "").strip()
                text = (row.get("target_text") or "").strip()
                if pid and tgt and text and not text.startswith("[DRY_RUN"):
                    out[(pid, tgt)] = text
    return out


def main() -> None:
    args = parse_args()
    if not SENTENCES.exists():
        raise SystemExit(f"Missing {SENTENCES}")

    flags = load_ready_flags()
    silver = load_silver_by_psa()
    rows = list(csv.DictReader(SENTENCES.open(encoding="utf-8", newline="")))
    # Prefer longer, non-synthetic
    scored = []
    for r in rows:
        text = (r.get("source_text") or "").strip()
        pid = (r.get("psa_id") or "").strip()
        if len(text.split()) < 8 or not pid:
            continue
        is_syn = flags.get(pid, True)  # unknown treated as synthetic for ranking
        scored.append((0 if not is_syn else 1, -len(text.split()), r))

    scored.sort(key=lambda x: (x[0], x[1]))
    # unique by psa_id first, then fill
    picked = []
    seen = set()
    for _, __, r in scored:
        pid = r["psa_id"]
        if pid in seen:
            continue
        seen.add(pid)
        picked.append(r)
        if len(picked) >= args.n:
            break
    if len(picked) < args.n:
        for _, __, r in scored:
            if r in picked:
                continue
            picked.append(r)
            if len(picked) >= args.n:
                break

    random.Random(args.seed).shuffle(picked)
    picked = picked[: args.n]

    out_rows = []
    for i, r in enumerate(picked, 1):
        pid = r["psa_id"]
        src = r["source_text"].strip()
        is_syn = flags.get(pid, "")
        out_rows.append(
            {
                "eval_id": f"heval_{i:04d}",
                "psa_id": pid,
                "Domain": r.get("Domain") or "",
                "source_lang": "en",
                "source_text": src,
                "synthetic_source": str(is_syn).lower() if is_syn != "" else "",
                "target_lang_sw": "sw",
                "mt_suggestion_sw": silver.get((pid, "sw"), ""),
                "target_lang_kik": "kik",
                "mt_suggestion_kik": silver.get((pid, "kik"), ""),
                "fluency_sw": "",
                "adequacy_sw": "",
                "cultural_sw": "",
                "fluency_kik": "",
                "adequacy_kik": "",
                "cultural_kik": "",
                "preferred_sw_edit": "",
                "preferred_kik_edit": "",
                "reviewer_id": "",
                "notes": "",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    real_n = sum(1 for r in out_rows if r["synthetic_source"] == "false")
    print(f"Wrote {len(out_rows)} rows -> {args.output} (real_psa~{real_n})")


if __name__ == "__main__":
    main()
