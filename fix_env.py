import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Make sure these are loaded before any imports that require API keys
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY", "")
os.environ["SCRAPELESS_API_KEY"] = os.getenv("SCRAPELESS_API_KEY", "")
os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY", "")

# Print environment variables for debugging
print(f"OPENAI_API_KEY set: {'Yes' if os.getenv('OPENAI_API_KEY') else 'No'}")
print(f"SCRAPELESS_API_KEY set: {'Yes' if os.getenv('SCRAPELESS_API_KEY') else 'No'}")
print(f"GOOGLE_API_KEY set: {'Yes' if os.getenv('GOOGLE_API_KEY') else 'No'}")