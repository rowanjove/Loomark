import time
import asyncio
import logging
from typing import Optional
from engine.fetcher.base import BaseFetcher, FetchResult
from engine.fetcher.browser_pool import BrowserPool, global_browser_pool

logger = logging.getLogger(__name__)

class BrowserFetcher(BaseFetcher):
    """
    Browser Fetcher executing JavaScript dynamic rendering via Playwright (PRD Section 9.2, 18.3, 100).
    Renders SPA pages, waits for DOM completion, handles Cloudflare Turnstile/5s challenge,
    and extracts rendered HTML alongside cookies (including cf_clearance).
    """
    def __init__(self, pool: Optional[BrowserPool] = None, timeout_seconds: int = 25):
        self.pool = pool or global_browser_pool
        self.timeout_seconds = timeout_seconds

    async def fetch(self, url: str, user_agent: Optional[str] = None, **kwargs) -> FetchResult:
        start_time = time.monotonic()
        context = None
        page = None
        try:
            context, page = await self.pool.acquire_page(user_agent=user_agent)
            page.set_default_timeout(self.timeout_seconds * 1000)

            # Navigate to URL
            response = await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_seconds * 1000)

            # Check if Cloudflare or similar challenge is active
            try:
                title = await page.title()
                content = await page.content()
                if "just a moment" in title.lower() or "checking your browser" in content.lower() or "cf-browser-verification" in content.lower():
                    logger.info(f"Cloudflare challenge detected on {url}, waiting for resolution...")
                    for _ in range(16):  # Wait up to 8s for challenge resolution
                        await asyncio.sleep(0.5)
                        curr_title = await page.title()
                        if "just a moment" not in curr_title.lower():
                            content = await page.content()
                            break
            except Exception:
                pass

            # Briefly wait for dynamic JS framework hydration (e.g. Next.js, Vue, React)
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except Exception:
                pass # networkidle timeout is common on pages with background analytics, proceed safely

            content = await page.content()
            status_code = response.status if response else 200
            headers = response.headers if response else {}

            # Extract cookies (e.g., cf_clearance, session tokens)
            cookies_dict = {}
            try:
                cookies_list = await context.cookies()
                for c in cookies_list:
                    cookies_dict[c["name"]] = c["value"]
            except Exception:
                pass

            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            return FetchResult(
                url=page.url or url,
                status_code=status_code,
                headers=headers,
                text=content,
                raw_bytes=content.encode("utf-8", errors="replace"),
                response_time_ms=elapsed_ms,
                content_type="text/html",
                cookies=cookies_dict,
                is_browser_rendered=True
            )

        except Exception as e:
            elapsed_ms = int((time.monotonic() - start_time) * 1000)
            logger.warning(f"Browser fetch failed for {url}: {e}")
            return FetchResult(
                url=url,
                status_code=0,
                headers={},
                text="",
                raw_bytes=b"",
                response_time_ms=elapsed_ms,
                content_type="text/html",
                is_browser_rendered=True,
                error=str(e)
            )
        finally:
            if context or page:
                await self.pool.release_page(context, page)

    async def close(self):
        # Pool cleanup is handled at app lifespan level
        pass
