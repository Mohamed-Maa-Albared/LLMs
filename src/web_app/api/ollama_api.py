from web_app.api.generate import ResponseGenerator


class OllamaAPI:
    def __init__(self):
        self.generator = ResponseGenerator()

    def list_ollama_models(self):
        return self.generator.list_ollama_models()

    def generate_response(
        self, prompt, model="dolphin-mixtral", temperature=0.7, max_tokens=100
    ):
        if model == "mO1":
            return self.generator.generate_reasoning_mO1(prompt)
        elif model == "mO1_mini":
            return self.generator.generate_reasoning_mO1_mini(prompt)

        return self.generator.generate_response(prompt, model, temperature, max_tokens)
