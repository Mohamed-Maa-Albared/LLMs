Ollama API Client
=====================

This is a Python script that serves as a client to interact with the Ollama API. It allows you to generate responses from various AI models using the generate_response method.

Installation
To run this app, you'll need to install the necessary libraries. You can do this by running:

pip install requests
Running the App
Once installed, you can run the app by executing:

python ollama_api.py
The script will start a client that connects to the Ollama API at http://localhost:11434/api/generate. You can use this client to generate responses from various AI models.

Using the Client
To use the client, you'll need to import the OllamaAPI class and create an instance of it. Then, you can call the generate_response method with your prompt and model of choice.

Here's an example:

from ollama_api import OllamaAPI

api = OllamaAPI()
response = api.generate_response("Hello, how are you?", "llama3.1:70b")
print(response)
Endpoints
This client has one endpoint:

/api/generate
: Accepts a JSON payload with the following properties:
prompt
: The text prompt to generate a response for.
model
: The AI model to use (default is
llama3.1:70b
). You can find more information about available models in the Ollama API documentation.
Error Handling
The client will return error messages as JSON responses if there's an issue generating a response or processing the request. Common errors include:

"error": "Prompt is required"
: No prompt was provided.
"error": "Failed to generate response"
: An unexpected error occurred while generating the response.