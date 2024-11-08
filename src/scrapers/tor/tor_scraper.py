from typing import Dict, Any
from .tor_manager import TorManager
from .tor_config import TorConfig
from .exceptions import TorException
from ..base_scraper import BaseScraper
from bs4 import BeautifulSoup
import logging
from urllib.parse import urlparse

class TorScraper(BaseScraper):
    """Scraper implementation for Tor hidden services"""
    
    def __init__(self, config: TorConfig = TorConfig()):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
        self.tor_manager = TorManager(config)
        self.config = config

    @staticmethod
    def is_onion_url(url: str) -> bool:
        """Check if the given URL is an onion service"""
        try:
            parsed = urlparse(url)
            return parsed.hostname.endswith('.onion') if parsed.hostname else False
        except Exception:
            return False

    async def fetch_content(self, url: str, proxy: str = None) -> str:
        """Fetch content from an onion site"""
        try:
            if not self.is_onion_url(url):
                raise ValueError("Not an onion URL")

            # Use Tor manager to fetch content
            content = await self.tor_manager.fetch_content(url)
            return content
        except Exception as e:
            self.logger.error(f"Error fetching onion content: {str(e)}")
            raise

    async def extract(self, content: str) -> Dict[str, Any]:
        """Extract data from the fetched content"""
        try:
            soup = BeautifulSoup(content, 'html.parser')
            return {
                'title': soup.title.string if soup.title else '',
                'text': soup.get_text(),
                'links': [a['href'] for a in soup.find_all('a', href=True)],
                'raw_html': content
            }
        except Exception as e:
            self.logger.error(f"Error extracting content: {str(e)}")
            raise

    async def scrape_onion(self, url: str) -> Dict[str, Any]:
        """Main method to scrape onion sites"""
        try:
            content = await self.fetch_content(url)
            return await self.extract(content)
        except Exception as e:
            self.logger.error(f"Error during onion scraping: {str(e)}")
            raise