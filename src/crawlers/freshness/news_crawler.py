"""
24-Hour Freshness AI News Crawler monitoring 5 premier AI news sources.
Extracts full-text content, normalizes publication timestamps, and enforces strict 24-hour freshness.
"""

import asyncio
import hashlib
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from bs4 import BeautifulSoup
import feedparser

from src.models.schemas import NewsEntity, NewsContent, current_iso_utc
from src.crawlers.stealth_client import StealthClient
from src.crawlers.freshness.date_normalizer import DateNormalizer
from src.config import config

logger = logging.getLogger("NewsCrawler")

# 5 Distinct High-Authority AI News Sources
NEWS_SOURCES = [
    {
        "name": "TechCrunch AI",
        "feed_url": "https://techcrunch.com/category/artificial-intelligence/feed/",
        "site_url": "https://techcrunch.com/category/artificial-intelligence/",
    },
    {
        "name": "VentureBeat AI",
        "feed_url": "https://venturebeat.com/category/ai/feed/",
        "site_url": "https://venturebeat.com/category/ai/",
    },
    {
        "name": "The Verge AI",
        "feed_url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
        "site_url": "https://www.theverge.com/ai-artificial-intelligence",
    },
    {
        "name": "AI News Daily",
        "feed_url": "https://www.artificialintelligence-news.com/feed/",
        "site_url": "https://www.artificialintelligence-news.com/",
    },
    {
        "name": "ArXiv AI Announcements",
        "feed_url": "https://rss.arxiv.org/rss/cs.AI",
        "site_url": "https://arxiv.org/list/cs.AI/recent",
    },
]


class NewsCrawler:
    def __init__(self, client: Optional[StealthClient] = None):
        self.client = client or StealthClient(max_connections=20)
        self._content_hashes = set()

    def _extract_clean_text(self, html_content: str) -> str:
        """Extracts dense article body text by pruning navigation, ads, headers, and boilerplate."""
        if not html_content:
            return ""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            # Remove non-content elements
            for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "svg", "noscript"]):
                tag.decompose()

            # Find primary content container if available
            article_container = (
                soup.find("article")
                or soup.find("main")
                or soup.find(class_=lambda c: c and any(k in c.lower() for k in ["article-body", "post-content", "entry-content", "article-content"]))
                or soup
            )

            paragraphs = article_container.find_all(["p", "h2", "h3"])
            clean_paragraphs = [p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 30]

            if clean_paragraphs:
                return "\n\n".join(clean_paragraphs)
            return " ".join(article_container.get_text().split())
        except Exception as e:
            logger.debug(f"Full-text extraction failed: {e}")
            return ""

    async def fetch_article_full_text(self, url: str) -> Tuple[str, Optional[datetime]]:
        """Asynchronously fetches and parses the full article text and meta date."""
        try:
            html = await self.client.fetch(url)
            if isinstance(html, str):
                full_text = self._extract_clean_text(html)
                html_date = DateNormalizer.extract_from_html(html)
                return full_text, html_date
        except Exception as e:
            logger.debug(f"Could not fetch full text for {url}: {e}")
        return "", None

    async def crawl_source(self, source_meta: Dict[str, str]) -> List[NewsEntity]:
        """Crawls a single news source, extracts full text, and filters strictly to <24h."""
        source_name = source_meta["name"]
        feed_url = source_meta["feed_url"]
        logger.info(f"Crawling 24-hr fresh AI news from {source_name}...")

        fresh_entities = []

        try:
            feed_content = await self.client.fetch(feed_url)
            if not isinstance(feed_content, str):
                return []

            parsed_feed = feedparser.parse(feed_content)
            entries = parsed_feed.entries[:25]

            async def process_entry(entry: Any) -> Optional[NewsEntity]:
                title = entry.get("title", "").strip()
                link = entry.get("link") or entry.get("id", "")
                summary = entry.get("summary") or entry.get("description", "")
                summary_clean = BeautifulSoup(summary, "html.parser").get_text().strip() if summary else title
                raw_pub_date = entry.get("published") or entry.get("updated") or entry.get("pubDate")

                if not link or not title:
                    return None

                content_hash = hashlib.sha256(f"{title}::{link}".encode()).hexdigest()
                if content_hash in self._content_hashes:
                    return None
                self._content_hashes.add(content_hash)

                is_fresh, iso_date, parsed_dt = DateNormalizer.normalize_and_validate_freshness(
                    raw_date=raw_pub_date,
                    max_hours=config.freshness_window_hours
                )

                # Fetch full-text content asynchronously if fresh or date check needed
                full_text = summary_clean
                try:
                    fetched_text, html_date = await asyncio.wait_for(self.fetch_article_full_text(link), timeout=6.0)
                    if fetched_text:
                        full_text = fetched_text
                    if not is_fresh and html_date:
                        is_fresh, iso_date, _ = DateNormalizer.normalize_and_validate_freshness(
                            raw_date=html_date,
                            max_hours=config.freshness_window_hours
                        )
                except Exception:
                    pass

                if not is_fresh:
                    return None

                return NewsEntity(
                    content=NewsContent(
                        title=title,
                        summary=summary_clean[:300] if len(summary_clean) > 300 else summary_clean,
                        full_text=full_text,
                        source_name=source_name,
                        source_url=link,
                        published_date=iso_date,
                        author=entry.get("author"),
                        tags=[t.get("term") for t in entry.get("tags", []) if isinstance(t, dict)] if "tags" in entry else ["AI", "Tech"],
                    )
                )

            tasks = [process_entry(e) for e in entries]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, NewsEntity):
                    fresh_entities.append(r)

        except Exception as e:
            logger.error(f"Error crawling news source {source_name}: {e}")

        logger.info(f"Source {source_name}: Found {len(fresh_entities)} guaranteed 24-hr fresh news articles.")
        return fresh_entities

    async def crawl(self) -> List[NewsEntity]:
        """Harvests full-text, verified 24-hour fresh AI news articles across all 5 sources."""
        logger.info("Starting Phase II: High-Fidelity 24-Hour Fresh AI News Ingestion...")
        tasks = [self.crawl_source(src) for src in NEWS_SOURCES]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_news: List[NewsEntity] = []
        for res in results:
            if isinstance(res, list):
                all_news.extend(res)

        logger.info(f"Successfully harvested {len(all_news)} total 24-hour fresh AI news articles.")
        return all_news
