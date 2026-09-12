"""
Unit tests for token bucket rate limiter and full jitter backoff (429 handling).
"""

import asyncio
import pytest
from src.llm.rate_limiter import TokenBucketRateLimiter, FullJitterBackoff


@pytest.mark.asyncio
async def test_token_bucket_acquire():
    limiter = TokenBucketRateLimiter(capacity=5, refill_rate_per_sec=10.0)
    # Acquiring within capacity should be immediate
    await limiter.acquire(3)
    assert limiter.tokens <= 2.1


def test_full_jitter_delay_range():
    backoff = FullJitterBackoff(base_delay=1.0, max_delay=16.0)

    for attempt in range(1, 6):
        delay = backoff.calculate_delay(attempt)
        assert 0.1 <= delay <= min(16.0, 1.0 * (2 ** (attempt - 1)))


def test_respects_explicit_retry_after():
    backoff = FullJitterBackoff()
    delay = backoff.calculate_delay(attempt=1, retry_after=5.0)
    assert 5.0 <= delay <= 5.6
