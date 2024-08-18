
from playwright.async_api import async_playwright
from .base_scraper import BaseScraper
from typing import Dict, Any, Optional

class PlaywrightScraper(BaseScraper):
    async def fetch_content(self, url: str, proxy: Optional[str] = None) -> str:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(proxy={"server": proxy} if proxy else None)
            page = await context.new_page()
            await page.goto(url)
            content = await page.content()
            await browser.close()
            return content

    async def extract(self, content: str) -> Dict[str, Any]:
        return {"raw_content": content}
