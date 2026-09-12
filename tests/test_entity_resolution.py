"""
Unit tests for deterministic entity resolution and canonicalization.
"""

from src.resolution.resolver import EntityResolver


def test_exact_and_alias_resolution():
    resolver = EntityResolver()

    # OpenAI test variants
    canon1, log1 = resolver.resolve_startup("OpenAI, Inc.")
    assert canon1 == "OpenAI"
    assert log1.confidence_score >= 0.98

    canon2, log2 = resolver.resolve_startup("Open AI")
    assert canon2 == "OpenAI"
    assert log2.confidence_score >= 0.98

    # Anthropic test variants
    canon3, log3 = resolver.resolve_startup("Anthropic PBC")
    assert canon3 == "Anthropic"
    assert log3.confidence_score >= 0.98

    # Mistral test variants
    canon4, log4 = resolver.resolve_startup("Mistral AI SAS")
    assert canon4 == "Mistral AI"
    assert log4.confidence_score >= 0.98

    # Hugging Face test variants
    canon5, log5 = resolver.resolve_startup("HuggingFace")
    assert canon5 == "Hugging Face"
    assert log5.confidence_score >= 0.98


def test_domain_based_resolution():
    resolver = EntityResolver()

    canon, log = resolver.resolve_startup("Messy Named Startup", website_url="https://www.openai.com/research")
    assert canon == "OpenAI"
    assert log.method_used == "DOMAIN_EXACT_MATCH"


def test_fuzzy_matching_resolution():
    resolver = EntityResolver()

    # Slight typographical noise
    canon, log = resolver.resolve_startup("Perplexity-AI Corp")
    assert canon == "Perplexity AI"
    assert log.confidence_score >= 0.85


def test_product_resolution():
    resolver = EntityResolver()

    clean_prod, canon_startup, log = resolver.resolve_product("ChatGPT Plus", "OpenAI, Inc.")
    assert clean_prod == "ChatGPT Plus"
    assert canon_startup == "OpenAI"
    assert log.entity_type == "PRODUCT"
