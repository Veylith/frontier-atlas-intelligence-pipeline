"""
Bulk AI Products Crawler extracting 1,000+ unique AI products and tools
with pricing models (FREE, FREEMIUM, PAID, ENTERPRISE), canonical parent company mapping,
and category enrichment.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Set

from src.models.schemas import (
    ProductEntity,
    ProductContent,
    PricingModelEnum,
    SourceMeta,
    current_iso_utc,
)
from src.crawlers.stealth_client import StealthClient
from src.config import config

logger = logging.getLogger("ProductsCrawler")


def determine_pricing_model(text: str) -> PricingModelEnum:
    """Intelligently infers pricing model enum from text / tags."""
    t = text.lower()
    if any(k in t for k in ["enterprise", "custom pricing", "contact sales", "quote"]):
        return PricingModelEnum.ENTERPRISE
    if any(k in t for k in ["freemium", "free tier", "free trial", "credits", "free plan"]):
        return PricingModelEnum.FREEMIUM
    if any(k in t for k in ["free", "open source", "mit license", "apache", "free to use"]):
        return PricingModelEnum.FREE
    if any(k in t for k in ["paid", "$", "subscription", "per month", "/mo", "pricing"]):
        return PricingModelEnum.PAID
    return PricingModelEnum.FREEMIUM


class ProductsCrawler:
    def __init__(self, client: Optional[StealthClient] = None):
        self.client = client or StealthClient(max_connections=30)

    async def fetch_huggingface_spaces(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Fetch real interactive AI applications and products from Hugging Face Spaces."""
        products = []
        url = f"https://huggingface.co/api/spaces?full=true&limit={limit}&sort=likes"
        try:
            spaces = await self.client.fetch_json(url)
            if isinstance(spaces, list):
                for sp in spaces:
                    space_id = sp.get("id", "")
                    if "/" in space_id:
                        org, prod_name = space_id.split("/", 1)
                    else:
                        org, prod_name = "Independent AI", space_id

                    card_data = sp.get("cardData", {}) or {}
                    title = card_data.get("title") or prod_name.replace("-", " ").title()
                    description = sp.get("description") or f"Interactive AI application: {title}"

                    products.append({
                        "product_name": title,
                        "startup_name": org.replace("-", " ").title(),
                        "pricing_model": PricingModelEnum.FREE,
                        "description": description,
                        "category": card_data.get("sdk", "Interactive AI App"),
                        "source_name": "Hugging Face Spaces",
                        "source_url": f"https://huggingface.co/spaces/{space_id}",
                        "website_url": f"https://huggingface.co/spaces/{space_id}",
                    })
        except Exception as e:
            logger.warning(f"HuggingFace spaces fetch error: {e}")
        return products

    async def fetch_curated_ai_tools(self) -> List[Dict[str, Any]]:
        """Fetch curated lists of AI products and SaaS tools from public datasets."""
        products = []
        urls = [
            "https://raw.githubusercontent.com/ai-collection/ai-tools-list/main/ai-tools.json",
            "https://raw.githubusercontent.com/steven2358/awesome-generative-ai/main/README.md",
            "https://raw.githubusercontent.com/mahseema/awesome-ai-tools/main/README.md",
            "https://raw.githubusercontent.com/eugeneyan/open-llms/main/README.md",
        ]

        # Fetch structured json tool catalogs
        catalog_urls = [
            "https://raw.githubusercontent.com/marcolardera/chatgpt-applications/main/apps.json",
            "https://raw.githubusercontent.com/SamurAIGPT/AI-Tools/main/ai_tools.json",
        ]

        for u in catalog_urls:
            try:
                data = await self.client.fetch_json(u)
                if isinstance(data, list):
                    for item in data:
                        p_name = item.get("name") or item.get("title")
                        if not p_name:
                            continue
                        pricing_str = item.get("pricing", "Freemium")
                        products.append({
                            "product_name": p_name.strip(),
                            "startup_name": item.get("company") or item.get("author") or p_name.strip(),
                            "pricing_model": determine_pricing_model(f"{pricing_str} {item.get('description', '')}"),
                            "description": item.get("description", f"AI productivity tool: {p_name}"),
                            "category": item.get("category", "Generative AI"),
                            "source_name": "AI Tool Directory",
                            "source_url": item.get("url") or item.get("link") or "https://frontieratlas.ai",
                            "website_url": item.get("url") or item.get("link"),
                        })
            except Exception:
                pass

        # Markdown scraping fallback for awesome repos
        for u in urls:
            try:
                md_text = await self.client.fetch(u)
                if isinstance(md_text, str):
                    import re
                    # Regex for [Tool Name](URL) - Description
                    matches = re.findall(r"-\s+\[([^\]]+)\]\((https?://[^\)]+)\)\s*[-:]?\s*([^\n\r]+)?", md_text)
                    for name, link, desc in matches:
                        if len(name) < 2 or "http" in name or name.lower() in ["license", "contributing", "readme"]:
                            continue
                        pricing = determine_pricing_model(desc or "")
                        # Try to deduce company from github or product name
                        company = name
                        if "github.com/" in link:
                            parts = link.split("github.com/")[1].split("/")
                            if len(parts) >= 2:
                                company = parts[0].replace("-", " ").title()

                        products.append({
                            "product_name": name.strip(),
                            "startup_name": company,
                            "pricing_model": pricing,
                            "description": (desc or f"AI Product & Tool: {name}").strip(),
                            "category": "AI Development & Productivity",
                            "source_name": "Curated AI Index",
                            "source_url": link,
                            "website_url": link,
                        })
            except Exception:
                pass

        return products

    async def fetch_huggingface_models(self, limit: int = 500) -> List[Dict[str, Any]]:
        """Fetch AI foundational models & enterprise inference products from Hugging Face."""
        products = []
        url = f"https://huggingface.co/api/models?limit={limit}&sort=downloads&direction=-1"
        try:
            models = await self.client.fetch_json(url)
            if isinstance(models, list):
                for m in models:
                    model_id = m.get("id", "")
                    if "/" in model_id:
                        org, name = model_id.split("/", 1)
                    else:
                        org, name = "Open Source Community", model_id
                    
                    pipeline = m.get("pipeline_tag", "foundation-model")
                    products.append({
                        "product_name": name.replace("-", " ").title(),
                        "startup_name": org.replace("-", " ").title(),
                        "pricing_model": PricingModelEnum.FREE,
                        "description": f"AI Foundation Model ({pipeline}): {model_id}",
                        "category": f"AI Model - {pipeline}",
                        "source_name": "Hugging Face Model Hub",
                        "source_url": f"https://huggingface.co/{model_id}",
                        "website_url": f"https://huggingface.co/{model_id}",
                    })
        except Exception as e:
            logger.warning(f"HuggingFace models fetch error: {e}")
        return products

    async def crawl(self, min_records: int = 1000) -> List[ProductEntity]:
        """Harvest and normalize 1,000+ unique AI Product entities."""
        logger.info(f"Starting Products crawl. Target: {min_records} products...")

        seen_names: Set[str] = set()
        entities: List[ProductEntity] = []

        spaces_task = self.fetch_huggingface_spaces(limit=600)
        models_task = self.fetch_huggingface_models(limit=600)
        tools_task = self.fetch_curated_ai_tools()

        results = await asyncio.gather(spaces_task, models_task, tools_task, return_exceptions=True)

        for res in results:
            if isinstance(res, list):
                for item in res:
                    raw_name = item.get("product_name", "").strip()
                    key = f"{raw_name.lower()}::{item.get('startup_name', '').lower()}"
                    if not raw_name or key in seen_names:
                        continue
                    seen_names.add(key)

                    prod_obj = ProductEntity(
                        source=SourceMeta(
                            name=item.get("source_name", "AI Product Catalog"),
                            url=item.get("source_url", "https://frontieratlas.ai"),
                        ),
                        content=ProductContent(
                            productName=raw_name,
                            startupName=item.get("startup_name", "Independent AI"),
                            pricingModel=item.get("pricing_model", PricingModelEnum.FREEMIUM),
                            description=item.get("description"),
                            category=item.get("category"),
                            website_url=item.get("website_url"),
                        )
                    )
                    entities.append(prod_obj)

        logger.info(f"Successfully harvested {len(entities)} unique Product entities.")
        return entities[:min_records]
