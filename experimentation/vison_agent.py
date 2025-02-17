import ollama


def analyze_image(user_prompt, image_path):
    model_name = "llama3.2-vision"

    response = ollama.chat(
        model=model_name,
        messages=[
            {
                "role": "user",
                "content": user_prompt,
                "images": [image_path],
            }
        ],
    )
    return response


# Example usage
image_path = "src/uploads/images/Mo.jpg"
user_prompt = (
    "What is in this image? How does the person look? "
    "Where do you think the picture was taken? "
    "Give me a detailed answer."
)
response = analyze_image(user_prompt, image_path)

print(response["message"]["content"])
