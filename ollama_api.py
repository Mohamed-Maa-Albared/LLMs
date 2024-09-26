import json

import requests


class OllamaAPI:
    def __init__(self, base_url="http://localhost:11434/api/generate"):
        self.base_url = base_url

    def generate_response(
        self,
        prompt,
        model="dolphin-mixtral",
        temperature=0.7,  # Default temperature
        max_tokens=100,  # Default max tokens (example parameter)
        headers={"Content-Type": "application/json"},
    ):
        # Create data dictionary with additional parameters
        data = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,  # Include temperature
            "max_tokens": max_tokens,  # Include max_tokens
            "stream": True,  # Enable streaming
        }

        response = requests.post(
            self.base_url, headers=headers, data=json.dumps(data), stream=True
        )

        if response.status_code != 200:
            print(f"Error: {response.status_code}, {response.text}")
            return None

        full_response = ""

        for line in response.iter_lines():
            if line:
                try:
                    json_line = json.loads(line.decode("utf-8"))
                    if json_line.get("response"):
                        full_response += json_line[
                            "response"
                        ]  # Append the response part
                    if json_line.get("done") and json_line["done"]:
                        break
                except json.JSONDecodeError:
                    print("Failed to decode JSON from line:", line)

        return full_response.strip()  # Return the complete response
