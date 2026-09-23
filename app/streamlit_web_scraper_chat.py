import asyncio
import logging
import streamlit as st
from src.web_extractor import WebExtractor
from src.scrapers.playwright_scraper import ScraperConfig

logger = logging.getLogger(__name__)


class StreamlitWebScraperChat:
    def __init__(self, model_name, scraper_config: ScraperConfig = None):
        self.web_extractor = WebExtractor(model_name=model_name, scraper_config=scraper_config)
        # The browser and the Tor session are bound to the loop they were created on,
        # so every message has to run on the same loop instead of a fresh asyncio.run().
        self._loop = asyncio.new_event_loop()

    def process_message(self, message: str, conversation_history: list[dict] | None = None) -> str:
        async def process_with_progress():
            progress_placeholder = st.empty()
            progress_placeholder.text("Processing...")
            result = await self.web_extractor.process_query(
                message,
                conversation_history=conversation_history,
                progress_callback=progress_placeholder.text
            )
            progress_placeholder.empty()
            return result

        return self._loop.run_until_complete(process_with_progress())

    def close(self) -> None:
        if self._loop.is_closed():
            return
        try:
            self._loop.run_until_complete(self.web_extractor.close())
        except Exception as e:
            logger.warning(f"Error while closing scraper: {e}")
        finally:
            self._loop.close()
