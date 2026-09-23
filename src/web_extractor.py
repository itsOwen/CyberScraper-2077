from __future__ import annotations

import json
import pandas as pd
from io import StringIO, BytesIO
import re
import hashlib
import logging
import csv

import tiktoken
from bs4 import BeautifulSoup, Comment
from urllib.parse import urlparse
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .models import Models
from .ollama_models import OllamaModel, OllamaModelManager
from .scrapers.playwright_scraper import PlaywrightScraper, ScraperConfig
from .utils.error_handler import ErrorMessages, check_model_api_key
from .prompts import get_prompt_for_model
from .scrapers.tor.tor_scraper import TorScraper
from .scrapers.tor.tor_config import TorConfig
from .scrapers.tor.exceptions import TorException

logger = logging.getLogger(__name__)

# Module-level cached tiktoken encoding (singleton pattern)
_TIKTOKEN_ENCODING: tiktoken.Encoding | None = None


def _get_tiktoken_encoding() -> tiktoken.Encoding:
    """Get or create cached tiktoken encoding. Saves ~100-200ms per call."""
    global _TIKTOKEN_ENCODING
    if _TIKTOKEN_ENCODING is None:
        _TIKTOKEN_ENCODING = tiktoken.encoding_for_model("gpt-4o-mini")
    return _TIKTOKEN_ENCODING


# Precompiled regex patterns for JSON extraction
_JSON_BLOCK_PATTERN = re.compile(r'```json\s*([\s\S]*?)\s*```')
_CODE_BLOCK_PATTERN = re.compile(r'```\s*([\s\S]*?)\s*```')
# Pattern to find JSON array in text (handles arrays that might have text before/after)
_JSON_ARRAY_PATTERN = re.compile(r'\[\s*\{[\s\S]*?\}\s*\]')
# URL extraction pattern
_URL_PATTERN = re.compile(r'https?://[^\s/$.?#][^\s]*', re.IGNORECASE)


def extract_url(text: str) -> str | None:
    """Extract URL from anywhere in the text using regex."""
    match = _URL_PATTERN.search(text)
    return match.group(0) if match else None


def get_website_name(url: str) -> str:
    """Extract a clean website name from URL."""
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith('www.'):
        domain = domain[4:]
    name = domain.split('.')[0].capitalize()
    # Truncate long names (e.g., onion URLs)
    if len(name) > 15:
        name = name[:12] + "..."
    return name


_PROMPT_RESERVE_TOKENS = 4000

_EXPORT_KEYWORDS = ('csv', 'json', 'excel', 'sql', 'html', 'export', 'extract', 'give me the data', 'table', 'download', 'file')


def is_export_request(query: str) -> bool:
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in _EXPORT_KEYWORDS)


# Tags to remove during preprocessing (single pass)
_REMOVE_TAGS = frozenset(['script', 'style', 'header', 'footer', 'nav', 'aside'])

