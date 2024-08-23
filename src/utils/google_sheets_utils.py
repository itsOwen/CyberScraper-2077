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
import logging
import hashlib

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive.file']

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
    if 'google_auth_token' in st.session_state:
        try:
            creds = Credentials.from_authorized_user_info(json.loads(st.session_state['google_auth_token']), SCOPES)
            logger.debug("Loaded credentials from session state")
        except Exception as e:
            logger.error(f"Error loading credentials from session state: {str(e)}")
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logger.debug("Refreshed expired credentials")
                st.session_state['google_auth_token'] = creds.to_json()
            except Exception as e:
                logger.error(f"Error refreshing credentials: {str(e)}")
                creds = None
    
    return creds

def upload_to_google_sheets(df):
    creds = get_google_sheets_credentials()
    if not creds:
        logger.error("Failed to obtain valid credentials.")
        return None

    try:
        service = build('sheets', 'v4', credentials=creds)
        logger.debug("Built Sheets service")
        
        spreadsheet = {
            'properties': {
                'title': f"CyberScraper Data {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            }
        }
        spreadsheet = service.spreadsheets().create(body=spreadsheet, fields='spreadsheetId').execute()
        spreadsheet_id = spreadsheet.get('spreadsheetId')
        logger.debug(f"Created new spreadsheet with ID: {spreadsheet_id}")

        values = [df.columns.tolist()] + df.values.tolist()
        body = {'values': values}
        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id, range='Sheet1',
            valueInputOption='RAW', body=body).execute()
        logger.debug(f"Updated spreadsheet. Cells updated: {result.get('updatedCells')}")

        return spreadsheet_id
    except HttpError as error:
        logger.error(f"An HTTP error occurred: {error}")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        return None

def display_google_sheets_button(df):
    
    df_hash = hash(str(df))

    if 'google_auth_token' not in st.session_state:
        auth_button = '🔑 Authorize Google Sheets'
        if st.button(auth_button, key=f"auth_sheets_{df_hash}", help="Authorize access to Google Sheets"):
            initiate_google_auth()
    else:
        upload_button = '✅ Upload to Google Sheets'
        if st.button(upload_button, key=f"upload_{df_hash}", help="Upload data to Google Sheets"):
            with st.spinner("Uploading to Google Sheets..."):
                spreadsheet_id = upload_to_google_sheets(df)
                if spreadsheet_id:
                    st.success(f"Data uploaded successfully. Spreadsheet ID: {spreadsheet_id}")
                    st.markdown(f"[Open Spreadsheet](https://docs.google.com/spreadsheets/d/{spreadsheet_id})")
                else:
                    st.error("Failed to upload data to Google Sheets.")