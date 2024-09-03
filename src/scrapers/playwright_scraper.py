from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from .base_scraper import BaseScraper
from typing import Dict, Any, Optional, List, Tuple
import asyncio
import random
import logging
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import platform
import subprocess
import time
import os
import tempfile

class ScraperConfig:
    def __init__(self,
                 use_stealth: bool = True,
                 simulate_human: bool = False,
                 use_custom_headers: bool = True,
                 hide_webdriver: bool = True,
                 bypass_cloudflare: bool = True,
                 headless: bool = True,
                 debug: bool = False,
                 timeout: int = 30000,
                 wait_for: str = 'domcontentloaded',
                 use_current_browser: bool = False,
                 max_retries: int = 3,
                 delay_after_load: int = 2):
        self.use_stealth = use_stealth
        self.simulate_human = simulate_human
        self.use_custom_headers = use_custom_headers
        self.hide_webdriver = hide_webdriver
        self.bypass_cloudflare = bypass_cloudflare
        self.headless = headless
        self.debug = debug
        self.timeout = timeout
        self.wait_for = wait_for
        self.use_current_browser = use_current_browser
        self.max_retries = max_retries
        self.delay_after_load = delay_after_load

class PlaywrightScraper(BaseScraper):
    def __init__(self, config: ScraperConfig = ScraperConfig()):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
        self.config = config
        self.chrome_process = None
        self.temp_user_data_dir = None

    async def fetch_content(self, url: str, proxy: Optional[str] = None, pages: Optional[str] = None, url_pattern: Optional[str] = None, handle_captcha: bool = False) -> List[str]:
        async with async_playwright() as p:
            if self.config.use_current_browser:
                browser = await self.launch_and_connect_to_chrome(p)
            else:
                browser = await self.launch_browser(p, proxy, handle_captcha)

            try:
                context = await self.create_context(browser, proxy)
                page = await context.new_page()

                if self.config.use_stealth:
                    await self.apply_stealth_settings(page)
                await self.set_browser_features(page)

                if handle_captcha:
                    await self.handle_captcha(page, url)
                
                contents = await self.scrape_multiple_pages(page, url, pages, url_pattern)
            except Exception as e:
                self.logger.error(f"Error during scraping: {str(e)}")
                contents = [f"Error: {str(e)}"]
            finally:
                if not self.config.use_current_browser:
                    await browser.close()
                    self.logger.info("Browser closed after scraping.")

        return contents

    async def handle_captcha(self, page: Page, url: str):
        self.logger.info("Waiting for user to solve CAPTCHA...")
        await page.goto(url, wait_until=self.config.wait_for, timeout=self.config.timeout)
        
        print("Please solve the CAPTCHA in the browser window.")
        print("Once solved, press Enter in this console to continue...")
        input()
        
        await page.wait_for_load_state('networkidle')
        self.logger.info("CAPTCHA handling completed.")

    async def launch_and_connect_to_chrome(self, playwright):
        if self.chrome_process is None:
            self.temp_user_data_dir = tempfile.mkdtemp(prefix="chrome_debug_profile_")
            chrome_executable = self.get_chrome_executable()
            command = [
                chrome_executable,
                f"--user-data-dir={self.temp_user_data_dir}",
                "--remote-debugging-port=9222",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            self.chrome_process = subprocess.Popen(command)
            self.logger.info("Launched Chrome with remote debugging.")

        for _ in range(30):
            try:
                browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
                self.logger.info("Successfully connected to Chrome.")
                return browser
            except Exception as e:
                self.logger.debug(f"Connection attempt failed: {str(e)}")
                await asyncio.sleep(1)
        
        raise Exception("Failed to connect to Chrome after 30 seconds")

    def get_chrome_executable(self):
        system = platform.system()
        if system == "Darwin":  # macOS
            return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        elif system == "Linux":
            return "google-chrome"
        else:
            raise NotImplementedError(f"Unsupported operating system: {system}")

    def __del__(self):
        if self.chrome_process:
            self.chrome_process.terminate()
            self.chrome_process.wait()
            self.logger.info("Chrome process terminated.")
        if self.temp_user_data_dir:
            import shutil
            shutil.rmtree(self.temp_user_data_dir, ignore_errors=True)
            self.logger.info(f"Temporary user data directory removed: {self.temp_user_data_dir}")

    async def connect_to_current_browser(self, playwright):
        system = platform.system()
        if system == "Darwin":
            subprocess.Popen(["open", "-a", "Google Chrome", "--args", "--remote-debugging-port=9222"])
        elif system == "Linux":
            subprocess.Popen(["google-chrome", "--remote-debugging-port=9222"])
        elif system == "Windows":
            subprocess.Popen(["start", "chrome", "--remote-debugging-port=9222"], shell=True)
        else:
            raise NotImplementedError(f"Connecting to current browser is not implemented for {system}")

        self.logger.info("Waiting for browser to start...")
        for _ in range(30):
            try:
                browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
                self.logger.info("Successfully connected to the browser.")
                return browser
            except Exception as e:
                self.logger.debug(f"Connection attempt failed: {str(e)}")
                await asyncio.sleep(1)
        
        raise Exception("Failed to connect to the current browser after 30 seconds")

    async def launch_browser(self, playwright, proxy: Optional[str] = None, handle_captcha: bool = False) -> Browser:
        return await playwright.chromium.launch(
            headless=self.config.headless and not handle_captcha,
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

    async def apply_stealth_settings(self, page: Page):
        await page.evaluate('''
            () => {
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });

                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });

                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            }
        ''')

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

    async def scrape_multiple_pages(self, page: Page, base_url: str, pages: Optional[str] = None, url_pattern: Optional[str] = None) -> List[str]:
        contents = []

        if not url_pattern:
            url_pattern = self.detect_url_pattern(base_url)

        if not url_pattern and not pages:
            # Single page scraping
            self.logger.info(f"Scraping single page: {base_url}")
            content = await self.navigate_and_get_content(page, base_url)
            contents.append(content)
        else:
            # Multiple page scraping
            page_numbers = self.parse_page_numbers(pages) if pages else [1]
            for page_num in page_numbers:
                current_url = self.apply_url_pattern(base_url, url_pattern, page_num) if url_pattern else base_url
                self.logger.info(f"Scraping page {page_num}: {current_url}")

                content = await self.navigate_and_get_content(page, current_url)
                contents.append(content)

                if page_num < len(page_numbers):
                    await asyncio.sleep(random.uniform(1, 2))

        return contents

    async def navigate_and_get_content(self, page: Page, url: str) -> str:
        try:
            self.logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until=self.config.wait_for, timeout=self.config.timeout)
            self.logger.info(f"Successfully loaded {url}")
            
            await asyncio.sleep(self.config.delay_after_load)
            
            self.logger.info("Extracting page content")
            content = await page.content()
            self.logger.info(f"Successfully extracted content (length: {len(content)})")
            return content
        except Exception as e:
            self.logger.error(f"Error navigating to {url}: {str(e)}")
            return f"Error: Failed to load {url}. {str(e)}"

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

        for param, value in query.items():
            if value and value[0].isdigit():
                return f"{param}={{{param}}}"

        path_parts = parsed_url.path.split('/')
        for i, part in enumerate(path_parts):
            if part.isdigit():
                path_parts[i] = "{page}"
                return '/'.join(path_parts)

        return None

    def apply_url_pattern(self, base_url: str, pattern: str, page_num: int) -> str:
        parsed_url = urlparse(base_url)
        if '=' in pattern: 
            query = parse_qs(parsed_url.query)
            param, value = pattern.split('=')
            query[param] = [value.format(**{param: page_num})]
            return urlunparse(parsed_url._replace(query=urlencode(query, doseq=True)))
        elif '{page}' in pattern:
            return urlunparse(parsed_url._replace(path=pattern.format(page=page_num)))
        else:
            return base_url

    def parse_page_numbers(self, pages: Optional[str]) -> List[int]:
        if not pages:
            return [1]

        page_numbers = []
        for part in pages.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                page_numbers.extend(range(start, end + 1))
            else:
                page_numbers.append(int(part))

        return sorted(set(page_numbers))

    async def extract(self, content: str) -> Dict[str, Any]:
        return {"raw_content": content}