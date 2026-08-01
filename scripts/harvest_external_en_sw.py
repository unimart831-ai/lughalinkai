"""Harvest public EN↔SW pairs from OPUS (Tatoeba Moses release) as silver bootstrap.

No human review. Writes datasets/parallel/en_sw_pairs.csv with:
  method=external_opus, verified=false, auto_qc_pass=true|false filtered to true.

Uses a direct OPUS download (avoids HF dataset-script / missing en-sw configs).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.translation.silver_qc import auto_qc_pair

OUT = ROOT / "datasets" / "parallel" / "en_sw_pairs.csv"
CACHE = ROOT / "datasets" / "interim" / "opus_globalvoices_en_sw.zip"

# OPUS GlobalVoices Moses package (EN-SW bitext; news-like, closer to PSAs than CCAligned).
OPUS_URL = "https://object.pouta.csc.fi/OPUS-GlobalVoices/v2018q4/moses/en-sw.txt.zip"

PSAISH = {
    "health",
    "vaccine",
    "school",
    "election",
    "vote",
    "police",
    "farm",
    "water",
    "government",
    "ministry",
    "register",
    "warning",
    "emergency",
    "hospital",
    "county",
    "please",
    "must",
    "should",
    "avoid",
    "report",
    "doctor",
    "child",
    "food",
    "safe",
    "disease",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Harvest OPUS Tatoeba EN-SW silver pairs")
    p.add_argument("--limit", type=int, default=3000, help="Max pairs to keep after QC")
    p.add_argument("--scan", type=int, default=50000, help="Max raw lines to scan")
    p.add_argument("--output", type=Path, default=OUT)
    p.add_argument("--url", type=str, default=OPUS_URL)
    p.add_argument("--cache", type=Path, default=CACHE)
    return p.parse_args()


def _score_psaish(text: str) -> int:
    toks = set(text.lower().replace(".", " ").replace(",", " ").split())
    return sum(1 for w in PSAISH if w in toks)


def download_zip(url: str, cache: Path) -> Path:
    cache.parent.mkdir(parents=True, exist_ok=True)
    if cache.exists() and cache.stat().st_size > 1000:
        print(f"Using cached OPUS zip -> {cache}")
        return cache
    print(f"Downloading {url}")
    with urlopen(url, timeout=120) as resp:  # noqa: S310 — fixed OPUS URL
        data = resp.read()
    cache.write_bytes(data)
    print(f"Cached {len(data):,} bytes -> {cache}")
    return cache


def iter_bitext(zip_path: Path):
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        en_name = next((n for n in names if n.endswith(".en")), None)
        sw_name = next((n for n in names if n.endswith(".sw")), None)
        if not en_name or not sw_name:
            raise SystemExit(f"Could not find .en/.sw in zip. Members={names}")
        with zf.open(en_name) as fe, zf.open(sw_name) as fs:
            for en_b, sw_b in zip(fe, fs):
                en = en_b.decode("utf-8", errors="replace").strip()
                sw = sw_b.decode("utf-8", errors="replace").strip()
                if en and sw:
                    yield en, sw


def main() -> None:
    args = parse_args()
    zip_path = download_zip(args.url, args.cache)

    kept: list[dict] = []
    scanned = 0
    for en, sw in iter_bitext(zip_path):
        scanned += 1
        if scanned > args.scan and len(kept) >= args.limit:
            break
        if scanned > args.scan:
            break
        qc = auto_qc_pair(en, sw, expected_tgt_lang="sw")
        if not qc["auto_qc_pass"]:
            continue
        # Early: keep everything that passes QC. Later: prefer psa-ish.
        if len(kept) > args.limit // 2 and _score_psaish(en) == 0 and scanned < args.scan:
            continue
        kept.append(
            {
                "pair_id": f"opus_en_sw_{len(kept)+1:06d}",
                "psa_id": "",
                "Domain": "General",
                "source_lang": "en",
                "target_lang": "sw",
                "source_text": en,
                "target_text": sw,
                "method": "external_opus",
                "confidence": qc["confidence"],
                "verified": "false",
                "auto_qc_pass": "true",
                "Source": "OPUS-GlobalVoices/v2018q4/en-sw",
                "Metadata": json.dumps(
                    {
                        "corpus": "opus_globalvoices",
                        "length_ratio": qc["length_ratio"],
                        "glossary_preservation": qc["glossary_preservation"],
                        "psaish_score": _score_psaish(en),
                        "silver": True,
                        "human_reviewed": False,
                    },
                    ensure_ascii=False,
                ),
            }
        )
        if len(kept) >= args.limit * 2:
            # collect extra then rank
            break

    if not kept:
        raise SystemExit("No OPUS pairs passed QC.")

    kept.sort(key=lambda r: json.loads(r["Metadata"]).get("psaish_score", 0), reverse=True)
    kept = kept[: args.limit]
    for i, row in enumerate(kept, start=1):
        row["pair_id"] = f"opus_en_sw_{i:06d}"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
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
    ]
    with args.output.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(kept)

    print(f"Scanned={scanned} kept={len(kept)} -> {args.output}")
    print("NOTE: silver data only (verified=false). No human review.")


if __name__ == "__main__":
    main()
