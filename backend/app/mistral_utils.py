import requests

class MistralLLM:
    def __init__(self, base_url="http://localhost:11434", model_name="mistral"):
        self.base_url = base_url
        self.model_name = model_name

    def generate_answer(self, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }
        )
        response.raise_for_status()
        return response.json()["response"]