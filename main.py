import warnings

# Suppress Pydantic V1 warning - upstream LangChain issue with Python 3.14
# See: https://github.com/langchain-ai/langchain/issues/33926
warnings.filterwarnings("ignore", message="Core Pydantic V1 functionality")

import streamlit as st

import streamlit.runtime.scriptrunner_utils.script_run_context as _ctx
_original_get_script_run_ctx = _ctx.get_script_run_ctx
_ctx.get_script_run_ctx = lambda suppress_warning=True: _original_get_script_run_ctx(suppress_warning=suppress_warning)
import json
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from app.streamlit_web_scraper_chat import StreamlitWebScraperChat
from app.ui_components import display_info_icons, extract_data_from_markdown, format_data
from app.utils import loading_animation
from src.web_extractor import extract_url, get_website_name
from datetime import datetime, timedelta
from src.ollama_models import OllamaModel
from src.utils.error_handler import ErrorMessages
import pandas as pd
import base64
from google_auth_oauthlib.flow import Flow
from io import BytesIO
from src.utils.google_sheets_utils import SCOPES, get_redirect_uri, display_google_sheets_button, initiate_google_auth
from src.scrapers.playwright_scraper import ScraperConfig
import time
import atexit
import logging

logger = logging.getLogger(__name__)

def handle_oauth_callback():
    if 'code' in st.query_params:
        try:
            flow = Flow.from_client_secrets_file(
                'client_secret.json',
                scopes=SCOPES,
                redirect_uri=get_redirect_uri()
            )
            flow.fetch_token(code=st.query_params['code'])
            st.session_state['google_auth_token'] = flow.credentials.to_json()
            st.success("Successfully authenticated with Google!")
            st.query_params.clear()
        except FileNotFoundError:
            st.error(ErrorMessages.OAUTH_FAILED)
            logger.error("client_secret.json not found")
        except Exception as e:
            st.error(f"{ErrorMessages.OAUTH_FAILED}\n\nDetails: {str(e)}")
            logger.error(f"OAuth error: {str(e)}")

def serialize_bytesio(obj):
    if isinstance(obj, BytesIO):
        return {
            "_type": "BytesIO",
            "data": base64.b64encode(obj.getvalue()).decode('utf-8')
        }
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def deserialize_bytesio(obj):
    if isinstance(obj, dict) and "_type" in obj and obj["_type"] == "BytesIO":
        return BytesIO(base64.b64decode(obj["data"]))
    return obj

def save_chat_history(chat_history):
    with open("chat_history.json", "w") as f:
        json.dump(chat_history, f, default=serialize_bytesio)

def load_chat_history():
    try:
        with open("chat_history.json", "r") as f:
            return json.load(f, object_hook=deserialize_bytesio)
    except FileNotFoundError:
        return {}

