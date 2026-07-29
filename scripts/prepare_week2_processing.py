"""Week 2 processing: clean corpus, EDA stats, validation subset, train/dev/test."""

from __future__ import annotations

import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.preprocessing.pipeline import CLEAN_FIELDS, compute_eda_stats, process_corpus
from services.preprocessing.splits import count_by, pick_validation_from_heldout, stratified_split
SRC = ROOT / "datasets" / "processed" / "week2_ready_psas.csv"
CLEANED = ROOT / "datasets" / "processed" / "week2_cleaned_psas.csv"
SPLITS_DIR = ROOT / "datasets" / "splits"
GOLD_DIR = ROOT / "datasets" / "gold"
VALIDATION = GOLD_DIR / "native_validation_500.csv"
EDA_STATS = ROOT / "datasets" / "interim" / "week2_eda_stats.json"
RUN_STATS = ROOT / "datasets" / "interim" / "week2_processing_stats.json"

VALIDATION_N = 500
SEED = 42
RATIOS = (0.8, 0.1, 0.1)

VALIDATION_FIELDS = CLEAN_FIELDS + [
    "reviewer",
    "is_valid_psa",
    "fluency_ok",
    "adequacy_ok",
    "cultural_ok",
    "review_notes",
    "verified",
]


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            out = {k: row.get(k, "") for k in fieldnames}
            if isinstance(out.get("code_switch"), bool):
                out["code_switch"] = str(out["code_switch"]).lower()
            if isinstance(out.get("has_kiswahili"), bool):
                out["has_kiswahili"] = str(out["has_kiswahili"]).lower()
            if isinstance(out.get("validation_subset"), bool):
                out["validation_subset"] = str(out["validation_subset"]).lower()
            writer.writerow(out)


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"Missing frozen Week 2 corpus: {SRC}")

    raw_rows = list(csv.DictReader(SRC.open(encoding="utf-8", newline="")))
    cleaned = process_corpus(raw_rows)
    if not cleaned:
        raise SystemExit("No usable English PSAs after preprocessing.")

    train, dev, test = stratified_split(cleaned, ratios=RATIOS, key="Domain", seed=SEED)
    split_map = {}
    for row in train:
        split_map[row["PSA_ID"]] = "train"
    for row in dev:
        split_map[row["PSA_ID"]] = "dev"
    for row in test:
        split_map[row["PSA_ID"]] = "test"

    validation = pick_validation_from_heldout(train, dev, test, n=VALIDATION_N, key="Domain", seed=SEED)
    val_ids = {r["PSA_ID"] for r in validation}

    for row in cleaned:
        row["split"] = split_map.get(row["PSA_ID"], "")
        row["validation_subset"] = row["PSA_ID"] in val_ids

    # Persist master cleaned sheet + splits.
    _write_csv(CLEANED, cleaned, CLEAN_FIELDS)
    SPLITS_DIR.mkdir(parents=True, exist_ok=True)
    _write_csv(SPLITS_DIR / "train.csv", [r for r in cleaned if r["split"] == "train"], CLEAN_FIELDS)
    _write_csv(SPLITS_DIR / "dev.csv", [r for r in cleaned if r["split"] == "dev"], CLEAN_FIELDS)
    _write_csv(SPLITS_DIR / "test.csv", [r for r in cleaned if r["split"] == "test"], CLEAN_FIELDS)

    val_out = []
    for row in validation:
        item = dict(row)
        item["split"] = split_map.get(row["PSA_ID"], "")
        item["validation_subset"] = True
        item.update(
            {
                "reviewer": "",
                "is_valid_psa": "",
                "fluency_ok": "",
                "adequacy_ok": "",
                "cultural_ok": "",
                "review_notes": "",
                "verified": "false",
            }
        )
        val_out.append(item)
    _write_csv(VALIDATION, val_out, VALIDATION_FIELDS)

    eda = compute_eda_stats(cleaned)
    eda["generated_at"] = datetime.now(timezone.utc).isoformat()
    eda["source"] = str(SRC.relative_to(ROOT))
    eda["cleaned"] = str(CLEANED.relative_to(ROOT))
    eda["splits"] = {
        "train": len(train),
        "dev": len(dev),
        "test": len(test),
        "ratios": list(RATIOS),
        "by_domain": {
            "train": count_by(train),
            "dev": count_by(dev),
            "test": count_by(test),
        },
    }
    eda["native_validation"] = {
        "path": str(VALIDATION.relative_to(ROOT)),
        "rows": len(val_out),
        "by_domain": count_by(val_out),
        "from_heldout_preferred": True,
    }

    EDA_STATS.parent.mkdir(parents=True, exist_ok=True)
    EDA_STATS.write_text(json.dumps(eda, indent=2), encoding="utf-8")

    run = {
        "generated_at": eda["generated_at"],
        "input_rows": len(raw_rows),
        "cleaned_rows": len(cleaned),
        "dropped_empty_english": len(raw_rows) - len(cleaned),
        "outputs": {
            "cleaned": str(CLEANED.relative_to(ROOT)),
            "train": "datasets/splits/train.csv",
            "dev": "datasets/splits/dev.csv",
            "test": "datasets/splits/test.csv",
            "native_validation": str(VALIDATION.relative_to(ROOT)),
            "eda_stats": str(EDA_STATS.relative_to(ROOT)),
        },
        "by_domain": eda["by_domain"],
        "splits": eda["splits"],
        "native_validation": eda["native_validation"],
    }
    RUN_STATS.write_text(json.dumps(run, indent=2), encoding="utf-8")
    print(json.dumps(run, indent=2))
    print(f"\nCleaned corpus -> {CLEANED} ({len(cleaned)} rows)")
    print(f"Splits -> {SPLITS_DIR} (train={len(train)} dev={len(dev)} test={len(test)})")
    print(f"Native validation -> {VALIDATION} ({len(val_out)} rows)")
    print(f"EDA stats -> {EDA_STATS}")


if __name__ == "__main__":
    main()
