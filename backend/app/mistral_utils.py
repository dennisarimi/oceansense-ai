import json
import requests
import os
from typing import Iterator


class MistralLLM:
    def __init__(self, base_url=None, model_name="mistral"):
        self.base_url = base_url or os.getenv(
            "OLLAMA_HOST", "http://localhost:11434")
        self.model_name = model_name

    def generate_answer(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                # Cap generation length so a runaway answer can't
                # multiply the wait time.
                "options": {"num_predict": 400},
            },
            timeout=300,
        )
        response.raise_for_status()
        return response.json()["response"]

    def stream_answer(self, prompt: str) -> Iterator[str]:
        """Yield response text chunks as Ollama generates them."""
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": True,
                "options": {"num_predict": 400},
            },
            timeout=300,
            stream=True,
        )
        response.raise_for_status()
        for line in response.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            if chunk.get("response"):
                yield chunk["response"]
            if chunk.get("done"):
                break
