import asyncio
import time
import random
from typing import Dict

class DomainRateLimiter:
    """
    Manages per-domain concurrency limits and request intervals with jitter
    to protect target websites and comply with PRD Section 11.
    """
    def __init__(self, domain_concurrent: int = 3, domain_delay_ms: int = 500):
        self.domain_concurrent = max(1, domain_concurrent)
        self.domain_delay_seconds = domain_delay_ms / 1000.0
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._last_request_time: Dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def _get_semaphore(self, domain: str) -> asyncio.Semaphore:
        async with self._lock:
            if domain not in self._semaphores:
                self._semaphores[domain] = asyncio.Semaphore(self.domain_concurrent)
            return self._semaphores[domain]

    async def acquire(self, domain: str):
        """Acquire a concurrency slot for domain and enforce interval delay."""
        sem = await self._get_semaphore(domain)
        await sem.acquire()
        try:
            # Enforce polite delay between successive requests to the same domain
            now = time.monotonic()
            last_time = self._last_request_time.get(domain, 0.0)
            elapsed = now - last_time
            jitter = random.uniform(0.0, 0.1) * self.domain_delay_seconds
            required_delay = self.domain_delay_seconds + jitter

            if elapsed < required_delay:
                await asyncio.sleep(required_delay - elapsed)

            self._last_request_time[domain] = time.monotonic()
        except BaseException:
            sem.release()
            raise

    def release(self, domain: str):
        """Release concurrency slot for domain."""
        if domain in self._semaphores:
            self._semaphores[domain].release()
