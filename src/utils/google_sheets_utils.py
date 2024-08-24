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
from io import BytesIO

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']
TOKEN_FILE = 'token.json'

def get_redirect_uri():
    return st.get_option("server.baseUrlPath") or "http://localhost:8501"

def initiate_google_auth():
    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=SCOPES,
        redirect_uri=get_redirect_uri()
    )
    
    authorization_url, state = flow.authorization_url(prompt='consent')
    
    st.session_state['oauth_state'] = state
    st.markdown(f"Please visit this URL to authorize the application: [Auth URL]({authorization_url})")
    st.info("After authorizing, you'll be redirected back to this app. Then you can proceed with uploading.")

def get_google_sheets_credentials():
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
                    st.success(f"Data uploaded successfully. Spreadsheet ID: {spreadsheet_id}")
                    st.markdown(f"[Open Spreadsheet](https://docs.google.com/spreadsheets/d/{spreadsheet_id})")
                else:
                    st.error("Failed to upload data to Google Sheets. Check the console for error details.")