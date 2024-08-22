import time
import streamlit as st
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
        "Crashing through the data barriers, Johnny-style...",
        "Data extraction in progress—neon lights flickering...",
        "Hacking the matrix, one data stream at a time...",
        "Engaging in data warfare, zero tolerance...",
        "Decrypting the web’s secrets, no going back...",
        "Plundering the net’s underbelly, Cyberpunk style...",
        "Overloading the data circuits, full throttle...",
        "Breach detected—data infiltration in full swing...",
        "Running stealth protocols, data extraction initiated...",
        "Reprogramming the data streams—Neo’s got nothing on us...",
        "Surging through the web’s dark alleys, data secured...",
        "Unleashing the data chaos—no boundaries...",
        "Breaking through digital fortresses, one byte at a time...",
        "Cracking the net’s encryption—data heist in motion...",
        "Navigating the data labyrinth, Cyberpunk flair...",
        "Infiltrating the data vaults—high-tech heist underway..."
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
        
        with st.spinner(loading_message):
            try:
                result = process_func(*args, **kwargs)
            except Exception as e:
                loading_placeholder.error(f"An error occurred: {str(e)}. Retrying...")
                time.sleep(1)
    
    loading_placeholder.empty()
    st.success("Done!")
    return result
