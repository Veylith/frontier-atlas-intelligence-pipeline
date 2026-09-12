"""
24-Hour Freshness AI Jobs Crawler monitoring 5 distinct AI job boards.
Categorizes role families, detects remote eligibility, normalizes timestamps,
and enforces strict 24-hour freshness.
"""

import asyncio
import hashlib
import logging
import re
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import feedparser

from src.models.schemas import JobEntity, JobContent, current_iso_utc
from src.crawlers.stealth_client import StealthClient
from src.crawlers.freshness.date_normalizer import DateNormalizer
from src.config import config

logger = logging.getLogger("JobsCrawler")


def classify_role_family(title: str, description: str = "") -> str:
    """Classifies a job posting into standardized role family."""
    t = f"{title} {description}".lower()
    if any(k in t for k in ["research scientist", "research engineer", "ai researcher", "scientist", "phd"]):
        return "Research & Science"
    if any(k in t for k in ["ml engineer", "machine learning", "deep learning", "ai engineer", "llm engineer", "prompt engineer"]):
        return "AI / Machine Learning Engineering"
    if any(k in t for k in ["data engineer", "data platform", "analytics engineer", "database"]):
        return "Data Engineering"
    if any(k in t for k in ["product manager", "product lead", "pm ", "head of product"]):
        return "Product Management"
    if any(k in t for k in ["frontend", "backend", "full stack", "software engineer", "devops", "sre", "infrastructure"]):
        return "Software Engineering"
    if any(k in t for k in ["designer", "ui/ux", "product designer"]):
        return "Design & UX"
    return "Operations & Strategy"


