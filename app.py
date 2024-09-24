from flask import Flask, jsonify, request, send_from_directory

import ollama_api

app = Flask(__name__)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/api/generate", methods=["POST"])
def generate_response():
    try:
        # Get JSON data from the request
        data = request.get_json()
        prompt = data.get("prompt")
        model = data.get("model", "llama3")

        # Check if prompt is provided
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # Prepare headers
        headers = {"Content-Type": "application/json"}

        # Call the Ollama API to generate a response
        response = ollama_api.OllamaAPI().generate_response(prompt, model, headers)

        # Check if response is valid
        if response is None:
            return jsonify({"error": "Failed to generate response"}), 500

        # Return the response as JSON
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
