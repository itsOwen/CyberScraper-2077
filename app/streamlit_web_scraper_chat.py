import asyncio
import streamlit as st
from src.web_extractor import WebExtractor
from src.scrapers.playwright_scraper import ScraperConfig

class StreamlitWebScraperChat:
    def __init__(self, model_name, scraper_config: ScraperConfig = None):
        self.web_extractor = WebExtractor(model_name=model_name, scraper_config=scraper_config)

    def process_message(self, message: str) -> str:
        async def process_with_progress():
            progress_placeholder = st.empty()
            progress_placeholder.text("Connecting to browser...")
            result = await self.web_extractor.process_query(message, progress_callback=progress_placeholder.text)
            progress_placeholder.empty()
            return result

        return asyncio.run(process_with_progress())