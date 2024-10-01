import timeit

import ollama

from ollama_api import OllamaAPI


def test_ollama_api():
    ollama = OllamaAPI()
    prompt = "Who are you?"
    response = ollama.generate_response("Just say yes", model="dolphin-mixtral")
    return response


def test_ollama_module():
    response = ollama.generate(model="dolphin-mixtral", prompt="Just say yes")
    return response["response"]

api_time = timeit.timeit(test_ollama_api, number=20)
module_time = timeit.timeit(test_ollama_module, number=20)

print("OLLAMA API Method:", api_time)
print("OLLAMA Module Method:", module_time)

if api_time < module_time:
    print("OLLAMA API Method is faster")
elif api_time > module_time:
    print("OLLAMA Module Method is faster")
else:
    print("Both methods are equally fast")

""""
from langchain_community.llms import Ollama

llm = Ollama(model="llama2")
response = llm.invoke("Explain partial functions in Python")
print(response)
"""