class JobsCrawler:
    def __init__(self, client: Optional[StealthClient] = None):
        self.client = client or StealthClient(max_connections=20)
        self._seen_jobs = set()

    async def crawl_remoteok_ai(self) -> List[JobEntity]:
        """Fetch real AI jobs from RemoteOK API with strict <24h filter."""
        jobs = []
        url = "https://remoteok.com/api?tag=ai"
        try:
            data = await self.client.fetch_json(url)
            if isinstance(data, list):
                # The first element is often a legal disclaimer dict
                items = data[1:] if len(data) > 1 and "legal" in str(data[0]) else data
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    company = item.get("company", "").strip()
                    position = item.get("position", "").strip()
                    date_val = item.get("date")
                    job_url = item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id', '')}"

                    if not company or not position:
                        continue

                    is_fresh, iso_date, _ = DateNormalizer.normalize_and_validate_freshness(
                        raw_date=date_val,
                        max_hours=config.freshness_window_hours
                    )
                    if not is_fresh:
                        continue

                    job_obj = JobEntity(
                        content=JobContent(
                            company=company,
                            title=position,
                            date=iso_date,
                            is_remote=True,
                            role_family=classify_role_family(position, item.get("description", "")),
                            source_url=job_url,
                            location=item.get("location", "Remote"),
                            description_snippet=BeautifulSoup(item.get("description", ""), "html.parser").get_text()[:250],
                        )
                    )
                    jobs.append(job_obj)
        except Exception as e:
            logger.warning(f"RemoteOK crawl error: {e}")
        return jobs

    async def crawl_remotive_ai(self) -> List[JobEntity]:
        """Fetch real AI jobs from Remotive API with strict <24h filter."""
        jobs = []
        url = "https://remotive.com/api/remote-jobs?search=ai"
        try:
            data = await self.client.fetch_json(url)
            job_list = data.get("jobs", [])
            for item in job_list:
                company = item.get("company_name", "").strip()
                title = item.get("title", "").strip()
                date_val = item.get("publication_date")
                job_url = item.get("url", "")

                if not company or not title:
                    continue

                is_fresh, iso_date, _ = DateNormalizer.normalize_and_validate_freshness(
                    raw_date=date_val,
                    max_hours=config.freshness_window_hours
                )
                if not is_fresh:
                    continue

                job_obj = JobEntity(
                    content=JobContent(
                        company=company,
                        title=title,
                        date=iso_date,
                        is_remote=True,
                        role_family=classify_role_family(title, item.get("description", "")),
                        source_url=job_url,
                        location=item.get("candidate_required_location", "Remote"),
                        description_snippet=BeautifulSoup(item.get("description", ""), "html.parser").get_text()[:250],
                    )
                )
                jobs.append(job_obj)
        except Exception as e:
            logger.warning(f"Remotive crawl error: {e}")
        return jobs

    async def crawl_jobicy_ai(self) -> List[JobEntity]:
        """Fetch real AI jobs from Jobicy API with strict <24h filter."""
        jobs = []
        url = "https://jobicy.com/api/v2/remote-jobs?count=50&tag=ai"
        try:
            data = await self.client.fetch_json(url)
            job_list = data.get("jobs", [])
            for item in job_list:
                company = item.get("companyName", "").strip()
                title = item.get("jobTitle", "").strip()
                date_val = item.get("pubDate")
                job_url = item.get("url", "")

                if not company or not title:
                    continue

                is_fresh, iso_date, _ = DateNormalizer.normalize_and_validate_freshness(
                    raw_date=date_val,
                    max_hours=config.freshness_window_hours
                )
                if not is_fresh:
                    continue

                job_obj = JobEntity(
                    content=JobContent(
                        company=company,
                        title=title,
                        date=iso_date,
                        is_remote=True,
                        role_family=classify_role_family(title, item.get("jobDescription", "")),
                        source_url=job_url,
                        location=item.get("jobGeo", "Remote"),
                        description_snippet=BeautifulSoup(item.get("jobDescription", ""), "html.parser").get_text()[:250],
                    )
                )
                jobs.append(job_obj)
        except Exception as e:
            logger.warning(f"Jobicy crawl error: {e}")
        return jobs

    async def crawl_weworkremotely_ai(self) -> List[JobEntity]:
        """Fetch remote AI programming jobs from WeWorkRemotely RSS with strict <24h filter."""
        jobs = []
        url = "https://weworkremotely.com/categories/remote-programming-jobs.rss"
        try:
            feed_text = await self.client.fetch(url)
            if isinstance(feed_text, str):
                parsed = feedparser.parse(feed_text)
                for entry in parsed.entries:
                    raw_title = entry.get("title", "")
                    link = entry.get("link", "")
                    raw_date = entry.get("published")
                    summary = entry.get("summary", "")

                    if ":" in raw_title:
                        company, title = raw_title.split(":", 1)
                    else:
                        company, title = "Tech Startup", raw_title

                    # Check for AI relevance
                    combined = f"{title} {summary}".lower()
                    if not any(k in combined for k in ["ai", "machine learning", "ml", "data", "llm", "python", "neural"]):
                        continue

                    is_fresh, iso_date, _ = DateNormalizer.normalize_and_validate_freshness(
                        raw_date=raw_date,
                        max_hours=config.freshness_window_hours
                    )
                    if not is_fresh:
                        continue

                    job_obj = JobEntity(
                        content=JobContent(
                            company=company.strip(),
                            title=title.strip(),
                            date=iso_date,
                            is_remote=True,
                            role_family=classify_role_family(title, summary),
                            source_url=link,
                            location="Remote",
                            description_snippet=BeautifulSoup(summary, "html.parser").get_text()[:250],
                        )
                    )
                    jobs.append(job_obj)
        except Exception as e:
            logger.warning(f"WeWorkRemotely crawl error: {e}")
        return jobs

    async def crawl_himalayas_ai(self) -> List[JobEntity]:
        """Fetch fresh remote jobs from Himalayas RSS feed with strict <24h filter."""
        jobs = []
        url = "https://himalayas.app/jobs/rss"
        try:
            feed_text = await self.client.fetch(url)
            if isinstance(feed_text, str):
                parsed = feedparser.parse(feed_text)
                for entry in parsed.entries:
                    raw_title = entry.get("title", "")
                    link = entry.get("link", "")
                    raw_date = entry.get("published") or entry.get("updated")
                    summary = entry.get("summary", "")

                    if " at " in raw_title:
                        title, company = raw_title.rsplit(" at ", 1)
                    elif "-" in raw_title:
                        company, title = raw_title.split("-", 1)
                    else:
                        company, title = "Himalayas Startup", raw_title

                    # Check for AI relevance
                    combined = f"{title} {summary}".lower()
                    if not any(k in combined for k in ["ai", "machine learning", "ml", "engineer", "data", "llm"]):
                        continue

                    is_fresh, iso_date, _ = DateNormalizer.normalize_and_validate_freshness(
                        raw_date=raw_date,
                        max_hours=config.freshness_window_hours
                    )
                    if not is_fresh:
                        continue

                    job_obj = JobEntity(
                        content=JobContent(
                            company=company.strip(),
                            title=title.strip(),
                            date=iso_date,
                            is_remote=True,
                            role_family=classify_role_family(title, summary),
                            source_url=link,
                            location="Remote",
                            description_snippet=BeautifulSoup(summary, "html.parser").get_text()[:250],
                        )
                    )
                    jobs.append(job_obj)
        except Exception as e:
            logger.warning(f"Himalayas crawl error: {e}")
        return jobs

    async def crawl(self) -> List[JobEntity]:
        """Harvests verified 24-hour fresh AI job postings across all 5 job boards."""
        logger.info("Starting Phase II: High-Fidelity 24-Hour Fresh AI Jobs Ingestion...")

        tasks = [
            self.crawl_remoteok_ai(),
            self.crawl_remotive_ai(),
            self.crawl_jobicy_ai(),
            self.crawl_weworkremotely_ai(),
            self.crawl_himalayas_ai(),
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        all_jobs: List[JobEntity] = []

        for res in results:
            if isinstance(res, list):
                for job in res:
                    key = f"{job.content.company.lower()}::{job.content.title.lower()}"
                    if key not in self._seen_jobs:
                        self._seen_jobs.add(key)
                        all_jobs.append(job)

        logger.info(f"Successfully harvested {len(all_jobs)} guaranteed 24-hour fresh AI job postings.")
        return all_jobs
