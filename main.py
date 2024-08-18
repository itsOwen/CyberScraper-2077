import streamlit as st
import time  
from app.streamlit_web_scraper_chat import StreamlitWebScraperChat
from app.ui_components import display_info_icons, display_message
from app.utils import get_loading_message

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

    st.markdown(
        """
        <h1 style="text-align: center; font-size: 30px; color: #333;">CyberScraper 2077</h1>
        """,
        unsafe_allow_html=True
    )

    default_model = "gpt-4o-mini"
    if "web_scraper_chat" not in st.session_state or st.session_state.selected_model != default_model:
        st.session_state.selected_model = default_model
        st.session_state.web_scraper_chat = StreamlitWebScraperChat(model_name=default_model)

    display_info_icons()

    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    chat_container = st.container()

    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                display_message(message)

    if prompt := st.chat_input("Enter the URL to scrape or ask a question regarding the data"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with chat_container:
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                loading_placeholder = st.empty()
                
                while True:
                    loading_placeholder.text(get_loading_message())
                    try:
                        full_response = st.session_state.web_scraper_chat.process_message(prompt)
                        break
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}. Retrying...")
                        time.sleep(1)
                
                loading_placeholder.empty()
                
                display_message({"role": "assistant", "content": full_response})
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})

    st.markdown(
        """
        <p style="text-align: center; font-size: 12px; color: #999;">CyberScraper 2077 can make mistakes sometimes. Report any issues to the developers.</p>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()