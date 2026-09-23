"""
Patchright Scraper Module

This module provides a robust web scraping implementation using Patchright
(undetected Playwright fork). It supports advanced features like stealth mode,
human simulation, CAPTCHA handling, and cloudflare bypassing.
"""

from typing import Any, Dict, List, Optional

from patchright.async_api import async_playwright, Browser, BrowserContext, Page
from .base_scraper import BaseScraper
import asyncio
import random
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import platform
import subprocess
import os
import tempfile

from ..utils.error_handler import ErrorMessages

# Elements and titles left on the page while a CAPTCHA or bot challenge is still pending.
_CAPTCHA_CHECK_SCRIPT = '''
    () => Boolean(
        document.querySelector(
            'iframe[src*="recaptcha"], iframe[src*="hcaptcha"], iframe[src*="challenges.cloudflare.com"], ' +
            '#challenge-form, #challenge-stage, .cf-turnstile, .g-recaptcha, .h-captcha'
        ) || /just a moment|attention required/i.test(document.title)
    )
'''


def _get_browser_channel():
    """Get browser channel based on platform. Chrome not available on ARM64 Linux."""
    system = platform.system().lower()
    machine = platform.machine().lower()
    # Chrome is not available for Linux ARM64 (e.g., Docker on Apple Silicon)
    if system == "linux" and machine in ("aarch64", "arm64"):
        return None  # Use default chromium
    return "chrome"  # Use Chrome for better stealth on x86/macOS/Windows


class ScraperConfig:
    """Configuration class for the Patchright scraper."""

    def __init__(
        self,
        use_stealth: bool = True,
        simulate_human: bool = False,
        use_custom_headers: bool = False,  # Disabled by default - creates detection signatures
        hide_webdriver: bool = True,
        bypass_cloudflare: bool = True,
        headless: bool = True,
        debug: bool = False,
        timeout: int = 30000,
        wait_for: str = 'domcontentloaded',
        use_current_browser: bool = False,
        use_persistent_context: bool = False,  # Use persistent context for max stealth
        captcha_timeout: int = 180,  # Seconds to wait for the user to solve a CAPTCHA
        max_retries: int = 3,
        delay_after_load: int = 2,
        max_concurrent_pages: int = 5,
        locale: str | None = None,  # e.g., 'en-US' - matches browser locale
        timezone_id: str | None = None,  # e.g., 'America/New_York' - matches browser timezone
    ):
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
        self.use_persistent_context = use_persistent_context
        self.captcha_timeout = captcha_timeout
        self.max_retries = max_retries
        self.delay_after_load = delay_after_load
        self.max_concurrent_pages = max_concurrent_pages
        self.locale = locale
        self.timezone_id = timezone_id


