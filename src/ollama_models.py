import requests
from typing import List, Dict, Any
import os
import json

class OllamaModel:
    def __init__(self, model_name: str):
        self.model_name = model_name
        self.base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')

    async def generate(self, prompt: str, system_prompt: str = "") -> str:
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
                        print(f"Error decoding JSON: {line}")
            
            return full_response
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            raise

    @staticmethod
    async def list_models() -> List[str]:
        base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
        try:
            response = requests.get(f"{base_url}/api/tags")
            response.raise_for_status()
            models = response.json()
            return [model['name'] for model in models['models']]
        except Exception as e:
            return []

class OllamaModelManager:
    @staticmethod
    def get_model(model_name: str) -> OllamaModel:
        return OllamaModel(model_name)