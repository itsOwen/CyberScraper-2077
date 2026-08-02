import os
from json import JSONDecodeError
import unittest
from unittest.mock import patch

import httpx
import openai

from src.models import Models


class LiteLLMModelTests(unittest.TestCase):
    @patch.dict(
        os.environ,
        {
            "LITELLM_API_KEY": "sk-test",
            "LITELLM_BASE_URL": "http://localhost:4000/v1/",
        },
        clear=True,
    )
    def test_builds_litellm_chat_model(self):
        model = Models.get_model("litellm:proxy-model")

        self.assertEqual(model.model_name, "proxy-model")
        self.assertEqual(str(model.openai_api_base), "http://localhost:4000/v1")

    @patch.dict(os.environ, {"LITELLM_API_KEY": "sk-test"}, clear=True)
    def test_rejects_empty_litellm_model(self):
        with self.assertRaisesRegex(ValueError, "cannot be empty"):
            Models.get_model("litellm:")

    @patch.dict(os.environ, {}, clear=True)
    def test_requires_litellm_api_key(self):
        with self.assertRaisesRegex(ValueError, "LITELLM_API_KEY"):
            Models.get_model("litellm:proxy-model")


class LiteLLMTransportTests(unittest.IsolatedAsyncioTestCase):
    async def _invoke_with_handler(self, handler):
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with patch.dict(
                os.environ,
                {
                    "LITELLM_API_KEY": "sk-test",
                    "LITELLM_BASE_URL": "http://proxy.test/v1",
                },
                clear=True,
            ):
                model = Models.get_model(
                    "litellm:proxy-model",
                    max_retries=0,
                    http_async_client=client,
                )
                return await model.ainvoke("hello")

    async def test_gateway_http_errors_keep_specific_sdk_types(self):
        cases = [
            (401, openai.AuthenticationError),
            (404, openai.NotFoundError),
            (429, openai.RateLimitError),
            (400, openai.BadRequestError),
        ]
        for status, error_type in cases:
            with self.subTest(status=status):
                def handler(_request, response_status=status):
                    return httpx.Response(
                        response_status,
                        json={"error": {"message": "gateway rejected request"}},
                    )

                with self.assertRaises(error_type):
                    await self._invoke_with_handler(handler)

    async def test_timeout_is_reported_as_connection_error(self):
        def handler(request):
            raise httpx.ReadTimeout("proxy timed out", request=request)

        with self.assertRaises(openai.APIConnectionError):
            await self._invoke_with_handler(handler)

    async def test_rate_limit_is_retried_when_configured(self):
        calls = 0

        def handler(_request):
            nonlocal calls
            calls += 1
            if calls == 1:
                return httpx.Response(
                    429,
                    headers={"retry-after-ms": "1"},
                    json={"error": {"message": "rate limited"}},
                )
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-ok",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "proxy-model",
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "OK"},
                            "finish_reason": "stop",
                        }
                    ],
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with patch.dict(
                os.environ,
                {
                    "LITELLM_API_KEY": "sk-test",
                    "LITELLM_BASE_URL": "http://proxy.test/v1",
                },
                clear=True,
            ):
                model = Models.get_model(
                    "litellm:proxy-model",
                    max_retries=1,
                    http_async_client=client,
                )
                result = await model.ainvoke("hello")

        self.assertEqual(result.content, "OK")
        self.assertEqual(calls, 2)

    async def test_malformed_response_is_rejected(self):
        def handler(_request):
            return httpx.Response(
                200,
                content=b"not-json",
                headers={"Content-Type": "application/json"},
            )

        with self.assertRaises(JSONDecodeError):
            await self._invoke_with_handler(handler)

    async def test_empty_choices_are_rejected(self):
        def handler(_request):
            return httpx.Response(
                200,
                json={
                    "id": "chatcmpl-empty",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "proxy-model",
                    "choices": [],
                },
            )

        with self.assertRaises(IndexError):
            await self._invoke_with_handler(handler)

    @unittest.skipUnless(
        all(
            os.environ.get(name)
            for name in (
                "LITELLM_E2E_BASE_URL",
                "LITELLM_E2E_API_KEY",
                "LITELLM_E2E_MODEL",
            )
        ),
        "LiteLLM live E2E environment is not configured",
    )
    async def test_live_litellm_response_structure(self):
        base_url = os.environ["LITELLM_E2E_BASE_URL"]
        api_key = os.environ["LITELLM_E2E_API_KEY"]
        model_name = os.environ["LITELLM_E2E_MODEL"]
        with patch.dict(
            os.environ,
            {
                "LITELLM_API_KEY": api_key,
                "LITELLM_BASE_URL": base_url,
            },
            clear=True,
        ):
            model = Models.get_model(
                f"litellm:{model_name}", max_retries=0
            )
            result = await model.ainvoke("Reply with OK.")

        self.assertIsInstance(result.content, str)
        self.assertTrue(result.content.strip())


if __name__ == "__main__":
    unittest.main()
