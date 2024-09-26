#from ollama_api import OllamaAPI

#ollama = OllamaAPI()
#prompt = "Who are you?"
#response = ollama.generate_response(prompt)
#print(response)  # Print the generated response

import ollama

# Generate text using the model
response = ollama.generate(model='llama3.1', 
                           prompt='What is a qubit?')

print(response['response'])

""""
from langchain_community.llms import Ollama

llm = Ollama(model="llama2")
response = llm.invoke("Explain partial functions in Python")
print(response)
"""