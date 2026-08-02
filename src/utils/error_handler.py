"""
Error handling utilities for CyberScraper-2077.

Provides user-friendly error messages with instructions and README links.
"""

import os


README_URL = "https://github.com/itsOwen/CyberScraper-2077/blob/main/README.md"


class ErrorMessages:
    """Centralized error messages with user-friendly instructions."""

    # Tor/Proxy errors
    TOR_PROXY_CONNECTION_FAILED = (
        "Failed to connect to Tor proxy.\n\n"
        "Install Tor:\n"
        "  Ubuntu/Debian: sudo apt install tor\n"
        "  macOS: brew install tor\n\n"
        "Start Tor:\n"
        "  Linux: sudo service tor start\n"
        "  macOS: brew services start tor\n\n"
        f"For more help, see: {README_URL}#-tor-network-scraping"
    )

    TOR_NOT_DETECTED = (
        "Connection is not using Tor network.\n\n"
        "Please verify your Tor configuration.\n\n"
        f"For help, see: {README_URL}#-tor-network-scraping"
    )

    ONION_URL_INVALID = (
        "Invalid onion URL provided.\n\n"
        "Onion URLs must end with '.onion'.\n\n"
        f"For more information, see: {README_URL}#-tor-network-scraping"
    )

    TOR_CONNECTION_ERROR = (
        "Unexpected Tor connection error.\n\n"
        "Please check:\n"
        "1. Tor is running (brew services list | grep tor)\n"
        "2. If just started, Tor needs 1-2 minutes to bootstrap\n"
        "   Check progress: tail /opt/homebrew/var/log/tor.log\n"
        "3. Wait for 'Bootstrapped 100%' before scraping .onion sites\n\n"
        f"For help, see: {README_URL}#-tor-network-scraping"
    )

    # API Key errors
    OPENAI_API_KEY_MISSING = (
        "OpenAI API Key is missing.\n\n"
        "Please set the OPENAI_API_KEY environment variable:\n"
        "1. Create a .env file in the project root\n"
        "2. Add: OPENAI_API_KEY=your_key_here\n"
        "3. Or export it: export OPENAI_API_KEY=your_key_here\n\n"
        f"For setup instructions, see: {README_URL}#installation"
    )

    GOOGLE_API_KEY_MISSING = (
        "Google API Key is missing.\n\n"
        "Please set the GOOGLE_API_KEY environment variable:\n"
        "1. Create a .env file in the project root\n"
        "2. Add: GOOGLE_API_KEY=your_key_here\n"
        "3. Or export it: export GOOGLE_API_KEY=your_key_here\n\n"
        f"For setup instructions, see: {README_URL}#installation"
    )

    OPENAI_API_KEY_INVALID = (
        "OpenAI API Key is invalid or expired.\n\n"
        "Please verify your API key at: https://platform.openai.com/api-keys\n\n"
        f"For help, see: {README_URL}#installation"
    )

    GOOGLE_API_KEY_INVALID = (
        "Google API Key is invalid or expired.\n\n"
        "Please verify your API key at: https://console.cloud.google.com/apis/credentials\n\n"
        f"For help, see: {README_URL}#installation"
    )

    # Ollama errors
    OLLAMA_NOT_RUNNING = (
        "Ollama is not running or not accessible.\n\n"
        "Please ensure:\n"
        "1. Ollama is installed and running\n"
        "2. Ollama is accessible at http://localhost:11434\n"
        "3. You have pulled the model you want to use\n\n"
        "Install Ollama: https://ollama.ai/download\n"
        f"For setup instructions, see: {README_URL}#ollama-setup"
    )

    OLLAMA_MODEL_NOT_FOUND = (
        "Ollama model not found.\n\n"
        "Please pull the model first:\n"
        "  ollama pull <model_name>\n\n"
        "List available models:\n"
        "  ollama list\n\n"
        f"For help, see: {README_URL}#ollama-setup"
    )

    # Scraping errors
    SCRAPING_FAILED = (
        "Failed to scrape the website.\n\n"
        "This could be due to:\n"
        "1. The website is blocking automated requests\n"
        "2. Network connectivity issues\n"
        "3. Invalid URL\n\n"
        "Try using the 'Use Current Browser' option in the sidebar.\n\n"
        f"For help, see: {README_URL}#troubleshooting"
    )

    URL_INVALID = (
        "Invalid URL provided.\n\n"
        "Please provide a valid URL starting with http:// or https://\n\n"
        f"For help, see: {README_URL}#usage"
    )

    TIMEOUT_ERROR = (
        "Request timed out.\n\n"
        "The website took too long to respond. This could be due to:\n"
        "1. Slow website response time\n"
        "2. Network connectivity issues\n"
        "3. The website is blocking requests\n\n"
        "Try again later or use the 'Use Current Browser' option.\n\n"
        f"For help, see: {README_URL}#troubleshooting"
    )

    # OAuth errors
    OAUTH_FAILED = (
        "Google OAuth authentication failed.\n\n"
        "Please ensure:\n"
        "1. client_secret.json exists in the project root\n"
        "2. The OAuth redirect URI is correctly configured\n"
        "3. You have authorized the application\n\n"
        f"For setup instructions, see: {README_URL}#google-sheets-integration"
    )

    OAUTH_TOKEN_MISSING = (
        "Google OAuth token is missing.\n\n"
        "Please authenticate with Google using the button in the sidebar.\n\n"
        f"For help, see: {README_URL}#google-sheets-integration"
    )

    # Generic error
    GENERIC_ERROR = (
        "An unexpected error occurred.\n\n"
        "Please try again. If the issue persists, please check the README for troubleshooting.\n\n"
        f"For help, see: {README_URL}#troubleshooting"
    )


def check_api_keys() -> list[str]:
    """
    Check for missing API keys and return list of missing keys.

    Returns:
        List of error messages for missing API keys
    """
    errors = []

    openai_models = ["gpt-4.1-mini", "gpt-4o-mini", "gpt-4", "gpt-3.5-turbo", "text-"]
    gemini_models = ["gemini-1.5-flash", "gemini-pro", "gemini-"]

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        errors.append(ErrorMessages.OPENAI_API_KEY_MISSING)

    # Check for Google API key
    if not os.getenv("GOOGLE_API_KEY"):
        errors.append(ErrorMessages.GOOGLE_API_KEY_MISSING)

    return errors


def check_model_api_key(model_name: str) -> str | None:
    """
    Check if the required API key for a model is present.

    Args:
        model_name: Name of the model to check

    Returns:
        Error message if API key is missing, None otherwise
    """
    if model_name.startswith(("gpt-", "text-")) and not os.getenv("OPENAI_API_KEY"):
        return ErrorMessages.OPENAI_API_KEY_MISSING

    if model_name.startswith("gemini-") and not os.getenv("GOOGLE_API_KEY"):
        return ErrorMessages.GOOGLE_API_KEY_MISSING

    if model_name.startswith("litellm:") and not os.getenv("LITELLM_API_KEY"):
        return (
            "LiteLLM API Key is missing. Set the LITELLM_API_KEY environment "
            "variable before using a litellm:<model> entry."
        )

    return None
