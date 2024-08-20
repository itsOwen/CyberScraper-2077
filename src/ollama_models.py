import ollama
from typing import List, Dict, Any
import logging

class OllamaModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        self.logger.debug(f"Generating with Ollama model: {self.model_name}")
        self.logger.debug(f"Prompt (first 500 chars): {prompt[:500]}...")
        try:
            response = ollama.generate(model=self.model_name, prompt=prompt, system=system_prompt)
            self.logger.debug(f"Ollama response (first 500 chars): {response['response'][:500]}...")
            return response['response']
        except Exception as e:
            self.logger.error(f"Error generating with Ollama: {str(e)}")
            raise

    @staticmethod
    async def list_models() -> List[str]:
        logger = logging.getLogger(__name__)
        try:
            models = ollama.list()
            logger.debug(f"Available Ollama models: {models['models']}")
            return [model['name'] for model in models['models']]
        except Exception as e:
            logger.error(f"Error listing Ollama models: {str(e)}")
            return []

class OllamaModelManager:
    @staticmethod
    def get_model(model_name: str) -> OllamaModel:
        return OllamaModel(model_name)