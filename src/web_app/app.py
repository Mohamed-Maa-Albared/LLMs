import os
import sys
from datetime import datetime

from werkzeug.utils import secure_filename

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


from flask import Flask, jsonify, render_template, request, send_from_directory

from web_app.api.ollama_api import OllamaAPI

# Get the current directory of the script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define paths for templates and static folders
template_folder = os.path.join(current_dir, "../templates")
static_folder = os.path.join(current_dir, "../static")

# Initialize the Flask app with specified folders
app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)

api = OllamaAPI()

UPLOAD_FOLDER = os.path.join(current_dir, "../uploads")
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "wav", "mp3"}

# Create upload folders if they don't exist
for folder in ["files", "images", "screenshots", "voice"]:
    folder_path = os.path.join(UPLOAD_FOLDER, folder)
    os.makedirs(folder_path, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size


# Serve the homepage from the templates folder
@app.route("/")
def home():
    return render_template("index.html")


# API route to fetch available models
@app.route("/api/models", methods=["GET"])
def get_models():
    try:
        models = api.list_ollama_models()
        return jsonify(models)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# API route to generate responses
@app.route("/api/generate", methods=["POST"])
def generate_response():
    try:
        # Get JSON data from the request
        data = request.get_json()
        prompt = data.get("prompt")
        model = data.get("model", "dolphin-mixtral")
        temperature = data.get("temperature", 0.7)
        # Check if prompt is provided
        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        # Call the Ollama API to generate a response
        response = api.generate_response(prompt, model, temperature)

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


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/upload/<type>", methods=["POST"])
def upload_file(type):
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        # Create a timestamp-based filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = secure_filename(f"{timestamp}_{file.filename}")

        # Determine the appropriate subfolder based on type
        subfolder = type  # 'files', 'images', 'screenshots', or 'voice'
        upload_path = os.path.join(app.config["UPLOAD_FOLDER"], subfolder)

        # Save the file
        file_path = os.path.join(upload_path, filename)
        file.save(file_path)

        return jsonify(
            {
                "message": "File uploaded successfully",
                "filename": filename,
                "path": f"/uploads/{subfolder}/{filename}",
            }
        )

    return jsonify({"error": "File type not allowed"}), 400


# Add a route to serve uploaded files
@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(debug=True)
