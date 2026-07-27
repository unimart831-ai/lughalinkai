"""Merge all teammate PSA CSVs into a single Week-1 submission dataset.

Also writes a quarantine sheet for rows rejected as non-PSA / junk.
"""

from __future__ import annotations

import csv
import hashlib
import json
import ast
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from langdetect import DetectorFactory, detect_langs
from langdetect.lang_detect_exception import LangDetectException

DetectorFactory.seed = 0

ROOT = Path(__file__).resolve().parents[1]
OUT_CSV = ROOT / "datasets" / "processed" / "week1_psa_merged.csv"
OUT_JSON = ROOT / "datasets" / "processed" / "week1_psa_merged.json"
OUT_QUARANTINE = ROOT / "datasets" / "processed" / "week1_psa_quarantined.csv"
OUT_STATS = ROOT / "datasets" / "processed" / "week1_merge_stats.json"

TARGET_LANGUAGES = ["Dholuo", "Ekegusii", "Somali"]
DOMAIN_MAP = {
    "health": "Health",
    "agriculture": "Agriculture",
    "education": "Education",
    "security": "Security",
    "security & safety": "Security",
    "governance": "Governance",
    "general": "Governance",
    "uncategorized": "Governance",
}

PSA_HINTS = re.compile(
    r"\b(public notice|press release|advisory|alert|announcement|"
    r"citizens? are (advised|reminded)|vaccinat|immuni|outbreak|"
    r"quarantine|evacuate|curfew|security alert|registration|deadline|"
    r"application|tender|gazette|ministry|commission|voters?|ballot|"
    r"helb|kcse|knec|ministry of health|\bmoh\b|\bkra\b|\biebc\b|"
    r"drought|famine|flood|relief|food security|extension|subsidy|"
    r"please note|members of the public|general public|chanjo|"
    r"wash hands|mosquito nets?|polio|cholera|malaria)\b",
    re.I,
)
NAV_JUNK = re.compile(
    r"(main navigation|home about us|quick links|copyright|"
    r"all rights reserved|facebook|twitter tweets|staff mail|"
    r"organogram|cookie|subscribe to|current page \d|next page|"
    r"last page|skip to content)",
    re.I,
)
LISTING_DUMP = re.compile(
    r"(SNo Notice Description|Notice Description Notice Year Notice Link)",
    re.I,
)
NGO_STUB = re.compile(
    r"(pray with us|click on the link to view|become a force for positive|"
    r"get involved|our structure|our vision and values|take action today|"
    r"follow us on twitter|download publication|annual reports?/)",
    re.I,
)
OFF_TOPIC_NEWS = re.compile(
    r"\b(stadium|indoor games|football|celebrity|gossip|goonism|"
    r"bhang trafficking|transfer rumour|trending)\b",
    re.I,
)
LISTICLE = re.compile(
    r"\b(full list|list of (public )?universities|courses in kenya|"
    r"how to apply for)\b",
    re.I,
)
ALLOWED_LANGS = {"en", "sw"}


def normalize_domain(raw: str | None) -> str:
    if not raw:
        return "Governance"
    key = str(raw).strip().lower()
    return DOMAIN_MAP.get(key, key.title() if key else "Governance")


def clean_text(text: str) -> str:
    text = (text or "").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def content_hash(text: str) -> str:
    norm = re.sub(r"\s+", " ", text.lower()).strip()
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()


def detect_language(text: str) -> str:
    sample = text[:2000]
    if len(sample.split()) < 5:
        return "unknown"
    try:
        langs = detect_langs(sample)
        if not langs:
            return "unknown"
        return langs[0].lang
    except LangDetectException:
        return "unknown"


def sentence_count(text: str) -> int:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return max(1, len([p for p in parts if len(p.split()) >= 3]))


