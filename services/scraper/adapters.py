from typing import Dict, Optional
import os
import re
import time
from abc import ABC, abstractmethod
from datetime import datetime
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import feedparser
import httpx
from bs4 import BeautifulSoup

from services.models import RawScrapedItem, ScrapeConfig, SourceRecord


def _ssl_verify() -> bool:
    """Set SCRAPER_SSL_VERIFY=false in .env if Windows SSL certs block gov sites."""
    return os.getenv("SCRAPER_SSL_VERIFY", "true").lower() not in {"0", "false", "no"}


class BaseAdapter(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self, source: SourceRecord) -> list[RawScrapedItem]:
        ...


class GenericHtmlAdapter(BaseAdapter):
    name = "generic_html"

    def fetch(self, source: SourceRecord) -> list[RawScrapedItem]:
        config = source.scrape_config
        if not config.listing_url:
            return []

        self._check_robots(source, config.listing_url)
        items: list[RawScrapedItem] = []

        with httpx.Client(timeout=30, follow_redirects=True, verify=_ssl_verify()) as client:
            listing_html = client.get(config.listing_url).text
            soup = BeautifulSoup(listing_html, "lxml")
            links = self._extract_article_links(soup, config, config.listing_url)

            for link in links[: max(1, config.max_items)]:
                time.sleep(config.rate_limit_seconds)
                try:
                    resp = client.get(link)
                    resp.raise_for_status()
                except httpx.HTTPError:
                    continue

                article_soup = BeautifulSoup(resp.text, "lxml")
                title_el = article_soup.select_one(config.title_selector)
                body_el = article_soup.select_one(config.body_selector)
                date_el = article_soup.select_one(config.date_selector)

                title = title_el.get_text(strip=True) if title_el else "Untitled"
                body = body_el.get_text("\n", strip=True) if body_el else ""
                if not body or len(body.split()) < 10:
                    continue

                published_at = None
                if date_el and date_el.get("datetime"):
                    try:
                        published_at = datetime.fromisoformat(
                            date_el["datetime"].replace("Z", "+00:00")
                        )
                    except ValueError:
                        published_at = None

                items.append(
                    RawScrapedItem(
                        source_id=source.source_id,
                        source_url=link,
                        title=title,
                        raw_html=resp.text,
                        raw_text=body,
                        published_at=published_at,
                    )
                )
        return items

    def _extract_article_links(
        self, soup: BeautifulSoup, config: ScrapeConfig, base_url: str
    ) -> list[str]:
        links: list[str] = []
        needle = (config.link_href_contains or "").lower()

        def _maybe_add(href: str) -> None:
            if not href:
                return
            full = urljoin(base_url, href).split("#")[0]
            if needle and needle not in full.lower():
                return
            if full not in links:
                links.append(full)

        for el in soup.select(f"{config.article_selector} a[href]"):
            _maybe_add(el.get("href", ""))
        if not links:
            for el in soup.select("a[href]"):
                href = el.get("href", "")
                if needle:
                    _maybe_add(href)
                elif re.search(r"(news|press|announce|alert|notice)", href, re.I):
                    _maybe_add(href)
        return links

    def _check_robots(self, source: SourceRecord, url: str) -> None:
        if not source.robots_txt_respected or not source.website:
            return
        rp = RobotFileParser()
        rp.set_url(urljoin(source.website, "/robots.txt"))
        try:
            rp.read()
            if not rp.can_fetch("*", url):
                raise PermissionError(f"robots.txt disallows scraping: {url}")
        except Exception:
            pass  # if robots.txt unreachable, proceed cautiously


class RssFeedAdapter(BaseAdapter):
    name = "rss_feed"

    def fetch(self, source: SourceRecord) -> list[RawScrapedItem]:
        if not source.rss_feed:
            return []

        feed = feedparser.parse(source.rss_feed)
        items: list[RawScrapedItem] = []
        for entry in feed.entries[:50]:
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
            text = BeautifulSoup(summary, "lxml").get_text("\n", strip=True)
            if len(text.split()) < 10:
                continue
            published_at = None
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published_at = datetime(*entry.published_parsed[:6])
            items.append(
                RawScrapedItem(
                    source_id=source.source_id,
                    source_url=entry.link,
                    title=getattr(entry, "title", "Untitled"),
                    raw_text=text,
                    published_at=published_at,
                )
            )
            time.sleep(source.scrape_config.rate_limit_seconds)
        return items


class ManualUploadAdapter(BaseAdapter):
    name = "manual_upload"

    def fetch(self, source: SourceRecord) -> list[RawScrapedItem]:
        return []  # populated via CLI upload command


ADAPTERS: dict[str, BaseAdapter] = {
    "generic_html": GenericHtmlAdapter(),
    "rss_feed": RssFeedAdapter(),
    "manual_upload": ManualUploadAdapter(),
}


class ScraperOrchestrator:
    def __init__(self, adapters: Optional[Dict[str, BaseAdapter]] = None):
        self.adapters = adapters or ADAPTERS

    def scrape(self, source: SourceRecord) -> list[RawScrapedItem]:
        adapter = self.adapters.get(source.adapter)
        if not adapter:
            raise ValueError(f"No adapter registered for: {source.adapter}")
        return adapter.fetch(source)
