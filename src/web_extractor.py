import asyncio
from typing import Dict, Any, Optional, List
import json
import pandas as pd
from io import BytesIO
import re
from .models import Models
from .scrapers import PlaywrightScraper, HTMLScraper, JSONScraper
from .utils.proxy_manager import ProxyManager
from .utils.markdown_formatter import MarkdownFormatter
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnableSequence
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
import time

class WebExtractor:
    def __init__(self, model_name: str = "gpt-4o-mini", model_kwargs: Dict[str, Any] = None, proxy: Optional[str] = None):
        model_kwargs = model_kwargs or {}
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

    @staticmethod
    def num_tokens_from_string(string: str) -> int:
        encoding = tiktoken.encoding_for_model("gpt-4o-mini")
        num_tokens = len(encoding.encode(string))
        return num_tokens

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
        return f"I've fetched and preprocessed the content from {self.current_url}. What would you like to know about it?"

    def _preprocess_content(self, content: str) -> str:
        content = re.sub(r'<script\b[^>]*>[\s\S]*?</script>', '', content)
        content = re.sub(r'<style\b[^>]*>[\s\S]*?</style>', '', content)
        content = re.sub(r'<!--[\s\S]*?-->', '', content)
        content = re.sub(r'<(?!/?(?:table|tr|th|td|thead|tbody|ul|ol|li|p|h[1-6]|br|hr)[>\s])\/?[^>]*>', '', content)
        content = re.sub(r'\s+', ' ', content)
        return content.strip()

    async def _extract_info(self, query: str) -> str:
        content_tokens = self.num_tokens_from_string(self.preprocessed_content)
        
        extraction_prompt = PromptTemplate(
            input_variables=["webpage_content", "query"],
            template="""You are an AI assistant that helps with web scraping tasks. 
            Based on the following preprocessed webpage content and the user's request, extract the relevant information.
            Present the data in a structured format as specified by the user's query:
            - If the user asks for JSON, respond with a JSON array of objects.
            - If the user asks for CSV, respond with CSV data (including headers).
            - If the user asks for Excel, respond with data in a tabular format suitable for Excel.
            - If the user asks for SQL, respond with a SQL table format including `CREATE TABLE` and `INSERT INTO` statements.
            - If the user asks for HTML, respond with an HTML table format.
            - If no format is specified, present the data as a list of dictionaries.

            Include all requested fields, and if a field is not found, use "N/A" as the value.
            Do not invent or fabricate any data. If the information is not present, use "N/A".
            If the user specifies a number of entries to extract, limit your response to that number.
            If the user asks for all extractable data, provide all entries you can find.
            Ensure that the extracted data accurately reflects the content of the webpage.
            
            Preprocessed webpage content:
            {webpage_content}
            
            Human: {query}
            AI: """
        )

        if content_tokens <= self.max_tokens - 1000:
            chain = RunnableSequence(extraction_prompt | self.model)
            response = await chain.ainvoke({"webpage_content": self.preprocessed_content, "query": query})
            extracted_data = response.content
        else:
            chunks = self.optimized_text_splitter(self.preprocessed_content)
            all_extracted_data = []
            for chunk in chunks:
                chain = RunnableSequence(extraction_prompt | self.model)
                response = await chain.ainvoke({"webpage_content": chunk, "query": query})
                all_extracted_data.append(response.content)
            extracted_data = "\n".join(all_extracted_data)

        if 'json' in query.lower():
            return self._format_as_json(extracted_data)
        elif 'csv' in query.lower():
            return self._format_as_csv(extracted_data)
        elif 'excel' in query.lower():
            return self._format_as_excel_and_save(extracted_data)
        else:
            return self._format_as_text(extracted_data)

    def optimized_text_splitter(self, text: str) -> List[str]:
        return self.text_splitter.split_text(text)

    def _format_as_json(self, data: str) -> str:
        return data

    def _format_as_csv(self, data: str) -> str:
        return data

    def _format_as_excel_and_save(self, data: str) -> str:
        try:
            lines = data.strip().split('\n')
            rows = [line.split('|') for line in lines if line.strip()]
            df = pd.DataFrame(rows[1:], columns=[col.strip() for col in rows[0]])
            output_filename = "output.xlsx"
            with pd.ExcelWriter(output_filename, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            return f"Excel data saved to {output_filename}"
        except Exception as e:
            return f"Error: Unable to convert to Excel format. {str(e)}. Raw data: {data[:500]}..."

    def _format_as_text(self, data: str) -> str:
        try:
            parsed_data = json.loads(data)
            return json.dumps(parsed_data, indent=2)
        except json.JSONDecodeError:
            return data

    async def save_data(self, filename: str) -> str:
        if not self.current_content:
            return "No data to save. Please fetch a webpage first."
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(self.current_content)
        return f"Data saved to {filename}"

    def format_to_markdown(self, text: str) -> str:
        return self.markdown_formatter.to_markdown(text)

    def format_from_markdown(self, markdown_text: str) -> str:
        return self.markdown_formatter.from_markdown(markdown_text)