class WebExtractor:
    def __init__(
        self,
        model_name: str = "gpt-4.1-mini",
        model_kwargs: dict | None = None,
        scraper_config: ScraperConfig | None = None,
        tor_config: TorConfig | None = None
    ):
        model_kwargs = model_kwargs or {}

        # Check for required API keys before initializing
        api_key_error = check_model_api_key(model_name)
        if api_key_error:
            logger.warning(api_key_error)

        if isinstance(model_name, str) and model_name.startswith("ollama:"):
            self.model = OllamaModelManager.get_model(model_name[7:])
        elif isinstance(model_name, OllamaModel):
            self.model = model_name
        elif model_name.startswith("gemini-"):
            self.model = ChatGoogleGenerativeAI(model=model_name, **model_kwargs)
        else:
            self.model = Models.get_model(model_name, **model_kwargs)

        self.model_name = model_name
        self.scraper_config = scraper_config or ScraperConfig()
        self.playwright_scraper = PlaywrightScraper(config=self.scraper_config)
        self.current_url: str | None = None
        self.current_content: str | None = None
        self.preprocessed_content: str | None = None
        self.max_tokens = self._context_window(model_name)
        # Leave room for the prompt template, conversation history and the answer.
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.max_tokens - _PROMPT_RESERVE_TOKENS,
            chunk_overlap=200,
            length_function=self.num_tokens_from_string,
        )
        self.query_cache: dict[tuple, str] = {}
        self.content_hash: str | None = None
        self.tor_config = tor_config or TorConfig()
        self.tor_scraper = TorScraper(self.tor_config)

    @staticmethod
    def _context_window(model_name: str) -> int:
        if isinstance(model_name, str) and model_name.startswith(("gpt-4.1", "gpt-4o", "gemini-")):
            return 128000
        return 16385

    async def close(self) -> None:
        await self.playwright_scraper.close()
        await self.tor_scraper.tor_manager.close()

    @staticmethod
    def num_tokens_from_string(string: str) -> int:
        encoding = _get_tiktoken_encoding()
        return len(encoding.encode(string))

    def _hash_content(self, content: str) -> str:
        return hashlib.md5(content.encode()).hexdigest()

    def _format_conversation_history(self, conversation_history: list[dict] | None) -> str:
        """Format conversation history for the prompt."""
        if not conversation_history:
            return "No previous conversation."

        history_text = ""
        # Use last 10 messages for context
        recent_history = conversation_history[-10:]
        for msg in recent_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
            # Truncate very long messages to avoid token overflow
            if len(content) > 500:
                content = content[:500] + "..."
            history_text += f"{role}: {content}\n\n"

        return history_text.strip() if history_text else "No previous conversation."

    async def _call_model(self, query: str, conversation_history: list[dict] | None = None) -> str:
        """Call the model to extract information from preprocessed content."""
        prompt_template = get_prompt_for_model(self.model_name)

        # Format conversation history
        history_text = self._format_conversation_history(conversation_history)

        if isinstance(self.model, OllamaModel):
            full_prompt = prompt_template.format(
                conversation_history=history_text,
                webpage_content=self.preprocessed_content,
                query=query
            )
            return await self.model.generate(prompt=full_prompt)
        else:
            chain = prompt_template | self.model
            response = await chain.ainvoke({
                "conversation_history": history_text,
                "webpage_content": self.preprocessed_content,
                "query": query
            })
            return response.content

    @staticmethod
    def _is_page_spec(value: str) -> bool:
        """Check if a string is a valid page specification (e.g., '1-5', '1,3,5', '2')."""
        if not value:
            return False
        # Valid page specs contain only digits, dashes, and commas
        return all(c.isdigit() or c in '-,' for c in value) and any(c.isdigit() for c in value)

    async def _chat_without_content(self, query: str, conversation_history: list[dict] | None = None) -> str:
        """Handle chat when no URL has been scraped yet - let LLM respond naturally."""
        history_text = self._format_conversation_history(conversation_history)

        prompt = f"""You are a netrunner AI with the personality of Rebecca from Cyberpunk 2077 / Edgerunners. Keep the attitude subtle but present.

You help users scrape and extract data from websites. Currently, no URL has been provided yet.

Respond to the user's message naturally. If they're greeting you or chatting, chat back! Guide them to provide a URL when appropriate so you can start scraping.

CyberScraper-2077:
{history_text}

User: {query}"""

        if isinstance(self.model, OllamaModel):
            return await self.model.generate(prompt=prompt)
        else:
            response = await self.model.ainvoke(prompt)
            return response.content

    async def process_query(self, user_input: str, conversation_history: list[dict] | None = None, progress_callback=None) -> str:
        url = extract_url(user_input)
        if url:
            # Get text after the URL for parsing parameters
            url_match = _URL_PATTERN.search(user_input)
            text_after_url = user_input[url_match.end():].strip()

            parts = text_after_url.split(maxsplit=2)
            # Only treat as pages if it looks like a page specification (e.g., "1-5", "1,3,5")
            pages = parts[0] if len(parts) > 0 and self._is_page_spec(parts[0]) else None
            url_pattern = parts[1] if len(parts) > 1 and not parts[1].startswith('-') else None
            handle_captcha = '-captcha' in user_input.lower()

            website_name = get_website_name(url)

            if progress_callback:
                progress_callback(f"Fetching content from {website_name}...")

            response = await self._fetch_url(url, pages, url_pattern, handle_captcha, progress_callback)
        elif not self.current_content:
            # No URL yet - let LLM chat naturally
            if progress_callback:
                progress_callback("Chatting...")
            response = await self._chat_without_content(user_input, conversation_history)
        else:
            if progress_callback:
                progress_callback("Extracting information...")
            response = await self._extract_info(user_input, conversation_history)

        return response

    async def _fetch_url(self, url: str, pages: str | None = None,
                        url_pattern: str | None = None,
                        handle_captcha: bool = False,
                        progress_callback=None) -> str:
        self.current_url = url

        try:
            # Check if it's an onion URL
            if TorScraper.is_onion_url(url):
                if progress_callback:
                    progress_callback("Fetching content through Tor network...")

                content = await self.tor_scraper.fetch_content(url)
                self.current_content = content

            else:
                # Regular scraping without Tor
                if progress_callback:
                    if handle_captcha:
                        progress_callback(
                            "Solve the CAPTCHA in the browser window that just opened. "
                            "Scraping continues automatically once it's solved."
                        )
                    else:
                        progress_callback(f"Fetching content from {url}")

                # Don't use proxy for non-onion URLs
                contents = await self.playwright_scraper.fetch_content(
                    url,
                    proxy=None,  # Explicitly set proxy to None for regular URLs
                    pages=pages,
                    url_pattern=url_pattern,
                    handle_captcha=handle_captcha
                )

                # Check if scraping failed - only match if content starts with "Error:"
                # (not just contains it, as HTML pages often have "Error:" in scripts)
                if contents and any(str(c).strip().startswith("Error:") for c in contents):
                    return f"{ErrorMessages.SCRAPING_FAILED}\n\nDetails: {' '.join(contents)}"

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
            return str(e)
        except Exception as e:
            logger.error(f"Error fetching content: {str(e)}")
            return f"{ErrorMessages.SCRAPING_FAILED}\n\nDetails: {str(e)}"

    def _preprocess_content(self, content: str) -> str:
        # Use lxml parser for better performance
        soup = BeautifulSoup(content, 'lxml')

        # Single pass: remove unwanted tags and comments
        for element in soup.find_all(_REMOVE_TAGS):
            element.decompose()

        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # Remove empty tags in one pass
        for tag in soup.find_all():
            if len(tag.get_text(strip=True)) == 0:
                tag.extract()

        text = soup.get_text()

        # Efficient text cleanup using generator expressions
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        return '\n'.join(chunk for chunk in chunks if chunk)

    async def _extract_info(self, query: str, conversation_history: list[dict] | None = None) -> str:
        if not self.preprocessed_content:
            return await self._chat_without_content(query, conversation_history)

        content_hash = self._hash_content(self.preprocessed_content)

        if self.content_hash != content_hash:
            self.content_hash = content_hash
            self.query_cache.clear()

        # Cache key includes model_name to prevent cross-model cache hits
        # Note: We don't include conversation_history in cache key since conversational
        # responses should consider the full context each time
        cache_key = (content_hash, query, self.model_name)

        # Only use cache for explicit data export requests (not conversational queries)
        export_request = is_export_request(query)

        if export_request and cache_key in self.query_cache:
            return self.query_cache[cache_key]

        content_tokens = self.num_tokens_from_string(self.preprocessed_content)

        if content_tokens <= self.max_tokens - _PROMPT_RESERVE_TOKENS:
            extracted_data = await self._call_model(query, conversation_history)
        else:
            chunks = self.optimized_text_splitter(self.preprocessed_content)
            # Store original content, process chunks, restore
            original_content = self.preprocessed_content
            all_extracted_data = []
            try:
                for chunk in chunks:
                    self.preprocessed_content = chunk
                    chunk_data = await self._call_model(query, conversation_history)
                    all_extracted_data.append(chunk_data)
            finally:
                self.preprocessed_content = original_content
            if export_request:
                extracted_data = self._merge_json_chunks(all_extracted_data)
            else:
                extracted_data = "\n\n".join(part.strip() for part in all_extracted_data if part and part.strip())

        formatted_result = self._format_result(extracted_data, query)

        # Only cache export requests
        if export_request:
            self.query_cache[cache_key] = formatted_result

        return formatted_result

    def _extract_json_data(self, extracted_data: str) -> list | dict | None:
        """Try multiple methods to extract JSON data from the response."""
        # Method 1: Try direct JSON parse
        try:
            return json.loads(extracted_data)
        except json.JSONDecodeError:
            pass

        # Method 2: Try extracting from markdown code blocks
        clean_data = self._extract_json_from_markdown(extracted_data)
        if clean_data != extracted_data:
            try:
                return json.loads(clean_data)
            except json.JSONDecodeError:
                pass

        # Method 3: Try finding JSON array pattern in text
        if match := _JSON_ARRAY_PATTERN.search(extracted_data):
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return None

    def _format_result(self, extracted_data: str, query: str) -> str | tuple[str, pd.DataFrame] | BytesIO:
        query_lower = query.lower()

        # Only try to parse as JSON if user explicitly requested data export
        if is_export_request(query):
            json_data = self._extract_json_data(extracted_data)

            if json_data is not None:
                if 'json' in query_lower:
                    return self._format_as_json(json.dumps(json_data))
                elif 'csv' in query_lower or 'file' in query_lower or 'download' in query_lower:
                    csv_string, df = self._format_as_csv(json.dumps(json_data))
                    return f"```csv\n{csv_string}\n```", df
                elif 'excel' in query_lower:
                    return self._format_as_excel(json.dumps(json_data))
                elif 'sql' in query_lower:
                    return self._format_as_sql(json.dumps(json_data))
                elif 'html' in query_lower:
                    return self._format_as_html(json.dumps(json_data))
                else:
                    # For generic export keywords (export, extract, table, give me the data)
                    if isinstance(json_data, list) and all(isinstance(item, dict) for item in json_data):
                        csv_string, df = self._format_as_csv(json.dumps(json_data))
                        return f"```csv\n{csv_string}\n```", df
                    else:
                        return self._format_as_json(json.dumps(json_data))

            # If JSON extraction fails for an export request, return as-is
            return extracted_data

        # For conversational responses, return as-is (no JSON parsing)
        return extracted_data

    def optimized_text_splitter(self, text: str) -> list[str]:
        return self.text_splitter.split_text(text)

    def _merge_json_chunks(self, chunks: list[str]) -> str:
        merged_data = []
        for chunk in chunks:
            data = self._extract_json_data(chunk)
            if data is None:
                logger.warning(f"Could not parse JSON from chunk: {chunk[:100]}...")
            elif isinstance(data, list):
                merged_data.extend(data)
            else:
                merged_data.append(data)
        return json.dumps(merged_data)

    @staticmethod
    def _extract_json_from_markdown(data: str) -> str:
        """Extract JSON content from markdown code blocks using precompiled patterns."""
        if match := _JSON_BLOCK_PATTERN.search(data):
            return match.group(1)
        if match := _CODE_BLOCK_PATTERN.search(data):
            return match.group(1)
        return data

    def _format_as_json(self, data: str) -> str:
        data = self._extract_json_from_markdown(data)
        try:
            parsed_data = json.loads(data)
            return f"```json\n{json.dumps(parsed_data, indent=2)}\n```"
        except json.JSONDecodeError:
            return f"Error: Invalid JSON data. Raw data: {data[:500]}..."

    def _format_as_csv(self, data: str) -> tuple[str, pd.DataFrame]:
        data = self._extract_json_from_markdown(data)
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
        except json.JSONDecodeError:
            error_msg = f"Error: Invalid JSON data. Raw data: {data[:500]}..."
            return error_msg, pd.DataFrame()
        except Exception as e:
            error_msg = f"Error: Failed to convert data to CSV. {str(e)}"
            return error_msg, pd.DataFrame()

    def _format_as_excel(self, data: str) -> tuple[BytesIO, pd.DataFrame]:
        data = self._extract_json_from_markdown(data)
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
        data = self._extract_json_from_markdown(data)
        try:
            parsed_data = json.loads(data)
            if not parsed_data:
                return "No data to convert to SQL."

            fields = ", ".join([f"{k} TEXT" for k in parsed_data[0].keys()])
            sql_parts = [f"CREATE TABLE extracted_data ({fields});"]

            for row in parsed_data:
                escaped_values = [str(v).replace("'", "''") for v in row.values()]
                values = ", ".join([f"'{v}'" for v in escaped_values])
                sql_parts.append(f"INSERT INTO extracted_data VALUES ({values});")

            return f"```sql\n{chr(10).join(sql_parts)}\n```"
        except json.JSONDecodeError:
            return f"Error: Invalid JSON data. Raw data: {data[:500]}..."

    def _format_as_html(self, data: str) -> str:
        data = self._extract_json_from_markdown(data)
        try:
            parsed_data = json.loads(data)
            if not parsed_data:
                return "No data to convert to HTML."

            html_parts = ["<table>", "<tr>"]
            html_parts.extend([f"<th>{k}</th>" for k in parsed_data[0].keys()])
            html_parts.append("</tr>")

            for row in parsed_data:
                html_parts.append("<tr>")
                html_parts.extend([f"<td>{v}</td>" for v in row.values()])
                html_parts.append("</tr>")

            html_parts.append("</table>")

            return f"```html\n{''.join(html_parts)}\n```"
        except json.JSONDecodeError:
            return f"Error: Invalid JSON data. Raw data: {data[:500]}..."

    @staticmethod
    async def list_ollama_models() -> list[str]:
        return await OllamaModel.list_models()