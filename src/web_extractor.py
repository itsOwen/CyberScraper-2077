import asyncio
from typing import Dict, Any, Optional, List, Tuple
import json
import pandas as pd
from io import StringIO
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
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableSequence
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
import logging
import csv
from bs4 import BeautifulSoup, Comment

class WebExtractor:
    def __init__(self, model_name: str = "gpt-4o-mini", model_kwargs: Dict[str, Any] = None, proxy: Optional[str] = None):
        model_kwargs = model_kwargs or {}
        if isinstance(model_name, str) and model_name.startswith("ollama:"):
            self.model = OllamaModelManager.get_model(model_name[7:])
        elif isinstance(model_name, OllamaModel):
            self.model = model_name
        else:
            self.model = Models.get_model(model_name, **model_kwargs)
        
        self.playwright_scraper = PlaywrightScraper()
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
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.query_cache = {}
        self.content_hash = None

    @staticmethod
    def num_tokens_from_string(string: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        num_tokens = len(encoding.encode(string))
        return num_tokens

    def _hash_content(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    @lru_cache(maxsize=100)
    async def _cached_api_call(self, content_hash: str, query: str) -> str:
        if isinstance(self.model, OllamaModel):
            prompt_template = self._prepare_prompt(self.preprocessed_content, query)
            full_prompt = prompt_template.format(webpage_content=self.preprocessed_content, query=query)
            return await self.model.generate(prompt=full_prompt)
        else:
            prompt_template = self._prepare_prompt(self.preprocessed_content, query)
            chain = prompt_template | self.model
            response = await chain.ainvoke({"webpage_content": self.preprocessed_content, "query": query})
            return response.content

    def _prepare_prompt(self, content: str, query: str) -> PromptTemplate:
        return PromptTemplate(
            input_variables=["webpage_content", "query"],
            template="""You are an AI assistant that helps with web scraping tasks. 
            Based on the following preprocessed webpage content and the user's request, extract the relevant information.
            Always present the data as a JSON array of objects, regardless of the user's requested format.
            Each object in the array should represent one item or row of data.
            Use the following format without any unnecessary text, provide only the format and nothing else:
            
            [
            {{
                "field1": "value1",
                "field2": "value2"
            }},
            {{
                "field1": "value1",
                "field2": "value2"
            }}
            ]

            If the user asks for information about the data on the webpage, explain about the data in bullet points and how can we use it, and provide further information if asked.
            Include all requested fields. If a field is not found, use "N/A" as the value.
            Do not invent or fabricate any data. If the information is not present, use "N/A".
            If the user specifies a number of entries to extract, limit your response to that number.
            If the user asks for all extractable data, provide all entries you can find.
            Ensure that the extracted data accurately reflects the content of the webpage.
            Use appropriate field names based on the webpage content and the user's query.
            
            Preprocessed webpage content:
            {webpage_content}
            
            Human: {query}
            AI: """
        )

    async def process_query(self, user_input: str) -> str:
        if user_input.lower().startswith("http"):
            response = await self._fetch_url(user_input)
        elif not self.current_content:
            response = "Please provide a URL first before asking for information."
        else:
            response = await self._extract_info(user_input)
        
        self.conversation_history.append(f"Human: {user_input}")
        self.conversation_history.append(f"AI: {response}")
        return response

    async def _fetch_url(self, url: str) -> str:
        self.current_url = url
        proxy = await self.proxy_manager.get_proxy()
        self.current_content = await self.playwright_scraper.fetch_content(self.current_url, proxy)
        self.preprocessed_content = self._preprocess_content(self.current_content)
        
        new_hash = self._hash_content(self.preprocessed_content)
        if self.content_hash != new_hash:
            self.content_hash = new_hash
            self.query_cache.clear()
        
        return f"I've fetched and preprocessed the content from {self.current_url}. What would you like to know about it?"

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
        self.logger.debug(f"Extracting info with model: {self.model}")
        
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
            self.logger.debug(f"Content split into {len(chunks)} chunks")
            all_extracted_data = []
            for i, chunk in enumerate(chunks):
                chunk_data = await self._cached_api_call(self._hash_content(chunk), query)
                all_extracted_data.append(chunk_data)
            extracted_data = self._merge_json_chunks(all_extracted_data)

        self.logger.debug(f"Extracted data (first 500 chars): {extracted_data[:500]}...")

        formatted_result = self._format_result(extracted_data, query)
        self.query_cache[cache_key] = formatted_result
        return formatted_result

    def _format_result(self, extracted_data: str, query: str) -> str:
        if 'json' in query.lower():
            return self._format_as_json(extracted_data)
        elif 'csv' in query.lower():
            csv_string, df = self._format_as_csv(extracted_data)
            return f"```csv\n{csv_string}\n```", df
        elif 'excel' in query.lower():
            return self._format_as_excel_and_save(extracted_data)
        elif 'sql' in query.lower():
            return self._format_as_sql(extracted_data)
        elif 'html' in query.lower():
            return self._format_as_html(extracted_data)
        else:
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
                self.logger.error(f"Failed to parse JSON chunk: {chunk[:100]}...")
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
            self.logger.error(f"JSON Decode Error: {str(e)}")
            error_msg = f"Error: Invalid JSON data. Raw data: {data[:500]}..."
            return error_msg, pd.DataFrame()
        except Exception as e:
            self.logger.error(f"Unexpected error in _format_as_csv: {str(e)}")
            error_msg = f"Error: Failed to convert data to CSV. {str(e)}"
            return error_msg, pd.DataFrame()

    def _format_as_excel_and_save(self, data: str) -> str:
        json_pattern = r'```json\s*([\s\S]*?)\s*```'
        match = re.search(json_pattern, data)
        if match:
            data = match.group(1)
        try:
            parsed_data = json.loads(data)
            if not parsed_data:
                return "No data to convert to Excel."
            
            df = pd.DataFrame(parsed_data)
            output_filename = "output.xlsx"
            with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            return f"Excel data saved to {output_filename}"
        except json.JSONDecodeError:
            return f"Error: Invalid JSON data. Raw data: {data[:500]}..."
        except Exception as e:
            return f"Error: Failed to convert data to Excel. {str(e)}"

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