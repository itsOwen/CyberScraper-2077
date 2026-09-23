import json
import unittest
from unittest.mock import AsyncMock, patch

import pandas as pd

from src.web_extractor import WebExtractor, is_export_request


def make_extractor(model_name="ollama:test-model"):
    return WebExtractor(model_name=model_name)


class ContextWindowTests(unittest.TestCase):
    def test_large_context_models(self):
        for name in ("gpt-4.1-mini", "gpt-4o-mini", "gemini-3.8-flash"):
            self.assertEqual(WebExtractor._context_window(name), 128000, name)

    def test_other_models_use_conservative_limit(self):
        for name in ("ollama:llama3.1", "litellm:proxy-model", "gpt-3.5-turbo"):
            self.assertEqual(WebExtractor._context_window(name), 16385, name)

    def test_chunks_fit_inside_the_context_window(self):
        extractor = make_extractor()
        self.assertLess(extractor.text_splitter._chunk_size, extractor.max_tokens)


class ExportDetectionTests(unittest.TestCase):
    def test_export_keywords(self):
        self.assertTrue(is_export_request("give me the products as CSV"))
        self.assertTrue(is_export_request("Download this"))

    def test_plain_question(self):
        self.assertFalse(is_export_request("what is this page about?"))


class LargePageTests(unittest.IsolatedAsyncioTestCase):
    async def _run_chunked(self, query, answers):
        extractor = make_extractor()
        extractor.preprocessed_content = "page text"
        with patch.object(extractor, "num_tokens_from_string", return_value=10**6), \
                patch.object(extractor, "optimized_text_splitter", return_value=["part 1", "part 2"]), \
                patch.object(extractor, "_call_model", AsyncMock(side_effect=answers)):
            result = await extractor._extract_info(query)
        return extractor, result

    async def test_question_about_large_page_keeps_the_answer(self):
        extractor, result = await self._run_chunked(
            "what is this page about?",
            ["It is a shop.", "It sells shoes."],
        )
        self.assertEqual(result, "It is a shop.\n\nIt sells shoes.")
        self.assertEqual(extractor.preprocessed_content, "page text")

    async def test_export_from_large_page_merges_fenced_json(self):
        _, result = await self._run_chunked(
            "export as json",
            ['```json\n[{"name": "a"}]\n```', 'Here you go: [{"name": "b"}]'],
        )
        self.assertIn('"name": "a"', result)
        self.assertIn('"name": "b"', result)

    async def test_content_is_restored_when_a_chunk_fails(self):
        extractor = make_extractor()
        extractor.preprocessed_content = "page text"
        with patch.object(extractor, "num_tokens_from_string", return_value=10**6), \
                patch.object(extractor, "optimized_text_splitter", return_value=["part 1"]), \
                patch.object(extractor, "_call_model", AsyncMock(side_effect=RuntimeError("boom"))):
            with self.assertRaises(RuntimeError):
                await extractor._extract_info("summary please")
        self.assertEqual(extractor.preprocessed_content, "page text")


class MergeJsonChunksTests(unittest.TestCase):
    def test_skips_unparseable_chunks(self):
        extractor = make_extractor()
        merged = extractor._merge_json_chunks(['[{"a": 1}]', "no data here", '{"a": 2}'])
        self.assertEqual(json.loads(merged), [{"a": 1}, {"a": 2}])


class FormatResultTests(unittest.TestCase):
    def setUp(self):
        self.extractor = make_extractor()
        self.data = '[{"name": "Widget", "price": "10"}]'

    def test_csv(self):
        text, df = self.extractor._format_result(self.data, "give me csv")
        self.assertTrue(text.startswith("```csv\nname,price"))
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)

    def test_json(self):
        result = self.extractor._format_result(self.data, "as json")
        self.assertTrue(result.startswith("```json"))

    def test_excel(self):
        buffer, df = self.extractor._format_result(self.data, "excel please")
        self.assertEqual(pd.read_excel(buffer).iloc[0]["name"], "Widget")

    def test_sql_escapes_quotes(self):
        result = self.extractor._format_result('[{"name": "O\'Reilly"}]', "sql")
        self.assertIn("'O''Reilly'", result)

    def test_conversation_is_returned_as_is(self):
        self.assertEqual(self.extractor._format_result("Just text", "what is it?"), "Just text")


class CloseTests(unittest.IsolatedAsyncioTestCase):
    async def test_close_releases_browser_and_tor_session(self):
        extractor = make_extractor()
        with patch.object(extractor.playwright_scraper, "close", AsyncMock()) as browser_close, \
                patch.object(extractor.tor_scraper.tor_manager, "close", AsyncMock()) as tor_close:
            await extractor.close()
        browser_close.assert_awaited_once()
        tor_close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
