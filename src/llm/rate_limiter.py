"""
Token Bucket Rate Limiter and Jittered Exponential Backoff for 429 Rate Limit Mitigation.
Enforces client-side rate limits and handles server 429 backoff gracefully.
"""

import asyncio
import random
import time
import logging
from typing import Optional

logger = logging.getLogger("RateLimiter")


class TokenBucketRateLimiter:
    """
    Token Bucket rate limiter ensuring request rate stays within provider limits.
    """
    def __init__(self, capacity: int = 60, refill_rate_per_sec: float = 10.0):
        self.capacity = capacity
        self.refill_rate = refill_rate_per_sec
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1):
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
                self.last_refill = now

                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return
                
                # Calculate sleep duration needed for refill
                deficit = tokens - self.tokens
                wait_time = deficit / self.refill_rate
                await asyncio.sleep(wait_time)


class FullJitterBackoff:
    """
    Full Jitter Exponential Backoff formula:
    Sleep = uniform(0, min(cap, base * 2 ^ attempt))
    Prevents thundering herd problems across distributed workers.
    """
    def __init__(self, base_delay: float = 1.0, max_delay: float = 32.0):
        self.base = base_delay
        self.cap = max_delay

    def calculate_delay(self, attempt: int, retry_after: Optional[float] = None) -> float:
        if retry_after is not None and retry_after > 0:
            # Respect server explicit Retry-After plus small jitter
            return retry_after + random.uniform(0.1, 0.5)
        
        exponential = self.base * (2 ** (attempt - 1))
        ceiling = min(self.cap, exponential)
        delay = random.uniform(0.1, ceiling)
        return delay

    async def sleep(self, attempt: int, retry_after: Optional[float] = None):
        delay = self.calculate_delay(attempt, retry_after)
        logger.warning(f"Backoff sleep: {delay:.2f}s (Attempt {attempt})")
        await asyncio.sleep(delay)
