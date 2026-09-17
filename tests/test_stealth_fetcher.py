import pytest
from engine.config import DEFAULT_USER_AGENT
from engine.fetcher.base import FetchResult, BaseFetcher
from engine.fetcher.http_fetcher import HttpFetcher, HAS_CURL_CFFI
from engine.fetcher.smart_fetcher import SmartFetcher, is_cloudflare_or_blocked, is_spa_or_empty_content

def test_default_user_agent_clean():
    """Verify DEFAULT_USER_AGENT has no identifying bot signatures like Loomark/1.0."""
    assert "Loomark" not in DEFAULT_USER_AGENT
    assert "Mozilla/5.0" in DEFAULT_USER_AGENT
    assert "Chrome/" in DEFAULT_USER_AGENT

def test_is_cloudflare_or_blocked():
    """Verify Cloudflare and anti-bot challenge detection."""
    # 1. Cloudflare 5s challenge title
    cf_html = "<html><head><title>Just a moment...</title></head><body>Checking your browser before accessing site.</body></html>"
    assert is_cloudflare_or_blocked(200, cf_html) is True
    assert is_cloudflare_or_blocked(503, cf_html) is True

    # 2. Turnstile challenge marker
    turnstile_html = "<div class='cf-turnstile' data-sitekey='xxx'></div><script src='https://challenges.cloudflare.com/turnstile/v0/api.js'></script>"
    assert is_cloudflare_or_blocked(200, turnstile_html) is True

    # 3. Cloudflare server header with 403 Forbidden
    assert is_cloudflare_or_blocked(403, "Access Denied", {"server": "cloudflare"}) is True

    # 4. Normal 200 HTML should not trigger
    normal_html = "<html><head><title>My Blog</title></head><body><h1>Welcome</h1><p>Content goes here.</p></body></html>"
    assert is_cloudflare_or_blocked(200, normal_html, {"server": "nginx"}) is False

    # 5. Normal 404 should not trigger
    assert is_cloudflare_or_blocked(404, "Page Not Found", {"server": "nginx"}) is False

@pytest.mark.asyncio
async def test_http_fetcher_curl_cffi_integration():
    """Verify HttpFetcher uses curl_cffi when available, with headers and cookies."""
    fetcher = HttpFetcher(timeout_seconds=10)
    assert HAS_CURL_CFFI is True

    # Test cookie update and headers
    fetcher.update_cookies({"cf_clearance": "mock_clearance_123"})
    assert fetcher.session_cookies["cf_clearance"] == "mock_clearance_123"

    # Test real fetch on example.com
    res = await fetcher.fetch("https://example.com")
    assert res.status_code == 200
    assert "Example Domain" in res.text
    assert res.is_browser_rendered is False
    await fetcher.close()

class MockBrowserFetcher(BaseFetcher):
    def __init__(self):
        self.called_urls = []

    async def fetch(self, url: str, **kwargs) -> FetchResult:
        self.called_urls.append(url)
        return FetchResult(
            url=url,
            status_code=200,
            text="<html><body>Rendered after Cloudflare Challenge</body></html>",
            cookies={"cf_clearance": "cleared_cookie_val_abc"},
            is_browser_rendered=True
        )

@pytest.mark.asyncio
async def test_smart_fetcher_escalation_and_cookie_sync():
    """Verify SmartFetcher escalates on Cloudflare block and saves clearance cookie."""
    # Create an HttpFetcher that simulates CF 403 challenge
    http_mock = HttpFetcher()
    async def mock_cf_fetch(url, **kwargs):
        return FetchResult(
            url=url,
            status_code=403,
            headers={"server": "cloudflare"},
            text="<title>Just a moment...</title> Checking your browser...",
            is_browser_rendered=False
        )
    http_mock.fetch = mock_cf_fetch

    mock_browser = MockBrowserFetcher()
    smart = SmartFetcher(http_fetcher=http_mock, browser_fetcher=mock_browser)

    url = "https://protected-site.com/data"
    result = await smart.fetch(url)

    # Escalated to browser
    assert result.status_code == 200
    assert result.is_browser_rendered is True
    assert "Rendered after Cloudflare" in result.text
    assert url in mock_browser.called_urls

    # Cookies should be stored for the domain
    domain_cookies = smart.get_domain_cookies(url)
    assert domain_cookies.get("cf_clearance") == "cleared_cookie_val_abc"
    # Cookies should be synchronized to http_fetcher
    assert http_mock.session_cookies.get("cf_clearance") == "cleared_cookie_val_abc"
