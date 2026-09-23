import streamlit as st
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
import pandas as pd
from datetime import datetime
import os
import json
import hashlib
import re
import threading
import time
from io import BytesIO

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
TOKEN_FILE = 'token.json'

OAUTH_STATE_TTL_SECONDS = 600

# Google redirects back into a brand new Streamlit session, so pending
# authorization requests are kept per process instead of in session_state.
_pending_oauth_states: dict[str, tuple[str | None, float]] = {}
_pending_oauth_lock = threading.Lock()


def get_redirect_uri():
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
    if redirect_uri:
        return redirect_uri
    port = st.get_option("server.port") or 8501
    base_path = (st.get_option("server.baseUrlPath") or "").strip("/")
    return f"http://localhost:{port}/" + (f"{base_path}/" if base_path else "")


def remember_oauth_state(state: str, code_verifier: str | None) -> None:
    now = time.time()
    with _pending_oauth_lock:
        for key, (_, created) in list(_pending_oauth_states.items()):
            if now - created > OAUTH_STATE_TTL_SECONDS:
                del _pending_oauth_states[key]
        _pending_oauth_states[state] = (code_verifier, now)


def pop_pending_oauth_state(state: str | None) -> str | None:
    """Return the PKCE code verifier for a pending authorization request, or None if the state is unknown."""
    if not state:
        return None
    with _pending_oauth_lock:
        entry = _pending_oauth_states.pop(state, None)
    if entry is None:
        return None
    code_verifier, created = entry
    if time.time() - created > OAUTH_STATE_TTL_SECONDS:
        return None
    # An empty string still marks the state as known when the flow did not use PKCE.
    return code_verifier or ""

def initiate_google_auth():
    if not os.path.exists('client_secret.json'):
        st.error("Google Sheets integration is not set up correctly.")
        st.markdown(
            "Please follow the setup guide for Google Sheets integration in the "
            "[CyberScraper-2077 README](https://github.com/itsOwen/CyberScraper-2077/blob/main/README.md#setup-google-sheets-authentication)."
        )
        st.info("Once you've completed the setup, restart the application.")
        return

    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=SCOPES,
        redirect_uri=get_redirect_uri()
    )
    
    authorization_url, state = flow.authorization_url(prompt='consent')

    remember_oauth_state(state, flow.code_verifier)
    st.markdown(f"Please visit this URL to authorize the application: [Auth URL]({authorization_url})")
    st.info("After authorizing, you'll be redirected back to this app. Then you can proceed with uploading.")

def get_google_sheets_credentials():
    if not os.path.exists('client_secret.json'):
        return None

    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception as e:
            print(f"Error loading credentials from file: {str(e)}")
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                save_credentials(creds)
            except Exception as e:
                print(f"Error refreshing credentials: {str(e)}")
                creds = None
        else:
            creds = None
    
    if not creds:
        if 'google_auth_token' in st.session_state:
            try:
                creds = Credentials.from_authorized_user_info(json.loads(st.session_state['google_auth_token']), SCOPES)
                save_credentials(creds)
            except Exception as e:
                print(f"Error creating credentials from session state: {str(e)}")
    return creds

def save_credentials(creds):
    try:
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    except Exception as e:
        print(f"Error saving credentials: {str(e)}")

def clean_data_for_sheets(df):
    def clean_value(val):
        if pd.isna(val):
            return ""
        if isinstance(val, (int, float)):
            return str(val)
        return str(val).replace('\n', ' ').replace('\r', '')

    for col in df.columns:
        df[col] = df[col].map(clean_value)

    if 'comments' in df.columns:
        df['comments'] = df['comments'].astype(str)

    return df

def upload_to_google_sheets(data):
    creds = get_google_sheets_credentials()
    if not creds:
        return None

    try:
        service = build('sheets', 'v4', credentials=creds)        
        spreadsheet = {
            'properties': {
                'title': f"CyberScraper Data {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')

        if isinstance(data, pd.DataFrame):
            df = clean_data_for_sheets(data)
        else:
            return None

        values = [df.columns.tolist()] + df.values.tolist()
        body = {'values': values}
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range='Sheet1',
            valueInputOption='RAW', body=body).execute()
        return spreadsheet_id
    except HttpError as error:
        print(f"An HTTP error occurred: {error}")
        return None
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None

def display_google_sheets_button(data, unique_key):
    if not os.path.exists('client_secret.json'):
        st.warning("Google Sheets integration is not set up.")
        st.markdown(
            "To enable Google Sheets integration, please follow the setup guide in the "
            "[CyberScraper-2077 README](https://github.com/itsOwen/CyberScraper-2077/blob/main/README.md#setup-google-sheets-authentication)."
        )
        return

    creds = get_google_sheets_credentials()
    if not creds:
        auth_button = '🔑 Authorize Google Sheets'
        if st.button(auth_button, key=f"auth_sheets_{unique_key}", help="Authorize access to Google Sheets"):
            initiate_google_auth()
    else:
        upload_button = '✅ Upload to Google Sheets'
        if st.button(upload_button, key=f"upload_{unique_key}", help="Upload data to Google Sheets"):
            with st.spinner("Uploading to Google Sheets..."):
                spreadsheet_id = upload_to_google_sheets(data)
                if spreadsheet_id:
                    st.success(f"Hey Choom! Data uploaded successfully. Spreadsheet ID: {spreadsheet_id}")
                    st.markdown(f"[Open Spreadsheet](https://docs.google.com/spreadsheets/d/{spreadsheet_id})")
                else:
                    st.error("Failed to upload data to Google Sheets. Check the console for error details.")
