
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper
from typing import Dict, Any

class HTMLScraper(BaseScraper):
    async def fetch_content(self, url: str, proxy: str = None) -> str:
        raise NotImplementedError("HTML content is fetched by PlaywrightScraper")

    async def extract(self, content: str) -> Dict[str, Any]:
        soup = BeautifulSoup(content, 'html.parser')
        return {
            'title': soup.title.string if soup.title else '',
            'text': soup.get_text(),
            'links': [a['href'] for a in soup.find_all('a', href=True)],
        }
