"""
Deterministic Entity Resolution Engine for Startups and Products.
Implements rule-based normalizers, domain matching, fuzzy string similarity (Jaro-Winkler/Token Sort),
and generates audit trail mapping logs.
"""

import re
import logging
from typing import Tuple, Optional, List, Dict, Any
from urllib.parse import urlparse
from rapidfuzz import fuzz, distance

from src.models.schemas import EntityMappingLog, current_iso_utc
from src.resolution.seed_db import CANONICAL_AI_STARTUPS

logger = logging.getLogger("EntityResolver")

# Suffixes and corporate designations to strip
LEGAL_SUFFIXES = [
    r",?\s*\binc\.?\b",
    r",?\s*\bllc\.?\b",
    r",?\s*\bltd\.?\b",
    r",?\s*\bcorp\.?\b",
    r",?\s*\bcorporation\b",
    r",?\s*\bpbc\b",
    r",?\s*\bpublic benefit corporation\b",
    r",?\s*\bgmbh\b",
    r",?\s*\bsas\b",
    r",?\s*\bb\.v\.?\b",
    r",?\s*\bpte\.?\s*ltd\.?\b",
    r",?\s*\bco\.?\b",
    r",?\s*\bcompany\b",
    r",?\s*\btechnologies\b",
    r",?\s*\blabs\b",
    r",?\s*\bsystems\b",
    r",?\s*\bgroup\b",
]

SUFFIX_REGEX = re.compile("|".join(LEGAL_SUFFIXES), re.IGNORECASE)


