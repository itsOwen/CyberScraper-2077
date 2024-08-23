import requests
from typing import List, Dict, Any
import logging
import os
import json

class OllamaModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
        self.logger.debug(f"Generating with Ollama model: {self.model_name}")
        self.logger.debug(f"Prompt (first 500 chars): {prompt[:500]}...")
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False
                },
                stream=True
            )
            response.raise_for_status()
            
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if 'response' in data:
                            full_response += data['response']
                    except json.JSONDecodeError:
                        self.logger.warning(f"Failed to parse JSON: {line}")
            
            self.logger.debug(f"Ollama response (first 500 chars): {full_response[:500]}...")
            return full_response
        except Exception as e:
            self.logger.error(f"Error generating with Ollama: {str(e)}")
            raise

    @staticmethod
    async def list_models() -> List[str]:
        logger = logging.getLogger(__name__)
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        try:
            response = requests.get(f"{base_url}/api/tags")
            response.raise_for_status()
            models = response.json()
            logger.debug(f"Available Ollama models: {models['models']}")
            return [model['name'] for model in models['models']]
        except Exception as e:
            logger.error(f"Error listing Ollama models: {str(e)}")
            return []

class OllamaModelManager:
    @staticmethod
    def get_model(model_name: str) -> OllamaModel:
        return OllamaModel(model_name)