def make_row(
    *,
    psa_id: str,
    domain: str,
    english: str,
    kiswahili: str,
    source: str,
    date: str,
    metadata: dict,
) -> dict | None:
    english = clean_text(english)
    kiswahili = clean_text(kiswahili)
    if len(english.split()) < 8 and len(kiswahili.split()) < 8:
        return None

    primary = english if len(english.split()) >= len(kiswahili.split()) else kiswahili
    lang = detect_language(primary)
    # Prefer English body; if detected SW and English empty, keep SW in Kiswahili
    if not english and kiswahili:
        english = ""
    meta = dict(metadata)
    meta.setdefault("lang_detected", lang)
    meta.setdefault("token_count", len(primary.split()))
    meta.setdefault("sentence_count", sentence_count(primary))
    meta.setdefault("content_hash", content_hash(primary))
    return {
        "PSA_ID": psa_id,
        "Domain": normalize_domain(domain),
        "English": english,
        "Kiswahili": kiswahili,
        "Target Languages": json.dumps(TARGET_LANGUAGES),
        "Source": source or "",
        "Date": date or "",
        "Metadata": json.dumps(meta, ensure_ascii=False),
    }


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", errors="replace", newline="") as fh:
        return list(csv.DictReader(fh))


def load_all_psa_export(path: Path) -> list[dict]:
    rows = []
    for i, r in enumerate(read_csv(path), start=1):
        title = clean_text(r.get("title") or "")
        body = clean_text(r.get("text") or "")
        english = f"{title}. {body}".strip(". ").strip() if title and body else (body or title)
        meta = {
            "contributor": "Iranzi Innocent / data/governance",
            "origin_file": str(path.name),
            "origin_psa_id": r.get("psa_id"),
            "organization": r.get("organization"),
            "urgency": r.get("urgency"),
            "language": r.get("language"),
            "source_schema": "all_psa_export",
        }
        try:
            extra = json.loads(r.get("metadata") or "{}")
            if isinstance(extra, dict):
                meta.update({f"src_{k}": v for k, v in extra.items()})
        except json.JSONDecodeError:
            pass
        row = make_row(
            psa_id=r.get("psa_id") or f"GOV_{i:05d}",
            domain=r.get("domain") or "governance",
            english=english,
            kiswahili="",
            source=r.get("source_url") or "",
            date=r.get("published_at") or "",
            metadata=meta,
        )
        if row:
            rows.append(row)
    return rows


def load_education(path: Path) -> list[dict]:
    rows = []
    for r in read_csv(path):
        english = r.get("English") or ""
        kiswahili = r.get("Kiswahili") or ""
        targets = ["Dholuo", "Ekegusii", "Somali"]
        if r.get("Kikuyu"):
            targets = ["Kikuyu", "Dholuo", "Ekegusii", "Somali"]
        meta = {
            "contributor": "Leona Kamau / data/education",
            "origin_file": path.name,
            "origin_psa_id": r.get("PSA_ID"),
            "sub_category": r.get("Sub_Category"),
            "urgency": r.get("Urgency"),
            "audience": r.get("Audience"),
            "psa_score": r.get("psa_score"),
            "lang_detected_source": r.get("lang_detected"),
            "source_schema": "psa_dataset_final",
        }
        row = make_row(
            psa_id=r.get("PSA_ID") or "",
            domain=r.get("Domain") or "Education",
            english=english,
            kiswahili=kiswahili,
            source=r.get("Source") or "",
            date=r.get("Date") or "",
            metadata=meta,
        )
        if row:
            row["Target Languages"] = json.dumps(targets)
            rows.append(row)
    return rows


def load_agriculture(path: Path) -> list[dict]:
    rows = []
    for r in read_csv(path):
        meta = {
            "contributor": "Jessica Kimani / data/agriculture",
            "origin_file": path.name,
            "origin_psa_id": r.get("PSA_ID"),
            "organization": r.get("Org"),
            "source_schema": "agriculture_psa_export",
        }
        try:
            extra = json.loads(r.get("Metadata") or "{}")
            if isinstance(extra, dict):
                meta["source_metadata"] = extra
        except json.JSONDecodeError:
            meta["source_metadata_raw"] = r.get("Metadata")
        targets = TARGET_LANGUAGES
        raw_targets = r.get("Target_Languages") or ""
        if raw_targets:
            try:
                parsed = ast.literal_eval(raw_targets) if raw_targets.startswith("{") else raw_targets
                if isinstance(parsed, dict):
                    targets = list(parsed.keys()) + TARGET_LANGUAGES
            except Exception:
                pass
        row = make_row(
            psa_id=r.get("PSA_ID") or "",
            domain=r.get("Domain") or "Agriculture",
            english=r.get("English") or "",
            kiswahili=r.get("Kiswahili") or "",
            source=r.get("Source") or "",
            date=r.get("Date") or "",
            metadata=meta,
        )
        if row:
            row["Target Languages"] = json.dumps(list(dict.fromkeys(targets)))
            rows.append(row)
    return rows


