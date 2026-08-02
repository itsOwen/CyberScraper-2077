"""Model factory for creating LLM instances."""

import os
from langchain_openai import ChatOpenAI, OpenAI
from langchain_core.language_models.base import BaseLanguageModel
from langchain_google_genai import ChatGoogleGenerativeAI

from .utils.error_handler import ErrorMessages, check_model_api_key


class Models:
    """Factory class for creating language model instances."""

    @staticmethod
    def get_model(model_name: str, **kwargs) -> BaseLanguageModel:
        """
        Get a language model instance based on the model name.

        Args:
            model_name: The name of the model to instantiate
            **kwargs: Additional arguments to pass to the model constructor

        Returns:
            A configured language model instance

        Raises:
            ValueError: If the model is not supported or API key is missing
        """
        # Check for required API keys before initializing
        api_key_error = check_model_api_key(model_name)
        if api_key_error:
            raise ValueError(api_key_error)

        match model_name:
            case name if name.startswith("litellm:"):
                proxy_model = name.removeprefix("litellm:").strip()
                if not proxy_model:
                    raise ValueError("LiteLLM model name cannot be empty")
                return ChatOpenAI(
                    model=proxy_model,
                    api_key=os.environ.get("LITELLM_API_KEY"),
                    base_url=os.environ.get(
                        "LITELLM_BASE_URL", "http://localhost:4000/v1"
                    ).rstrip("/"),
                    **kwargs,
                )
            case "gpt-4.1-mini" | "gpt-4o-mini" | "gpt-4" | "gpt-3.5-turbo":
                return ChatOpenAI(model_name=model_name, **kwargs)
            case name if name.startswith("text-"):
                return OpenAI(model_name=model_name, **kwargs)
            case name if name.startswith("gemini-"):
                return ChatGoogleGenerativeAI(model=model_name, **kwargs)
            case _:
                raise ValueError(f"Unsupported model: {model_name}")
