from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import stealth_async
from .base_scraper import BaseScraper
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import random
import logging
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

class ScraperConfig:
    def __init__(self,
                 use_stealth: bool = True,
                 simulate_human: bool = False,
                 use_custom_headers: bool = True,
                 hide_webdriver: bool = True,
                 bypass_cloudflare: bool = True,
                 headless: bool = True,
                 debug: bool = False,
                 timeout: int = 60000,
                 wait_for: str = 'networkidle'):
        self.use_stealth = use_stealth
        self.simulate_human = simulate_human
        self.use_custom_headers = use_custom_headers
        self.hide_webdriver = hide_webdriver
        self.bypass_cloudflare = bypass_cloudflare
        self.headless = headless
        self.debug = debug
        self.timeout = timeout
        self.wait_for = wait_for

class PlaywrightScraper(BaseScraper):
    def __init__(self, config: ScraperConfig = ScraperConfig()):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
        self.config = config

    async def fetch_content(self, url: str, proxy: Optional[str] = None, pages: Optional[str] = None, url_pattern: Optional[str] = None) -> List[str]:
        async with async_playwright() as p:
            browser = await self.launch_browser(p, proxy)
            context = await self.create_context(browser, proxy)
            page = await context.new_page()
            
            if self.config.use_stealth:
                await stealth_async(page)
            await self.set_browser_features(page)
            
            try:
                contents = await self.scrape_multiple_pages(page, url, pages, url_pattern)
            except Exception as e:
                self.logger.error(f"Error during scraping: {str(e)}")
                contents = [f"Error: {str(e)}"]
            finally:
                if self.config.debug:
                    self.logger.info("Scraping completed. Keeping browser open for debugging.")
                    await asyncio.sleep(30)  # Keep the browser open for 30 seconds
                await browser.close()
            
            return contents

    async def scrape_multiple_pages(self, page: Page, base_url: str, pages: Optional[str] = None, url_pattern: Optional[str] = None) -> List[str]:
        if not url_pattern:
            url_pattern = self.detect_url_pattern(base_url)
            if not url_pattern:
                return ["Error: Unable to detect URL pattern. Please provide a pattern."]

        page_numbers = self.parse_page_numbers(pages)
        contents = []

        for page_num in page_numbers:
            current_url = self.apply_url_pattern(base_url, url_pattern, page_num)
            self.logger.info(f"Scraping page {page_num}: {current_url}")
            
            content = await self.navigate_and_get_content(page, current_url)
            if self.config.bypass_cloudflare and "Cloudflare" in content and "ray ID" in content.lower():
                self.logger.info("Cloudflare detected, attempting to bypass...")
                content = await self.bypass_cloudflare(page, current_url)
            
            contents.append(content)
            
            # Add a delay between page navigations
            await asyncio.sleep(random.uniform(1, 3))

        return contents

    async def launch_browser(self, playwright, proxy: Optional[str] = None) -> Browser:
        return await playwright.chromium.launch(
            headless=self.config.headless,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-infobars',
                  '--window-position=0,0', '--ignore-certifcate-errors',
                  '--ignore-certifcate-errors-spki-list'],
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
        if self.config.use_custom_headers:
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
        if self.config.hide_webdriver:
            await page.evaluate('''
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                })
            ''')

    async def navigate_and_get_content(self, page: Page, url: str) -> str:
        await page.goto(url, wait_until=self.config.wait_for, timeout=self.config.timeout)
        if self.config.simulate_human:
            await self.simulate_human_behavior(page)
        else:
            await asyncio.sleep(2)  # Wait for 2 seconds to ensure content is loaded
        return await page.content()

    async def bypass_cloudflare(self, page: Page, url: str) -> str:
        max_retries = 3
        for _ in range(max_retries):
            await page.reload(wait_until=self.config.wait_for, timeout=self.config.timeout)
            if self.config.simulate_human:
                await self.simulate_human_behavior(page)
            else:
                await asyncio.sleep(2)
            
            content = await page.content()
            if "Cloudflare" not in content or "ray ID" not in content.lower():
                self.logger.info("Successfully bypassed Cloudflare")
                return content
            
            self.logger.info("Cloudflare still detected, retrying...")
        
        self.logger.warning("Failed to bypass Cloudflare after multiple attempts")
        return content

    async def simulate_human_behavior(self, page: Page):
        # Scrolling behavior
        await page.evaluate('window.scrollBy(0, window.innerHeight / 2)')
        await asyncio.sleep(random.uniform(0.5, 1))

        # Mouse movement behavior
        for _ in range(2):
            x = random.randint(100, 500)
            y = random.randint(100, 500)
            await page.mouse.move(x, y)
            await asyncio.sleep(random.uniform(0.1, 0.3))

        # Hover over a random element (without clicking)
        elements = await page.query_selector_all('a, button, input, select')
        if elements:
            random_element = random.choice(elements)
            await random_element.hover()
            await asyncio.sleep(random.uniform(0.3, 0.7))

    def detect_url_pattern(self, url: str) -> Optional[str]:
        parsed_url = urlparse(url)
        query = parse_qs(parsed_url.query)

        # Check query parameters for any numeric values
        for param, value in query.items():
            if value and value[0].isdigit():
                return f"{param}={{{param}}}"

        # Check path for numeric segments
        path_parts = parsed_url.path.split('/')
        for i, part in enumerate(path_parts):
            if part.isdigit():
                path_parts[i] = "{page}"
                return '/'.join(path_parts)

        # If no pattern is detected, return None
        return None

    def apply_url_pattern(self, base_url: str, pattern: str, page_num: int) -> str:
        parsed_url = urlparse(base_url)
        if '=' in pattern:  # Query parameter pattern
            query = parse_qs(parsed_url.query)
            param, value = pattern.split('=')
            query[param] = [value.format(**{param: page_num})]
            return urlunparse(parsed_url._replace(query=urlencode(query, doseq=True)))
        else:  # Path pattern
            return urlunparse(parsed_url._replace(path=pattern.format(page=page_num)))

    def parse_page_numbers(self, pages: Optional[str]) -> List[int]:
        if not pages:
            return [1]  # Default to first page if not specified
        
        page_numbers = []
        for part in pages.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                page_numbers.extend(range(start, end + 1))
            else:
                page_numbers.append(int(part))
        
        return sorted(set(page_numbers))  # Remove duplicates and sort

    async def extract(self, content: str) -> Dict[str, Any]:
        return {"raw_content": content}