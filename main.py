import streamlit as st
from app.streamlit_web_scraper_chat import StreamlitWebScraperChat
from app.ui_components import display_info_icons, display_message
from app.utils import loading_animation, get_loading_message

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

    if "processing" not in st.session_state:
        st.session_state.processing = False

    chat_container = st.container()

    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                display_message(message)

    if prompt := st.chat_input("Enter the URL to scrape or ask a question regarding the data", key="user_input"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.processing = True
        st.rerun()

    if st.session_state.processing:
        with st.chat_message("assistant"):
            try:
                full_response = loading_animation(
                    safe_process_message,
                    st.session_state.web_scraper_chat,
                    st.session_state.messages[-1]["content"]
                )
                if full_response is not None:
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
            except Exception as e:
                st.error(f"An unexpected error occurred: {str(e)}")
            finally:
                st.session_state.processing = False
        st.rerun()

    st.markdown(
        """
        <p style="text-align: center; font-size: 12px; color: #999;">CyberScraper 2077 can make mistakes sometimes. Report any issues to the developers.</p>
        """,
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()