import json

import requests


class OllamaAPI:
    def __init__(self, base_url="http://localhost:11434/api/generate"):
        self.base_url = base_url  # Print error message if command fails

    def generate_response(
        self, prompt, model="llama3", headers={"Content-Type": "application/json"}
    ):
        data = {"model": model, "prompt": prompt, "stream": True}  # Enable streaming
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
