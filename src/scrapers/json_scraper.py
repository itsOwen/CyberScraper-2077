
import json
from .base_scraper import BaseScraper
from typing import Dict, Any

class JSONScraper(BaseScraper):
    async def fetch_content(self, url: str, proxy: str = None) -> str:
        raise NotImplementedError("JSON content is fetched by PlaywrightScraper")

    async def extract(self, content: str) -> Dict[str, Any]:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {"error": "Invalid JSON content"}
