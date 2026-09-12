"""
Unit tests for data schemas and validation models.
"""

import pytest
from pydantic import ValidationError
from src.models.schemas import (
    StartupEntity,
    ProductEntity,
    ResearchPaperEntity,
    JobEntity,
    NewsEntity,
    EntityMappingLog,
    PricingModelEnum,
    SourceMeta,
    StartupContent,
    StartupData,
    ProductContent,
    ResearchPaperContent,
    JobContent,
    NewsContent,
)


def test_startup_schema_valid():
    startup = StartupEntity(
        source=SourceMeta(name="Y Combinator", url="https://ycombinator.com/companies/openai"),
        content=StartupContent(
            entityName="OpenAI",
            data=StartupData(
                employeeCount=1500,
                description="AI research and deployment company",
                website="https://openai.com",
                foundedYear=2015,
                categories=["AI", "LLM"],
                headquarters="San Francisco, CA",
            )
        )
    )
    assert startup.recordType == "STARTUP"
    assert startup.content.entityName == "OpenAI"
    assert startup.content.data.employeeCount == 1500


def test_product_schema_valid():
    product = ProductEntity(
        source=SourceMeta(name="ProductHunt", url="https://producthunt.com/posts/claude-3-5"),
        content=ProductContent(
            productName="Claude 3.5 Sonnet",
            startupName="Anthropic",
            pricingModel=PricingModelEnum.FREEMIUM,
            description="State of the art intelligence model",
            category="AI Assistant",
            website_url="https://claude.ai",
        )
    )
    assert product.recordType == "PRODUCT"
    assert product.content.pricingModel == PricingModelEnum.FREEMIUM


def test_research_paper_schema_valid():
    paper = ResearchPaperEntity(
        content=ResearchPaperContent(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer", "Niki Parmar"],
            paper_url="https://arxiv.org/abs/1706.03762",
            github_url="https://github.com/tensorflow/tensor2tensor",
            github_stars=12500,
            published_date="2017-06-12T00:00:00Z",
            primary_category="cs.CL",
        )
    )
    assert paper.recordType == "RESEARCH_PAPER"
    assert paper.content.github_stars == 12500


def test_job_schema_valid():
    job = JobEntity(
        content=JobContent(
            company="Mistral AI",
            title="Senior ML Infrastructure Engineer",
            date="2026-09-12T12:00:00Z",
            is_remote=True,
            role_family="AI / Machine Learning Engineering",
            source_url="https://remoteok.com/remote-jobs/12345",
            location="Paris / Remote",
        )
    )
    assert job.recordType == "JOB"
    assert job.content.is_remote is True


def test_news_schema_valid():
    news = NewsEntity(
        content=NewsContent(
            title="OpenAI announces next frontier milestone",
            summary="New reasoning capabilities unveiled.",
            full_text="Today OpenAI announced groundbreaking new architectures...",
            source_name="TechCrunch AI",
            source_url="https://techcrunch.com/2026/09/12/openai-announcement",
            published_date="2026-09-12T14:00:00Z",
            tags=["AI", "OpenAI"],
        )
    )
    assert news.recordType == "NEWS"
    assert news.content.source_name == "TechCrunch AI"


def test_invalid_record_type_raises():
    with pytest.raises(ValidationError):
        StartupEntity(
            recordType="INVALID_TYPE",
            source=SourceMeta(name="Test", url="https://test.com"),
            content=StartupContent(entityName="Test")
        )
