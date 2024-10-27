from typing import Dict, Any, Optional, List, Tuple, Union
import json
import pandas as pd
from io import StringIO, BytesIO
import base64
import re
from functools import lru_cache
import hashlib
from .models import Models
from .ollama_models import OllamaModel, OllamaModelManager
from .scrapers.playwright_scraper import PlaywrightScraper
from .scrapers.html_scraper import HTMLScraper
from .scrapers.json_scraper import JSONScraper
from .utils.proxy_manager import ProxyManager
from .utils.markdown_formatter import MarkdownFormatter
from .prompts import get_prompt_for_model
from langchain.schema.runnable import RunnableSequence
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
import csv
from bs4 import BeautifulSoup, Comment
from .scrapers.playwright_scraper import PlaywrightScraper, ScraperConfig
from urllib.parse import urlparse
import streamlit as st
import os
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from .scrapers.tor.tor_scraper import TorScraper
from .scrapers.tor.tor_config import TorConfig
from .scrapers.tor.exceptions import TorException

class WebExtractor:
    def __init__(self, model_name: str = "gpt-4o-mini", model_kwargs: Dict[str, Any] = None, 
                 proxy: Optional[str] = None, scraper_config: ScraperConfig = None,
                 tor_config: TorConfig = None):
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
        self.scraper_config = scraper_config or ScraperConfig()
        self.playwright_scraper = PlaywrightScraper(config=self.scraper_config)
        self.html_scraper = HTMLScraper()
        self.json_scraper = JSONScraper()
        self.proxy_manager = ProxyManager(proxy)
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
        self.tor_config = tor_config or TorConfig()
        self.tor_scraper = TorScraper(self.tor_config)

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

    async def process_query(self, user_input: str, progress_callback=None) -> str:
        if user_input.lower().startswith("http"):
            parts = user_input.split(maxsplit=3)
            url = parts[0]
            pages = parts[1] if len(parts) > 1 and not parts[1].startswith('-') else None
            url_pattern = parts[2] if len(parts) > 2 and not parts[2].startswith('-') else None
            handle_captcha = '-captcha' in user_input.lower()

            website_name = self.get_website_name(url)

            if progress_callback:
                progress_callback(f"Fetching content from {website_name}...")

            response = await self._fetch_url(url, pages, url_pattern, handle_captcha, progress_callback)
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
                        url_pattern: Optional[str] = None, 
                        handle_captcha: bool = False, 
                        progress_callback=None) -> str:
        self.current_url = url
        
        try:
            # Check if it's an onion URL using the static method
            if TorScraper.is_onion_url(url):
                if progress_callback:
                    progress_callback("Fetching content through Tor network...")
                
                content = await self.tor_scraper.fetch_content(url)
                self.current_content = content
                
            else:
                # Existing regular scraping logic
                proxy = await self.proxy_manager.get_proxy()
                contents = await self.playwright_scraper.fetch_content(
                    url, proxy, pages, url_pattern, handle_captcha
                )
                self.current_content = "\n".join(contents)
            
            if progress_callback:
                progress_callback("Preprocessing content...")
            
            self.preprocessed_content = self._preprocess_content(self.current_content)
            
            new_hash = self._hash_content(self.preprocessed_content)
            if self.content_hash != new_hash:
                self.content_hash = new_hash
                self.query_cache.clear()

            source_type = "Tor network" if TorScraper.is_onion_url(url) else "regular web"
            return f"I've fetched and preprocessed the content from {self.current_url} via {source_type}" + \
                (f" (pages: {pages})" if pages else "") + \
                ". What would you like to know about it?"
                
        except TorException as e:
            return f"Error accessing onion service: {str(e)}"
        except Exception as e:
            return f"Error fetching content: {str(e)}"

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
        if not self.preprocessed_content:
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
            
            output = StringIO()
            writer = csv.DictWriter(output, fieldnames=parsed_data[0].keys())
            writer.writeheader()
            writer.writerows(parsed_data)
            csv_string = output.getvalue()
            
            df = pd.DataFrame(parsed_data)
            
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