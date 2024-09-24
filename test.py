import subprocess


def list_ollama_models():
    """List all models available in Ollama using the CLI command and return as a list of dictionaries."""
    try:
        # Run the 'ollama list' command
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, check=True
        )

        # Split the output into lines and process them
        lines = result.stdout.strip().split("\n")

        # Skip the header line and create a list of dictionaries for each model
        models = []
        for line in lines[1:]:  # Skip the header
            parts = line.split()  # Split by whitespace
            if len(parts) >= 6:  # Ensure there are enough parts (name, id, size, date)
                model_info = {
                    "name": parts[0],  # Model name
                    "id": parts[1],  # Unique identifier
                    "size": parts[2:4],  # Size of the model
                    "last_updated": parts[4:6],  # Last updated time
                }
                models.append(model_info)

        return models

    except subprocess.CalledProcessError as e:
        print(f"Error: {e.stderr.strip()}")  # Print error message if command fails
        return []


# Example usage
if __name__ == "__main__":
    models = list_ollama_models()
    print("Available Models:")
    for model in models:
        print(model)
