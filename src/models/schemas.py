"""
Data models and canonical schemas for FrontierAtlas Intelligence Graph.
Enforces strict schema validation, ISO-8601 timestamping, and exact field structure.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, HttpUrl, field_validator


def current_iso_utc() -> str:
    """Returns current UTC timestamp in ISO-8601 format."""
    return datetime.now(timezone.utc).isoformat()


class PricingModelEnum(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"


class SourceMeta(BaseModel):
    name: str = Field(..., description="Name of the source site")
    url: str = Field(..., description="Original source URL")


# ==========================================
# 1. STARTUP ENTITY SCHEMA
# ==========================================

class StartupData(BaseModel):
    employeeCount: Optional[int] = Field(None, description="Number of employees (if available)")
    description: Optional[str] = Field(None, description="Brief overview of the startup")
    website: Optional[str] = Field(None, description="Company website URL")
    foundedYear: Optional[int] = Field(None, description="Year founded")
    categories: Optional[List[str]] = Field(default_factory=list, description="Industry categories/tags")
    headquarters: Optional[str] = Field(None, description="Headquarters location")
    totalFunding: Optional[str] = Field(None, description="Total funding raised if known")


class StartupContent(BaseModel):
    entityName: str = Field(..., description="Canonical startup name")
    data: StartupData = Field(default_factory=StartupData)


class StartupEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Schema version")
    recordType: str = Field(default="STARTUP", description="Fixed to STARTUP")
    source: SourceMeta
    content: StartupContent
    collectedAt: str = Field(default_factory=current_iso_utc, description="ISO-8601 collection timestamp")

    @field_validator("recordType")
    def validate_record_type(cls, v):
        if v != "STARTUP":
            raise ValueError("recordType must be 'STARTUP'")
        return v


# ==========================================
# 2. PRODUCT ENTITY SCHEMA
# ==========================================

class ProductContent(BaseModel):
    productName: str = Field(..., description="Name of the product/tool")
    startupName: str = Field(..., description="Canonical parent startup name")
    pricingModel: PricingModelEnum = Field(..., description="FREE, FREEMIUM, PAID, ENTERPRISE")
    description: Optional[str] = Field(None, description="Product description")
    category: Optional[str] = Field(None, description="Primary product category")
    website_url: Optional[str] = Field(None, description="Product direct URL")
    features: Optional[List[str]] = Field(default_factory=list, description="Key features")


class ProductEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Schema version")
    recordType: str = Field(default="PRODUCT", description="Fixed to PRODUCT")
    source: SourceMeta
    content: ProductContent
    collectedAt: str = Field(default_factory=current_iso_utc, description="ISO-8601 collection timestamp")

    @field_validator("recordType")
    def validate_record_type(cls, v):
        if v != "PRODUCT":
            raise ValueError("recordType must be 'PRODUCT'")
        return v


# ==========================================
# 3. RESEARCH PAPER ENTITY SCHEMA
# ==========================================

class ResearchPaperContent(BaseModel):
    title: str = Field(..., description="Title of the research paper")
    authors: List[str] = Field(default_factory=list, description="List of author names")
    paper_url: str = Field(..., description="Link to the Arxiv/PDF page")
    github_url: Optional[str] = Field(None, description="Link to associated code repository")
    github_stars: int = Field(default=0, description="Current number of stars on GitHub repository")
    published_date: str = Field(..., description="ISO-8601 publication date")
    abstract: Optional[str] = Field(None, description="Paper abstract")
    primary_category: Optional[str] = Field(None, description="Primary subject domain")


class ResearchPaperEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Schema version")
    recordType: str = Field(default="RESEARCH_PAPER", description="Fixed to RESEARCH_PAPER")
    content: ResearchPaperContent
    collectedAt: str = Field(default_factory=current_iso_utc, description="ISO-8601 collection timestamp")

    @field_validator("recordType")
    def validate_record_type(cls, v):
        if v != "RESEARCH_PAPER":
            raise ValueError("recordType must be 'RESEARCH_PAPER'")
        return v


# ==========================================
# 4. JOB ENTITY SCHEMA
# ==========================================

class JobContent(BaseModel):
    company: str = Field(..., description="Canonical company name")
    title: str = Field(..., description="Job posting title")
    date: str = Field(..., description="ISO-8601 publication date (<24h fresh)")
    is_remote: bool = Field(default=False, description="Remote eligibility")
    role_family: str = Field(..., description="Functional category (e.g. Engineering, Research, Product)")
    source_url: str = Field(..., description="URL to the job listing")
    location: Optional[str] = Field(None, description="Location if specified")
    description_snippet: Optional[str] = Field(None, description="Summary snippet of the job requirements")


class JobEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Schema version")
    recordType: str = Field(default="JOB", description="Fixed to JOB")
    content: JobContent
    collectedAt: str = Field(default_factory=current_iso_utc, description="ISO-8601 collection timestamp")

    @field_validator("recordType")
    def validate_record_type(cls, v):
        if v != "JOB":
            raise ValueError("recordType must be 'JOB'")
        return v


# ==========================================
# 5. NEWS ENTITY SCHEMA
# ==========================================

class NewsContent(BaseModel):
    title: str = Field(..., description="News headline")
    summary: str = Field(..., description="Concise synopsis")
    full_text: str = Field(..., description="Full text content of the article")
    source_name: str = Field(..., description="News publisher name")
    source_url: str = Field(..., description="Direct article URL")
    published_date: str = Field(..., description="ISO-8601 publication timestamp (<24h fresh)")
    author: Optional[str] = Field(None, description="Article author")
    tags: Optional[List[str]] = Field(default_factory=list, description="Topic tags")


class NewsEntity(BaseModel):
    schemaVersion: str = Field(default="1.0", description="Schema version")
    recordType: str = Field(default="NEWS", description="Fixed to NEWS")
    content: NewsContent
    collectedAt: str = Field(default_factory=current_iso_utc, description="ISO-8601 collection timestamp")

    @field_validator("recordType")
    def validate_record_type(cls, v):
        if v != "NEWS":
            raise ValueError("recordType must be 'NEWS'")
        return v


# ==========================================
# 6. ENTITY MAPPING LOG SCHEMA
# ==========================================

class EntityMappingLog(BaseModel):
    raw_name: str = Field(..., description="Raw extracted entity name")
    canonical_name: str = Field(..., description="Canonical resolved entity name")
    entity_type: str = Field(..., description="STARTUP or PRODUCT")
    confidence_score: float = Field(..., description="Confidence score between 0.0 and 1.0")
    method_used: str = Field(..., description="Resolution method (EXACT_SEED, RULE_CLEAN, FUZZY_TOKEN_SORT, DOMAIN_MATCH, LLM)")
    matched_alias: Optional[str] = Field(None, description="The alias/seed matched against")
    source_url: str = Field(..., description="URL where raw entity was found")
    timestamp: str = Field(default_factory=current_iso_utc, description="ISO-8601 resolution timestamp")
