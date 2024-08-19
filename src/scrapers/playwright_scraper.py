from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth_async
from .base_scraper import BaseScraper
from typing import Dict, Any, Optional
import asyncio
import random
import logging

class PlaywrightScraper(BaseScraper):
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    async def fetch_content(self, url: str, proxy: Optional[str] = None) -> str:
        async with async_playwright() as p:
            browser = await self.launch_browser(p, proxy)
            context = await self.create_context(browser, proxy)
            page = await context.new_page()
            
            await stealth_async(page)
            await self.set_browser_features(page)
            
            try:
                content = await self.navigate_and_get_content(page, url)
                if "Cloudflare" in content and "ray ID" in content.lower():
                    self.logger.info("Cloudflare detected, attempting to bypass...")
                    content = await self.bypass_cloudflare(page, url)
            except Exception as e:
                self.logger.error(f"Error during scraping: {str(e)}")
                content = f"Error: {str(e)}"
            finally:
                await browser.close()
            
            return content

    async def launch_browser(self, playwright, proxy: Optional[str] = None) -> Browser:
        return await playwright.chromium.launch(
            headless=True,  # Set to False for GUI
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-infobars',
                  '--window-position=0,0', '--ignore-certifcate-errors',
                  '--ignore-certifcate-errors-spki-list', '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'],
            proxy={'server': proxy} if proxy else None
        )

    async def create_context(self, browser: Browser, proxy: Optional[str] = None) -> BrowserContext:
        return await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            proxy={'server': proxy} if proxy else None,
            java_script_enabled=True,
            ignore_https_errors=True
        )

    async def set_browser_features(self, page: Page):
        await page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1'
        })
        await page.evaluate('''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        ''')

    async def navigate_and_get_content(self, page: Page, url: str) -> str:
        await page.goto(url, wait_until='networkidle', timeout=60000)
        await self.simulate_human_behavior(page)
        await asyncio.sleep(random.uniform(3, 7))
        return await page.content()

    async def bypass_cloudflare(self, page: Page, url: str) -> str:
        max_retries = 3
        for _ in range(max_retries):
            await page.reload(wait_until='networkidle', timeout=60000)
            await self.simulate_human_behavior(page)
            await asyncio.sleep(random.uniform(5, 10))
            
            content = await page.content()
            if "Cloudflare" not in content or "ray ID" not in content.lower():
                self.logger.info("Successfully bypassed Cloudflare")
                return content
            
            self.logger.info("Cloudflare still detected, retrying...")
        
        self.logger.warning("Failed to bypass Cloudflare after multiple attempts")
        return content

    async def simulate_human_behavior(self, page: Page):
        for _ in range(random.randint(2, 5)):
            await page.evaluate('window.scrollBy(0, window.innerHeight / 2)')
            await asyncio.sleep(random.uniform(0.5, 2))

        for _ in range(random.randint(3, 7)):
            await page.mouse.move(random.randint(100, 500), random.randint(100, 500))
            await asyncio.sleep(random.uniform(0.1, 0.5))

        try:
            await page.mouse.click(random.randint(100, 500), random.randint(100, 500))
        except:
            pass

    async def extract(self, content: str) -> Dict[str, Any]:
        return {"raw_content": content}