import streamlit as st
import json
import asyncio
import os
import sys
from app.streamlit_web_scraper_chat import StreamlitWebScraperChat
from app.ui_components import display_info_icons, display_message, extract_data_from_markdown, format_data
from app.utils import loading_animation, get_loading_message
from datetime import datetime, timedelta
from src.ollama_models import OllamaModel
import pandas as pd
import base64
from google_auth_oauthlib.flow import Flow
import io
from io import BytesIO
import re
from src.utils.google_sheets_utils import SCOPES, get_redirect_uri, display_google_sheets_button, initiate_google_auth
from src.web_extractor import ScrapelessConfig
import time
from urllib.parse import urlparse
import atexit

# Check for required API keys at startup
api_keys = {
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    "SCRAPELESS_API_KEY": os.environ.get("SCRAPELESS_API_KEY", ""),
    "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY", "")
}

# Print debug info about API keys without revealing full keys
for key_name, key_value in api_keys.items():
    is_set = bool(key_value)
    print(f"{key_name}: {'Set (' + key_value[:5] + '...)' if is_set else 'Not set'}")

# Initialize session state variables for content persistence
if 'current_url' not in st.session_state:
    st.session_state.current_url = None
if 'current_content' not in st.session_state:
    st.session_state.current_content = None
if 'preprocessed_content' not in st.session_state:
    st.session_state.preprocessed_content = None
if 'content_hash' not in st.session_state:
    st.session_state.content_hash = None

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
        except Exception as e:
            st.error(f"Error during OAuth callback: {str(e)}")

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

