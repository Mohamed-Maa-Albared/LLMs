import ollama

response = ollama.chat(
    model="llama3.2-vision",
    messages=[
        {
            "role": "user",
            "content": "What is in this image, How does the person look, Where do you think the picture was taken?, Give me a detailed answer",
            "images": ["src/uploads/images/Mo.jpg"],
        }
    ],
)

print(response["message"]["content"])
