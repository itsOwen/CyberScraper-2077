from langchain_openai import ChatOpenAI
from langchain_openai import OpenAI
from langchain.base_language import BaseLanguageModel
import google.generativeai as genai
import os
import streamlit as st

class Models:
    @staticmethod
    def get_model(model_name: str, **kwargs) -> BaseLanguageModel:
        # Get API keys directly from environment
        openai_api_key = os.environ.get("OPENAI_API_KEY", "")
        google_api_key = os.environ.get("GOOGLE_API_KEY", "")
        
        if model_name in ["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"]:
            if not openai_api_key:
                st.error("OpenAI API Key is not set. Please set the OPENAI_API_KEY environment variable.")
                st.info("""
                Set it using the following command:
                ```
                export OPENAI_API_KEY=your-api-key-here
                ```
                """)
                raise ValueError("OpenAI API Key is not set")
            return ChatOpenAI(model_name=model_name, api_key=openai_api_key, **kwargs)
        elif model_name.startswith("text-"):
            if not openai_api_key:
                st.error("OpenAI API Key is not set. Please set the OPENAI_API_KEY environment variable.")
                st.info("""
                Set it using the following command:
                ```
                export OPENAI_API_KEY=your-api-key-here
                ```
                """)
                raise ValueError("OpenAI API Key is not set")
            return OpenAI(model_name=model_name, api_key=openai_api_key, **kwargs)
        elif model_name.startswith("gemini-"):
            if not google_api_key:
                st.error("Google API Key is not set. Please set the GOOGLE_API_KEY environment variable.")
                st.info("""
                Set it using the following command:
                ```
                export GOOGLE_API_KEY=your-api-key-here
                ```
                """)
                raise ValueError("Google API Key is not set")
            genai.configure(api_key=google_api_key)
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=model_name, google_api_key=google_api_key, **kwargs)
        else:
            raise ValueError(f"Unsupported model: {model_name}")