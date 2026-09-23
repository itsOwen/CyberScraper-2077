import asyncio
import os
import shutil
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest.mock import AsyncMock, patch

from src.scrapers.playwright_scraper import PlaywrightScraper, ScraperConfig


class PageNumberTests(unittest.TestCase):
    def setUp(self):
        self.scraper = PlaywrightScraper()

    def test_ranges_and_single_pages(self):
        self.assertEqual(self.scraper.parse_page_numbers("1-3,5,3"), [1, 2, 3, 5])

    def test_default_is_first_page(self):
        self.assertEqual(self.scraper.parse_page_numbers(None), [1])


class UrlPatternTests(unittest.TestCase):
    def setUp(self):
        self.scraper = PlaywrightScraper()

    def test_query_parameter(self):
        url = "https://news.ycombinator.com/?p=1"
        pattern = self.scraper.detect_url_pattern(url)
        self.assertEqual(pattern, "p={p}")
        self.assertEqual(self.scraper.apply_url_pattern(url, pattern, 3), "https://news.ycombinator.com/?p=3")

    def test_path_segment(self):
        url = "https://example.com/list/2/items"
        pattern = self.scraper.detect_url_pattern(url)
        self.assertEqual(self.scraper.apply_url_pattern(url, pattern, 7), "https://example.com/list/7/items")

    def test_no_pattern(self):
        self.assertIsNone(self.scraper.detect_url_pattern("https://example.com/about"))


class FakePage:
    def __init__(self, results):
        self.results = list(results)
        self.goto = AsyncMock()
        self.wait_for_load_state = AsyncMock()

    async def evaluate(self, script):
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class CaptchaTests(unittest.IsolatedAsyncioTestCase):
    async def test_waits_until_captcha_is_gone(self):
        scraper = PlaywrightScraper(ScraperConfig(captcha_timeout=30))
        page = FakePage([True, Exception("Execution context was destroyed"), False])
        with patch("src.scrapers.playwright_scraper.asyncio.sleep", AsyncMock()) as sleep:
            await scraper.handle_captcha(page, "https://example.com")
        self.assertEqual(sleep.await_count, 2)
        self.assertEqual(page.results, [])

    async def test_gives_up_after_timeout(self):
        scraper = PlaywrightScraper(ScraperConfig(captcha_timeout=0))
        page = FakePage([True, True])
        await scraper.handle_captcha(page, "https://example.com")
        self.assertEqual(len(page.results), 1)

    async def test_closed_browser_is_reported(self):
        scraper = PlaywrightScraper()
        page = FakePage([Exception("Target page, context or browser has been closed")])
        with self.assertRaises(Exception):
            await scraper.handle_captcha(page, "https://example.com")

    async def test_captcha_mode_without_display_returns_error(self):
        scraper = PlaywrightScraper()
        with patch.object(PlaywrightScraper, "_can_show_browser_window", return_value=False):
            result = await scraper.fetch_content("https://example.com", handle_captcha=True)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].startswith("Error: CAPTCHA mode needs a visible browser window"))

    def test_display_detection_on_linux(self):
        with patch("src.scrapers.playwright_scraper.platform.system", return_value="Linux"):
            with patch.dict(os.environ, {}, clear=True):
                self.assertFalse(PlaywrightScraper._can_show_browser_window())
            with patch.dict(os.environ, {"DISPLAY": ":0"}, clear=True):
                self.assertTrue(PlaywrightScraper._can_show_browser_window())


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = f"<html><body><p>page {self.path}</p></body></html>".encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def _chromium_installed():
    cache = os.path.expanduser(os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "~/.cache/ms-playwright"))
    return os.path.isdir(cache) and any(name.startswith("chromium") for name in os.listdir(cache))


@unittest.skipUnless(_chromium_installed(), "Patchright Chromium is not installed")
class RepeatedScrapeTests(unittest.TestCase):
    """Streamlit handles every chat message in a separate call, the browser has to survive between them."""

    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_second_url_in_the_same_chat_works(self):
        from app.streamlit_web_scraper_chat import StreamlitWebScraperChat

        chat = StreamlitWebScraperChat("ollama:test-model", ScraperConfig(delay_after_load=0, timeout=15000))
        try:
            for path in ("/first", "/second", "/third"):
                reply = chat.process_message(f"{self.base_url}{path}")
                self.assertIn("I've fetched", reply, reply)
                self.assertIn(f"page {path}", chat.web_extractor.preprocessed_content)
        finally:
            chat.close()
        self.assertIsNone(chat.web_extractor.playwright_scraper._browser)
        self.assertTrue(chat._loop.is_closed())

    def test_close_can_be_called_twice(self):
        from app.streamlit_web_scraper_chat import StreamlitWebScraperChat

        chat = StreamlitWebScraperChat("ollama:test-model")
        chat.close()
        chat.close()


if __name__ == "__main__":
    unittest.main()
