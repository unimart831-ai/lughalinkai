"""Audit teammate CSVs for non-PSA / junk rows."""

from __future__ import annotations

import csv
import re
from collections import Counter
from html import unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "datasets" / "processed"

PSA_HINTS = re.compile(
    r"\b(public notice|press release|advisory|alert|announcement|"
    r"citizens? are (advised|reminded)|vaccinat|immuni|outbreak|"
    r"quarantine|evacuate|curfew|security alert|registration|deadline|"
    r"application|tender|gazette|ministry|commission|voters?|ballot|"
    r"helb|kcse|knec|ministry of health|moh|kra|iebc|drought|famine|"
    r"flood|relief|food security|extension|subsidy|please note|"
    r"members of the public|general public)\b",
    re.I,
)
NAV_JUNK = re.compile(
    r"(main navigation|home about us|quick links|copyright|"
    r"all rights reserved|facebook|twitter tweets|staff mail|"
    r"organogram|cookie|subscribe to|current page \d|next page|"
    r"last page|skip to content)",
    re.I,
)
COURSE_LIST = re.compile(
    r"\b(full list|list of|courses in kenya|universities in kenya|"
    r"how to apply for)\b",
    re.I,
)
NEWS_OPINION = re.compile(
    r"\b(opinion|celebrity|gossip|football|transfer rumour|trending)\b",
    re.I,
)


def text_of(row: dict, keys: list[str]) -> str:
    for k in keys:
        v = (row.get(k) or "").strip()
        if v:
            return unescape(v)
    return ""


def assess(text: str, source: str = "") -> tuple[str, list[str], int, bool]:
    t = (text or "").strip()
    reasons: list[str] = []
    toks = t.split()
    n = len(toks)
    if n == 0:
        reasons.append("empty")
    elif n < 12:
        reasons.append("too_short")
    if NAV_JUNK.search(t):
        reasons.append("nav_boilerplate")
    if t.count("Home") >= 3 and t.count("About") >= 1:
        reasons.append("menu_like")
    if COURSE_LIST.search(t) and not PSA_HINTS.search(t):
        reasons.append("listicle_not_psa")
    if NEWS_OPINION.search(t):
        reasons.append("entertainment_news")
    if n > 800:
        reasons.append("very_long_report")
    if "Notice Description Notice Year Notice Link" in t or "SNo Notice Description" in t:
        reasons.append("listing_page_dump")
    src_l = (source or "").strip().lower()
    if src_l in {"official press release archive", "pressrelease feed", "n/a", "unknown"} and n < 25:
        reasons.append("weak_source_short")
    has_psa = bool(PSA_HINTS.search(t))
    if not reasons and has_psa:
        label = "likely_psa"
    elif not reasons and n >= 40:
        label = "maybe_psa"
    elif reasons and has_psa and reasons == ["very_long_report"]:
        label = "long_but_thematic"
    elif reasons:
        label = "non_psa_suspect"
    else:
        label = "weak_uncertain"
    return label, reasons, n, has_psa


SOURCES = {
    "Iranzi / all_psa_export": ROOT / "all_psa_export.csv",
    "Leona / education": ROOT / "psa_dataset_final.csv",
    "Jessica / agriculture": ROOT / "agriculture_psa_export.csv",
    "Media archives / michenitumaini": ROOT / "media_archives_psa_dataset.csv",
    "Angela / psa_dataset": ROOT / "psa_dataset.csv",
}


def load_rows(path: Path, contributor: str) -> list[dict]:
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        rows = list(csv.DictReader(f))
    out = []
    for i, row in enumerate(rows, 1):
        text = text_of(
            row,
            ["English", "english", "cleaned_text", "text", "body", "raw_text", "Kiswahili", "content"],
        )
        src = text_of(row, ["Source", "source", "source_url", "url", "URL"])
        dom = text_of(row, ["Domain", "domain", "category"])
        label, reasons, n, has_psa = assess(text, src)
        out.append(
            {
                "contributor": contributor,
                "row": i,
                "domain": dom,
                "source": src[:120],
                "tokens": n,
                "label": label,
                "reasons": reasons,
                "has_psa_hint": has_psa,
                "excerpt": re.sub(r"\s+", " ", text)[:140],
            }
        )
    return out


def main() -> None:
    all_rows: list[dict] = []
    for name, path in SOURCES.items():
        if not path.exists():
            print("MISSING", path)
            continue
        rows = load_rows(path, name)
        all_rows.extend(rows)
        labels = Counter(r["label"] for r in rows)
        reason_c: Counter[str] = Counter()
        for r in rows:
            reason_c.update(r["reasons"])
        print(f"\n## {name}")
        print(f"total={len(rows)} labels={dict(labels)}")
        print(f"top_reasons={reason_c.most_common(8)}")

    print("\n=== SAMPLE NON-PSA SUSPECTS (up to 6 each) ===")
    for name in SOURCES:
        suspects = [r for r in all_rows if r["contributor"] == name and r["label"] == "non_psa_suspect"]
        print(f"\n-- {name}: {len(suspects)} suspects --")
        for r in suspects[:6]:
            print(f"  row{r['row']} toks={r['tokens']} reasons={r['reasons']}")
            print(f"    src={r['source']}")
            print(f"    {r['excerpt']}")

    print("\n=== LONG REPORTS (>800 tokens) ===")
    for name in SOURCES:
        longs = [r for r in all_rows if r["contributor"] == name and "very_long_report" in r["reasons"]]
        print(f"{name}: {len(longs)}")

    print("\n=== VERDICT COUNTS ===")
    for name in SOURCES:
        rows = [r for r in all_rows if r["contributor"] == name]
        if not rows:
            continue
        suspects = sum(1 for r in rows if r["label"] == "non_psa_suspect")
        long_only = sum(1 for r in rows if r["label"] == "long_but_thematic")
        likely = sum(1 for r in rows if r["label"] in {"likely_psa", "maybe_psa"})
        print(
            f"{name}: likely/maybe={likely} long_reports={long_only} "
            f"non_psa_suspect={suspects} ({100*suspects/len(rows):.1f}%)"
        )


if __name__ == "__main__":
    main()
