"""Utility functions for the Streamlit app."""

import streamlit as st
import random

# Loading messages for the cyberpunk theme
_LOADING_MESSAGES = (
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
    "Decrypting the web's secrets, no going back...",
    "Plundering the net's underbelly, Cyberpunk style...",
    "Overloading the data circuits, full throttle...",
    "Breach detected—data infiltration in full swing...",
    "Running stealth protocols, data extraction initiated...",
    "Reprogramming the data streams—Neo's got nothing on us...",
    "Surging through the web's dark alleys, data secured...",
    "Unleashing the data chaos—no boundaries...",
    "Breaking through digital fortresses, one byte at a time...",
    "Cracking the net's encryption—data heist in motion...",
    "Navigating the data labyrinth, Cyberpunk flair...",
    "Infiltrating the data vaults—high-tech heist underway...",
)


def get_loading_message() -> str:
    """Get a random cyberpunk-themed loading message."""
    return random.choice(_LOADING_MESSAGES)


def loading_animation(process_func, *args, **kwargs):
    """Run a function while showing a random cyberpunk-themed spinner message."""
    with st.spinner(get_loading_message()):
        return process_func(*args, **kwargs)
