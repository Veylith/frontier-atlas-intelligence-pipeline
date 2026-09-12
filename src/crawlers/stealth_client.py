"""
Stealth Async HTTP Client with User-Agent pool rotation, browser fingerprinting,
connection pooling, rate limiting, and exponential backoff with full jitter.
"""

import asyncio
import random
import logging
import time
from typing import Optional, Dict, Any, Union, List
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger("StealthClient")

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
]


class StealthClient:
    def __init__(
        self,
        max_connections: int = 50,
        timeout_seconds: int = 25,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        self.max_connections = max_connections
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds, connect=10)
        self.default_headers = default_headers or {}
        self._session: Optional[aiohttp.ClientSession] = None
        self._lock = asyncio.Lock()

    async def get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            async with self._lock:
                if self._session is None or self._session.closed:
                    connector = aiohttp.TCPConnector(
                        limit=self.max_connections,
                        ttl_dns_cache=300,
                        enable_cleanup_closed=True,
                        ssl=False,
                    )
                    self._session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=self.timeout,
                    )
        return self._session

    def _generate_headers(self, custom_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        ua = random.choice(USER_AGENTS)
        is_windows = "Windows" in ua
        is_mac = "Macintosh" in ua
        platform = '"Windows"' if is_windows else ('"macOS"' if is_mac else '"Linux"')

        headers = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Sec-Ch-Ua": '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": platform,
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0",
        }
        headers.update(self.default_headers)
        if custom_headers:
            headers.update(custom_headers)
        return headers

    async def fetch(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_body: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
        max_retries: int = 3,
        backoff_base: float = 1.5,
    ) -> Union[str, Dict[str, Any], bytes]:
        session = await self.get_session()
        req_headers = self._generate_headers(headers)

        for attempt in range(1, max_retries + 1):
            try:
                async with session.request(
                    method=method,
                    url=url,
                    headers=req_headers,
                    params=params,
                    json=json_body,
                    data=data,
                ) as response:
                    # Handle 429 Too Many Requests
                    if response.status == 429:
                        retry_after = response.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            wait_time = float(retry_after) + random.uniform(0.5, 2.0)
                        else:
                            # Exponential backoff with full jitter
                            wait_time = random.uniform(0, min(30.0, backoff_base * (2 ** attempt)))
                        logger.warning(f"Rate limited (429) on {url}. Backing off for {wait_time:.2f}s (Attempt {attempt}/{max_retries})")
                        await asyncio.sleep(wait_time)
                        continue

                    # Handle 5xx Server Errors
                    if response.status in (500, 502, 503, 504):
                        wait_time = random.uniform(0.5, backoff_base * (2 ** attempt))
                        logger.warning(f"Server error ({response.status}) on {url}. Retrying in {wait_time:.2f}s...")
                        await asyncio.sleep(wait_time)
                        continue

                    # If successful
                    if response.status in (200, 201):
                        content_type = response.headers.get("Content-Type", "").lower()
                        if "application/json" in content_type:
                            return await response.json()
                        return await response.text()

                    # Other status codes
                    logger.debug(f"HTTP {response.status} for {url}")
                    return await response.text()

            except (aiohttp.ClientError, asyncio.TimeoutError) as err:
                wait_time = random.uniform(0.5, backoff_base * (2 ** attempt))
                logger.warning(f"Network error on {url}: {err}. Retry {attempt}/{max_retries} in {wait_time:.2f}s")
                if attempt == max_retries:
                    logger.error(f"Exhausted retries for {url}: {err}")
                    raise
                await asyncio.sleep(wait_time)

        raise RuntimeError(f"Failed to fetch {url} after {max_retries} attempts.")

    async def fetch_json(self, url: str, **kwargs) -> Union[Dict[str, Any], List[Any]]:
        res = await self.fetch(url, **kwargs)
        if isinstance(res, (dict, list)):
            return res
        import json
        return json.loads(res)

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
