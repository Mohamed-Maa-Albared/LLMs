from ollama_api import OllamaAPI

ollama = OllamaAPI()
prompt = "Who are you?"
response = ollama.generate_response(prompt)
print(response)  # Print the generated response