def load_media_archives(path: Path) -> list[dict]:
    rows = []
    for r in read_csv(path):
        meta = {
            "contributor": "michenitumaini-ux / main",
            "origin_file": path.name,
            "origin_psa_id": r.get("PSA_ID"),
            "source_schema": "media_archives",
        }
        try:
            extra = json.loads(r.get("Metadata") or "{}")
            if isinstance(extra, dict):
                meta["source_metadata"] = extra
        except json.JSONDecodeError:
            meta["source_metadata_raw"] = r.get("Metadata")
        row = make_row(
            psa_id=r.get("PSA_ID") or "",
            domain=r.get("Domain") or "Governance",
            english=r.get("English") or "",
            kiswahili=r.get("Kiswahili") or "",
            source=r.get("Source") or "",
            date="",
            metadata=meta,
        )
        if row:
            rows.append(row)
    return rows


def load_angela_raw(path: Path) -> list[dict]:
    rows = []
    for i, r in enumerate(read_csv(path), start=1):
        english = r.get("cleaned_text") or r.get("raw_text") or ""
        meta = {
            "contributor": "Angela Irungu / main",
            "origin_file": path.name,
            "source_schema": "psa_dataset_raw_text",
        }
        row = make_row(
            psa_id=f"ANG_{i:05d}",
            domain="Governance",
            english=english,
            kiswahili="",
            source=r.get("source_url") or "",
            date="",
            metadata=meta,
        )
        if row:
            rows.append(row)
    return rows


def dedupe(rows: list[dict]) -> tuple[list[dict], int]:
    seen = set()
    out = []
    dropped = 0
    for row in rows:
        meta = json.loads(row["Metadata"])
        h = meta.get("content_hash") or content_hash(row["English"] or row["Kiswahili"])
        if h in seen:
            dropped += 1
            continue
        seen.add(h)
        out.append(row)
    return out, dropped


def renumber(rows: list[dict], prefix: str = "psa") -> list[dict]:
    year = datetime.now(timezone.utc).year
    for i, row in enumerate(rows, start=1):
        meta = json.loads(row["Metadata"])
        meta["original_psa_id"] = row["PSA_ID"]
        row["PSA_ID"] = f"{prefix}_{year}_{i:06d}"
        row["Metadata"] = json.dumps(meta, ensure_ascii=False)
    return rows


def quarantine_reason(row: dict) -> str | None:
    """Return a rejection reason if this row should not stay in the clean sheet."""
    english = clean_text(row.get("English") or "")
    kiswahili = clean_text(row.get("Kiswahili") or "")
    primary = english if len(english.split()) >= len(kiswahili.split()) else kiswahili
    source = (row.get("Source") or "").lower()
    meta = json.loads(row.get("Metadata") or "{}")
    contributor = (meta.get("contributor") or "").lower()
    tokens = len(primary.split())
    lang = meta.get("lang_detected") or detect_language(primary)

    if tokens == 0:
        return "empty_text"
    if "angela" in contributor or meta.get("origin_file") == "psa_dataset.csv":
        # Angela upload is Treasury site chrome / listing dumps — quarantine all.
        return "angela_raw_scrape"
    if NAV_JUNK.search(primary):
        return "nav_boilerplate"
    if LISTING_DUMP.search(primary):
        return "listing_page_dump"
    if primary.count("Home") >= 3 and "About" in primary:
        return "menu_like"
    if NGO_STUB.search(primary) and not PSA_HINTS.search(primary):
        return "ngo_website_stub"
    if any(x in source for x in ("/get-involved", "/about-us/", "/role-faith", "/annual-reports", "/faq")):
        if not PSA_HINTS.search(primary) or tokens < 40:
            return "ngo_about_page"
    if OFF_TOPIC_NEWS.search(primary) and not PSA_HINTS.search(primary):
        return "off_topic_news"
    if LISTICLE.search(primary) and not PSA_HINTS.search(primary):
        return "listicle_not_psa"
    if tokens < 12:
        # Keep short advisories that look like real PSAs (media-archives style).
        if PSA_HINTS.search(primary) and tokens >= 8:
            return None
        return "too_short"
    if tokens > 800:
        return "very_long_report"
    if lang not in ALLOWED_LANGS and lang != "unknown":
        return f"non_target_language:{lang}"
    # Weak generic NGO blurbs with no PSA signal
    if tokens < 25 and not PSA_HINTS.search(primary):
        if any(h in source for h in ("wvi.org", "amref.org", "vsointernational", "actionagainsthunger")):
            return "short_ngo_non_psa"
    return None


