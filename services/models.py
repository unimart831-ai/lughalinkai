from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class Urgency(str, Enum):
    EMERGENCY = "emergency"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class SourceType(str, Enum):
    GOVERNMENT = "government"
    UN_AGENCY = "un_agency"
    NGO = "ngo"
    MEDIA = "media"


class ScrapeConfig(BaseModel):
    listing_url: Optional[str] = None
    article_selector: str = "article"
    title_selector: str = "h1"
    body_selector: str = ".entry-content"
    date_selector: str = "time"
    rate_limit_seconds: float = 2.0
    requires_psa_filter: bool = False
    link_href_contains: Optional[str] = None  # e.g. "/news/?" or "newsdetails"
    max_items: int = 50
    fetch_full_article: bool = False  # for RSS: follow link and extract title/body from HTML


class SourceRecord(BaseModel):
    source_id: str
    organization: str
    country: str = "Kenya"
    source_type: SourceType
    domains_covered: List[str]
    website: Optional[str] = None
    rss_feed: Optional[str] = None
    twitter_handle: Optional[str] = None
    primary_language: str = "en"
    secondary_languages: List[str] = Field(default_factory=list)
    trust_score: int = Field(ge=0, le=100)
    priority: str = "medium"
    adapter: str = "generic_html"
    scrape_config: ScrapeConfig = Field(default_factory=ScrapeConfig)
    robots_txt_respected: bool = True
    active: bool = True


class RawScrapedItem(BaseModel):
    source_id: str
    source_url: str
    title: str
    raw_html: Optional[str] = None
    raw_text: Optional[str] = None
    published_at: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)


class PSARecord(BaseModel):
    psa_id: str
    title: str
    text: str
    language: str
    domain: str
    sub_category: Optional[str] = None
    urgency: Urgency = Urgency.MEDIUM
    audience: List[str] = Field(default_factory=list)
    location: Dict[str, Any] = Field(default_factory=lambda: {"country": "Kenya"})
    organization: str
    published_at: Optional[datetime] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    source_id: str
    source_url: str
    trust_score: int
    verified: bool = False
    is_psa: bool = True
    classification_confidence: Optional[float] = None
    keywords: List[str] = Field(default_factory=list)
    token_count: int = 0
    content_hash: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: str = "active"


class ValidationResult(BaseModel):
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
