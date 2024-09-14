import streamlit as st
import json
import asyncio
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
from langchain.chat_models import ChatOpenAI
from langchain.llms import OpenAI

# AI Feature: Auto-Summarization and Analysis
def summarize_and_analyze(content):
    llm = OpenAI(model_name="text-davinci-003")
    summary_prompt = f"Please summarize and analyze the following content: {content}"
    response = llm.predict(summary_prompt)
    return response

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
        response = web_scraper_chat.process_message(message)
        st.write("Debug: Response type:", type(response))
        
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
        else:
            st.write("Debug: Response is not a tuple")
        
        # AI Feature: Summarize and Analyze
        summary = summarize_and_analyze(response)
        st.write("AI Summary and Analysis:", summary)
        
        return response
    except AttributeError as e:
        if "'NoneType' object has no attribute 'lower'" in str(e):
            return "I encountered an issue while processing your request. It seems like I received an unexpected empty value. Could you please try rephrasing your input?"
        else:
            raise e
    except Exception as e:
        st.write("Debug: Exception occurred:", str(e))
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
        model = OllamaModel(st.session_state.selected_model[7:])
    else:
        model = st.session_state.selected_model
    web_scraper_chat = StreamlitWebScraperChat(model_name=model)
    if url:
        web_scraper_chat.process_message(url)
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
