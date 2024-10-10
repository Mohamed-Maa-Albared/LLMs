import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache


class OllamaModelManager:
    def __init__(self):
        self.custom_models = []
        self.last_fetch_time = 0
        self.cache_duration = 60  # Cache duration in seconds

    @lru_cache(maxsize=None)
    def _run_ollama_command(self, command):
        """Run an Ollama command and return the result."""
        try:
            result = subprocess.run(
                command.split(), capture_output=True, text=True, check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            print(f"Error running command {command}: {e}")
            return ""

    def _parse_model_line(self, line):
        """Parse a single line of Ollama output into a model dictionary."""
        parts = line.split()
        if len(parts) >= 7:
            return {
                "name": parts[0],
                "id": parts[1],
                "size": " ".join(parts[2:4]),
                "last_updated": " ".join(parts[4:7]),
            }
        return None

    def _fetch_ollama_models(self):
        """Fetch Ollama models using the CLI command."""
        output = self._run_ollama_command("ollama list")
        lines = output.split("\n")[1:]  # Skip the header line
        return [
            self._parse_model_line(line)
            for line in lines
            if self._parse_model_line(line)
        ]

    def add_custom_model(self, model):
        """Add a custom model to the list."""
        self.custom_models.append(model)

    def list_ollama_models(self, force_refresh=False):
        """List all models available in Ollama and custom models."""
        current_time = time.time()
        if force_refresh or (current_time - self.last_fetch_time > self.cache_duration):
            with ThreadPoolExecutor() as executor:
                future = executor.submit(self._fetch_ollama_models)
                ollama_models = future.result()
            self.last_fetch_time = current_time
        else:
            ollama_models = self._fetch_ollama_models()

        all_models = ollama_models + self.custom_models
        return all_models

    def sort_models(self, models, key="name", reverse=False):
        """Sort the models based on a specified key."""
        return sorted(models, key=lambda x: x[key], reverse=reverse)

    def filter_models(self, models, **kwargs):
        """Filter out models based on multiple criteria."""
        return [
            model
            for model in models
            if all(model.get(k) != v for k, v in kwargs.items())
        ]

    def to_json(self, models):
        """Convert models to JSON format."""
        return json.dumps(models, indent=2)