def safe_process_message(web_scraper_chat, message, conversation_history=None):
    if message is None or message.strip() == "":
        return "I'm sorry, but I didn't receive any input. Could you please try again?"
    try:
        progress_placeholder = st.empty()
        progress_placeholder.text("Initializing scraper...")

        start_time = time.time()
        response = web_scraper_chat.process_message(message, conversation_history)
        end_time = time.time()

        progress_placeholder.text(f"Scraping completed in {end_time - start_time:.2f} seconds.")

        # Check for error messages in response
        if isinstance(response, str) and ("Error:" in response or "Failed to" in response or "is missing" in response):
            st.error(response)

        if isinstance(response, tuple):
            if len(response) == 2 and isinstance(response[1], pd.DataFrame):
                csv_string, df = response
                st.dataframe(df)

                csv_buffer = BytesIO()
                df.to_csv(csv_buffer, index=False)
                csv_buffer.seek(0)
                st.download_button(
                    label="Download CSV",
                    data=csv_buffer,
                    file_name="data.csv",
                    mime="text/csv"
                )

                return csv_string
            elif len(response) == 2 and isinstance(response[0], BytesIO):
                excel_buffer, df = response
                st.dataframe(df)

                excel_buffer.seek(0)
                st.download_button(
                    label="Download Excel",
                    data=excel_buffer,
                    file_name="data.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                return ("Excel data displayed and available for download.", excel_buffer)
        elif isinstance(response, pd.DataFrame):
            st.dataframe(response)

            csv_buffer = BytesIO()
            response.to_csv(csv_buffer, index=False)
            csv_buffer.seek(0)
            st.download_button(
                label="Download CSV",
                data=csv_buffer,
                file_name="data.csv",
                mime="text/csv"
            )

            return "DataFrame displayed and available for download as CSV."

        return response
    except ValueError as e:
        # Handle API key errors specifically
        error_msg = str(e)
        if "API Key" in error_msg or "missing" in error_msg.lower():
            st.error(error_msg)
        else:
            st.error(f"{ErrorMessages.SCRAPING_FAILED}\n\nDetails: {error_msg}")
        logger.error(f"ValueError during processing: {error_msg}")
        return error_msg
    except Exception as e:
        st.error(f"{ErrorMessages.GENERIC_ERROR}\n\nDetails: {str(e)}")
        logger.error(f"Unexpected error during processing: {str(e)}")
        return f"{ErrorMessages.GENERIC_ERROR}\n\nDetails: {str(e)}"

def get_date_group(date_str):
    date = datetime.strptime(date_str, "%Y-%m-%d")
    today = datetime.now().date()
    if date.date() == today:
        return "Today"
    elif date.date() == today - timedelta(days=1):
        return "Yesterday"
    elif date.date() > today - timedelta(days=7):
        return date.strftime("%A")
    else:
        return date.strftime("%B %d, %Y")

def get_last_url_from_chat(messages):
    for message in reversed(messages):
        if message['role'] == 'user':
            url = extract_url(message['content'])
            if url:
                return url
    return None

def initialize_web_scraper_chat(url=None):
    if st.session_state.selected_model.startswith("ollama:"):
        model = st.session_state.selected_model
    else:
        model = st.session_state.selected_model

    scraper_config = ScraperConfig(
        use_current_browser=st.session_state.use_current_browser,
        headless=not st.session_state.use_current_browser,
        max_retries=3,
        delay_after_load=5,
        debug=True,
        wait_for='domcontentloaded'
    )

    try:
        web_scraper_chat = StreamlitWebScraperChat(model_name=model, scraper_config=scraper_config)
        if url:
            web_scraper_chat.process_message(url)

            website_name = get_website_name(url)
            st.session_state.chat_history[st.session_state.current_chat_id]["name"] = website_name

        return web_scraper_chat
    except ValueError as e:
        # Handle API key errors
        st.error(str(e))
        return None
    except Exception as e:
        st.error(f"{ErrorMessages.GENERIC_ERROR}\n\nDetails: {str(e)}")
        logger.error(f"Error initializing web scraper: {str(e)}")
        return None

async def list_ollama_models():
    try:
        return await OllamaModel.list_models()
    except Exception as e:
        logger.warning(f"Error fetching Ollama models: {str(e)}")
        # Don't show error to user, just return empty list
        # The warning in the sidebar will guide users
        return []

def load_css():
    with open("app/styles.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

@st.cache_data
def get_image_base64(image_path: str) -> str:
    """Get base64 encoded image with caching to avoid re-encoding on every render."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()


def check_service_status() -> dict:
    """Check the status of all services and return a dict with their status."""
    status = {
        "openai": {
            "name": "OpenAI",
            "configured": bool(os.getenv("OPENAI_API_KEY")),
            "env_var": "OPENAI_API_KEY"
        },
        "gemini": {
            "name": "Gemini",
            "configured": bool(os.getenv("GOOGLE_API_KEY")),
            "env_var": "GOOGLE_API_KEY"
        },
        "litellm": {
            "name": "LiteLLM",
            "configured": bool(os.getenv("LITELLM_API_KEY")),
            "env_var": "LITELLM_API_KEY"
        },
        "tor": {
            "name": "Tor",
            "configured": False,  # Will be checked dynamically
            "env_var": None
        },
        "google_sheets": {
            "name": "Google Sheets",
            "configured": os.path.exists("client_secret.json"),
            "env_var": "client_secret.json"
        }
    }

    # Check Tor status by checking if port 9050 is open
    import socket

    def is_tor_running():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', 9050))
            sock.close()
            return result == 0
        except Exception:
            return False

    status["tor"]["configured"] = is_tor_running()

    return status


def display_service_status():
    """Display service status with checkmarks/crosses in the sidebar."""
    status = check_service_status()

    # Inject CSS styles
    st.markdown("""
    <style>
        div[data-testid="stSidebar"] > div:first-child {
            overflow: visible !important;
        }
        .service-status {
            display: flex;
            align-items: center;
            margin: 1px 0;
        }
        .status-icon {
            width: 25px;
            font-size: 18px;
            text-align: center;
            margin-right: 8px;
        }
        .status-icon-check {
            color: #28a745;
        }
        .status-icon-cross {
            color: #dc3545;
        }
        .status-text {
            flex: 1;
            font-size: 14px;
        }
        .status-env {
            font-size: 11px;
            color: #6c757d;
            margin-left: 4px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### Setup Status")

    for key, info in status.items():
        if info["configured"]:
            icon_html = f'<span class="status-icon status-icon-check">✓</span>'
            env_html = ""
        else:
            icon_html = f'<span class="status-icon status-icon-cross">✗</span>'
            if info["env_var"]:
                env_html = f'<span class="status-env">({info["env_var"]})</span>'
            else:
                env_html = '<span class="status-env">(Tor not running)</span>'

        html = f"""
            <div class="service-status">
                {icon_html}
                <span class="status-text">{info["name"]}</span>
                {env_html}
            </div>
        """
        st.markdown(html, unsafe_allow_html=True)

    # Show setup help if any service is missing
    missing_services = [key for key, info in status.items() if not info["configured"]]
    if missing_services:
        st.markdown("---")
        st.markdown("""<p style="margin: 0; padding: 0; line-height: 1.4;"><strong>Setup Help:</strong><br>
See <a href="https://github.com/itsOwen/CyberScraper-2077/blob/main/README.md">README</a> for configuration instructions.</p>""", unsafe_allow_html=True)

def render_message(role, content, avatar_path):
    message_class = "user-message" if role == "user" else "assistant-message"
    avatar_base64 = get_image_base64(avatar_path)
    return f"""
    <div class="chat-message {message_class}">
        <div class="avatar">
            <img src="data:image/png;base64,{avatar_base64}" alt="{role} avatar">
        </div>
        <div class="message-content">{content}</div>
    </div>
    """

def display_message_with_sheets_upload(message, message_index):
    content = message["content"]
    if isinstance(content, (str, bytes, BytesIO)):
        data = extract_data_from_markdown(content)
        if data is not None:
            try:
                is_excel = isinstance(data, BytesIO) or (isinstance(content, str) and 'excel' in content.lower())
                if is_excel:
                    df = format_data(data, 'excel')
                else:
                    df = format_data(data, 'csv')
                
                if df is not None:
                    st.dataframe(df)
                    
                    if not is_excel:
                        csv_buffer = BytesIO()
                        df.to_csv(csv_buffer, index=False)
                        csv_buffer.seek(0)
                        st.download_button(
                            label="📥 Download as CSV",
                            data=csv_buffer,
                            file_name="data.csv",
                            mime="text/csv",
                            key=f"csv_download_{message_index}"
                        )
                    else:
                        excel_buffer = BytesIO()
                        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False, sheet_name='Sheet1')
                        excel_buffer.seek(0)
                        st.download_button(
                            label="📥 Download as Excel",
                            data=excel_buffer,
                            file_name="data.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"excel_download_{message_index}"
                        )
                    
                    display_google_sheets_button(df, f"sheets_upload_{message_index}")
                else:
                    st.warning("Failed to display data as a table. Showing raw content:")
                    st.code(content)
            except Exception as e:
                st.error(f"Error processing data: {str(e)}")
                st.code(content)
        else:
            st.markdown(content)
    else:
        st.markdown(str(content))

def cleanup():
    """Clean up resources on exit."""
    try:
        if 'web_scraper_chat' in st.session_state and st.session_state.web_scraper_chat:
            del st.session_state.web_scraper_chat
    except Exception:
        pass  # Ignore errors during cleanup

atexit.register(cleanup)

def main():

    st.set_page_config(
        page_title="CyberScraper 2077",
        page_icon="app/icons/radiation.png",
        layout="wide"
    )

    load_css()

    handle_oauth_callback()

    # avatar paths
    user_avatar_path = "app/icons/man.png"
    ai_avatar_path = "app/icons/skull.png"

    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = load_chat_history()
    if 'current_chat_id' not in st.session_state or st.session_state.current_chat_id not in st.session_state.chat_history:
        if st.session_state.chat_history:
            st.session_state.current_chat_id = next(iter(st.session_state.chat_history))
        else:
            new_chat_id = str(datetime.now().timestamp())
            st.session_state.chat_history[new_chat_id] = {
                "messages": [],
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            st.session_state.current_chat_id = new_chat_id
            save_chat_history(st.session_state.chat_history)
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = "gpt-4.1-mini"
    if 'web_scraper_chat' not in st.session_state:
        st.session_state.web_scraper_chat = None

    with st.sidebar:
        st.title("CyberScraper-2077")

        # Model selection
        st.subheader("Select Model")
        default_models = ["gpt-4.1-mini", "gpt-4o-mini", "gemini-1.5-flash", "gemini-pro"]
        ollama_models = st.session_state.get('ollama_models', [])
        litellm_models = [
            f"litellm:{model.strip()}"
            for model in os.getenv("LITELLM_MODELS", "").split(",")
            if model.strip()
        ]
        all_models = default_models + litellm_models + [f"ollama:{model}" for model in ollama_models]
        selected_model = st.selectbox("Choose a model", all_models, index=all_models.index(st.session_state.selected_model) if st.session_state.selected_model in all_models else 0)

        if selected_model != st.session_state.selected_model:
            st.session_state.selected_model = selected_model
            st.session_state.web_scraper_chat = None
            st.rerun()

        # Display service status with checkmarks/crosses
        display_service_status()

        st.markdown("---")

        st.session_state.use_current_browser = st.checkbox("Use Current Browser (No Docker)", value=False, help="Works Natively, Doesn't Work with Docker. if a website is blocking your browser, you can use this option to use the current browser instead of opening a new one.")

        if st.button("Refresh Ollama Models"):
            with st.spinner("Fetching Ollama models..."):
                st.session_state.ollama_models = asyncio.run(list_ollama_models())
            st.success(f"Found {len(st.session_state.ollama_models)} Ollama models")
            st.rerun()

        if st.button("+ 🗨️ New Chat", key="new_chat", use_container_width=True):
            new_chat_id = str(datetime.now().timestamp())
            st.session_state.chat_history[new_chat_id] = {
                "messages": [],
                "date": datetime.now().strftime("%Y-%m-%d"),
                "name": "🗨️ New Chat"
            }
            st.session_state.current_chat_id = new_chat_id
            st.session_state.web_scraper_chat = None
            save_chat_history(st.session_state.chat_history)
            st.rerun()

        grouped_chats = {}
        for chat_id, chat_data in st.session_state.chat_history.items():
            date_group = get_date_group(chat_data['date'])
            if date_group not in grouped_chats:
                grouped_chats[date_group] = []
            grouped_chats[date_group].append((chat_id, chat_data))

        for date_group, chats in grouped_chats.items():
            st.markdown(f"<div class='date-group'>{date_group}</div>", unsafe_allow_html=True)
            for chat_id, chat_data in chats:
                button_label = chat_data.get('name', "🗨️ Unnamed Chat")

                col1, col2 = st.columns([0.78, 0.22])

                with col1:
                    if st.button(button_label, key=f"history_{chat_id}", use_container_width=True):
                        st.session_state.current_chat_id = chat_id
                        messages = chat_data['messages']
                        last_url = get_last_url_from_chat(messages)
                        if last_url and not st.session_state.web_scraper_chat:
                            st.session_state.web_scraper_chat = initialize_web_scraper_chat(last_url)
                        st.rerun()

                with col2:
                    if st.button("🗑️", key=f"delete_{chat_id}"):
                        del st.session_state.chat_history[chat_id]
                        save_chat_history(st.session_state.chat_history)
                        if st.session_state.current_chat_id == chat_id:
                            if st.session_state.chat_history:
                                st.session_state.current_chat_id = next(iter(st.session_state.chat_history))
                            else:
                                st.session_state.current_chat_id = None
                            st.session_state.web_scraper_chat = None
                        st.rerun()

    st.markdown(
        """
        <h1 style="text-align: center; font-size: 30px; color: #333;">CyberScraper 2077</h1>
        """,
        unsafe_allow_html=True
    )

    display_info_icons()

    if st.session_state.current_chat_id not in st.session_state.chat_history:
        if st.session_state.chat_history:
            st.session_state.current_chat_id = next(iter(st.session_state.chat_history))
        else:
            new_chat_id = str(datetime.now().timestamp())
            st.session_state.chat_history[new_chat_id] = {
                "messages": [],
                "date": datetime.now().strftime("%Y-%m-%d")
            }
            st.session_state.current_chat_id = new_chat_id
            save_chat_history(st.session_state.chat_history)

    chat_container = st.container()

    with chat_container:
        st.markdown('<div class="chat-container">', unsafe_allow_html=True)
        for index, message in enumerate(st.session_state.chat_history[st.session_state.current_chat_id]["messages"]):
            if message["role"] == "user":
                st.markdown(render_message("user", message["content"], user_avatar_path), unsafe_allow_html=True)
            else:
                with st.container():
                    st.markdown(render_message("assistant", "", ai_avatar_path), unsafe_allow_html=True)
                    display_message_with_sheets_upload(message, index)
        st.markdown('</div>', unsafe_allow_html=True)

    prompt = st.chat_input("Enter the URL to scrape or ask a question regarding the data", key="user_input")

    if prompt:
        st.session_state.chat_history[st.session_state.current_chat_id]["messages"].append({"role": "user", "content": prompt})

        if not st.session_state.web_scraper_chat:
            st.session_state.web_scraper_chat = initialize_web_scraper_chat()

        url = extract_url(prompt)
        if url:
            website_name = get_website_name(url)
            st.session_state.chat_history[st.session_state.current_chat_id]["name"] = website_name

        with st.chat_message("assistant"):
            try:
                # Get current chat messages for conversation context
                chat_messages = st.session_state.chat_history[st.session_state.current_chat_id]["messages"]
                full_response = loading_animation(
                    safe_process_message,
                    st.session_state.web_scraper_chat,
                    prompt,
                    chat_messages
                )
                if isinstance(full_response, str) and not full_response.startswith("Error:"):
                    st.success("Scraping completed successfully!")

                if full_response is not None:
                    if isinstance(full_response, tuple) and len(full_response) == 2 and isinstance(full_response[1], BytesIO):
                        st.session_state.chat_history[st.session_state.current_chat_id]["messages"].append({"role": "assistant", "content": full_response[0]})
                    else:
                        st.session_state.chat_history[st.session_state.current_chat_id]["messages"].append({"role": "assistant", "content": full_response})
                    save_chat_history(st.session_state.chat_history)
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
            save_chat_history(st.session_state.chat_history)
            st.rerun()

    st.markdown(
        """
        <p style="text-align: center; font-size: 12px; color: #666666;">CyberScraper 2077 can make mistakes sometimes. Report any issues to the developers.</p>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
