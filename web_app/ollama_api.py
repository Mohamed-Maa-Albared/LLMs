import subprocess

from .generate import ResponseGenerator


class OllamaAPI:
    def __init__(self, base_url="http://localhost:11434/api/generate"):
        self.generator = ResponseGenerator(base_url)

    def list_ollama_models(self):
        return self.generator.list_ollama_models()

    def generate_response(
        self, prompt, model="dolphin-mixtral", temperature=0.7, max_tokens=100
    ):
        if model == "mO1":
            return self.generator.generate_reasoning(prompt)
        return self.generator.generate_response(prompt, model, temperature, max_tokens)