class EntityResolver:
    def __init__(self, seed_kb: Optional[Dict[str, Dict[str, Any]]] = None):
        self.seed_kb = seed_kb or CANONICAL_AI_STARTUPS
        self._build_lookup_index()

    def _build_lookup_index(self):
        """Builds fast lookup tables for exact names, aliases, normalized strings, and domains."""
        self.alias_to_canonical: Dict[str, str] = {}
        self.normalized_to_canonical: Dict[str, str] = {}
        self.domain_to_canonical: Dict[str, str] = {}
        self.product_to_startup: Dict[str, str] = {}

        for canonical_name, data in self.seed_kb.items():
            # Canonical name itself
            self.alias_to_canonical[canonical_name.lower()] = canonical_name
            norm_name = self.normalize_string(canonical_name)
            self.normalized_to_canonical[norm_name] = canonical_name

            # Aliases
            for alias in data.get("aliases", []):
                self.alias_to_canonical[alias.lower()] = canonical_name
                norm_alias = self.normalize_string(alias)
                self.normalized_to_canonical[norm_alias] = canonical_name

            # Domains
            for domain in data.get("domains", []):
                clean_dom = domain.lower().replace("www.", "")
                self.domain_to_canonical[clean_dom] = canonical_name

            # Flagship products
            for prod in data.get("flagship_products", []):
                self.product_to_startup[prod.lower()] = canonical_name

    @staticmethod
    def normalize_string(text: str) -> str:
        """Strips legal suffixes, punctuation, and extraneous whitespace."""
        if not text:
            return ""
        # 1. Remove legal suffixes
        cleaned = SUFFIX_REGEX.sub("", text)
        # 2. Remove punctuation except internal alphanumeric
        cleaned = re.sub(r"[^\w\s]", " ", cleaned)
        # 3. Collapse whitespace and lowercase
        cleaned = " ".join(cleaned.lower().split())
        return cleaned

    @staticmethod
    def extract_domain(url: str) -> Optional[str]:
        """Extracts clean base domain from a URL."""
        if not url:
            return None
        try:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url
            parsed = urlparse(url)
            netloc = parsed.netloc.lower().replace("www.", "")
            return netloc.split(":")[0] if netloc else None
        except Exception:
            return None

    def resolve_startup(
        self,
        raw_name: str,
        source_url: str = "",
        website_url: str = "",
        fuzzy_threshold: float = 0.85,
    ) -> Tuple[str, EntityMappingLog]:
        """
        Resolves a raw startup name to its canonical form and returns the resolution audit log.
        Returns: (canonical_name: str, mapping_log: EntityMappingLog)
        """
        raw_clean = raw_name.strip()
        raw_lower = raw_clean.lower()
        norm_raw = self.normalize_string(raw_clean)

        # 1. Exact Seed / Alias Match
        if raw_lower in self.alias_to_canonical:
            canonical = self.alias_to_canonical[raw_lower]
            log = EntityMappingLog(
                raw_name=raw_clean,
                canonical_name=canonical,
                entity_type="STARTUP",
                confidence_score=1.0,
                method_used="EXACT_SEED_OR_ALIAS",
                matched_alias=raw_clean,
                source_url=source_url or website_url or "https://frontieratlas.ai",
            )
            return canonical, log

        # 2. Normalized Rule Match
        if norm_raw in self.normalized_to_canonical:
            canonical = self.normalized_to_canonical[norm_raw]
            log = EntityMappingLog(
                raw_name=raw_clean,
                canonical_name=canonical,
                entity_type="STARTUP",
                confidence_score=0.98,
                method_used="RULE_NORMALIZED_MATCH",
                matched_alias=norm_raw,
                source_url=source_url or website_url or "https://frontieratlas.ai",
            )
            return canonical, log

        # 3. Domain Matching
        for u in [website_url, source_url]:
            dom = self.extract_domain(u)
            if dom and dom in self.domain_to_canonical:
                canonical = self.domain_to_canonical[dom]
                log = EntityMappingLog(
                    raw_name=raw_clean,
                    canonical_name=canonical,
                    entity_type="STARTUP",
                    confidence_score=0.95,
                    method_used="DOMAIN_EXACT_MATCH",
                    matched_alias=dom,
                    source_url=u,
                )
                return canonical, log

        # 4. Fuzzy Matching against Known Seed Canonical Names & Aliases
        best_match = None
        best_score = 0.0
        best_alias = None

        for alias_clean, canonical in self.alias_to_canonical.items():
            # RapidFuzz Token Sort Ratio
            score_token = fuzz.token_sort_ratio(norm_raw, self.normalize_string(alias_clean)) / 100.0
            # Jaro-Winkler Similarity
            score_jw = distance.JaroWinkler.similarity(norm_raw, self.normalize_string(alias_clean))
            composite_score = max(score_token, score_jw)

            if composite_score > best_score:
                best_score = composite_score
                best_match = canonical
                best_alias = alias_clean

        if best_match and best_score >= fuzzy_threshold:
            log = EntityMappingLog(
                raw_name=raw_clean,
                canonical_name=best_match,
                entity_type="STARTUP",
                confidence_score=round(best_score, 4),
                method_used="FUZZY_STRING_SIMILARITY",
                matched_alias=best_alias,
                source_url=source_url or website_url or "https://frontieratlas.ai",
            )
            return best_match, log

        # 5. Fallback: Clean string formatting for non-seed entities
        clean_fallback = SUFFIX_REGEX.sub("", raw_clean).strip(" ,.-")
        if not clean_fallback:
            clean_fallback = raw_clean

        log = EntityMappingLog(
            raw_name=raw_clean,
            canonical_name=clean_fallback,
            entity_type="STARTUP",
            confidence_score=0.80,
            method_used="CANONICAL_RULE_STRIP",
            matched_alias=None,
            source_url=source_url or website_url or "https://frontieratlas.ai",
        )
        return clean_fallback, log

    def resolve_product(
        self,
        raw_product_name: str,
        raw_startup_name: str = "",
        source_url: str = "",
    ) -> Tuple[str, str, EntityMappingLog]:
        """Resolves a product entity and associates it with its canonical startup."""
        canonical_startup, _ = self.resolve_startup(raw_startup_name, source_url)
        clean_prod = re.sub(r"[^\w\s\-\.]", "", raw_product_name).strip()

        # Check if product is known flagship
        prod_lower = clean_prod.lower()
        if prod_lower in self.product_to_startup:
            canonical_startup = self.product_to_startup[prod_lower]

        log = EntityMappingLog(
            raw_name=raw_product_name,
            canonical_name=clean_prod,
            entity_type="PRODUCT",
            confidence_score=0.92,
            method_used="PRODUCT_NORMALIZATION",
            matched_alias=canonical_startup,
            source_url=source_url or "https://frontieratlas.ai",
        )
        return clean_prod, canonical_startup, log
