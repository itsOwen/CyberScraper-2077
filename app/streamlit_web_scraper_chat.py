import asyncio
from src.web_extractor import WebExtractor

class StreamlitWebScraperChat:
    def __init__(self, model_name: str = "gpt-4o-mini"):
        self.web_extractor = WebExtractor(model_name=model_name)

    def process_message(self, message: str) -> str:
        return asyncio.run(self.web_extractor.process_query(message))