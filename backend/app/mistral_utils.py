import json
import requests
import os
from typing import Dict, Iterator, List


class MistralLLM:
    def __init__(self, base_url=None, model_name="mistral"):
        self.base_url = base_url or os.getenv(
            "OLLAMA_HOST", "http://localhost:11434")
        self.model_name = model_name

    def generate_answer(self, messages: List[Dict[str, str]]) -> str:
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model_name,
                "messages": messages,
                "stream": False,
            },
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["message"]["content"]

    def stream_answer(self, messages: List[Dict[str, str]]) -> Iterator[str]:
        """Yield response text chunks as Ollama generates them."""
        response = requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model_name,
                "messages": messages,
                "stream": True,
            },
            timeout=300,
            stream=True,
        )
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            content = chunk.get("message", {}).get("content")
            if content:
                yield content
            if chunk.get("done"):
                break
