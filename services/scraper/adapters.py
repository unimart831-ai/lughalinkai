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

    def __init__(self):
        self.skip_urls: set = set()

    def fetch(self, source: SourceRecord) -> list[RawScrapedItem]:
        config = source.scrape_config
        if not config.listing_url:
            return []

        self._check_robots(source, config.listing_url)
        items: list[RawScrapedItem] = []
        seen_links: set[str] = set()
        pages = max(1, config.max_listing_pages)

        with httpx.Client(timeout=30, follow_redirects=True, verify=_ssl_verify()) as client:
            for page in range(pages):
                listing_url = config.listing_url
                if page > 0:
                    sep = "&" if "?" in listing_url else "?"
                    listing_url = f"{listing_url}{sep}{config.page_param}={page}"

                try:
                    listing_html = client.get(listing_url).text
                except httpx.HTTPError:
                    continue

                soup = BeautifulSoup(listing_html, "lxml")
                links = self._extract_article_links(soup, config, listing_url)

                for link in links:
                    if link in seen_links:
                        continue
                    if config.listing_url and link.rstrip("/") == config.listing_url.rstrip("/"):
                        continue
                    if link in self.skip_urls:
                        seen_links.add(link)
                        continue
                    seen_links.add(link)
                    if len(items) >= max(1, config.max_items):
                        return items

                    time.sleep(config.rate_limit_seconds)
                    try:
                        resp = client.get(link)
                        resp.raise_for_status()
                    except httpx.HTTPError:
                        continue

                    article_soup = BeautifulSoup(resp.text, "lxml")
                    title_el = self._select_first(article_soup, config.title_selector)
                    _body_el, body = self._select_body(article_soup, config.body_selector)
                    date_el = self._select_first(article_soup, config.date_selector)

                    title = title_el.get_text(strip=True) if title_el else "Untitled"
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

    def _select_first(self, soup: BeautifulSoup, selector: str):
        """Try comma-separated selectors in listed preference order."""
        for part in [p.strip() for p in (selector or "").split(",") if p.strip()]:
            el = soup.select_one(part)
            if el:
                return el
        return None

    def _select_body(self, soup: BeautifulSoup, selector: str) -> tuple:
        best_el = None
        best_text = ""
        for part in [p.strip() for p in (selector or "").split(",") if p.strip()]:
            el = soup.select_one(part)
            if not el:
                continue
            text = el.get_text("\n", strip=True)
            if len(text.split()) >= 10:
                return el, text
            if len(text.split()) > len(best_text.split()):
                best_el, best_text = el, text
        return best_el, best_text

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
            slug = full.rstrip("/").split("/")[-1]
            if config.link_min_slug_chars and len(slug) < config.link_min_slug_chars:
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

        config = source.scrape_config
        feed = feedparser.parse(source.rss_feed)
        items: list[RawScrapedItem] = []
        limit = max(1, config.max_items)

        with httpx.Client(timeout=30, follow_redirects=True, verify=_ssl_verify()) as client:
            for entry in feed.entries[:limit]:
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                text = BeautifulSoup(summary, "lxml").get_text("\n", strip=True)
                title = getattr(entry, "title", "Untitled")
                link = getattr(entry, "link", "")
                raw_html = None

                # Optional: open the article page and extract full body (better than short RSS blurb)
                if config.fetch_full_article and link:
                    time.sleep(config.rate_limit_seconds)
                    try:
                        resp = client.get(link)
                        resp.raise_for_status()
                        raw_html = resp.text
                        article_soup = BeautifulSoup(resp.text, "lxml")
                        title_el = None
                        body_el = None
                        for part in [p.strip() for p in (config.title_selector or "h1").split(",") if p.strip()]:
                            title_el = article_soup.select_one(part)
                            if title_el:
                                break
                        for part in [p.strip() for p in (config.body_selector or "article").split(",") if p.strip()]:
                            cand = article_soup.select_one(part)
                            if cand and len(cand.get_text(" ", strip=True).split()) >= 10:
                                body_el = cand
                                break
                        if title_el:
                            title = title_el.get_text(strip=True) or title
                        if body_el:
                            body = body_el.get_text("\n", strip=True)
                            if len(body.split()) >= 10:
                                text = body
                    except httpx.HTTPError:
                        pass
                else:
                    time.sleep(config.rate_limit_seconds)

                if len(text.split()) < 10:
                    continue

                published_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6])

                items.append(
                    RawScrapedItem(
                        source_id=source.source_id,
                        source_url=link,
                        title=title,
                        raw_html=raw_html,
                        raw_text=text,
                        published_at=published_at,
                    )
                )
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

    def scrape(self, source: SourceRecord, skip_urls: Optional[set] = None) -> list[RawScrapedItem]:
        adapter = self.adapters.get(source.adapter)
        if not adapter:
            raise ValueError(f"No adapter registered for: {source.adapter}")
        if skip_urls and hasattr(adapter, "skip_urls"):
            adapter.skip_urls = skip_urls
        try:
            return adapter.fetch(source)
        finally:
            if hasattr(adapter, "skip_urls"):
                adapter.skip_urls = set()
