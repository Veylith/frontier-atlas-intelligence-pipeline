"""
Precision Date Normalizer and 24-Hour Freshness Validator.
Handles ISO-8601, RFC 2822, Unix timestamps, HTML microdata (JSON-LD, OpenGraph, <time>),
relative human timestamps ('2 hours ago', '45m ago', 'yesterday'), and fallback heuristics.
"""

import re
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Any
from bs4 import BeautifulSoup
import dateutil.parser

logger = logging.getLogger("DateNormalizer")

# Regex patterns for relative time
RELATIVE_TIME_PATTERNS = [
    (re.compile(r"(\d+)\s*(?:seconds?|secs?|s)\s*ago", re.IGNORECASE), lambda m: timedelta(seconds=int(m.group(1)))),
    (re.compile(r"(\d+)\s*(?:minutes?|mins?|m)\s*ago", re.IGNORECASE), lambda m: timedelta(minutes=int(m.group(1)))),
    (re.compile(r"(\d+)\s*(?:hours?|hrs?|h)\s*ago", re.IGNORECASE), lambda m: timedelta(hours=int(m.group(1)))),
    (re.compile(r"(\d+)\s*(?:days?|d)\s*ago", re.IGNORECASE), lambda m: timedelta(days=int(m.group(1)))),
    (re.compile(r"just\s*now", re.IGNORECASE), lambda m: timedelta(seconds=10)),
    (re.compile(r"an?\s*hour\s*ago", re.IGNORECASE), lambda m: timedelta(hours=1)),
    (re.compile(r"yesterday", re.IGNORECASE), lambda m: timedelta(days=1)),
    (re.compile(r"today", re.IGNORECASE), lambda m: timedelta(hours=2)),
]


class DateNormalizer:
    @staticmethod
    def now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @classmethod
    def parse_relative_date(cls, text: str, ref_time: Optional[datetime] = None) -> Optional[datetime]:
        """Parses human relative string into UTC datetime."""
        if not text:
            return None
        clean_text = text.strip()
        ref = ref_time or cls.now_utc()

        for pattern, delta_fn in RELATIVE_TIME_PATTERNS:
            match = pattern.search(clean_text)
            if match:
                delta = delta_fn(match)
                return ref - delta
        return None

    @classmethod
    def parse_iso_or_rfc(cls, date_str: str) -> Optional[datetime]:
        """Parses ISO-8601 or RFC-2822 date string with timezone awareness."""
        if not date_str:
            return None
        clean_str = date_str.strip()

        # Handle unix timestamps
        if clean_str.isdigit() and len(clean_str) in (10, 13):
            ts = int(clean_str)
            if len(clean_str) == 13:
                ts /= 1000.0
            return datetime.fromtimestamp(ts, tz=timezone.utc)

        try:
            dt = dateutil.parser.parse(clean_str)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            else:
                dt = dt.astimezone(timezone.utc)
            return dt
        except Exception:
            return None

    @classmethod
    def extract_from_html(cls, html_content: str) -> Optional[datetime]:
        """Extracts publication date from JSON-LD, OpenGraph, or HTML <time> tags."""
        if not html_content:
            return None

        try:
            soup = BeautifulSoup(html_content, "html.parser")

            # 1. Check JSON-LD metadata
            for script in soup.find_all("script", type="application/ld+json"):
                if script.string:
                    try:
                        data = json.loads(script.string)
                        items = data if isinstance(data, list) else [data]
                        for item in items:
                            pub_date = item.get("datePublished") or item.get("uploadDate") or item.get("dateModified")
                            if pub_date:
                                dt = cls.parse_iso_or_rfc(pub_date)
                                if dt:
                                    return dt
                    except Exception:
                        pass

            # 2. Check meta tags (OpenGraph, Article, Dublin Core)
            meta_properties = [
                ("meta", {"property": "article:published_time"}),
                ("meta", {"property": "og:published_time"}),
                ("meta", {"name": "publication_date"}),
                ("meta", {"name": "date"}),
                ("meta", {"name": "dc.date"}),
                ("meta", {"name": "sailthru.date"}),
                ("meta", {"itemprop": "datePublished"}),
            ]
            for tag_name, attrs in meta_properties:
                tag = soup.find(tag_name, attrs)
                if tag and tag.get("content"):
                    dt = cls.parse_iso_or_rfc(tag["content"])
                    if dt:
                        return dt

            # 3. Check <time> tag with datetime attribute
            time_tag = soup.find("time")
            if time_tag:
                dt_val = time_tag.get("datetime") or time_tag.text
                if dt_val:
                    dt = cls.parse_iso_or_rfc(dt_val) or cls.parse_relative_date(dt_val)
                    if dt:
                        return dt

        except Exception as e:
            logger.debug(f"HTML date extraction failed: {e}")

        return None

    @classmethod
    def normalize_and_validate_freshness(
        cls,
        raw_date: Any,
        html_fallback: Optional[str] = None,
        max_hours: float = 24.0,
        ref_time: Optional[datetime] = None,
    ) -> Tuple[bool, str, Optional[datetime]]:
        """
        Normalizes any date representation into ISO-8601 UTC string and checks if within last 24 hours.
        Returns: (is_fresh: bool, iso_string: str, parsed_datetime: Optional[datetime])
        """
        ref = ref_time or cls.now_utc()
        parsed_dt: Optional[datetime] = None

        if isinstance(raw_date, datetime):
            parsed_dt = raw_date if raw_date.tzinfo else raw_date.replace(tzinfo=timezone.utc)
        elif isinstance(raw_date, str):
            # Try relative date first
            parsed_dt = cls.parse_relative_date(raw_date, ref)
            if not parsed_dt:
                # Try ISO / RFC parser
                parsed_dt = cls.parse_iso_or_rfc(raw_date)

        # Fallback to HTML extraction
        if not parsed_dt and html_fallback:
            parsed_dt = cls.extract_from_html(html_fallback)

        if not parsed_dt:
            # Fallback: if totally missing, return current time but flag for heuristic validation
            return False, ref.isoformat(), None

        age_hours = (ref - parsed_dt).total_seconds() / 3600.0
        # Check freshness: published within max_hours (and not in distant future)
        is_fresh = -1.0 <= age_hours <= max_hours

        return is_fresh, parsed_dt.isoformat(), parsed_dt
