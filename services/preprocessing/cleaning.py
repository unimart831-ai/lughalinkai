import re
import unicodedata
from typing import Optional

from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0

WHITESPACE_RE = re.compile(r"\s+")


def extract_text(raw_text: Optional[str], raw_html: Optional[str] = None) -> str:
    if raw_text and raw_text.strip():
        return raw_text.strip()
    if raw_html:
        from bs4 import BeautifulSoup

        return BeautifulSoup(raw_html, "lxml").get_text("\n", strip=True)
    return ""


def strip_boilerplate(text: str) -> str:
    lines = [ln.strip() for ln in text.splitlines()]
    cleaned = []
    skip_patterns = (
        r"^(home|menu|share|tweet|copyright|all rights reserved|subscribe)",
        r"^(related|read also|advertisement|click here)",
    )
    for line in lines:
        if not line:
            continue
        if any(re.match(p, line, re.I) for p in skip_patterns):
            continue
        cleaned.append(line)
    return "\n".join(cleaned)


def normalize_whitespace(text: str) -> str:
    return WHITESPACE_RE.sub(" ", text).strip()


def fix_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def detect_language(text: str) -> Optional[str]:
    try:
        code = detect(text)
        return {"en": "en", "sw": "sw", "so": "som"}.get(code, code)
    except LangDetectException:
        return None


def token_count(text: str) -> int:
    return len(text.split())


def clean_raw_content(raw_text: Optional[str], raw_html: Optional[str] = None) -> dict:
    text = extract_text(raw_text, raw_html)
    text = strip_boilerplate(text)
    text = normalize_whitespace(text)
    text = fix_unicode(text)
    language = detect_language(text)
    return {
        "text": text,
        "language": language,
        "token_count": token_count(text),
    }
