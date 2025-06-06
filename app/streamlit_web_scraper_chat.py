import asyncio
import streamlit as st
from src.web_extractor import WebExtractor, ScrapelessConfig
import os

class StreamlitWebScraperChat:
    def __init__(self, model_name, scrapeless_config: ScrapelessConfig = None):
        # Get API key from environment
        api_key = os.getenv("SCRAPELESS_API_KEY", "")
        
        if not api_key:
            st.error("SCRAPELESS_API_KEY is not set. Please set it in your environment variables.")
            
        if not scrapeless_config:
            scrapeless_config = ScrapelessConfig(api_key=api_key)
            
        try:
            self.web_extractor = WebExtractor(model_name=model_name, scrapeless_config=scrapeless_config)
        except ValueError as e:
            st.error(f"Error initializing extractor: {str(e)}")
            raise
        
        # Save current state
        if 'current_url' in st.session_state:
            self.web_extractor.current_url = st.session_state.current_url
        if 'current_content' in st.session_state:
            self.web_extractor.current_content = st.session_state.current_content
        if 'preprocessed_content' in st.session_state:
            self.web_extractor.preprocessed_content = st.session_state.preprocessed_content
        if 'content_hash' in st.session_state:
            self.web_extractor.content_hash = st.session_state.content_hash

    def process_message(self, message: str) -> str:
        async def process_with_progress():
            progress_placeholder = st.empty()
            progress_placeholder.text("Processing...")
            result = await self.web_extractor.process_query(message, progress_callback=progress_placeholder.text)
            progress_placeholder.empty()
            
            # Save state for next session
            st.session_state.current_url = self.web_extractor.current_url
            st.session_state.current_content = self.web_extractor.current_content
            st.session_state.preprocessed_content = self.web_extractor.preprocessed_content
            st.session_state.content_hash = self.web_extractor.content_hash
            
            # Debug info
            print(f"After processing, content exists: {self.web_extractor.current_content is not None}")
            print(f"Content length: {len(self.web_extractor.current_content) if self.web_extractor.current_content else 0}")
            
            return result

        return asyncio.run(process_with_progress())