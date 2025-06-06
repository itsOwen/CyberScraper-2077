from typing import Dict, Any, Optional, List, Tuple, Union, Callable
import json
import pandas as pd
from io import StringIO, BytesIO
import base64
import re
from functools import lru_cache
import hashlib
from .models import Models
from .ollama_models import OllamaModel, OllamaModelManager
from .utils.markdown_formatter import MarkdownFormatter
from .prompts import get_prompt_for_model
from langchain.schema.runnable import RunnableSequence
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
import csv
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse
import streamlit as st
import os
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from scrapeless import ScrapelessClient

class ScrapelessConfig:
    """Configuration for Scrapeless SDK"""
    def __init__(self, 
                 api_key: Optional[str] = None,
                 proxy_country: str = "ANY",
                 timeout: int = 30,
                 debug: bool = False,
                 max_retries: int = 3):
        self.api_key = api_key or os.getenv("SCRAPELESS_API_KEY", "")
        self.proxy_country = proxy_country
        self.timeout = timeout
        self.debug = debug
        self.max_retries = max_retries

class WebExtractor:
    def __init__(self, model_name: str = "gpt-4o-mini", model_kwargs: Dict[str, Any] = None,
                 scrapeless_config: ScrapelessConfig = None):
        model_kwargs = model_kwargs or {}
        if isinstance(model_name, str) and model_name.startswith("ollama:"):
            self.model = OllamaModelManager.get_model(model_name[7:])
        elif isinstance(model_name, OllamaModel):
            self.model = model_name
        elif model_name.startswith("gemini-"):
            genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
            self.model = ChatGoogleGenerativeAI(model=model_name, **model_kwargs)
        else:
            self.model = Models.get_model(model_name, **model_kwargs)
        
        self.model_name = model_name
        self.scrapeless_config = scrapeless_config or ScrapelessConfig()
        self.scrapeless = ScrapelessClient(api_key=self.scrapeless_config.api_key)
        self.markdown_formatter = MarkdownFormatter()
        self.current_url = None
        self.current_content = None
        self.preprocessed_content = None
        self.conversation_history: List[str] = []
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=32000,
            chunk_overlap=200,
            length_function=self.num_tokens_from_string,
        )
        self.max_tokens = 128000 if model_name == "gpt-4o-mini" else 16385
        self.query_cache = {}
        self.content_hash = None

    @staticmethod
    def num_tokens_from_string(string: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        num_tokens = len(encoding.encode(string))
        return num_tokens

    def _hash_content(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    def get_website_name(self, url: str) -> str:
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain.split('.')[0].capitalize()

    @lru_cache(maxsize=100)
    async def _cached_api_call(self, content_hash: str, query: str) -> str:
        prompt_template = get_prompt_for_model(self.model_name)
        full_prompt = prompt_template.format(webpage_content=self.preprocessed_content, query=query)
        
        if isinstance(self.model, OllamaModel):
            return await self.model.generate(prompt=full_prompt)
        else:
            chain = prompt_template | self.model
            response = await chain.ainvoke({"webpage_content": self.preprocessed_content, "query": query})
            return response.content

    async def process_query(self, user_input: str, progress_callback: Optional[Callable] = None) -> str:
        if user_input.lower().startswith("http"):
            parts = user_input.split(maxsplit=3)
            url = parts[0]
            pages = parts[1] if len(parts) > 1 and not parts[1].startswith('-') else None
            handle_captcha = '-captcha' in user_input.lower()

            website_name = self.get_website_name(url)

            if progress_callback:
                progress_callback(f"Fetching content from {website_name}...")

            response = await self._fetch_url(url, pages, handle_captcha, progress_callback)
        elif not self.current_content:
            response = "Please provide a URL first before asking for information."
        else:
            if progress_callback:
                progress_callback("Extracting information...")
            response = await self._extract_info(user_input)

        self.conversation_history.append(f"Human: {user_input}")
        self.conversation_history.append(f"AI: {response}")
        return response

    async def _fetch_url(self, url: str, pages: Optional[str] = None,
                        handle_captcha: bool = False,
                        progress_callback=None) -> str:
        self.current_url = url
        
        try:
            # Check if captcha handling is needed
            if handle_captcha:
                if progress_callback:
                    progress_callback(f"Solving CAPTCHA for {url}...")
                
                result = self._handle_captcha(url)
                if "error" in result:
                    return f"Error solving CAPTCHA: {result.get('error', 'Unknown error')}"
                
                if progress_callback:
                    progress_callback("CAPTCHA solved successfully!")
            
            if progress_callback:
                progress_callback(f"Scraping content from {url}...")
            
            # Use Scrapeless Web Unlocker to fetch the content
            unlocker_result = await self._fetch_with_unlocker(url)
            
            if "error" in unlocker_result:
                return f"Error fetching content: {unlocker_result.get('error', 'Unknown error')}"
                
            if progress_callback:
                progress_callback("Preprocessing content...")
            
            # Handle content from multiple pages if needed
            if pages:
                all_contents = await self._fetch_multiple_pages(url, pages, progress_callback)
                self.current_content = "\n".join(all_contents)
            else:
                # Extract the HTML content from the unlocker result
                self.current_content = unlocker_result.get("html", "")
            
            # Make sure content is not empty
            if not self.current_content or len(self.current_content.strip()) < 10:
                return f"Error: Received empty or minimal content from {url}"
            
            # Ensure the content is preprocessed and saved
            self.preprocessed_content = self._preprocess_content(self.current_content)
            
            # Debug info
            print(f"Content length: {len(self.current_content)}")
            print(f"Preprocessed content length: {len(self.preprocessed_content)}")
            
            new_hash = self._hash_content(self.preprocessed_content)
            if self.content_hash != new_hash:
                self.content_hash = new_hash
                self.query_cache.clear()

            return f"I've fetched and preprocessed the content from {self.current_url}" + \
                (f" (pages: {pages})" if pages else "") + \
                ". What would you like to know about it?"
                
        except Exception as e:
            return f"Error fetching content: {str(e)}"
    
    async def _fetch_with_unlocker(self, url: str) -> Dict[str, Any]:
        """Fetch content using Scrapeless Web Unlocker"""
        try:
            result = self.scrapeless.unlocker(
                actor="unlocker.webunlocker",
                input={
                    "url": url,
                    "proxy_country": self.scrapeless_config.proxy_country,
                    "method": "GET",
                    "redirect": True,  # Changed to True to follow redirects
                    "js_render": True,  # Added to ensure JavaScript rendering
                },
                proxy={
                    "country": self.scrapeless_config.proxy_country
                }
            )
            
            # Debug info
            print(f"Unlocker result keys: {result.keys() if isinstance(result, dict) else 'Not a dict'}")
            if isinstance(result, dict):
                print(f"Response structure: {json.dumps(result, indent=2)[:500]}...")
            
            if isinstance(result, dict):
                # Check for error
                if "error" in result:
                    return {"error": result.get("error", "Unknown error")}
                
                # New structure: The API returns {"code": 200, "data": {...}}
                if "code" in result and "data" in result:
                    if result["code"] == 200:
                        # Extract HTML from data field
                        data = result["data"]
                        
                        # Check for different possible structures
                        if isinstance(data, dict):
                            if "html" in data:
                                return {"html": data["html"]}
                            elif "body" in data:
                                return {"html": data["body"]}
                            elif "content" in data:
                                return {"html": data["content"]}
                            elif "response" in data and "body" in data["response"]:
                                return {"html": data["response"]["body"]}
                            else:
                                # If we can't find HTML content in any expected field, return the whole data
                                print(f"Data keys: {data.keys() if isinstance(data, dict) else 'Not a dict'}")
                                # Try to extract any text content we can find
                                for key in ["text", "content", "result", "page", "value"]:
                                    if key in data and isinstance(data[key], str):
                                        return {"html": data[key]}
                                
                                # Last resort: convert the entire data to string
                                return {"html": str(data)}
                        elif isinstance(data, str):
                            # If data is already a string, assume it's HTML
                            return {"html": data}
                        else:
                            return {"error": f"Unexpected data type in response: {type(data)}"}
                    else:
                        return {"error": f"API returned non-200 code: {result['code']}"}
                
                # Fall back to checking for direct HTML
                if "html" in result:
                    return {"html": result["html"]}
                elif "body" in result:
                    return {"html": result["body"]}
                
                # Last resort: return error
                return {"error": "Could not find HTML content in the response"}
            else:
                return {"error": f"Unexpected result type: {type(result)}"}
        except Exception as e:
            print(f"Exception in _fetch_with_unlocker: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}
    
    async def _fetch_multiple_pages(self, base_url: str, pages: str, progress_callback=None) -> List[str]:
        """Fetch content from multiple pages"""
        page_numbers = self._parse_page_numbers(pages)
        all_contents = []
        
        for page_num in page_numbers:
            if progress_callback:
                progress_callback(f"Fetching page {page_num}...")
                
            page_url = self._construct_page_url(base_url, page_num)
            unlocker_result = await self._fetch_with_unlocker(page_url)
            
            if "error" in unlocker_result:
                if progress_callback:
                    progress_callback(f"Error fetching page {page_num}: {unlocker_result.get('error', 'Unknown error')}")
                continue
                
            all_contents.append(unlocker_result.get("html", ""))
                
        return all_contents
    
    def _parse_page_numbers(self, pages: str) -> List[int]:
        """Parse page number specification (e.g. '1-5,7,9-12')"""
        page_numbers = []
        for part in pages.split(','):
            if '-' in part:
                start, end = map(int, part.split('-'))
                page_numbers.extend(range(start, end + 1))
            else:
                page_numbers.append(int(part))
        
        return sorted(set(page_numbers))
    
    def _construct_page_url(self, base_url: str, page_num: int) -> str:
        """Construct URL for pagination based on common patterns"""
        parsed_url = urlparse(base_url)
        
        # Check if URL already has pagination parameters
        if 'page=' in base_url:
            return re.sub(r'page=\d+', f'page={page_num}', base_url)
        elif 'p=' in base_url:
            return re.sub(r'p=\d+', f'p={page_num}', base_url)
        
        # If URL ends with a number, replace it
        if re.search(r'/\d+/?$', parsed_url.path):
            return re.sub(r'/\d+/?$', f'/{page_num}/', base_url)
        
        # Append page parameter
        if '?' in base_url:
            return f"{base_url}&page={page_num}"
        else:
            return f"{base_url}?page={page_num}"
    
    def _handle_captcha(self, url: str) -> Dict[str, Any]:
        """Solve CAPTCHA using Scrapeless Captcha Solver"""
        try:
            # Extract the site key (this is a simplified example)
            # In a real implementation, you would need to detect the CAPTCHA type and site key
            parsed_url = urlparse(url)
            base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
            
            result = self.scrapeless.solver_captcha(
                actor="captcha.recaptcha",
                input={
                    "version": "v2",
                    "pageURL": base_url,
                    "siteKey": "6Le-wvkSAAAAAPBMRTvw0Q4Muexq9bi0DJwx_mJ-",  # This should be extracted from the page
                    "pageAction": ""
                },
                timeout=self.scrapeless_config.timeout
            )
            
            return result
        except Exception as e:
            return {"error": str(e)}

    def _preprocess_content(self, content: str) -> str:
        soup = BeautifulSoup(content, 'html.parser')

        for script in soup(["script", "style"]):
            script.decompose()

        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
            comment.extract()

        for tag in soup(["header", "footer", "nav", "aside"]):
            tag.decompose()

        for tag in soup.find_all():
            if len(tag.get_text(strip=True)) == 0:
                tag.extract()

        text = soup.get_text()

        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        return text

    async def _extract_info(self, query: str) -> str:        
        # Debug logs
        print(f"Current URL: {self.current_url}")
        print(f"Content exists: {self.current_content is not None}")
        print(f"Preprocessed content exists: {self.preprocessed_content is not None}")
        
        if not self.preprocessed_content:
            # If the URL was processed but content wasn't saved correctly
            if self.current_url and not self.current_content:
                print(f"URL exists but content missing. Re-fetching: {self.current_url}")
                # Try to re-fetch the content
                fetch_result = await self._fetch_url(self.current_url)
                if "Error" in fetch_result:
                    return fetch_result
            else:
                return "Please provide a URL first before asking for information."

        content_hash = self._hash_content(self.preprocessed_content)
        
        if self.content_hash != content_hash:
            self.content_hash = content_hash
            self.query_cache.clear()
        
        cache_key = (content_hash, query)
        
        if cache_key in self.query_cache:
            return self.query_cache[cache_key]
        
        content_tokens = self.num_tokens_from_string(self.preprocessed_content)
        
        if content_tokens <= self.max_tokens - 1000:
            extracted_data = await self._cached_api_call(content_hash, query)
        else:
            chunks = self.optimized_text_splitter(self.preprocessed_content)
            all_extracted_data = []
            for i, chunk in enumerate(chunks):
                chunk_data = await self._cached_api_call(self._hash_content(chunk), query)
                all_extracted_data.append(chunk_data)
            extracted_data = self._merge_json_chunks(all_extracted_data)

        formatted_result = self._format_result(extracted_data, query)
        self.query_cache[cache_key] = formatted_result
        return formatted_result

    def _format_result(self, extracted_data: str, query: str) -> Union[str, Tuple[str, pd.DataFrame], BytesIO]:
        try:
            json_data = json.loads(extracted_data)
            
            if 'json' in query.lower():
                return self._format_as_json(json.dumps(json_data))
            elif 'csv' in query.lower():
                csv_string, df = self._format_as_csv(json.dumps(json_data))
                return f"```csv\n{csv_string}\n```", df
            elif 'excel' in query.lower():
                return self._format_as_excel(json.dumps(json_data))
            elif 'sql' in query.lower():
                return self._format_as_sql(json.dumps(json_data))
            elif 'html' in query.lower():
                return self._format_as_html(json.dumps(json_data))
            else:
                if isinstance(json_data, list) and all(isinstance(item, dict) for item in json_data):
                    csv_string, df = self._format_as_csv(json.dumps(json_data))
                    return f"```csv\n{csv_string}\n```", df
                else:
                    return self._format_as_json(json.dumps(json_data))
        
        except json.JSONDecodeError:
            return self._format_as_text(extracted_data)

    def optimized_text_splitter(self, text: str) -> List[str]:
        return self.text_splitter.split_text(text)

    def _merge_json_chunks(self, chunks: List[str]) -> str:
        merged_data = []
        for chunk in chunks:
            try:
                data = json.loads(chunk)
                if isinstance(data, list):
                    merged_data.extend(data)
                else:
                    merged_data.append(data)
            except json.JSONDecodeError:
                print(f"Error decoding JSON chunk: {chunk[:100]}...")
        return json.dumps(merged_data)

    def _format_as_json(self, data: str) -> str:
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, data)
        if match:
            data = match.group(1)
        try:
            parsed_data = json.loads(data)
            return f"```json\n{json.dumps(parsed_data, indent=2)}\n```"
        except json.JSONDecodeError:
            return f"Error: Invalid JSON data. Raw data: {data[:500]}..."

    def _format_as_csv(self, data: str) -> Tuple[str, pd.DataFrame]:
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, data)
        if match:
            data = match.group(1)
        else:
            code_block_pattern = r'```\s*([\s\S]*?)\s*```'
            match = re.search(code_block_pattern, data)
            if match:
                data = match.group(1)

        try:
            parsed_data = json.loads(data)
            if not parsed_data:
                return "No data to convert to CSV.", pd.DataFrame()
            
            # Generate CSV string
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=parsed_data[0].keys())
            writer.writeheader()
            writer.writerows(parsed_data)
            csv_string = output.getvalue()
            
            # Create DataFrame with clean data types
            df = pd.DataFrame(parsed_data)
            
            # Clean up data types to fix PyArrow conversion issues
            for col in df.columns:
                # Convert N/A strings to actual NaN values
                df[col] = df[col].replace('N/A', pd.NA)
                
                # Detect numeric columns and convert to appropriate types
                if pd.api.types.is_numeric_dtype(df[col]):
                    # Force numeric columns with N/A to be float (as int can't handle NaN)
                    if df[col].isna().any():
                        df[col] = pd.to_numeric(df[col], errors='coerce')
                    else:
                        # If no NaN values, try to convert to int if possible
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                            # Convert to int if all values are whole numbers
                            if (df[col] % 1 == 0).all():
                                df[col] = df[col].astype('Int64')  # Use nullable integer type
                        except:
                            pass
                else:
                    # Convert string columns to string type explicitly
                    df[col] = df[col].astype(str)
                    # Replace 'nan' strings with empty strings
                    df[col] = df[col].replace('nan', '')
            
            return csv_string, df
        except json.JSONDecodeError as e:
            error_msg = f"Error: Invalid JSON data. Raw data: {data[:500]}..."
            return error_msg, pd.DataFrame()
        except Exception as e:
            error_msg = f"Error: Failed to convert data to CSV. {str(e)}"
            return error_msg, pd.DataFrame()

    def _format_as_excel(self, data: str) -> Tuple[BytesIO, pd.DataFrame]:
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, data)
        if match:
            data = match.group(1)
        try:
            parsed_data = json.loads(data)
            if not parsed_data:
                return BytesIO(b"No data to convert to Excel."), pd.DataFrame()
            
            df = pd.DataFrame(parsed_data)
            excel_buffer = BytesIO()
            with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Sheet1')
            excel_buffer.seek(0)
            
            return excel_buffer, df
        except json.JSONDecodeError:
            error_msg = f"Error: Invalid JSON data. Raw data: {data[:500]}..."
            return BytesIO(error_msg.encode()), pd.DataFrame()
        except Exception as e:
            error_msg = f"Error: Failed to convert data to Excel. {str(e)}"
            return BytesIO(error_msg.encode()), pd.DataFrame()

    def _format_as_sql(self, data: str) -> str:
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, data)
        if match:
            data = match.group(1)
        try:
            parsed_data = json.loads(data)
            if not parsed_data:
                return "No data to convert to SQL."
            
            fields = ", ".join([f"{k} TEXT" for k in parsed_data[0].keys()])
            sql = f"CREATE TABLE extracted_data ({fields});\n"

            for row in parsed_data:
                escaped_values = [str(v).replace("'", "''") for v in row.values()]
                values = ", ".join([f"'{v}'" for v in escaped_values])
                sql += f"INSERT INTO extracted_data VALUES ({values});\n"
            
            return f"```sql\n{sql}\n```"
        except json.JSONDecodeError:
            return f"Error: Invalid JSON data. Raw data: {data[:500]}..."

    def _format_as_html(self, data: str) -> str:
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, data)
        if match:
            data = match.group(1)
        try:
            parsed_data = json.loads(data)
            if not parsed_data:
                return "No data to convert to HTML."

            html = "<table>\n<tr>\n"
            html += "".join([f"<th>{k}</th>" for k in parsed_data[0].keys()])
            html += "</tr>\n"

            for row in parsed_data:
                html += "<tr>\n"
                html += "".join([f"<td>{v}</td>" for v in row.values()])
                html += "</tr>\n"

            html += "</table>"
            
            return f"```html\n{html}\n```"
        except json.JSONDecodeError:
            return f"Error: Invalid JSON data. Raw data: {data[:500]}..."

    def _format_as_text(self, data: str) -> str:
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, data)
        if match:
            data = match.group(1)
        try:
            parsed_data = json.loads(data)
            return "\n".join([", ".join([f"{k}: {v}" for k, v in item.items()]) for item in parsed_data])
        except json.JSONDecodeError:
            return data

    def format_to_markdown(self, text: str) -> str:
        return self.markdown_formatter.to_markdown(text)

    def format_from_markdown(self, markdown_text: str) -> str:
        return self.markdown_formatter.from_markdown(markdown_text)

    @staticmethod
    async def list_ollama_models() -> List[str]:
        return await OllamaModel.list_models()