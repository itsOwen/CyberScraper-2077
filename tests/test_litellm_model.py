import os
import unittest
from unittest.mock import patch

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


if __name__ == "__main__":
    unittest.main()
