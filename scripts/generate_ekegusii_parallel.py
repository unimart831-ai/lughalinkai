"""Generate EN↔Ekegusii PSA parallel pairs from English sentence sheet.

Ekegusii is not in stock NLLB-200. This builds template silver targets for
zero-shot baselines and few-shot fine-tunes (mT5 + NLLB vocab-extend).

  python scripts/generate_ekegusii_parallel.py --limit 5200
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SENTENCES = ROOT / "datasets" / "interim" / "week2_mt_sentences.csv"
LEXICON = ROOT / "configs" / "ekegusii_psa_lexicon.yaml"
OUT = ROOT / "datasets" / "parallel" / "guz_psa_template.csv"
STATS = ROOT / "datasets" / "interim" / "guz_parallel_stats.json"

ORG_RE = re.compile(
    r"\b("
    r"IEBC|EACC|Huduma Kenya|Kenya Revenue Authority|Public Service Commission|"
    r"Ministry of Health|Social Health Authority|County Department of Health|"
    r"Kenya Red Cross|WHO Kenya|National Police Service|NDMA|"
    r"Kenya Meteorological Department|NTSA|Ministry of Interior|"
    r"Kenya Wildlife Service|Ministry of Education|KNEC|HELB|KUCCPS|TSC|"
    r"Ministry of Agriculture|KEPHIS|KALRO|County Department of Agriculture|"
    r"Communications Authority of Kenya|The National Treasury"
    r")\b",
    re.I,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate EN↔Ekegusii PSA template pairs")
    p.add_argument("--input", type=Path, default=SENTENCES)
    p.add_argument("--lexicon", type=Path, default=LEXICON)
    p.add_argument("--output", type=Path, default=OUT)
    p.add_argument("--limit", type=int, default=5200)
    p.add_argument("--seed", type=int, default=42)
    return p.parse_args()


def load_lexicon(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def match_verb(english: str, verb_map: dict[str, str]) -> str | None:
    low = english.lower()
    # Longest key first for better matches
    for en, guz in sorted(verb_map.items(), key=lambda kv: -len(kv[0])):
        if en.lower() in low:
            return guz
    return None


def pick_org(english: str, domain: str, lex: dict, rng: random.Random) -> str:
    m = ORG_RE.search(english or "")
    if m:
        return m.group(1)
    orgs = (lex.get("orgs") or {}).get(domain) or ["IEBC"]
    return rng.choice(orgs)


def render_guz(
    *,
    english: str,
    domain: str,
    lex: dict,
    rng: random.Random,
) -> tuple[str, str]:
    """Return (guz_text, match_mode)."""
    domain = domain if domain in (lex.get("orgs") or {}) else "Governance"
    verb = match_verb(english, lex.get("verb_map") or {})
    mode = "verb_map" if verb else "domain_fallback"
    if not verb:
        verb = (lex.get("domain_fallback_verbs") or {}).get(domain) or (
            "gokora amachiko a goseka"
        )

    org = pick_org(english, domain, lex, rng)
    audience = rng.choice((lex.get("audiences") or {}).get(domain) or ["abanto bonsi"])
    stem = rng.choice(lex.get("action_stems") or ["{org} nigo ekoransia {audience} go {verb}."])
    location = rng.choice(lex.get("locations") or ["Kisii County"])
    deadline = rng.choice(lex.get("deadlines") or ["Ororagererio rwa rero rwatangire buna."])
    closer = rng.choice(lex.get("closers") or [""])
    month = rng.choice(lex.get("months") or ["August"])
    day = rng.randint(1, 28)

    body = stem.format(org=org, audience=audience, verb=verb, location=location)
    deadline = deadline.format(day=day, month=month)
    parts = [body.strip(), deadline.strip(), closer.strip()]
    guz = " ".join(p for p in parts if p)
    guz = re.sub(r"\s+", " ", guz).strip()
    return guz, mode


def main() -> None:
    args = parse_args()
    if not args.input.exists():
        raise SystemExit(f"Missing sentence sheet: {args.input}")
    if not args.lexicon.exists():
        raise SystemExit(f"Missing lexicon: {args.lexicon}")

    lex = load_lexicon(args.lexicon)
    rng = random.Random(args.seed)
    rows = list(csv.DictReader(args.input.open(encoding="utf-8", newline="")))
    if args.limit and args.limit > 0:
        rows = rows[: args.limit]

    out_rows: list[dict] = []
    modes: dict[str, int] = {}
    for i, row in enumerate(rows, start=1):
        src = (row.get("source_text") or "").strip()
        if not src:
            continue
        domain = (row.get("Domain") or "Governance").strip() or "Governance"
        guz, mode = render_guz(english=src, domain=domain, lex=lex, rng=rng)
        modes[mode] = modes.get(mode, 0) + 1
        psa_id = (row.get("psa_id") or "").strip() or f"guz_src_{i:05d}"
        sid = (row.get("sentence_id") or f"{psa_id}_s01").strip()
        out_rows.append(
            {
                "pair_id": f"guz_tpl_{i:06d}",
                "psa_id": psa_id,
                "Domain": domain,
                "source_lang": "en",
                "target_lang": "guz",
                "source_text": src,
                "target_text": guz,
                "method": "guz_psa_template",
                "confidence": 0.55 if mode == "verb_map" else 0.4,
                "verified": "false",
                "Source": row.get("Source") or "",
                "Metadata": json.dumps(
                    {
                        "synthetic": True,
                        "method": "guz_psa_template",
                        "match_mode": mode,
                        "sentence_id": sid,
                        "human_reviewed": False,
                        "silver": True,
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    },
                    ensure_ascii=False,
                ),
            }
        )

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
        "Source",
        "Metadata",
    ]
    with args.output.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(out_rows)

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": str(args.input),
        "output": str(args.output),
        "rows": len(out_rows),
        "match_modes": modes,
        "note": "Template silver EN↔Ekegusii. Not human gold. For zero-shot baselines and few-shot FT.",
    }
    STATS.parent.mkdir(parents=True, exist_ok=True)
    STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")
    print(f"Wrote {len(out_rows)} pairs -> {args.output}")
    print(json.dumps(modes, indent=2))


if __name__ == "__main__":
    main()
