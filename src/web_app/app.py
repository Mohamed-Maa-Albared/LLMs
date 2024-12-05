import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from flask import Flask, jsonify, render_template, request, send_from_directory
from werkzeug.utils import secure_filename

# Import custom API module
from web_app.api.ollama_api import OllamaAPI

# Define constants for file paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_FOLDER = os.path.join(CURRENT_DIR, "../templates")
STATIC_FOLDER = os.path.join(CURRENT_DIR, "../static")
UPLOAD_FOLDER = os.path.join(CURRENT_DIR, "../uploads")

# Create Flask app instance with specified folders
app = Flask(__name__, template_folder=TEMPLATES_FOLDER, static_folder=STATIC_FOLDER)
api = OllamaAPI()

# Configure upload folder and maximum file size
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB

# Define allowed file extensions
ALLOWED_EXTENSIONS = {"txt", "pdf", "png", "jpg", "jpeg", "gif", "wav", "mp3"}

# Create upload subfolders if they don't exist
for folder in ["files", "images", "screenshots", "voice"]:
    os.makedirs(os.path.join(UPLOAD_FOLDER, folder), exist_ok=True)


@app.route("/")
def home():
    """Render the homepage."""
    return render_template("index.html")


@app.route("/api/models", methods=["GET"])
def get_models():
    """
    Fetch and return a list of available models.

    Returns:
        JSON response with model data or error message.
    """
    try:
        models = api.list_ollama_models()
        return jsonify(models)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/generate", methods=["POST"])
def generate_response():
    """
    Generate a response based on the provided prompt.

    Returns:
        JSON response with generated text or error message.
    """
    try:
        data = request.get_json()
        prompt = data.get("prompt")
        model = data.get("model", "dolphin-mixtral")
        temperature = data.get("temperature", 0.7)

        if not prompt:
            return jsonify({"error": "Prompt is required"}), 400

        response = api.generate_response(prompt, model, temperature)
        if response is None:
            return jsonify({"error": "Failed to generate response"}), 500

        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/static/<path:path>")
def serve_static_files(path):
    """
    Serve static files from the specified path.

    Args:
        path (str): Path to the static file.

    Returns:
        The requested static file.
    """
    return send_from_directory("static", path)


def allowed_file(filename):
    """
    Check if the file has an allowed extension.

    Args:
        filename (str): Name of the file.

    Returns:
        bool: True if the file is allowed, False otherwise.
    """
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/api/upload/<type>", methods=["POST"])
def upload_file(type):
    """
    Handle file uploads to specified type folders.

    Args:
        type (str): Type of the folder where the file should be uploaded.

    Returns:
        JSON response with success message or error details.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = secure_filename(f"{timestamp}_{file.filename}")
        upload_path = os.path.join(UPLOAD_FOLDER, type)

        # Ensure the subfolder exists
        os.makedirs(upload_path, exist_ok=True)

        file_path = os.path.join(upload_path, filename)
        file.save(file_path)

        return jsonify(
            {
                "message": "File uploaded successfully",
                "filename": filename,
                "path": f"/uploads/{type}/{filename}",
            }
        )

    return jsonify({"error": "File type not allowed"}), 400


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    """
    Serve uploaded files.

    Args:
        filename (str): Name of the file to serve.

    Returns:
        The requested uploaded file.
    """
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)


if __name__ == "__main__":
    app.run(debug=True)
