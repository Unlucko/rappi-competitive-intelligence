import logging
import random
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

logger = logging.getLogger(__name__)


class BrowserManager:

    def __init__(
        self,
        headless: bool = True,
        user_agents: Optional[list[str]] = None,
        navigation_timeout_ms: int = 45000,
    ):
        self.headless = headless
        self.user_agents = user_agents or []
        self.navigation_timeout_ms = navigation_timeout_ms
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def start(self) -> None:
        logger.info("Launching Playwright Chromium browser (headless=%s)", self.headless)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

    async def create_context(self) -> BrowserContext:
        if self._browser is None:
            await self.start()

        selected_user_agent = random.choice(self.user_agents) if self.user_agents else None

        context_options = {
            "viewport": {"width": 1366, "height": 768},
            "locale": "es-MX",
            "timezone_id": "America/Mexico_City",
            "geolocation": {"latitude": 19.4326, "longitude": -99.1332},
            "permissions": ["geolocation"],
        }

        if selected_user_agent:
            context_options["user_agent"] = selected_user_agent

        context = await self._browser.new_context(**context_options)
        context.set_default_navigation_timeout(self.navigation_timeout_ms)
        context.set_default_timeout(self.navigation_timeout_ms)

        return context

    async def create_page(self, context: Optional[BrowserContext] = None) -> Page:
        if context is None:
            context = await self.create_context()

        page = await context.new_page()

        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        return page

    async def close_context(self, context: BrowserContext) -> None:
        try:
            await context.close()
        except Exception as close_error:
            logger.warning("Error closing browser context: %s", close_error)

    async def stop(self) -> None:
        if self._browser:
            try:
                await self._browser.close()
                logger.info("Browser closed successfully")
            except Exception as close_error:
                logger.warning("Error closing browser: %s", close_error)
            self._browser = None

        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as stop_error:
                logger.warning("Error stopping Playwright: %s", stop_error)
            self._playwright = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
        return False
