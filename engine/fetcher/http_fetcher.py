import time
import logging
from typing import Dict, Optional, Any
from engine.config import DEFAULT_USER_AGENT
from engine.fetcher.base import BaseFetcher, FetchResult

logger = logging.getLogger(__name__)

try:
    from curl_cffi.requests import AsyncSession
    HAS_CURL_CFFI = True
except ImportError:
    HAS_CURL_CFFI = False
    AsyncSession = None

import httpx

class HttpFetcher(BaseFetcher):
    """
    High-performance async HTTP fetcher with browser TLS/JA3/HTTP2 fingerprint
    impersonation via curl_cffi, connection pooling, redirect handling, and
    automatic fallback to httpx.
    """
    MAX_BODY_SIZE = 20 * 1024 * 1024  # 20 MB

    def __init__(self, timeout_seconds: int = 20, proxy: Optional[str] = None,
                 custom_headers: Optional[Dict[str, str]] = None,
                 verify_ssl: bool = False,
                 impersonate: str = "chrome131"):
        self.timeout_seconds = timeout_seconds
        self.proxy = proxy
        self.verify_ssl = verify_ssl
        self.impersonate = impersonate
        self.headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Sec-Ch-Ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        if custom_headers:
            self.headers.update(custom_headers)

        self._curl_session = None
        self._httpx_client: Optional[httpx.AsyncClient] = None
        self.session_cookies: Dict[str, str] = {}

    def update_cookies(self, cookies: Dict[str, str]):
        """Update active session cookies (e.g. cf_clearance obtained from browser)."""
        if cookies:
            self.session_cookies.update(cookies)
            if self._curl_session and hasattr(self._curl_session, "cookies"):
                for k, v in cookies.items():
                    self._curl_session.cookies.set(k, v)

    async def get_curl_session(self):
        if self._curl_session is None:
            self._curl_session = AsyncSession(
                impersonate=self.impersonate,
                verify=self.verify_ssl,
                timeout=self.timeout_seconds,
                proxy=self.proxy
            )
            if self.session_cookies:
                for k, v in self.session_cookies.items():
                    self._curl_session.cookies.set(k, v)
        return self._curl_session

    async def get_httpx_client(self) -> httpx.AsyncClient:
        if self._httpx_client is None or self._httpx_client.is_closed:
            self._httpx_client = httpx.AsyncClient(
                headers=self.headers,
                timeout=httpx.Timeout(self.timeout_seconds, connect=10.0),
                proxy=self.proxy,
                follow_redirects=True,
                verify=self.verify_ssl,
                http2=False
            )
        return self._httpx_client

    async def fetch(self, url: str, cookies: Optional[Dict[str, str]] = None, **kwargs) -> FetchResult:
        if HAS_CURL_CFFI:
            try:
                return await self._fetch_curl(url, cookies=cookies, **kwargs)
            except Exception as e:
                logger.warning(f"curl_cffi fetch failed for {url} ({e}), falling back to httpx")

        return await self._fetch_httpx(url, cookies=cookies, **kwargs)

    async def _fetch_curl(self, url: str, cookies: Optional[Dict[str, str]] = None, **kwargs) -> FetchResult:
        session = await self.get_curl_session()
        start = time.monotonic()
        req_cookies = dict(self.session_cookies)
        if cookies:
            req_cookies.update(cookies)

        resp = await session.get(
            url,
            headers=self.headers,
            cookies=req_cookies if req_cookies else None,
            timeout=self.timeout_seconds,
            allow_redirects=True
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        raw_bytes = resp.content or b""

        if len(raw_bytes) > self.MAX_BODY_SIZE:
            return FetchResult(
                url=str(resp.url),
                status_code=resp.status_code,
                headers=dict(resp.headers),
                response_time_ms=elapsed_ms,
                error=f"Resource exceeds size limit ({len(raw_bytes)} bytes)"
            )

        encoding = resp.encoding
        if not encoding or encoding.lower() in ("iso-8859-1", "ascii"):
            try:
                text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                text = raw_bytes.decode("gb18030", errors="replace")
        else:
            try:
                text = raw_bytes.decode(encoding, errors="replace")
            except Exception:
                text = raw_bytes.decode("utf-8", errors="replace")

        res_cookies = dict(resp.cookies)
        if res_cookies:
            self.session_cookies.update(res_cookies)

        content_type = resp.headers.get("content-type", "text/html").lower()
        return FetchResult(
            url=str(resp.url),
            status_code=resp.status_code,
            headers=dict(resp.headers),
            text=text,
            raw_bytes=raw_bytes,
            response_time_ms=elapsed_ms,
            content_type=content_type,
            cookies=res_cookies,
            is_browser_rendered=False
        )

    async def _fetch_httpx(self, url: str, cookies: Optional[Dict[str, str]] = None, **kwargs) -> FetchResult:
        client = await self.get_httpx_client()
        start = time.monotonic()
        req_cookies = dict(self.session_cookies)
        if cookies:
            req_cookies.update(cookies)

        try:
            async with client.stream("GET", url, cookies=req_cookies if req_cookies else None) as resp:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                content_type = resp.headers.get("content-type", "text/html").lower()
                content_length = resp.headers.get("content-length")

                if content_length and int(content_length) > self.MAX_BODY_SIZE:
                    return FetchResult(
                        url=str(resp.url),
                        status_code=resp.status_code,
                        headers=dict(resp.headers),
                        response_time_ms=elapsed_ms,
                        content_type=content_type,
                        error=f"Resource exceeds size limit ({content_length} bytes)"
                    )

                chunks = []
                total_bytes = 0
                async for chunk in resp.aiter_bytes(chunk_size=65536):
                    total_bytes += len(chunk)
                    if total_bytes > self.MAX_BODY_SIZE:
                        return FetchResult(
                            url=str(resp.url),
                            status_code=resp.status_code,
                            headers=dict(resp.headers),
                            response_time_ms=elapsed_ms,
                            content_type=content_type,
                            error=f"Resource exceeds size limit ({self.MAX_BODY_SIZE} bytes)"
                        )
                    chunks.append(chunk)

                raw_bytes = b"".join(chunks)
                encoding = resp.encoding
                if not encoding or encoding.lower() in ("iso-8859-1", "ascii"):
                    try:
                        text = raw_bytes.decode("utf-8")
                    except UnicodeDecodeError:
                        text = raw_bytes.decode("gb18030", errors="replace")
                else:
                    try:
                        text = raw_bytes.decode(encoding, errors="replace")
                    except Exception:
                        text = raw_bytes.decode("utf-8", errors="replace")

                res_cookies = dict(resp.cookies)
                if res_cookies:
                    self.session_cookies.update(res_cookies)

                return FetchResult(
                    url=str(resp.url),
                    status_code=resp.status_code,
                    headers=dict(resp.headers),
                    text=text,
                    raw_bytes=raw_bytes,
                    response_time_ms=elapsed_ms,
                    content_type=content_type,
                    cookies=res_cookies,
                    is_browser_rendered=False
                )
        except Exception as e:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return FetchResult(
                url=url,
                status_code=0,
                response_time_ms=elapsed_ms,
                error=str(e)
            )

    async def close(self):
        if self._curl_session:
            try:
                await self._curl_session.close()
            except Exception:
                pass
            self._curl_session = None

        if self._httpx_client and not self._httpx_client.is_closed:
            await self._httpx_client.aclose()
            self._httpx_client = None

