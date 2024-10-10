"""
import statistics
import time

import ollama

from web_app.backup_api.ollama_api_alt import OllamaAPI


def timer():
    start = time.perf_counter()
    return lambda: time.perf_counter() - start


def test_ollama_api():
    ollama_api = OllamaAPI()
    prompt = "hello, what's your name?"
    response = ollama_api.generate_response(prompt, model="dolphin-mixtral")
    return response


def test_ollama_module():
    prompt = "hello, what's your name?"
    response = ollama.generate(model="dolphin-mixtral", prompt=prompt)
    return response["response"]


# Warm up: Load models for both methods
print("Warming up models...")
test_ollama_api()
test_ollama_module()
print("Warm-up complete.")

# Number of iterations
n_iterations = 75

# Test OLLAMA API Method
api_times = []
for _ in range(n_iterations):
    t = timer()
    test_ollama_api()
    api_times.append(t())

# Test OLLAMA Module Method
module_times = []
for _ in range(n_iterations):
    t = timer()
    test_ollama_module()
    module_times.append(t())

# Calculate average times
avg_api_time = statistics.mean(api_times)
avg_module_time = statistics.mean(module_times)

print(f"Average OLLAMA API Method time: {avg_api_time:.4f} seconds")
print(f"Average OLLAMA Module Method time: {avg_module_time:.4f} seconds")

if avg_api_time < avg_module_time:
    print("OLLAMA API Method is faster")
elif avg_api_time > avg_module_time:
    print("OLLAMA Module Method is faster")
else:
    print("Both methods are equally fast")

# Print additional statistics
print(f"\nOLLAMA API Method:")
print(f"  Min: {min(api_times):.4f} seconds")
print(f"  Max: {max(api_times):.4f} seconds")
print(f"  Standard Deviation: {statistics.stdev(api_times):.4f} seconds")

print(f"\nOLLAMA Module Method:")
print(f"  Min: {min(module_times):.4f} seconds")
print(f"  Max: {max(module_times):.4f} seconds")
print(f"  Standard Deviation: {statistics.stdev(module_times):.4f} seconds")
"""

""""
from langchain_community.llms import Ollama

llm = Ollama(model="llama2")
response = llm.invoke("Explain partial functions in Python")
print(response)
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.web_app.api.ollama_api import OllamaAPI

api = OllamaAPI()

while True:
    prompt = input("Ask")
    if property == "bye":
        break
    print(api.generate_response(model="llama3.1:latest", prompt=prompt))
