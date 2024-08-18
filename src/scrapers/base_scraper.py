
from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseScraper(ABC):
    @abstractmethod
    async def fetch_content(self, url: str, proxy: str = None) -> str:
        pass

    @abstractmethod
    async def extract(self, content: str) -> Dict[str, Any]:
        pass
