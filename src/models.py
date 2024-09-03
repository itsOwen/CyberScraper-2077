from langchain_openai import ChatOpenAI
from langchain_openai import OpenAI
from langchain.base_language import BaseLanguageModel
import google.generativeai as genai
import os
from langchain_google_genai import ChatGoogleGenerativeAI

class Models:
    @staticmethod
    def get_model(model_name: str, **kwargs) -> BaseLanguageModel:
        if model_name in ["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"]:
            return ChatOpenAI(model_name=model_name, **kwargs)
        elif model_name.startswith("text-"):
            return OpenAI(model_name=model_name, **kwargs)
        elif model_name.startswith("gemini-"):
            return ChatGoogleGenerativeAI(model=model_name, **kwargs)
        else:
            raise ValueError(f"Unsupported model: {model_name}")