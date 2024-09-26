from flask import Flask, jsonify, render_template, request, send_from_directory

import ollama_api

app = Flask(__name__)


# Serve the homepage from the templates folder
@app.route("/")
def home():
    return render_template("index.html")


# API route to generate responses
@app.route("/api/generate", methods=["POST"])
def generate_response():
    try:
        # Get JSON data from the request
        data = request.get_json()
        prompt = data.get("prompt")
        model = data.get("model", "dolphin-mixtral")
        # Check if prompt is provided
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # Call the Ollama API to generate a response
        response = ollama_api.OllamaAPI().generate_response(prompt, model)

        # Check if response is valid
        if response is None:
            return jsonify({"error": "Failed to generate response"}), 500

        # Return the response as JSON
        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Serve static files such as CSS and JavaScript
@app.route("/static/<path:path>")
def serve_static_files(path):
    return send_from_directory("static", path)


if __name__ == "__main__":
    app.run(debug=True)
