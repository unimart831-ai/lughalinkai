"""Build MT-ready silver parallel corpus + train/dev/test (no human review).

Steps:
1. Sentence-split PSA seed candidates → interim sentence sheet
2. Merge existing parallel CSVs (OPUS EN-SW, NLLB silver, …)
3. Auto-QC filter (rejects dry-run / near-copy / bad ratios)
4. Stratified-ish split → datasets/mt/{train,dev,test}.csv
5. Write readiness stats JSON

Does NOT claim human gold. All rows verified=false unless already true.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.translation.sentences import split_sentences
from services.translation.silver_qc import auto_qc_pair

CANDIDATES = ROOT / "datasets" / "interim" / "week2_seed_candidates.csv"
SENT_OUT = ROOT / "datasets" / "interim" / "week2_mt_sentences.csv"
PARALLEL_DIR = ROOT / "datasets" / "parallel"
MT_DIR = ROOT / "datasets" / "mt"
STATS = ROOT / "datasets" / "interim" / "mt_training_ready_stats.json"

PAIR_FIELDS = [
    "pair_id",
    "psa_id",
    "Domain",
    "source_lang",
    "target_lang",
    "source_text",
    "target_text",
    "method",
    "confidence",
    "verified",
    "auto_qc_pass",
    "Source",
    "Metadata",
    "split",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Prepare silver MT training data")
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--ratios", type=str, default="0.8,0.1,0.1")
    p.add_argument(
        "--parallel-glob",
        type=str,
        default="*.csv",
        help="Glob under datasets/parallel to merge",
    )
    return p.parse_args()


def write_sentence_sheet(path: Path) -> int:
    if not CANDIDATES.exists():
        print(f"WARN: missing {CANDIDATES}; run prepare_week2_baseline.py")
        return 0
    rows = list(csv.DictReader(CANDIDATES.open(encoding="utf-8", newline="")))
    out = []
    for row in rows:
        sents = split_sentences(row.get("seed_text") or "")
        for i, sent in enumerate(sents, start=1):
            out.append(
                {
                    "sentence_id": f"{row.get('psa_id')}_s{i:02d}",
                    "psa_id": row.get("psa_id") or "",
                    "Domain": row.get("Domain") or "",
                    "source_text": sent,
                    "token_count": len(sent.split()),
                    "Source": row.get("Source") or "",
                    "status": "awaiting_nllb_seed",
                }
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(
            fh,
            fieldnames=[
                "sentence_id",
                "psa_id",
                "Domain",
                "source_text",
                "token_count",
                "Source",
                "status",
            ],
        )
        w.writeheader()
        w.writerows(out)
    print(f"Sentence candidates -> {path} ({len(out)})")
    return len(out)


def load_parallel_files(pattern: str) -> list[dict]:
    files = sorted(PARALLEL_DIR.glob(pattern))
    merged: list[dict] = []
    for fp in files:
        if fp.name == ".gitkeep":
            continue
        with fp.open(encoding="utf-8", newline="") as fh:
            for row in csv.DictReader(fh):
                row["_from_file"] = fp.name
                merged.append(row)
    return merged


def normalize_pair(row: dict, idx: int) -> dict | None:
    src = (row.get("source_text") or "").strip()
    tgt = (row.get("target_text") or "").strip()
    if not src or not tgt:
        return None
    tgt_lang = (row.get("target_lang") or "sw").strip()
    expected = "sw" if tgt_lang == "sw" else None
    qc = auto_qc_pair(src, tgt, expected_tgt_lang=expected)
    if not qc["auto_qc_pass"]:
        return None

    meta = {}
    raw_meta = row.get("Metadata") or row.get("metadata") or ""
    if raw_meta:
        try:
            meta = json.loads(raw_meta)
        except json.JSONDecodeError:
            meta = {"raw_metadata": raw_meta}
    meta.update(
        {
            "silver": True,
            "human_reviewed": False,
            "auto_qc": qc,
            "from_file": row.get("_from_file"),
        }
    )
    verified = str(row.get("verified") or "false").lower() == "true"
    return {
        "pair_id": row.get("pair_id") or f"mt_{idx:06d}",
        "psa_id": row.get("psa_id") or "",
        "Domain": row.get("Domain") or "General",
        "source_lang": row.get("source_lang") or "en",
        "target_lang": tgt_lang,
        "source_text": src,
        "target_text": tgt,
        "method": row.get("method") or "unknown",
        "confidence": row.get("confidence") or qc["confidence"],
        "verified": "true" if verified else "false",
        "auto_qc_pass": "true",
        "Source": row.get("Source") or "",
        "Metadata": json.dumps(meta, ensure_ascii=False),
        "split": "",
    }


def split_pairs(
    pairs: list[dict], ratios: tuple[float, float, float], seed: int
) -> dict[str, list[dict]]:
    rng = random.Random(seed)
    by_lang: dict[str, list[dict]] = {}
    for p in pairs:
        by_lang.setdefault(p["target_lang"], []).append(p)

    out = {"train": [], "dev": [], "test": []}
    for lang, items in by_lang.items():
        rng.shuffle(items)
        n = len(items)
        n_train = int(n * ratios[0])
        n_dev = int(n * ratios[1])
        train = items[:n_train]
        dev = items[n_train : n_train + n_dev]
        test = items[n_train + n_dev :]
        if n >= 10 and not test and train:
            test = [train.pop()]
        if n >= 10 and not dev and train:
            dev = [train.pop()]
        for r, name in ((train, "train"), (dev, "dev"), (test, "test")):
            for row in r:
                row["split"] = name
                out[name].append(row)
    for name in out:
        rng.shuffle(out[name])
    return out


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=PAIR_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    args = parse_args()
    ratios = tuple(float(x) for x in args.ratios.split(","))
    if len(ratios) != 3 or abs(sum(ratios) - 1.0) > 1e-6:
        raise SystemExit("--ratios must be three floats summing to 1")

    n_sent = write_sentence_sheet(SENT_OUT)
    raw = load_parallel_files(args.parallel_glob)
    pairs: list[dict] = []
    rejected = 0
    for i, row in enumerate(raw, start=1):
        norm = normalize_pair(row, i)
        if norm is None:
            rejected += 1
            continue
        pairs.append(norm)

    if not pairs:
        raise SystemExit(
            "No parallel pairs passed auto-QC.\n"
            "Run first: python scripts/harvest_external_en_sw.py --limit 3000\n"
            "On Navon GPU: python scripts/seed_nllb_sample.py --targets sw --limit 200 "
            "--output datasets/parallel/nllb_en_sw_silver.csv"
        )

    splits = split_pairs(pairs, ratios, args.seed)
    MT_DIR.mkdir(parents=True, exist_ok=True)
    all_rows = splits["train"] + splits["dev"] + splits["test"]
    write_csv(MT_DIR / "all_pairs.csv", all_rows)
    write_csv(MT_DIR / "train.csv", splits["train"])
    write_csv(MT_DIR / "dev.csv", splits["dev"])
    write_csv(MT_DIR / "test.csv", splits["test"])

    by_method = Counter(r["method"] for r in all_rows)
    by_tgt = Counter(r["target_lang"] for r in all_rows)
    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "human_reviewed": False,
        "note": "Silver/auto-QC only. Safe for baseline fine-tuning; not gold.",
        "psa_sentence_candidates": n_sent,
        "parallel_raw_rows": len(raw),
        "rejected_by_auto_qc": rejected,
        "kept_pairs": len(all_rows),
        "by_method": dict(by_method),
        "by_target_lang": dict(by_tgt),
        "splits": {k: len(v) for k, v in splits.items()},
        "outputs": {
            "sentences": str(SENT_OUT.relative_to(ROOT)),
            "all": "datasets/mt/all_pairs.csv",
            "train": "datasets/mt/train.csv",
            "dev": "datasets/mt/dev.csv",
            "test": "datasets/mt/test.csv",
        },
        "navon_next": [
            "pip install -e '.[mt]'",
            "python scripts/seed_nllb_sample.py --targets sw,luo,guz,som --limit 200 "
            "--output datasets/parallel/nllb_psa_silver.csv",
            "python scripts/prepare_mt_training_data.py",
            "python scripts/train_baseline.py --dry-run",
            "python scripts/train_baseline.py --pair en-sw --epochs 1 --max-train-samples 500",
        ],
    }
    STATS.parent.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
