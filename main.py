import streamlit as st
import json
from app.streamlit_web_scraper_chat import StreamlitWebScraperChat
from app.ui_components import display_info_icons, display_message
from app.utils import loading_animation, get_loading_message
from datetime import datetime, timedelta

def safe_process_message(web_scraper_chat, message):
    if message is None or message.strip() == "":
        return "I'm sorry, but I didn't receive any input. Could you please try again?"
    try:
        return web_scraper_chat.process_message(message)
    except AttributeError as e:
        if "'NoneType' object has no attribute 'lower'" in str(e):
            return "I encountered an issue while processing your request. It seems like I received an unexpected empty value. Could you please try rephrasing your input?"
        else:
            raise e
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}. Please try again or contact support if the issue persists."

def load_chat_history():
    try:
        with open("chat_history.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_chat_history(chat_history):
    with open("chat_history.json", "w") as f:
        json.dump(chat_history, f)

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
    web_scraper_chat = StreamlitWebScraperChat(model_name=st.session_state.selected_model)
    if url:
        web_scraper_chat.process_message(url)
    return web_scraper_chat

def main():
    st.set_page_config(page_title="CyberScraper 2077", page_icon="🌐", layout="wide")

    hide_streamlit_style = """
        <style>
            header {visibility: hidden;}
            .streamlit-footer {display: none;}
            .st-emotion-cache-uf99v8 {display: none;}
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

    st.markdown("""
    <style>
    .stSidebar {
        background-color: #f0f2f6;
        padding: 1rem;
    }
    .stSidebar .sidebar-content {
        padding: 0;
    }
    .sidebar-chat-button {
        background-color: #ffffff;
        color: #333333;
        border: 1px solid #e0e0e0;
        border-radius: 5px;
        padding: 0.5rem;
        margin-bottom: 0.5rem;
        text-align: left;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .sidebar-chat-button:hover {
        background-color: #f0f0f0;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
        display: flex;
        align-items: flex-start;
    }
    .chat-message.user {
        background-color: #f0f2f6;
    }
    .chat-message.bot {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
    }
    .chat-message .avatar {
        width: 30px;
        height: 30px;
        border-radius: 2px;
        object-fit: cover;
        margin-right: 1rem;
    }
    .chat-message .message {
        flex-grow: 1;
        color: #333333;
    }
    .date-group {
        color: #666666;
        font-size: 0.8rem;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .delete-button {
        color: #666666;
        background: none;
        border: none;
        cursor: pointer;
        margin-left: 0.5rem;
    }
    .delete-button:hover {
        color: #333333;
    }
    </style>
    """, unsafe_allow_html=True)

    # Initialize session state
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

    with st.sidebar:
        st.title("Conversation History")
        if st.button("+ 🗨️ New Chat", key="new_chat", use_container_width=True):
            new_chat_id = str(datetime.now().timestamp())
            st.session_state.chat_history[new_chat_id] = {
                "messages": [],
                "date": datetime.now().strftime("%Y-%m-%d")
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
                messages = chat_data['messages']
                if messages:
                    button_label = f"{messages[0]['content'][:25]}..."
                else:
                    button_label = "🗨️ Empty Chat"
                
                col1, col2 = st.columns([0.85, 0.15]) 
                
                with col1:
                    if st.button(button_label, key=f"history_{chat_id}", use_container_width=True):
                        st.session_state.current_chat_id = chat_id
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
        for message in st.session_state.chat_history[st.session_state.current_chat_id]["messages"]:
            with st.chat_message(message["role"]):
                display_message(message)

    prompt = st.chat_input("Enter the URL to scrape or ask a question regarding the data", key="user_input")

    if prompt:
        st.session_state.chat_history[st.session_state.current_chat_id]["messages"].append({"role": "user", "content": prompt})
        save_chat_history(st.session_state.chat_history)
        
        if not st.session_state.web_scraper_chat:
            st.session_state.web_scraper_chat = initialize_web_scraper_chat()

        with st.chat_message("assistant"):
            try:
                full_response = loading_animation(
                    safe_process_message,
                    st.session_state.web_scraper_chat,
                    prompt
                )
                if full_response is not None:
                    st.session_state.chat_history[st.session_state.current_chat_id]["messages"].append({"role": "assistant", "content": full_response})
                    save_chat_history(st.session_state.chat_history)
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
        
        st.rerun()

    st.markdown(
        """
        <p style="text-align: center; font-size: 12px; color: #666666;">CyberScraper 2077 can make mistakes sometimes. Report any issues to the developers.</p>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()