def main() -> None:
    sources = [
        ("all_psa_export", ROOT / "datasets/processed/all_psa_export.csv", load_all_psa_export),
        ("education_final", ROOT / "datasets/processed/psa_dataset_final.csv", load_education),
        ("agriculture", ROOT / "datasets/processed/agriculture_psa_export.csv", load_agriculture),
        ("media_archives", ROOT / "datasets/processed/media_archives_psa_dataset.csv", load_media_archives),
        ("angela_raw", ROOT / "datasets/processed/psa_dataset.csv", load_angela_raw),
    ]

    loaded = {}
    merged = []
    for name, path, loader in sources:
        if not path.exists():
            loaded[name] = {"path": str(path), "rows": 0, "missing": True}
            continue
        rows = loader(path)
        loaded[name] = {"path": str(path), "rows": len(rows), "missing": False}
        merged.extend(rows)

    before = len(merged)
    merged, dropped = dedupe(merged)

    clean: list[dict] = []
    quarantined: list[dict] = []
    reason_counts: Counter[str] = Counter()
    quarantine_by_contributor: Counter[str] = Counter()

    for row in merged:
        reason = quarantine_reason(row)
        meta = json.loads(row["Metadata"])
        contrib = meta.get("contributor", "unknown")
        if reason:
            meta["quarantine_reason"] = reason
            row["Metadata"] = json.dumps(meta, ensure_ascii=False)
            qrow = dict(row)
            qrow["Quarantine_Reason"] = reason
            quarantined.append(qrow)
            reason_counts[reason] += 1
            quarantine_by_contributor[contrib] += 1
        else:
            clean.append(row)

    clean = renumber(clean, prefix="psa")
    quarantined = renumber(quarantined, prefix="qpsa")

    fieldnames = [
        "PSA_ID",
        "Domain",
        "English",
        "Kiswahili",
        "Target Languages",
        "Source",
        "Date",
        "Metadata",
    ]
    q_fields = fieldnames + ["Quarantine_Reason"]

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(clean)

    with OUT_QUARANTINE.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=q_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(quarantined)

    with OUT_JSON.open("w", encoding="utf-8") as fh:
        json.dump(clean, fh, ensure_ascii=False, indent=2)

    by_domain = Counter(r["Domain"] for r in clean)
    by_lang = Counter(json.loads(r["Metadata"]).get("lang_detected", "unknown") for r in clean)
    by_contributor = Counter(
        json.loads(r["Metadata"]).get("contributor", "unknown") for r in clean
    )
    total_sentences = sum(json.loads(r["Metadata"]).get("sentence_count", 1) for r in clean)
    with_sw = sum(1 for r in clean if clean_text(r["Kiswahili"]))

    stats = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_csv": str(OUT_CSV.relative_to(ROOT)),
        "output_json": str(OUT_JSON.relative_to(ROOT)),
        "quarantine_csv": str(OUT_QUARANTINE.relative_to(ROOT)),
        "source_inputs": loaded,
        "rows_before_dedupe": before,
        "duplicates_removed": dropped,
        "rows_quarantined": len(quarantined),
        "rows_final_clean": len(clean),
        "quarantine_reasons": dict(reason_counts),
        "quarantine_by_contributor": dict(quarantine_by_contributor),
        "approx_english_sentences": total_sentences,
        "rows_with_kiswahili_text": with_sw,
        "by_domain": dict(by_domain),
        "by_lang_detected": dict(by_lang),
        "by_contributor": dict(by_contributor),
        "target_languages_placeholder": TARGET_LANGUAGES,
    }
    OUT_STATS.write_text(json.dumps(stats, indent=2), encoding="utf-8")

    print(json.dumps(stats, indent=2))
    print(f"\nWrote {OUT_CSV} ({len(clean)} clean)")
    print(f"Wrote {OUT_QUARANTINE} ({len(quarantined)} quarantined)")
    print(f"Wrote {OUT_JSON}")


if __name__ == "__main__":
    main()
