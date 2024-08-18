import streamlit as st
import time
import random

def get_loading_message():
    messages = [
        "Ripping data from the net, Silverhand style...",
        "Scraping the web, leaving no trace...",
        "Burning through the data cores...",
        "Jacking in, scraping every byte...",
        "Tearing down the firewall, extracting the goods...",
        "No rules, just raw data extraction...",
        "Slicing through the web's defenses...",
        "No mercy for the web, just pure data...",
        "Scraping the net, one byte at a time...",
        "Crashing through the data barriers, Johnny-style..."
    ]
    return random.choice(messages)

def loading_animation(process_func, *args, **kwargs):
    loading_placeholder = st.empty()
    result = None
    start_time = time.time()
    while result is None:
        elapsed_time = time.time() - start_time
        if elapsed_time > 30:  # Timeout after 30 seconds
            loading_placeholder.error("Request timed out. Please try again.")
            return None
        
        loading_message = get_loading_message()
        loading_placeholder.text(loading_message)
        
        try:
            result = process_func(*args, **kwargs)
        except Exception as e:
            loading_placeholder.error(f"An error occurred: {str(e)}. Retrying...")
            time.sleep(1)
    
    loading_placeholder.empty()
    return result