class PlaywrightScraper(BaseScraper):
    """
    Advanced web scraper implementation using Patchright (undetected Playwright fork).

    Features:
    - Undetected browser automation (bypasses Cloudflare, Akamai, etc.)
    - Browser instance reuse for better performance
    - Concurrent page scraping with configurable concurrency
    - Persistent context support for maximum stealth
    - CAPTCHA handling
    - Automatic stealth patches via Patchright
    """

    def __init__(self, config: ScraperConfig | None = None):
        config = config or ScraperConfig()
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
        self.config = config
        self.chrome_process = None
        self.temp_user_data_dir = None
        # Browser pooling
        self._playwright = None
        self._browser: Browser | None = None
        self._persistent_context: BrowserContext | None = None
        self._browser_lock = asyncio.Lock()

    async def _get_browser(self, proxy: str | None = None, handle_captcha: bool = False) -> Browser:
        """Get or create a pooled browser instance with thread-safe locking."""
        async with self._browser_lock:
            if self._browser is None or not self._browser.is_connected():
                if self._playwright is None:
                    self._playwright = await async_playwright().start()
                if self.config.use_current_browser:
                    self._browser = await self.launch_and_connect_to_chrome(self._playwright)
                elif self.config.use_persistent_context:
                    # Persistent context for maximum stealth - returns context, not browser
                    self._persistent_context = await self.launch_persistent_context(
                        self._playwright, proxy, handle_captcha
                    )
                    self._browser = self._persistent_context.browser
                else:
                    self._browser = await self.launch_browser(self._playwright, proxy, handle_captcha)
            return self._browser

    async def launch_persistent_context(
        self, playwright, proxy: Optional[str] = None, handle_captcha: bool = False
    ) -> BrowserContext:
        """
        Launch a persistent browser context for maximum stealth.

        Patchright recommends persistent context with real Chrome for best undetectability.
        This uses a real Chrome profile which appears more human-like.

        Args:
            playwright: Patchright instance
            proxy: Optional proxy server
            handle_captcha: Whether CAPTCHA handling is enabled

        Returns:
            BrowserContext: Persistent browser context
        """
        if self.temp_user_data_dir is None:
            self.temp_user_data_dir = tempfile.mkdtemp(prefix="patchright_profile_")

        context_options = {
            'user_data_dir': self.temp_user_data_dir,
            'channel': _get_browser_channel(),
            'headless': self.config.headless and not handle_captcha,
            'no_viewport': True,  # Removes viewport fingerprint
            'proxy': {'server': proxy} if proxy else None,
            'args': ['--no-sandbox', '--disable-setuid-sandbox'],
            'ignore_https_errors': True,
            'locale': self.config.locale,
            'timezone_id': self.config.timezone_id,
        }

        try:
            context = await playwright.chromium.launch_persistent_context(
                **{k: v for k, v in context_options.items() if v is not None}
            )

            # Note: Init script disabled - Patchright handles stealth automatically
            # if self.config.use_stealth:
            #     await self._add_stealth_init_script(context)

            return context
        except Exception as e:
            raise Exception(
                f"Failed to launch persistent context: {str(e)}\n\n"
                "Make sure Chrome is installed or run: patchright install chrome"
            )

    async def fetch_content(
        self,
        url: str,
        proxy: str | None = None,
        pages: str | None = None,
        url_pattern: str | None = None,
        handle_captcha: bool = False
    ) -> list[str]:
        """
        Fetch content from a given URL using Playwright with browser pooling.

        Args:
            url: The URL to fetch content from
            proxy: Proxy server to use for the request
            pages: Page numbers to scrape (e.g., "1-5" or "1,3,5")
            url_pattern: Pattern for constructing multi-page URLs
            handle_captcha: Whether to pause for CAPTCHA solving

        Returns:
            List of content strings from scraped pages
        """
        if handle_captcha:
            if not self._can_show_browser_window():
                return [
                    "Error: CAPTCHA mode needs a visible browser window, which is not available here "
                    "(for example inside Docker). Run CyberScraper locally to solve CAPTCHAs."
                ]
            # A pooled browser may be headless, and the user needs a visible window.
            if self._browser and self._browser.is_connected():
                await self._browser.close()
                self._browser = None

        context = None
        try:
            browser = await self._get_browser(proxy, handle_captcha)
            if handle_captcha:
                # For CAPTCHA mode: create context, handle CAPTCHA, then scrape pages
                context = await self.create_context(browser, proxy)
                page = await context.new_page()

                if self.config.use_stealth:
                    await self.apply_stealth_settings(page)
                await self.set_browser_features(page)

                await self.handle_captcha(page, url)

                # After CAPTCHA is solved, get content from the current page
                await asyncio.sleep(self.config.delay_after_load)
                first_page_content = await page.content()

                # Check if we need to scrape multiple pages
                if pages:
                    page_numbers = self.parse_page_numbers(pages)
                    if not url_pattern:
                        url_pattern = self.detect_url_pattern(url)

                    contents = [first_page_content]  # First page already scraped

                    # Scrape remaining pages (skip first one since we already have it)
                    for page_num in page_numbers[1:]:
                        page_url = self.apply_url_pattern(url, url_pattern, page_num) if url_pattern else url
                        self.logger.info(f"Scraping page {page_num}: {page_url}")
                        await page.goto(page_url, wait_until=self.config.wait_for, timeout=self.config.timeout)
                        await asyncio.sleep(self.config.delay_after_load)
                        content = await page.content()
                        contents.append(content)
                else:
                    contents = [first_page_content]
            else:
                # Normal mode: use scrape_multiple_pages
                contents = await self.scrape_multiple_pages(browser, url, pages, url_pattern, proxy)
        except Exception as e:
            import traceback
            error_details = f"{type(e).__name__}: {str(e)}"
            self.logger.error(f"Error during scraping: {error_details}")
            self.logger.error(traceback.format_exc())
            contents = [f"Error: {error_details}"]
        finally:
            if context:
                await context.close()
            # Close browser after CAPTCHA mode to clean up the visible window
            if handle_captcha and self._browser and self._browser.is_connected():
                await self._browser.close()
                self._browser = None

        return contents

    @staticmethod
    def _can_show_browser_window() -> bool:
        if platform.system() != "Linux":
            return True
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))

    async def handle_captcha(self, page: Page, url: str):
        """
        Open the URL in a visible browser window and wait until the user solves the CAPTCHA.

        The page is checked every couple of seconds for common CAPTCHA and bot challenge
        widgets. Scraping continues once they are gone, or after config.captcha_timeout
        seconds, whichever comes first.

        Args:
            page (Page): Playwright page object
            url (str): URL to navigate to for CAPTCHA solving
        """
        self.logger.info("Waiting for user to solve CAPTCHA...")
        try:
            await page.goto(url, wait_until=self.config.wait_for, timeout=self.config.timeout)

            loop = asyncio.get_running_loop()
            deadline = loop.time() + self.config.captcha_timeout
            while await self._captcha_pending(page):
                if loop.time() >= deadline:
                    self.logger.warning("CAPTCHA still visible after timeout, continuing with current page")
                    break
                await asyncio.sleep(2)

            # Use 'load' instead of 'networkidle' - modern sites never reach networkidle
            # due to constant analytics/tracking requests
            await page.wait_for_load_state('load', timeout=5000)
            self.logger.info("CAPTCHA handling completed.")
        except Exception as e:
            # Handle browser closure or timeout gracefully
            if "closed" in str(e).lower():
                self.logger.warning("Browser was closed during CAPTCHA handling")
                raise
            self.logger.warning(f"CAPTCHA wait completed with: {e}")

    async def _captcha_pending(self, page: Page) -> bool:
        try:
            return await page.evaluate(_CAPTCHA_CHECK_SCRIPT)
        except Exception as e:
            if "closed" in str(e).lower():
                raise
            # The page is navigating (e.g. right after the challenge was solved).
            return True

    async def launch_and_connect_to_chrome(self, playwright):
        """
        Launch a new Chrome instance with remote debugging enabled and connect to it.

        This method creates a temporary user data directory and launches Chrome
        with remote debugging on port 9222, then connects to it via Playwright.

        Args:
            playwright: Playwright instance

        Returns:
            Browser: Connected browser instance

        Raises:
            Exception: If unable to connect to Chrome after 30 seconds
        """
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
        """
        Get the path to Chrome executable based on the operating system.

        Returns:
            str: Path to Chrome executable

        Raises:
            NotImplementedError: If the operating system is not supported
        """
        system = platform.system()
        if system == "Darwin":  # macOS
            return "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        elif system == "Linux":
            return "google-chrome"
        elif system == "Windows":
            return "chrome"
        else:
            raise NotImplementedError(f"Unsupported operating system: {system}")

    async def close(self) -> None:
        """
        Clean up resources including browser, Chrome process, and temp directories.

        This should be called when done using the scraper, or use it as an async context manager.
        """
        import shutil

        # Close persistent context if used
        if self._persistent_context:
            await self._persistent_context.close()
            self._persistent_context = None
            self.logger.info("Persistent context closed.")

        # Close pooled browser
        if self._browser and self._browser.is_connected():
            await self._browser.close()
            self._browser = None
            self.logger.info("Browser closed.")

        # Stop playwright
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

        # Terminate Chrome process if we started one
        if self.chrome_process:
            self.chrome_process.terminate()
            self.chrome_process.wait()
            self.chrome_process = None
            self.logger.info("Chrome process terminated.")

        # Remove temp directory
        if self.temp_user_data_dir:
            shutil.rmtree(self.temp_user_data_dir, ignore_errors=True)
            self.logger.info(f"Temporary user data directory removed: {self.temp_user_data_dir}")
            self.temp_user_data_dir = None

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with cleanup."""
        await self.close()
        return False

    async def connect_to_current_browser(self, playwright):
        """
        Connect to an existing browser instance with remote debugging enabled.

        This method launches a browser with remote debugging and attempts to
        connect to it via Playwright.

        Args:
            playwright: Playwright instance

        Returns:
            Browser: Connected browser instance

        Raises:
            NotImplementedError: If the operating system is not supported
            Exception: If unable to connect to the browser after 30 seconds
        """
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
        """
        Launch a new browser instance with specified configuration.

        Args:
            playwright: Patchright instance
            proxy (Optional[str]): Proxy server to use
            handle_captcha (bool): Whether CAPTCHA handling is enabled

        Returns:
            Browser: Launched browser instance
        """
        try:
            channel = _get_browser_channel()
            launch_options = {
                'headless': self.config.headless and not handle_captcha,
                'args': ['--no-sandbox', '--disable-setuid-sandbox', '--disable-infobars',
                         '--window-position=0,0', '--ignore-certificate-errors',
                         '--ignore-certificate-errors-spki-list'],
                'proxy': {'server': proxy} if proxy else None
            }
            if channel:
                launch_options['channel'] = channel
            return await playwright.chromium.launch(**launch_options)
        except EOFError:
            raise Exception(
                "Patchright browsers are not installed.\n\n"
                "Please run: patchright install chromium\n\n"
                "Or for better stealth: patchright install chrome"
            )
        except Exception as e:
            raise Exception(f"Failed to launch browser: {str(e)}")

    async def create_context(self, browser: Browser, proxy: Optional[str] = None) -> BrowserContext:
        """
        Create a new browser context with specified settings.

        Note: Patchright recommends NOT setting custom user_agent or viewport
        as these create detection signatures. Let the browser use defaults.

        Args:
            browser (Browser): Browser instance
            proxy (Optional[str]): Proxy server to use

        Returns:
            BrowserContext: Created browser context
        """
        context_options = {
            'proxy': {'server': proxy} if proxy else None,
            'java_script_enabled': True,
            'ignore_https_errors': True,
            'locale': self.config.locale,
            'timezone_id': self.config.timezone_id,
        }
        # Don't set viewport or user_agent - Patchright handles stealth better without them
        context = await browser.new_context(**{k: v for k, v in context_options.items() if v is not None})

        # Note: Init script disabled - Patchright handles stealth automatically
        # If needed, uncomment:
        # if self.config.use_stealth:
        #     await self._add_stealth_init_script(context)

        return context

    async def _add_stealth_init_script(self, context: BrowserContext):
        """
        Add init script to context for additional stealth before page scripts run.

        This runs before any page JavaScript executes, patching detection vectors
        that Patchright might not cover. Uses the Playwright add_init_script API.

        Args:
            context: Browser context to add init script to
        """
        stealth_script = '''
            () => {
                // Patch chrome.runtime to avoid detection
                if (!window.chrome) {
                    window.chrome = {};
                }
                if (!window.chrome.runtime) {
                    window.chrome.runtime = {};
                }

                // Patch plugins array to look like real browser
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        const plugins = [
                            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                            { name: 'Native Client', filename: 'internal-nacl-plugin' }
                        ];
                        plugins.item = (i) => plugins[i] || null;
                        plugins.namedItem = (name) => plugins.find(p => p.name === name) || null;
                        plugins.refresh = () => {};
                        return plugins;
                    }
                });

                // Patch languages to look normal
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });

                // Ensure webdriver is not set (Patchright handles this but extra safety)
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });

                // Patch connection info
                if (navigator.connection) {
                    Object.defineProperty(navigator.connection, 'rtt', {
                        get: () => 50
                    });
                }
            }
        '''
        await context.add_init_script(stealth_script)

    async def apply_stealth_settings(self, page: Page):
        """
        Apply additional stealth settings to avoid bot detection.

        Note: Patchright already handles most stealth features automatically:
        - navigator.webdriver is already undefined
        - Automation flags are already removed
        - Runtime.enable leak is already patched

        This method only applies minimal additional patches that don't interfere.

        Args:
            page (Page): Patchright page object
        """
        # Patchright handles most stealth automatically via isolated contexts
        # Only apply minimal non-conflicting patches
        await page.evaluate('''
            () => {
                // Patch permissions query for notifications
                const originalQuery = window.navigator.permissions.query;
                if (originalQuery) {
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                            Promise.resolve({ state: Notification.permission }) :
                            originalQuery(parameters)
                    );
                }
            }
        ''')

    async def set_browser_features(self, page: Page):
        """
        Set browser features like custom headers if enabled in configuration.
        
        Args:
            page (Page): Playwright page object
        """
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

    async def scrape_multiple_pages(
        self,
        browser: Browser,
        base_url: str,
        pages: str | None = None,
        url_pattern: str | None = None,
        proxy: str | None = None
    ) -> list[str]:
        """
        Scrape content from single or multiple pages with concurrent execution.

        Uses asyncio.gather with a semaphore for controlled concurrency.
        Supports both regular browser contexts and persistent contexts.

        Args:
            browser: Browser instance for creating contexts
            base_url: Base URL to scrape
            pages: Page numbers to scrape
            url_pattern: Pattern for constructing multi-page URLs
            proxy: Optional proxy for context creation

        Returns:
            List of content strings from scraped pages
        """
        if not url_pattern:
            url_pattern = self.detect_url_pattern(base_url)

        # Use persistent context if available, otherwise create new contexts
        use_persistent = self._persistent_context is not None

        if not url_pattern and not pages:
            # Single page scraping
            self.logger.info(f"Scraping single page: {base_url}")
            if use_persistent:
                page = await self._persistent_context.new_page()
                try:
                    if self.config.use_stealth:
                        await self.apply_stealth_settings(page)
                    await self.set_browser_features(page)
                    content = await self.navigate_and_get_content(page, base_url)
                    return [content]
                finally:
                    await page.close()
            else:
                context = await self.create_context(browser, proxy)
                try:
                    page = await context.new_page()
                    if self.config.use_stealth:
                        await self.apply_stealth_settings(page)
                    await self.set_browser_features(page)
                    content = await self.navigate_and_get_content(page, base_url)
                    return [content]
                finally:
                    await context.close()

        # Multiple page scraping with concurrency
        page_numbers = self.parse_page_numbers(pages) if pages else [1]
        urls = [
            self.apply_url_pattern(base_url, url_pattern, page_num) if url_pattern else base_url
            for page_num in page_numbers
        ]

        semaphore = asyncio.Semaphore(self.config.max_concurrent_pages)

        async def scrape_with_context(url: str, page_num: int) -> str:
            async with semaphore:
                self.logger.info(f"Scraping page {page_num}: {url}")
                if use_persistent:
                    page = await self._persistent_context.new_page()
                    try:
                        if self.config.use_stealth:
                            await self.apply_stealth_settings(page)
                        await self.set_browser_features(page)
                        content = await self.navigate_and_get_content(page, url)
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        return content
                    finally:
                        await page.close()
                else:
                    context = await self.create_context(browser, proxy)
                    try:
                        page = await context.new_page()
                        if self.config.use_stealth:
                            await self.apply_stealth_settings(page)
                        await self.set_browser_features(page)
                        content = await self.navigate_and_get_content(page, url)
                        await asyncio.sleep(random.uniform(0.5, 1.5))
                        return content
                    finally:
                        await context.close()

        # Execute concurrently and maintain order
        tasks = [
            scrape_with_context(url, page_num)
            for page_num, url in zip(page_numbers, urls)
        ]
        return await asyncio.gather(*tasks)

    async def navigate_and_get_content(self, page: Page, url: str) -> str:
        """
        Navigate to a URL and extract its content.

        Args:
            page (Page): Playwright page object
            url (str): URL to navigate to

        Returns:
            str: Page content or error message
        """
        try:
            self.logger.info(f"Navigating to {url}")
            await page.goto(url, wait_until=self.config.wait_for, timeout=self.config.timeout)
            self.logger.info(f"Successfully loaded {url}")

            await asyncio.sleep(self.config.delay_after_load)

            self.logger.info("Extracting page content")
            content = await page.content()
            self.logger.info(f"Successfully extracted content (length: {len(content)})")
            return content
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout loading {url}")
            return f"Error: {ErrorMessages.TIMEOUT_ERROR}"
        except Exception as e:
            self.logger.error(f"Error navigating to {url}: {str(e)}")
            error_details = str(e) if len(str(e)) < 200 else str(e)[:200] + "..."
            return f"Error: {ErrorMessages.SCRAPING_FAILED}\n\nDetails: {error_details}"

    async def bypass_cloudflare(self, page: Page, url: str) -> str:
        """
        Attempt to bypass Cloudflare protection.
        
        This method reloads the page multiple times and simulates human behavior
        to try to bypass Cloudflare's bot detection.
        
        Args:
            page (Page): Playwright page object
            url (str): URL to bypass Cloudflare for
            
        Returns:
            str: Page content after bypass attempt
        """
        max_retries = 3
        for _ in range(max_retries):
            await page.reload(wait_until=self.config.wait_for, timeout=self.config.timeout)
            if self.config.simulate_human:
                await self.simulate_human_behavior(page)
            else:
                await asyncio.sleep(2)

            content = await page.content()
            content_lower = content.lower()
            if "cloudflare" not in content_lower or "ray id" not in content_lower:
                self.logger.info("Successfully bypassed Cloudflare")
                return content

            self.logger.info("Cloudflare still detected, retrying...")

        self.logger.warning("Failed to bypass Cloudflare after multiple attempts")
        return content

    async def simulate_human_behavior(self, page: Page):
        """
        Simulate human-like browsing behavior.
        
        This method simulates human behavior like scrolling, mouse movements,
        and hovering over elements to make automation less detectable.
        
        Args:
            page (Page): Playwright page object
        """
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
        """
        Detect URL pagination pattern from a given URL.
        
        This method analyzes the URL to identify common pagination patterns
        in query parameters or path segments.
        
        Args:
            url (str): URL to analyze for pagination patterns
            
        Returns:
            Optional[str]: Detected pattern or None if no pattern found
        """
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
        """
        Apply a URL pattern to generate a paginated URL.
        
        Args:
            base_url (str): Base URL to apply pattern to
            pattern (str): Pattern to apply
            page_num (int): Page number to insert into pattern
            
        Returns:
            str: Generated URL with page number applied
        """
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
        """
        Parse page number specification into a list of integers.
        
        This method parses page specifications like "1-5" or "1,3,5" into
        a sorted list of unique page numbers.
        
        Args:
            pages (Optional[str]): Page specification string
            
        Returns:
            List[int]: Sorted list of unique page numbers
        """
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
        """
        Extract structured data from content.
        
        For the Playwright scraper, this method simply returns the raw content
        since Playwright is primarily used for fetching content rather than
        extracting structured data.
        
        Args:
            content (str): Raw content to extract data from
            
        Returns:
            Dict[str, Any]: Dictionary containing the raw content
        """
        return {"raw_content": content}