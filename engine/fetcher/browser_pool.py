import asyncio
import logging
from typing import Optional, Tuple
from engine.config import DEFAULT_USER_AGENT

logger = logging.getLogger(__name__)

class BrowserPool:
    """
    Playwright Browser Pool (PRD Section 9.2-9.3, 18-19, 100)
    Maintains a reusable headless Chromium browser instance with isolated BrowserContexts
    to handle dynamic JavaScript SPA pages and infinite scroll without spawning a new browser per URL.
    """
    def __init__(self, max_concurrent: int = 4, headless: bool = True):
        self.max_concurrent = max_concurrent
        self.headless = headless
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._playwright = None
        self._browser = None
        self._lock = asyncio.Lock()
        self.is_initialized = False

    async def initialize(self) -> bool:
        if self.is_initialized and self._browser and self._browser.is_connected():
            return True

        async with self._lock:
            if self.is_initialized and self._browser and self._browser.is_connected():
                return True
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=self.headless,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-gpu",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--no-first-run",
                        "--no-service-autorun",
                        "--password-store=basic"
                    ]
                )
                self.is_initialized = True
                logger.info("Playwright BrowserPool initialized successfully.")
                return True
            except Exception as e:
                logger.warning(f"BrowserPool initialization failed (Playwright or Chromium missing): {e}")
                self.is_initialized = False
                return False

    async def acquire_page(self, user_agent: Optional[str] = None) -> Tuple[any, any]:
        """
        Acquire a slot from the pool and create an isolated context and page.
        Caller must call release_page(context, page) when finished.
        """
        await self._semaphore.acquire()
        context = None
        try:
            initialized = await self.initialize()
            if not initialized:
                raise RuntimeError("Playwright browser is unavailable or failed to launch.")

            context = await self._browser.new_context(
                user_agent=user_agent or DEFAULT_USER_AGENT,
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
                timezone_id="Asia/Shanghai"
            )
            await context.add_init_script("""
                // Hide webdriver flag
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Mock chrome object
                window.chrome = {
                    app: { isInstalled: false },
                    runtime: {},
                    csi: function() {},
                    loadTimes: function() {}
                };

                // Mock permissions
                if (window.navigator.permissions) {
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                }

                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [
                        { name: 'PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'Chrome PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                        { name: 'Chromium PDF Viewer', filename: 'internal-pdf-viewer', description: 'Portable Document Format' }
                    ]
                });

                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['zh-CN', 'zh', 'en']
                });
            """)
            page = await context.new_page()
            return context, page
        except Exception:
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
            self._semaphore.release()
            raise

    async def release_page(self, context, page):
        """Release the acquired page, close context, and free the semaphore slot."""
        try:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass
            if context:
                try:
                    await context.close()
                except Exception:
                    pass
        finally:
            self._semaphore.release()

    async def close(self):
        """Shutdown all browser resources and stop playwright."""
        async with self._lock:
            if self._browser:
                try:
                    await self._browser.close()
                except Exception:
                    pass
                self._browser = None
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
                self._playwright = None
            self.is_initialized = False
            logger.info("BrowserPool closed.")

# Global shared browser pool instance
global_browser_pool = BrowserPool(max_concurrent=4)
