import streamlit as st
import time
import pandas as pd
import io
import re
from typing import Union
import csv

def display_info_icons():
    if "info_icons_displayed" not in st.session_state:
        st.session_state.info_icons_displayed = True
        st.session_state.info_icons_time = time.time()

    if st.session_state.info_icons_displayed:
        st.markdown(
            """
            <div style="display: flex; justify-content: center; align-items: center; flex-direction: column; gap: 10px; padding: 20px;">
                <div style="display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; max-width: 800px;">
                    <div class="info-box" data-type="enter-url">
                        <h3 style="color: #0066cc;">💻 Enter URL</h3>
                        <p style="color: #000000;">Fetch webpage content for extraction.</p>
                    </div>
                    <div class="info-box" data-type="specify-data">
                        <h3 style="color: #cc6600;">🔍 Specify Data</h3>
                        <p style="color: #000000;">Define what data you want to extract.</p>
                    </div>
                    <div class="info-box" data-type="save-data">
                        <h3 style="color: #006600;">💾 Save Data</h3>
                        <p style="color: #000000;">Save in JSON, CSV, or Excel format.</p>
                    </div>
                    <div class="info-box" data-type="convert-data">
                        <h3 style="color: #cc0000;">🔄 Convert Data</h3>
                        <p style="color: #000000;">Convert between different formats.</p>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if time.time() - st.session_state.info_icons_time > 10 or ("messages" in st.session_state and len(st.session_state.messages) > 0):
            st.session_state.info_icons_displayed = False

def extract_data_from_markdown(text: Union[str, bytes, io.BytesIO]) -> Union[str, bytes, None]:
    if isinstance(text, io.BytesIO):
        return text
    if isinstance(text, bytes):
        text = text.decode('utf-8')
    pattern = r'```(csv|excel)\n(.*?)\n```'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(2).strip()
    return None

def format_data(data: Union[str, bytes, io.BytesIO], format_type: str):
    try:
        if isinstance(data, io.BytesIO):
            data.seek(0)
            return pd.read_excel(data, engine='openpyxl')
        elif isinstance(data, bytes):
            return pd.read_excel(io.BytesIO(data), engine='openpyxl')
        else:
            if format_type == 'csv':
                csv_data = []
                csv_reader = csv.reader(io.StringIO(data))
                for row in csv_reader:
                    csv_data.append(row)
                
                if not csv_data:
                    raise ValueError("Empty CSV data")
                
                max_columns = max(len(row) for row in csv_data)
                
                padded_data = [row + [''] * (max_columns - len(row)) for row in csv_data]
                
                headers = padded_data[0]
                unique_headers = []
                for i, header in enumerate(headers):
                    if header == '' or header in unique_headers:
                        unique_headers.append(f'Column_{i+1}')
                    else:
                        unique_headers.append(header)
                
                df = pd.DataFrame(padded_data[1:], columns=unique_headers)
                
                df = df.loc[:, (df != '').any(axis=0)]
                
                return df
            elif format_type == 'excel':
                return pd.read_excel(io.BytesIO(data.encode()), engine='openpyxl')
    except Exception as e:
        st.error(f"Error formatting data: {str(e)}")
        st.error(f"Data type: {type(data)}")
        st.error(f"Data content: {data[:100] if isinstance(data, (str, bytes)) else 'BytesIO object'}")
        
        st.text("Raw data (first 500 characters):")
        st.text(data[:500] if isinstance(data, (str, bytes)) else "BytesIO object")
        
        return None

def display_message(message):
    content = message["content"]
    if isinstance(content, (str, bytes, io.BytesIO)):
        data = extract_data_from_markdown(content)
        if data is not None:
            if isinstance(data, io.BytesIO) or (isinstance(content, str) and 'excel' in content.lower()):
                df = format_data(data, 'excel')
            else:
                df = format_data(data, 'csv')
            
            if df is not None:
                st.dataframe(df)
            else:
                st.warning("Failed to display data as a table. Showing raw content:")
                st.code(content)
        else:
            st.markdown(content)
    else:
        st.markdown(str(content))