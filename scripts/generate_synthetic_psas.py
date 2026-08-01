"""Generate synthetic PSAs from patterns in the strict real freeze.

Uses template + slot-filling guided by DOCS/PSA FRAMEWORK.pdf cues
(action / advisory / alert). All rows are labeled:
  Metadata.synthetic=true, method=synthetic_template, verified=false

Usage:
  python scripts/generate_synthetic_psas.py --target-total 5000
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.metadata.psa_framework import classify_psa_framework

READY = ROOT / "datasets" / "processed" / "week2_ready_psas.csv"
OUT_SYN = ROOT / "datasets" / "processed" / "week2_synthetic_psas.csv"
OUT_MERGED = ROOT / "datasets" / "processed" / "week2_ready_psas.csv"
STATS = ROOT / "datasets" / "interim" / "synthetic_psa_stats.json"

FIELDS = [
    "PSA_ID",
    "Domain",
    "English",
    "Kiswahili",
    "Target Languages",
    "Source",
    "Date",
    "Metadata",
]

ORGS = {
    "Governance": [
        "IEBC",
        "EACC",
        "Huduma Kenya",
        "Kenya Revenue Authority",
        "Public Service Commission",
        "Communications Authority of Kenya",
        "The National Treasury",
    ],
    "Health": [
        "Ministry of Health",
        "Social Health Authority",
        "County Department of Health",
        "Kenya Red Cross",
        "WHO Kenya",
    ],
    "Security": [
        "National Police Service",
        "NDMA",
        "Kenya Meteorological Department",
        "NTSA",
        "Ministry of Interior",
        "Kenya Wildlife Service",
    ],
    "Education": [
        "Ministry of Education",
        "KNEC",
        "HELB",
        "KUCCPS",
        "TSC",
    ],
    "Agriculture": [
        "Ministry of Agriculture",
        "KEPHIS",
        "KALRO",
        "NDMA",
        "County Department of Agriculture",
    ],
}

AUDIENCES = {
    "Governance": ["members of the public", "all citizens", "taxpayers", "voters", "job applicants"],
    "Health": ["members of the public", "parents and caregivers", "health workers", "pregnant women"],
    "Security": ["motorists", "residents", "farmers in arid areas", "members of the public", "drivers"],
    "Education": ["students", "parents and guardians", "school heads", "candidates"],
    "Agriculture": ["farmers", "livestock keepers", "traders", "cooperative members"],
}

ACTIONS = [
    "urges {audience} to {verb_phrase}",
    "reminds {audience} to {verb_phrase}",
    "advises {audience} to {verb_phrase}",
    "warns {audience} to {verb_phrase}",
    "requests {audience} to {verb_phrase}",
]

VERBS = {
    "Governance": [
        "verify their details via the official portal",
        "report corruption through the official hotline",
        "renew expired licences before the deadline",
        "ignore unverified social media claims and rely on official notices",
        "complete registration using their original national ID",
        "submit required documents at the nearest Huduma Centre",
    ],
    "Health": [
        "wash hands regularly with soap and clean water",
        "seek medical care immediately if symptoms appear",
        "complete routine immunization for children under five",
        "avoid unnecessary travel to affected areas",
        "register for SHA cover through official channels only",
        "boil drinking water during the current advisory period",
    ],
    "Security": [
        "observe the road safety rules and avoid overspeeding",
        "evacuate low-lying areas when flood alerts are issued",
        "report suspicious activity to the nearest police station",
        "follow official weather advisories before travel",
        "keep children away from flooded rivers and open drains",
        "use only designated crossing points during heavy rains",
    ],
    "Education": [
        "confirm school placement results on the official portal",
        "complete HELB loan applications before the deadline",
        "ensure learners report to school with required documents",
        "avoid exam malpractice and report any malpractice attempts",
        "update contact details for scholarship communication",
        "collect examination cards from designated centres only",
    ],
    "Agriculture": [
        "plant drought-tolerant varieties recommended for this season",
        "report pest outbreaks to the nearest agricultural officer",
        "store harvested produce in dry, secure facilities",
        "vaccinate livestock according to the county schedule",
        "avoid fake fertiliser and buy only from licensed agrovets",
        "follow grazing advisories during the drought period",
    ],
}

DEADLINES = [
    "Deadline: {day} {month} 2026.",
    "This advisory takes effect immediately.",
    "Please comply within 7 days.",
    "Registration closes on {day} {month} 2026.",
    "Act before {day} {month} 2026 to avoid penalties.",
]

CLOSERS = [
    "For accurate information, visit the official website and follow verified social media channels only.",
    "The public is hereby informed to disregard rumours not issued through official channels.",
    "Further updates will be shared through official government platforms.",
    "Failure to comply may attract penalties under applicable laws.",
]

MONTHS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

LOCATIONS = [
    "Nairobi County",
    "Mombasa County",
    "Kisumu County",
    "Nakuru County",
    "Nyeri County",
    "Garissa County",
    "Turkana County",
    "Kakamega County",
    "Kiambu County",
    "Machakos County",
]

TEMPLATES = [
    "PUBLIC NOTICE. {org} {action}. {deadline} {closer}",
    "ALERT. {org} {action} in {location}. {deadline} {closer}",
    "{org}: {audience_cap} are advised to {verb_phrase}. {deadline} {closer}",
    "The {org} reminds {audience} to {verb_phrase}. {deadline} {closer}",
    "ADVISORY. {org} warns {audience} to {verb_phrase}. {deadline} {closer}",
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate synthetic PSAs from strict patterns")
    p.add_argument("--target-total", type=int, default=5000)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--max-attempts", type=int, default=20000)
    p.add_argument(
        "--balance",
        action="store_true",
        default=True,
        help="Prefer under-filled domains (Education/Agriculture)",
    )
    return p.parse_args()


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def load_real() -> list[dict]:
    if not READY.exists():
        raise SystemExit(f"Missing strict freeze: {READY}")
    return list(csv.DictReader(READY.open(encoding="utf-8", newline="")))


def domain_weights(real_counts: Counter[str], target_extra: int) -> list[str]:
    """Sample domains with inverse-frequency bias to rebalance."""
    domains = ["Governance", "Health", "Security", "Education", "Agriculture"]
    # Ideal roughly even among non-governance, keep some governance.
    ideal = {
        "Governance": 0.28,
        "Health": 0.20,
        "Security": 0.20,
        "Education": 0.16,
        "Agriculture": 0.16,
    }
    # Shortage score
    total_real = sum(real_counts.values()) or 1
    scores = []
    for d in domains:
        current = real_counts.get(d, 0) / total_real
        gap = max(0.01, ideal[d] - current)
        scores.append((d, gap))
    # Build weighted bag
    bag: list[str] = []
    for d, gap in scores:
        bag.extend([d] * max(1, int(gap * 100)))
    return bag


def one_psa(rng: random.Random, domain: str) -> str:
    org = rng.choice(ORGS[domain])
    audience = rng.choice(AUDIENCES[domain])
    verb = rng.choice(VERBS[domain])
    action_tmpl = rng.choice(ACTIONS)
    action = action_tmpl.format(audience=audience, verb_phrase=verb)
    deadline = rng.choice(DEADLINES).format(day=rng.randint(1, 28), month=rng.choice(MONTHS))
    closer = rng.choice(CLOSERS)
    location = rng.choice(LOCATIONS)
    tmpl = rng.choice(TEMPLATES)
    text = tmpl.format(
        org=org,
        action=action,
        deadline=deadline,
        closer=closer,
        location=location,
        audience=audience,
        audience_cap=audience[:1].upper() + audience[1:],
        verb_phrase=verb,
    )
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    args = parse_args()
    rng = random.Random(args.seed)
    real = load_real()
    real_counts = Counter(r.get("Domain") or "Governance" for r in real)
    need = max(0, args.target_total - len(real))
    if need == 0:
        print(json.dumps({"strict_real": len(real), "synthetic_added": 0, "total": len(real)}, indent=2))
        return

    bag = domain_weights(real_counts, need)
    seen = {_norm(r.get("English") or "") for r in real}
    seen.discard("")

    synthetic: list[dict] = []
    attempts = 0
    reject = Counter()
    while len(synthetic) < need and attempts < args.max_attempts:
        attempts += 1
        domain = rng.choice(bag)
        text = one_psa(rng, domain)
        key = _norm(text)
        if not key or key in seen:
            reject["duplicate"] += 1
            continue
        fw = classify_psa_framework(text, title=text.split(".")[0])
        if not fw["is_strict_psa"]:
            reject[fw["framework_label"]] += 1
            continue
        seen.add(key)
        synthetic.append(
            {
                "PSA_ID": "",
                "Domain": domain,
                "English": text,
                "Kiswahili": "",
                "Target Languages": '["Kikuyu"]',
                "Source": "synthetic://lughalink/psa_framework_template",
                "Date": "",
                "Metadata": json.dumps(
                    {
                        "synthetic": True,
                        "method": "synthetic_template",
                        "human_reviewed": False,
                        "framework_label": fw["framework_label"],
                        "framework_confidence": fw["framework_confidence"],
                        "based_on_strict_patterns": True,
                        "seed": args.seed,
                    },
                    ensure_ascii=False,
                ),
            }
        )

    year = datetime.now(timezone.utc).year
    # Merge: keep real first, then synthetic; renumber
    merged = []
    for row in real:
        r = dict(row)
        # Ensure target lang placeholder is Kikuyu
        r["Target Languages"] = r.get("Target Languages") or '["Kikuyu"]'
        try:
            meta = json.loads(r.get("Metadata") or "{}")
        except json.JSONDecodeError:
            meta = {}
        meta.setdefault("synthetic", False)
        r["Metadata"] = json.dumps(meta, ensure_ascii=False)
        merged.append(r)
    merged.extend(synthetic)

    for i, row in enumerate(merged, start=1):
        meta = json.loads(row.get("Metadata") or "{}")
        meta["original_psa_id"] = meta.get("original_psa_id") or row.get("PSA_ID")
        row["PSA_ID"] = f"psa_{year}_{i:06d}"
        row["Metadata"] = json.dumps(meta, ensure_ascii=False)

    OUT_SYN.parent.mkdir(parents=True, exist_ok=True)
    with OUT_SYN.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(synthetic)

    with OUT_MERGED.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(merged)

    # Sync working sheets
    for path in (
        ROOT / "datasets" / "processed" / "week2_strict_psas.csv",
        ROOT / "datasets" / "processed" / "week1_psa_merged.csv",
        ROOT / "datasets" / "processed" / "week1_baseline_psa.csv",
    ):
        with path.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(merged)

    by_domain = Counter(r["Domain"] for r in merged)
    by_origin = Counter(
        "synthetic" if json.loads(r.get("Metadata") or "{}").get("synthetic") else "real"
        for r in merged
    )
    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "strict_real_input": len(real),
        "synthetic_added": len(synthetic),
        "total": len(merged),
        "target_total": args.target_total,
        "attempts": attempts,
        "reject_reasons": dict(reject),
        "by_domain": dict(by_domain),
        "by_origin": dict(by_origin),
        "outputs": {
            "synthetic_only": str(OUT_SYN.relative_to(ROOT)),
            "merged_ready": str(OUT_MERGED.relative_to(ROOT)),
        },
        "note": (
            "Synthetic rows are framework-filtered template PSAs for volume. "
            "They are NOT scraped government text. Keep verified=false."
        ),
    }
    STATS.parent.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    (ROOT / "datasets" / "processed" / "week2_ready_psas_stats.json").write_text(
        json.dumps(
            {
                "generated_at": stats["generated_at"],
                "file": str(OUT_MERGED),
                "rows": len(merged),
                "by_domain": dict(by_domain),
                "by_origin": dict(by_origin),
                "purpose": "Strict real PSAs + framework-valid synthetic templates toward 5k",
                "do_not_overwrite_with_quarantine": True,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