def safe_process_message(web_scraper_chat, message):
    if message is None or message.strip() == "":
        return "I'm sorry, but I didn't receive any input. Could you please try again?"
    try:
        progress_placeholder = st.empty()
        progress_placeholder.text("Initializing scraper...")
        
        start_time = time.time()
        response = web_scraper_chat.process_message(message)
        end_time = time.time()
        
        progress_placeholder.text(f"Scraping completed in {end_time - start_time:.2f} seconds.")
        
        st.write("Debug: Response type:", type(response))
        
        if isinstance(response, str):
            if "Error:" in response:
                st.error(response)
            else:
                st.write("Debug: Response content:", response[:500] + "..." if len(response) > 500 else response)

        if isinstance(response, tuple):
            st.write("Debug: Response is a tuple")
            if len(response) == 2 and isinstance(response[1], pd.DataFrame):
                st.write("Debug: CSV data detected")
                csv_string, df = response
                st.text("CSV Data:")
                st.code(csv_string, language="csv")
                st.text("Interactive Table:")
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
                st.write("Debug: Excel data detected")
                excel_buffer, df = response
                st.text("Excel Data:")
                st.dataframe(df)

                excel_buffer.seek(0)
                st.download_button(
                    label="Download Original Excel file",
                    data=excel_buffer,
                    file_name="data_original.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                excel_data = BytesIO()
                with pd.ExcelWriter(excel_data, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Sheet1')
                excel_data.seek(0)

                st.download_button(
                    label="Download Excel (from DataFrame)",
                    data=excel_data,
                    file_name="data_from_df.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                return ("Excel data displayed and available for download.", excel_buffer)
        elif isinstance(response, pd.DataFrame):
            st.write("Debug: Response is a DataFrame")
            st.text("Data:")
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
        else:
            st.write("Debug: Response is not a tuple or DataFrame")

        return response
    except Exception as e:
        st.error(f"An error occurred during scraping: {str(e)}")
        return f"An unexpected error occurred: {str(e)}. Please try again or contact support if the issue persists."

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
        if message['role'] == 'user' and message['content'].lower().startswith('http'):
            return message['content']
    return None

def initialize_web_scraper_chat(url=None):
    if st.session_state.selected_model.startswith("ollama:"):
        model = st.session_state.selected_model
    else:
        model = st.session_state.selected_model
    
    api_key = os.getenv("SCRAPELESS_API_KEY", "")
    if not api_key:
        st.warning("SCRAPELESS_API_KEY is not set. Please set it in your environment variables.")
    
    scrapeless_config = ScrapelessConfig(
        api_key=api_key,
        proxy_country=st.session_state.get("proxy_country", "ANY"),
        timeout=30,
        debug=True,
        max_retries=3
    )
    
    web_scraper_chat = StreamlitWebScraperChat(model_name=model, scrapeless_config=scrapeless_config)
    if url:
        web_scraper_chat.process_message(url)
        
        website_name = get_website_name(url)
        st.session_state.chat_history[st.session_state.current_chat_id]["name"] = website_name
    
    return web_scraper_chat

async def list_ollama_models():
    try:
        return await OllamaModel.list_models()
    except Exception as e:
        st.error(f"Error fetching Ollama models: {str(e)}")
        return []

def load_css():
    with open("app/styles.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

def get_image_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

def get_website_name(url: str) -> str:
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    return domain.split('.')[0].capitalize()

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
    if 'web_scraper_chat' in st.session_state and st.session_state.web_scraper_chat:
        del st.session_state.web_scraper_chat

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
        st.session_state.selected_model = "gpt-4o-mini"
    if 'web_scraper_chat' not in st.session_state:
        st.session_state.web_scraper_chat = None
    if 'proxy_country' not in st.session_state:
        st.session_state.proxy_country = "ANY"

    with st.sidebar:
        st.title("Conversation History")

        # Model selection
        st.subheader("Select Model")
        default_models = ["gpt-4o-mini", "gpt-3.5-turbo", "gemini-1.5-flash", "gemini-pro"]
        ollama_models = st.session_state.get('ollama_models', [])
        all_models = default_models + [f"ollama:{model}" for model in ollama_models]
        selected_model = st.selectbox("Choose a model", all_models, index=all_models.index(st.session_state.selected_model) if st.session_state.selected_model in all_models else 0)

        if selected_model != st.session_state.selected_model:
            st.session_state.selected_model = selected_model
            st.session_state.web_scraper_chat = None
            st.rerun()

        # Display warnings for missing API keys
        if not os.getenv("OPENAI_API_KEY") and any(model.startswith(("gpt-", "text-")) for model in all_models):
            st.warning("OpenAI API Key is not set. Some models may not be available.")
        
        if not os.getenv("GOOGLE_API_KEY") and any(model.startswith("gemini-") for model in all_models):
            st.warning("Google API Key is not set. Gemini models may not be available.")
            
        if not os.getenv("SCRAPELESS_API_KEY"):
            st.warning("Scrapeless API Key is not set. Scraping functionality will not work.")

        # Scrapeless configuration
        st.sidebar.subheader("Scrapeless Configuration")
        proxy_countries = ["ANY", "US", "UK", "CA", "AU", "DE", "FR", "JP", "SG"]
        selected_country = st.sidebar.selectbox("Proxy Country", proxy_countries, index=0)
        
        if selected_country != st.session_state.proxy_country:
            st.session_state.proxy_country = selected_country
            if st.session_state.web_scraper_chat:
                st.session_state.web_scraper_chat = None

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

                col1, col2 = st.columns([0.85, 0.15])

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
        <p style="text-align: center; font-size: 18px; color: #666;">Powered by Scrapeless</p>
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

        if prompt.lower().startswith("http"):
            website_name = get_website_name(prompt)
            st.session_state.chat_history[st.session_state.current_chat_id]["name"] = website_name
            st.info(f"Scraping {website_name} using Scrapeless... This may take a moment.")
            # Clear previous content state when a new URL is entered
            st.session_state.current_content = None
            st.session_state.preprocessed_content = None

        with st.chat_message("assistant"):
            try:
                # Add debug output
                st.write(f"Debug - Has current content: {'Yes' if st.session_state.current_content else 'No'}")
                
                full_response = loading_animation(
                    safe_process_message,
                    st.session_state.web_scraper_chat,
                    prompt
                )
                
                # Check content state after processing
                st.write(f"Debug - After processing, has content: {'Yes' if st.session_state.current_content else 'No'}")
                
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