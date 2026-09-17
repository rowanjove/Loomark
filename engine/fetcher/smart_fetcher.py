import re
import logging
from typing import Optional, Dict
from urllib.parse import urlparse
from engine.fetcher.base import BaseFetcher, FetchResult
from engine.fetcher.http_fetcher import HttpFetcher

logger = logging.getLogger(__name__)

SPA_MARKERS = [
    re.compile(r'<div\s+id=["\'](?:app|root|__next|main)["\']\s*>\s*</div>', re.IGNORECASE),
    re.compile(r'you need to enable javascript to run this app', re.IGNORECASE),
    re.compile(r'requires javascript', re.IGNORECASE),
    re.compile(r'window\.__INITIAL_STATE__\s*=', re.IGNORECASE)
]

CF_CHALLENGE_MARKERS = [
    re.compile(r'<title>[^<]*Just a moment\.\.\.[^<]*</title>', re.IGNORECASE),
    re.compile(r'checking your browser before accessing', re.IGNORECASE),
    re.compile(r'cf-browser-verification', re.IGNORECASE),
    re.compile(r'challenges\.cloudflare\.com', re.IGNORECASE),
    re.compile(r'turnstile', re.IGNORECASE),
    re.compile(r'<title>[^<]*Attention Required! \| Cloudflare[^<]*</title>', re.IGNORECASE),
    re.compile(r'ray id: [0-9a-f]{16}', re.IGNORECASE),
]

def is_spa_or_empty_content(html: str) -> bool:
    """
    Detect if the fetched HTML is an empty client-rendered SPA
    requiring browser JavaScript execution.
    """
    if not html or len(html.strip()) < 100:
        return True

    # Strip script and style tags to gauge actual human-readable body content
    no_script = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    clean_text = re.sub(r'<[^>]+>', ' ', no_script).strip()

    # If text is extremely short and SPA markers are present
    if len(clean_text) < 150:
        for marker in SPA_MARKERS:
            if marker.search(html):
                return True

    return False

def is_cloudflare_or_blocked(status_code: int, html: str, headers: Optional[Dict[str, str]] = None) -> bool:
    """
    Detect if the HTTP response is a Cloudflare anti-bot challenge, Turnstile, or WAF block.
    """
    headers = headers or {}
    server = headers.get("server", "").lower()

    if status_code in (403, 503):
        if "cloudflare" in server:
            return True
        for marker in CF_CHALLENGE_MARKERS:
            if marker.search(html):
                return True

    if html:
        for marker in CF_CHALLENGE_MARKERS:
            if marker.search(html):
                return True

    return False

class SmartFetcher(BaseFetcher):
    """
    Smart Mode Fetcher (PRD Section 18-19):
    Performs fast HTTP fetch first (with TLS impersonation via curl_cffi).
    If page is detected to be an unrendered JavaScript SPA, empty container,
    or blocked by Cloudflare anti-bot challenges / 403 / 503, it automatically
    escalates to stealth Playwright BrowserFetcher to resolve the challenge,
    capture cf_clearance and session cookies, and synchronize cookies back
    to HttpFetcher for fast future crawls on the domain.
    """
    def __init__(self, http_fetcher: Optional[HttpFetcher] = None,
                 browser_fetcher: Optional[BaseFetcher] = None):
        self.http_fetcher = http_fetcher or HttpFetcher()
        if browser_fetcher is not None:
            self.browser_fetcher = browser_fetcher
        else:
            try:
                from engine.fetcher.browser_fetcher import BrowserFetcher
                self.browser_fetcher = BrowserFetcher()
            except Exception:
                self.browser_fetcher = None
        self.domain_cookies: Dict[str, Dict[str, str]] = {}

    def get_domain_cookies(self, url: str) -> Dict[str, str]:
        netloc = urlparse(url).netloc
        return self.domain_cookies.get(netloc, {})

    def save_domain_cookies(self, url: str, cookies: Dict[str, str]):
        if not cookies:
            return
        netloc = urlparse(url).netloc
        if netloc not in self.domain_cookies:
            self.domain_cookies[netloc] = {}
        self.domain_cookies[netloc].update(cookies)
        if hasattr(self.http_fetcher, "update_cookies"):
            self.http_fetcher.update_cookies(cookies)

    async def fetch(self, url: str, **kwargs) -> FetchResult:
        # Apply cached domain cookies if available
        cached_cookies = self.get_domain_cookies(url)
        if cached_cookies and "cookies" not in kwargs:
            kwargs["cookies"] = cached_cookies

        result = await self.http_fetcher.fetch(url, **kwargs)

        # 1. Check if blocked by Cloudflare or WAF
        is_cf_blocked = is_cloudflare_or_blocked(result.status_code, result.text or "", result.headers)

        # 2. Check if SPA empty content
        is_spa = result.status_code == 200 and result.text and is_spa_or_empty_content(result.text)

        if is_cf_blocked or is_spa:
            if self.browser_fetcher is not None:
                logger.info(f"SmartFetcher escalating {url} to browser (status={result.status_code}, CF={is_cf_blocked}, SPA={is_spa})")
                browser_res = await self.browser_fetcher.fetch(url, **kwargs)
                if browser_res.status_code != 0:
                    if browser_res.cookies:
                        self.save_domain_cookies(url, browser_res.cookies)
                    return browser_res

        if result.cookies:
            self.save_domain_cookies(url, result.cookies)

        return result

    async def close(self):
        await self.http_fetcher.close()
        if self.browser_fetcher and hasattr(self.browser_fetcher, "close"):
            await self.browser_fetcher.close()
